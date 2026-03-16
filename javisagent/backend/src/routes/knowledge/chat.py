import json
import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from src.models import get_db
from src.models.knowledge import KnowledgeBase, Conversation, Message
from src.schemas.knowledge import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse, ConversationUpdate
from src.services.knowledge import EmbeddingService, LLMService, HybridRetriever, MilvusVectorStore
from src.services.knowledge.rag_strategies import RAGConfig, RetrievalStrategy, ChunkingStrategy

logger = logging.getLogger("routes.knowledge.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _parse_rag_config(config_dict: dict) -> RAGConfig:
    """解析RAG配置字典为RAGConfig对象"""
    if not config_dict:
        return RAGConfig()

    # 获取检索策略
    retrieval_strategy = RetrievalStrategy(config_dict.get("retrieval_strategy", "hybrid"))

    # 如果检索策略是 graph_rag，自动启用 use_graph_rag
    use_graph_rag = config_dict.get("use_graph_rag", False)
    if retrieval_strategy == RetrievalStrategy.GRAPH_RAG:
        use_graph_rag = True

    return RAGConfig(
        chunking_strategy=ChunkingStrategy(config_dict.get("chunking_strategy", "fixed")),
        retrieval_strategy=retrieval_strategy,
        chunk_size=config_dict.get("chunk_size", 500),
        chunk_overlap=config_dict.get("chunk_overlap", 100),
        parent_chunk_size=config_dict.get("parent_chunk_size", 2000),
        child_chunk_size=config_dict.get("child_chunk_size", 200),
        semantic_threshold=config_dict.get("semantic_threshold", 0.5),
        use_chinese_tokenizer=config_dict.get("use_chinese_tokenizer", True),
        use_contextual_embedding=config_dict.get("use_contextual_embedding", False),
        use_hyde=config_dict.get("use_hyde", False),
        use_multi_query=config_dict.get("use_multi_query", False),
        multi_query_count=config_dict.get("multi_query_count", 3),
        use_graph_rag=use_graph_rag,
        graph_rag_llm_model=config_dict.get("graph_rag_llm_model", "gpt-4o"),
    )


# 意图分类 Prompt
INTENT_CLASSIFICATION_PROMPT = """判断用户消息是否需要查询知识库。

用户消息: {message}

分类规则:
- "chitchat": 问候、寒暄、闲聊、感谢、告别、询问助手身份等不需要知识库的对话
- "query": 需要从知识库检索信息才能回答的问题

只回复一个单词: chitchat 或 query"""

# 闲聊回复 Prompt
CHITCHAT_PROMPT = """你是一个友好的知识库问答助手。用户发送了一条问候或闲聊消息，请用简短、友好的方式回复。

用户消息: {message}

要求:
1. 回复要简短友好
2. 可以适当介绍自己是知识库问答助手
3. 引导用户提出与知识库相关的问题"""

async def classify_intent(llm: LLMService, message: str) -> str:
    """使用 LLM 判断用户意图"""
    prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)
    response = ""
    async for chunk in llm.astream(prompt):
        response += chunk
    result = response.strip().lower()
    intent = "chitchat" if "chitchat" in result else "query"
    logger.info(f"[意图分类] 用户消息: '{message[:50]}...' | 分类结果: {intent} | LLM原始回复: '{result}'")
    return intent

RAG_PROMPT = """你是一个专业的知识库问答助手。请根据以下参考资料回答用户问题。

## 参考资料
{context}

## 用户问题
{question}

## 回答要求
1. 仅基于参考资料回答，不要编造信息
2. 如果资料中没有相关内容，请明确告知
3. 回答要简洁准确
4. 在回答中使用【1】【2】【3】等标记引用对应的参考资料，标记应紧跟在引用内容之后
5. 每个引用标记对应参考资料中的编号"""

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    conv = Conversation(**data.model_dump())
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).order_by(Conversation.updated_at.desc()).all()

@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv

@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Deleted"}

