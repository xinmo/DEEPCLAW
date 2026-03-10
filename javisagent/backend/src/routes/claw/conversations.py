from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from src.models import get_db
from src.models.claw import ClawConversation
from src.schemas.claw import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    DirectoryValidation,
    DirectoryValidationResponse,
    ModelInfo,
    ModelsResponse
)
from src.services.claw import validate_working_directory

router = APIRouter(prefix="/api/claw", tags=["claw"])


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db)
):
    """创建新对话"""
    # 验证工作目录
    valid, reason = validate_working_directory(data.working_directory)
    if not valid:
        raise HTTPException(status_code=400, detail=f"无效的工作目录: {reason}")

    # 创建对话
    conversation = ClawConversation(
        title=data.title,
        working_directory=data.working_directory,
        llm_model=data.llm_model
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(db: Session = Depends(get_db)):
    """获取对话列表"""
    conversations = db.query(ClawConversation).order_by(
        ClawConversation.updated_at.desc()
    ).all()
    return conversations


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: UUID,
    db: Session = Depends(get_db)
):
    """获取对话详情"""
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conversation


@router.put("/conversations/{conv_id}", response_model=ConversationResponse)
async def update_conversation(
    conv_id: UUID,
    data: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """更新对话"""
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 如果更新工作目录，需要验证
    if data.working_directory:
        valid, reason = validate_working_directory(data.working_directory)
        if not valid:
            raise HTTPException(status_code=400, detail=f"无效的工作目录: {reason}")
        conversation.working_directory = data.working_directory

    if data.title is not None:
        conversation.title = data.title

    if data.llm_model:
        conversation.llm_model = data.llm_model

    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: UUID,
    db: Session = Depends(get_db)
):
    """删除对话"""
    conversation = db.query(ClawConversation).filter_by(id=conv_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    db.delete(conversation)
    db.commit()
    return {"message": "删除成功"}


@router.post("/validate-directory", response_model=DirectoryValidationResponse)
async def validate_directory(data: DirectoryValidation):
    """验证工作目录"""
    valid, reason = validate_working_directory(data.path)
    return DirectoryValidationResponse(valid=valid, reason=reason)


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """获取可用模型列表"""
    models = [
        ModelInfo(model_id="claude-opus-4-6", name="Claude Opus 4.6", provider="Anthropic"),
        ModelInfo(model_id="claude-sonnet-4-6", name="Claude Sonnet 4.6", provider="Anthropic"),
        ModelInfo(model_id="gpt-4o", name="GPT-4o", provider="OpenAI"),
        ModelInfo(model_id="gpt-4o-mini", name="GPT-4o Mini", provider="OpenAI"),
    ]
    return ModelsResponse(models=models)
