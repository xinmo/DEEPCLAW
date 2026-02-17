from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models import get_db
from models.knowledge import KnowledgeBase
from schemas.knowledge import KBCreate, KBUpdate, KBResponse
from services.knowledge.vector_store import MilvusVectorStore

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])

@router.post("", response_model=KBResponse)
async def create_kb(data: KBCreate, db: Session = Depends(get_db)):
    kb = KnowledgeBase(**data.model_dump())
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
    # 删除 Milvus collection
    try:
        vector_store = MilvusVectorStore(kb_id)
        vector_store.drop_collection()
    except:
        pass
    db.delete(kb)
    db.commit()
    return {"message": "Deleted"}
