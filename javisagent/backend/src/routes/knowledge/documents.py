import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from src.models import get_db
from src.models.knowledge import KnowledgeBase, KBDocument
from src.schemas.knowledge import DocumentResponse
from src.services.knowledge import DocumentProcessor, EmbeddingService, get_knowledge_settings, LLMService
from src.services.knowledge.processing_stages import ProcessingStage, STAGE_MESSAGES, STAGE_PROGRESS
from src.services.mineru import mineru_client

logger = logging.getLogger(__name__)
settings = get_knowledge_settings()
router = APIRouter(prefix="/api/kb/{kb_id}/documents", tags=["documents"])

@router.post("", response_model=DocumentResponse)
async def upload_document(kb_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    logger.info(f"[上传文档] ===== 开始 =====")
    logger.info(f"[上传文档] 知识库: {kb.name} (id={kb_id})")
    logger.info(f"[上传文档] 文件名: {file.filename} | embedding模型: {kb.embedding_model}")
    logger.info(f"[上传文档] RAG配置: {kb.rag_config}")

    # 保存文件
    doc_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    save_dir = os.path.join(settings.kb_upload_dir, kb_id)
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, f"{doc_id}{ext}")

    # 创建文档记录 - 初始状态为上传中
    doc = KBDocument(
        id=doc_id, kb_id=kb_id, filename=file.filename,
        file_type=ext.lstrip('.'), file_size=0,
        file_path=file_path, status="processing",
        processing_stage=ProcessingStage.UPLOADING,
        processing_progress=STAGE_PROGRESS[ProcessingStage.UPLOADING],
        processing_message=STAGE_MESSAGES[ProcessingStage.UPLOADING]
    )
    db.add(doc)
    db.commit()

    # 上传文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    doc.file_size = len(content)
    db.commit()
    logger.info(f"[上传文档] 文件已保存 | doc_id={doc_id} | 大小={len(content)} bytes | 路径={file_path}")

    # 处理文档
    try:
        # 更新为解析阶段
        doc.processing_stage = ProcessingStage.PARSING
        doc.processing_progress = STAGE_PROGRESS[ProcessingStage.PARSING]
        doc.processing_message = STAGE_MESSAGES[ProcessingStage.PARSING]
        db.commit()

        embedding_service = EmbeddingService(model_id=kb.embedding_model)
        rag_config = kb.rag_config or {}
        graph_enabled = rag_config.get("retrieval_strategy") == "graph_rag" or rag_config.get("use_graph_rag")
        logger.info(f"[上传文档] 创建 DocumentProcessor | embedding模型={kb.embedding_model} | rag_config={rag_config}")

        # 如果启用 GraphRAG，需要 LLM 服务进行实体抽取
        llm_service = None
        if graph_enabled:
            graph_rag_llm_model = rag_config.get("graph_rag_llm_model", "gpt-4o")
            llm_service = LLMService(model_id=graph_rag_llm_model)
            logger.info(f"[上传文档] GraphRAG 已启用，创建 LLM 服务用于实体抽取 | 模型={graph_rag_llm_model}")

        processor = DocumentProcessor(kb_id, embedding_service, rag_config, llm_service=llm_service, db_session=db)
        result = await processor.process_file(file_path, doc_id, file.filename)

        if result["status"] == "completed":
            doc.status = "completed"
            doc.chunk_count = result["chunk_count"]
            doc.processing_stage = ProcessingStage.COMPLETED
            doc.processing_progress = 100
            if graph_enabled:
                graph_warning = result.get("graph_warning", "")
                entity_count = result.get("entity_count", 0)
                relationship_count = result.get("relationship_count", 0)
                if entity_count > 0 or relationship_count > 0:
                    summary = (
                        f"文档已入库，图谱已生成：{entity_count} 个实体，"
                        f"{relationship_count} 条关系"
                    )
                    doc.processing_message = f"{summary}；{graph_warning}" if graph_warning else summary
                    doc.error_msg = graph_warning or ""
                else:
                    doc.processing_message = graph_warning or "文档已入库，但未生成图谱数据"
                    doc.error_msg = graph_warning or doc.error_msg
            else:
                doc.processing_message = STAGE_MESSAGES[ProcessingStage.COMPLETED]
            kb.doc_count += 1
            kb.chunk_count += result["chunk_count"]
            logger.info(f"[上传文档] 处理完成 | doc_id={doc_id} | chunks={result['chunk_count']}")
        else:
            # MinerU 异步处理，保存 batch_id 用于后续轮询
            batch_id = result.get("batch_id", "")
            doc.mineru_batch_id = batch_id
            doc.status = "processing"
            doc.processing_stage = ProcessingStage.PARSING
            doc.processing_progress = 15  # 解析中，进度15%
            doc.processing_message = "MinerU 正在解析文档..."
            logger.info(f"Document {doc_id} submitted to MinerU, batch_id: {batch_id}")

        db.commit()
    except Exception as e:
        import traceback
        logger.error(f"Error processing document {doc_id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        doc.status = "failed"
        doc.processing_stage = ProcessingStage.FAILED
        doc.processing_progress = 0
        doc.processing_message = f"处理失败: {str(e)[:100]}"
        doc.error_msg = str(e)
        db.commit()

    db.refresh(doc)
    return doc

@router.get("", response_model=List[DocumentResponse])
async def list_documents(kb_id: str, db: Session = Depends(get_db)):
    return db.query(KBDocument).filter(KBDocument.kb_id == kb_id).order_by(KBDocument.created_at.desc()).all()


@router.post("/{doc_id}/check-status", response_model=DocumentResponse)
async def check_document_status(kb_id: str, doc_id: str, db: Session = Depends(get_db)):
    """检查处理中的文档状态，如果 MinerU 解析完成则处理并更新状态"""
    doc = db.query(KBDocument).filter(KBDocument.id == doc_id, KBDocument.kb_id == kb_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    # 只处理 processing 状态且有 batch_id 的文档
    if doc.status != "processing" or not doc.mineru_batch_id:
        return doc

    # 防止并发重复处理：如果已经在切片/向量化/存储阶段，直接返回当前状态
    if doc.processing_stage in [ProcessingStage.CHUNKING, ProcessingStage.EMBEDDING, ProcessingStage.STORING]:
        logger.info(f"[check-status] 文档 {doc_id} 正在处理中 (stage={doc.processing_stage})，跳过重复处理")
        return doc

    logger.info(f"[check-status] Checking doc {doc_id}, batch_id: {doc.mineru_batch_id}")

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    # 查询 MinerU 解析状态
    try:
        result = mineru_client.get_batch_status(doc.mineru_batch_id)
        logger.debug(f"[check-status] MinerU response code: {result.get('code')}")

        if result.get("code") != 0:
            logger.warning(f"[check-status] MinerU error: {result.get('msg')}")
            return doc

        extract_result = result.get("data", {}).get("extract_result", [])
        if not extract_result:
            logger.debug(f"[check-status] No extract_result yet")
            return doc

        file_result = extract_result[0]
        state = file_result.get("state")
        logger.debug(f"[check-status] MinerU state: {state}")

        # 更新 MinerU 解析进度
        if state == "processing":
            progress = file_result.get("progress", 0)
            doc.processing_progress = 10 + int(progress * 0.4)  # 10-50%
            doc.processing_message = f"MinerU 解析中 ({progress}%)..."
            db.commit()

        elif state == "done":
            # 获取 markdown 内容 - full_zip_url 直接在 file_result 中
            full_zip_url = file_result.get("full_zip_url", "")
            logger.debug(f"[check-status] full_zip_url: {full_zip_url[:100] if full_zip_url else 'None'}...")

            if full_zip_url:
                # 更新为切片阶段
                doc.processing_stage = ProcessingStage.CHUNKING
                doc.processing_progress = 50
                doc.processing_message = STAGE_MESSAGES[ProcessingStage.CHUNKING]
                db.commit()

                # 使用 mineru_client 的方法下载并提取 markdown
                logger.info(f"[check-status] Downloading and extracting markdown...")
                markdown_content = mineru_client.download_and_extract_markdown(full_zip_url)

                if markdown_content:
                    logger.info(f"[check-status] Got markdown content, length: {len(markdown_content)}")

                    # 创建进度回调
                    def update_progress(stage: str, progress: int, message: str):
                        doc.processing_stage = stage
                        doc.processing_progress = progress
                        doc.processing_message = message
                        db.commit()

                    # 处理文档内容
                    embedding_service = EmbeddingService(model_id=kb.embedding_model)
                    rag_config = kb.rag_config or {}
                    graph_enabled = rag_config.get("retrieval_strategy") == "graph_rag" or rag_config.get("use_graph_rag")
                    logger.info(f"[check-status] 创建 DocumentProcessor | embedding模型={kb.embedding_model} | rag_config={rag_config}")

                    # 如果启用 GraphRAG，需要 LLM 服务进行实体抽取
                    llm_service = None
                    if graph_enabled:
                        graph_rag_llm_model = rag_config.get("graph_rag_llm_model", "gpt-4o")
                        llm_service = LLMService(model_id=graph_rag_llm_model)
                        logger.info(f"[check-status] GraphRAG 已启用，创建 LLM 服务用于实体抽取 | 模型={graph_rag_llm_model}")

                    processor = DocumentProcessor(
                        kb_id, embedding_service, rag_config,
                        llm_service=llm_service,
                        progress_callback=update_progress,
                        db_session=db
                    )
                    process_result = await processor.process_mineru_result(doc_id, markdown_content, doc.filename)

                    # 更新文档状态
                    doc.status = "completed"
                    doc.chunk_count = process_result["chunk_count"]
                    doc.processing_stage = ProcessingStage.COMPLETED
                    doc.processing_progress = 100
                    if graph_enabled:
                        graph_warning = process_result.get("graph_warning", "")
                        entity_count = process_result.get("entity_count", 0)
                        relationship_count = process_result.get("relationship_count", 0)
                        if entity_count > 0 or relationship_count > 0:
                            summary = (
                                f"文档已入库，图谱已生成：{entity_count} 个实体，"
                                f"{relationship_count} 条关系"
                            )
                            doc.processing_message = f"{summary}；{graph_warning}" if graph_warning else summary
                            doc.error_msg = graph_warning or ""
                        else:
                            doc.processing_message = graph_warning or "文档已入库，但未生成图谱数据"
                            doc.error_msg = graph_warning or doc.error_msg
                    else:
                        doc.processing_message = STAGE_MESSAGES[ProcessingStage.COMPLETED]
                    kb.doc_count += 1
                    kb.chunk_count += process_result["chunk_count"]
                    db.commit()
                    logger.info(f"[check-status] Document {doc_id} completed with {doc.chunk_count} chunks")
                else:
                    doc.status = "failed"
                    doc.processing_stage = ProcessingStage.FAILED
                    doc.processing_progress = 0
                    doc.processing_message = "无法提取 Markdown 内容"
                    doc.error_msg = "无法提取 Markdown 内容"
                    db.commit()
                    logger.error(f"[check-status] Failed to extract markdown content")
            else:
                logger.warning(f"[check-status] No full_zip_url in result")

        elif state == "failed":
            doc.status = "failed"
            doc.processing_stage = ProcessingStage.FAILED
            doc.processing_progress = 0
            doc.processing_message = file_result.get("err_msg", "MinerU 解析失败")
            doc.error_msg = file_result.get("err_msg", "MinerU 解析失败")
            db.commit()
            logger.error(f"[check-status] MinerU parsing failed: {doc.error_msg}")

    except Exception as e:
        import traceback
        logger.error(f"[check-status] Error: {e}")
        logger.error(f"[check-status] Traceback: {traceback.format_exc()}")

    db.refresh(doc)
    return doc


@router.delete("/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KBDocument).filter(KBDocument.id == doc_id, KBDocument.kb_id == kb_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    # 只有已完成的文档才需要删除向量和更新统计
    if doc.status == "completed":
        # 删除向量
        try:
            embedding_service = EmbeddingService(model_id=kb.embedding_model)
            processor = DocumentProcessor(kb_id, embedding_service, db_session=db)
            processor.delete_document(doc_id)
        except Exception as e:
            # 向量删除失败不阻止文档删除
            logger.warning(f"Failed to delete vectors for doc {doc_id}: {e}")

        # 更新统计
        kb.doc_count = max(0, kb.doc_count - 1)
        kb.chunk_count = max(0, kb.chunk_count - (doc.chunk_count or 0))

    # 删除文件
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"message": "Deleted"}
