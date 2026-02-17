import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from models import get_db
from models.knowledge import KnowledgeBase, KBDocument
from schemas.knowledge import DocumentResponse
from services.knowledge import DocumentProcessor, EmbeddingService, get_knowledge_settings

settings = get_knowledge_settings()
router = APIRouter(prefix="/api/kb/{kb_id}/documents", tags=["documents"])

@router.post("", response_model=DocumentResponse)
async def upload_document(kb_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    # 保存文件
    doc_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    save_dir = os.path.join(settings.kb_upload_dir, kb_id)
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, f"{doc_id}{ext}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建文档记录
    doc = KBDocument(
        id=doc_id, kb_id=kb_id, filename=file.filename,
        file_type=ext.lstrip('.'), file_size=len(content),
        file_path=file_path, status="processing"
    )
    db.add(doc)
    db.commit()

    # 处理文档
    embedding_service = EmbeddingService(model_id=kb.embedding_model)
    processor = DocumentProcessor(kb_id, embedding_service)
    result = await processor.process_file(file_path, doc_id, file.filename)

    if result["status"] == "completed":
        doc.status = "completed"
        doc.chunk_count = result["chunk_count"]
        kb.doc_count += 1
        kb.chunk_count += result["chunk_count"]
    else:
        doc.mineru_batch_id = result.get("batch_id", "")

    db.commit()
    db.refresh(doc)
    return doc

@router.get("", response_model=List[DocumentResponse])
async def list_documents(kb_id: str, db: Session = Depends(get_db)):
    return db.query(KBDocument).filter(KBDocument.kb_id == kb_id).order_by(KBDocument.created_at.desc()).all()

@router.delete("/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KBDocument).filter(KBDocument.id == doc_id, KBDocument.kb_id == kb_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    # 删除向量
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    embedding_service = EmbeddingService(model_id=kb.embedding_model)
    processor = DocumentProcessor(kb_id, embedding_service)
    processor.delete_document(doc_id)

    # 更新统计
    kb.doc_count -= 1
    kb.chunk_count -= doc.chunk_count

    # 删除文件
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"message": "Deleted"}
