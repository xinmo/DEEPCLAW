import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from models import get_db
from models.knowledge import KnowledgeBase, Conversation, Message
from schemas.knowledge import ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
from services.knowledge import EmbeddingService, LLMService, HybridRetriever, MilvusVectorStore

router = APIRouter(prefix="/api/chat", tags=["chat"])

RAG_PROMPT = """你是一个专业的知识库问答助手。请根据以下参考资料回答用户问题。

## 参考资料
{context}

## 用户问题
{question}

## 回答要求
1. 仅基于参考资料回答，不要编造信息
2. 如果资料中没有相关内容，请明确告知
3. 回答要简洁准确"""

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

    # 检索相关文档
    sources = []
    context_parts = []
    for kb_id in conv.kb_ids:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb:
            embedding_service = EmbeddingService(model_id=kb.embedding_model)
            vector_store = MilvusVectorStore(kb_id, embedding_service.dimension)
            retriever = HybridRetriever(vector_store, embedding_service)
            results = retriever.retrieve(data.content, top_k=3)
            for r in results:
                context_parts.append(r["content"])
                sources.append({"doc_id": r["doc_id"], "text": r["content"][:200],
                               "score": r.get("rerank_score", r.get("score", 0)),
                               "filename": r.get("metadata", {}).get("filename", "")})

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
