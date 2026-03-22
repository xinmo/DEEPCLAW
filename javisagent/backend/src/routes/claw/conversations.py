from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os
from pathlib import Path

from src.models import get_db
from src.models.channels import ChannelSession
from src.models.claw import ClawConversation, ClawConversationPromptSnapshot
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
from src.services.claw.prompt_registry import get_current_prompt_bundle

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

    current_prompt_bundle = get_current_prompt_bundle()
    current_prompt = current_prompt_bundle["system_prompt"]

    # 创建对话
    conversation = ClawConversation(
        title=data.title,
        working_directory=data.working_directory,
        llm_model=data.llm_model,
        system_prompt=current_prompt
    )
    conversation.prompt_snapshot = ClawConversationPromptSnapshot(
        prompt_bundle=current_prompt_bundle
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
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
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
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
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
    conversation = db.query(ClawConversation).filter_by(id=str(conv_id)).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    db.query(ChannelSession).filter_by(conversation_id=str(conv_id)).delete(
        synchronize_session=False
    )
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
        ModelInfo(model_id="deepseek-chat", name="DeepSeek Chat", provider="DeepSeek"),
        ModelInfo(model_id="deepseek-coder", name="DeepSeek Coder", provider="DeepSeek"),
        ModelInfo(model_id="claude-opus-4-6", name="Claude Opus 4.6", provider="Anthropic"),
        ModelInfo(model_id="claude-sonnet-4-6", name="Claude Sonnet 4.6", provider="Anthropic"),
        ModelInfo(model_id="gpt-4o", name="GPT-4o", provider="OpenAI"),
        ModelInfo(model_id="gpt-4o-mini", name="GPT-4o Mini", provider="OpenAI"),
    ]
    return ModelsResponse(models=models)


@router.get("/browse-directories")
async def browse_directories(path: str = None):
    """浏览文件系统目录"""
    try:
        # 如果没有提供路径，返回根目录或用户主目录
        if not path:
            if os.name == 'nt':  # Windows
                # 返回所有驱动器
                drives = [f"{d}:\\" for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{d}:\\")]
                return {
                    "current_path": "",
                    "parent_path": None,
                    "directories": [{"name": d, "path": d} for d in drives]
                }
            else:  # Unix-like
                path = str(Path.home())

        # 验证路径存在
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="路径不存在")

        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="不是有效的目录")

        # 获取父目录
        parent_path = str(Path(path).parent) if path != Path(path).anchor else None

        # 列出子目录
        directories = []
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    directories.append({
                        "name": item,
                        "path": item_path
                    })
        except PermissionError:
            pass

        # 按名称排序
        directories.sort(key=lambda x: x["name"].lower())

        return {
            "current_path": path,
            "parent_path": parent_path,
            "directories": directories
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
