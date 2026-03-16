from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
from src.models import get_db
from src.models.knowledge import KnowledgeBase, KBDocument
from src.schemas.knowledge import KBCreate, KBUpdate, KBResponse
from src.services.knowledge.vector_store import MilvusVectorStore

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])

@router.post("", response_model=KBResponse)
async def create_kb(data: KBCreate, db: Session = Depends(get_db)):
    # 处理RAG配置
    kb_data = data.model_dump()
    if kb_data.get("rag_config"):
        # 将RAGConfigSchema转为dict存储
        kb_data["rag_config"] = kb_data["rag_config"]
    else:
        # 使用默认RAG配置
        kb_data["rag_config"] = {
            "chunking_strategy": "fixed",
            "retrieval_strategy": "hybrid",
            "chunk_size": 500,
            "chunk_overlap": 100,
            "parent_chunk_size": 2000,
            "child_chunk_size": 200,
            "semantic_threshold": 0.5,
            "use_chinese_tokenizer": True,
            "use_contextual_embedding": False,
            "use_hyde": False,
            "use_multi_query": False,
            "multi_query_count": 3,
            "use_graph_rag": False,
            "graph_rag_llm_model": "gpt-4o",
        }
    kb = KnowledgeBase(**kb_data)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb

@router.get("", response_model=List[KBResponse])
async def list_kbs(db: Session = Depends(get_db)):
    return db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()

@router.get("/{kb_id}", response_model=KBResponse)
async def get_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")
    return kb

@router.put("/{kb_id}", response_model=KBResponse)
async def update_kb(kb_id: str, data: KBUpdate, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(kb, key, value)
    db.commit()
    db.refresh(kb)
    return kb

@router.delete("/{kb_id}")
async def delete_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(404, "Knowledge base not found")

    # 先删除所有关联的文档记录和文件
    docs = db.query(KBDocument).filter(KBDocument.kb_id == kb_id).all()
    for doc in docs:
        # 删除文件
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                print(f"Warning: Failed to delete file {doc.file_path}: {e}")
        db.delete(doc)

    # 删除 Milvus collection
    try:
        vector_store = MilvusVectorStore(kb_id)
        vector_store.drop_collection()
    except Exception as e:
        print(f"Warning: Failed to drop Milvus collection {kb_id}: {e}")

    db.delete(kb)
    db.commit()
    return {"message": "Deleted"}
