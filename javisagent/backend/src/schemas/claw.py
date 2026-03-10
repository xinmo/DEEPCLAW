from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


# 对话相关 Schema
class ConversationCreate(BaseModel):
    title: Optional[str] = "新对话"
    working_directory: str
    llm_model: str = "claude-opus-4-6"


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    working_directory: Optional[str] = None
    llm_model: Optional[str] = None


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    working_directory: str
    llm_model: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 消息相关 Schema
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ToolCallInfo(BaseModel):
    id: UUID
    tool_name: str
    tool_input: Any
    tool_output: Optional[Any] = None
    status: str
    duration: Optional[float] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    metadata: dict
    tool_calls: List[ToolCallInfo] = []
    created_at: datetime

    class Config:
        from_attributes = True


# 工具验证 Schema
class DirectoryValidation(BaseModel):
    path: str


class DirectoryValidationResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None


# 模型列表 Schema
class ModelInfo(BaseModel):
    model_id: str
    name: str
    provider: str


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