@router.put("/conversations/{conv_id}", response_model=ConversationResponse)
async def update_conversation(conv_id: str, data: ConversationUpdate, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(conv, key, value)
    db.commit()
    db.refresh(conv)
    return conv

@router.get("/conversations/{conv_id}/messages", response_model=List[MessageResponse])
async def get_messages(conv_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at.asc()).all()

@router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, data: MessageCreate, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")

    # 保存用户消息
    user_msg = Message(conversation_id=conv_id, role="user", content=data.content)
    db.add(user_msg)
    db.commit()

    # 使用 LLM 判断意图
    llm = LLMService(model_id=conv.llm_model)
    logger.info(f"[Chat] 新消息 | conv_id={conv_id} | LLM模型={conv.llm_model} | 知识库={conv.kb_ids}")
    intent = await classify_intent(llm, data.content)

    # 闲聊模式：跳过检索，直接回复
    if intent == "chitchat":
        logger.info(f"[Chat] 闲聊模式，跳过知识库检索")
        async def generate_chitchat():
            prompt = CHITCHAT_PROMPT.format(message=data.content)
            full_response = ""
            async for chunk in llm.astream(prompt):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # 闲聊不返回来源
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"

            # 保存助手消息
            assistant_msg = Message(conversation_id=conv_id, role="assistant",
                                   content=full_response, sources=[])
            db.add(assistant_msg)
            db.commit()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(generate_chitchat(), media_type="text/event-stream")

    # 正常 RAG 模式：检索相关文档
    logger.info(f"[Chat] ===== 开始 RAG 检索 =====")
    sources = []
    context_parts = []
    source_index = 1
    retrieval_start = time.time()
    for kb_id in conv.kb_ids:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb:
            logger.info(f"[Chat] 检索知识库: {kb.name} (id={kb_id})")
            embedding_service = EmbeddingService(model_id=kb.embedding_model)
            vector_store = MilvusVectorStore(kb_id, embedding_service.dimension)

            # 解析RAG配置
            rag_config = _parse_rag_config(kb.rag_config)
            logger.info(f"[Chat] RAG配置详情 | 知识库={kb.name}:")
            logger.info(f"[Chat]   检索策略: {rag_config.retrieval_strategy.value}")
            logger.info(f"[Chat]   切片策略: {rag_config.chunking_strategy.value}")
            logger.info(f"[Chat]   中文分词(P0): {rag_config.use_chinese_tokenizer}")
            logger.info(f"[Chat]   上下文增强(P1): {rag_config.use_contextual_embedding}")
            logger.info(f"[Chat]   HyDE(P2): {rag_config.use_hyde}")
            logger.info(f"[Chat]   Multi-Query(P2): {rag_config.use_multi_query} (数量={rag_config.multi_query_count})")
            logger.info(f"[Chat]   GraphRAG(P5): {rag_config.use_graph_rag}")

            # 创建带RAG配置的检索器
            retriever = HybridRetriever(
                vector_store,
                embedding_service,
                rag_config=rag_config,
                llm_service=llm,  # 用于HyDE/Multi-Query
                db_session=db,
                kb_id=kb_id
            )

            # 根据策略选择同步或异步检索
            kb_retrieval_start = time.time()
            if rag_config.retrieval_strategy in [RetrievalStrategy.HYDE, RetrievalStrategy.MULTI_QUERY]:
                # 异步检索（支持Query改写）
                logger.info(f"[Chat] 使用异步检索 (策略={rag_config.retrieval_strategy.value})")
                results = await retriever.aretrieve(data.content, top_k=3)
            else:
                # 同步检索
                logger.info(f"[Chat] 使用同步检索 (策略={rag_config.retrieval_strategy.value})")
                results = retriever.retrieve(data.content, top_k=3)

            logger.info(f"[Chat] 知识库 {kb.name} 检索完成 | 结果数={len(results)} | 耗时={time.time()-kb_retrieval_start:.2f}s")

            for idx, r in enumerate(results):
                score = r.get("rerank_score", r.get("score", 0))
                logger.info(f"[Chat]   结果[{source_index}]: score={score:.4f} | doc_id={r['doc_id']} | 内容预览='{r['content'][:60]}...'")
                # 添加带编号的参考资料
                context_parts.append(f"【{source_index}】{r['content']}")
                sources.append({
                    "index": source_index,
                    "doc_id": r["doc_id"],
                    "text": r["content"],  # 保存完整内容用于前端展示
                    "score": score,
                    "filename": r.get("metadata", {}).get("filename", "")
                })
                source_index += 1

    logger.info(f"[Chat] ===== RAG 检索完成 ===== | 总来源数={len(sources)} | 总耗时={time.time()-retrieval_start:.2f}s")

    context = "\n\n".join(context_parts)
    prompt = RAG_PROMPT.format(context=context, question=data.content)

    async def generate():
        llm = LLMService(model_id=conv.llm_model)
        full_response = ""
        async for chunk in llm.astream(prompt):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        # 发送来源
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        # 保存助手消息
        assistant_msg = Message(conversation_id=conv_id, role="assistant",
                               content=full_response, sources=sources)
        db.add(assistant_msg)
        db.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
