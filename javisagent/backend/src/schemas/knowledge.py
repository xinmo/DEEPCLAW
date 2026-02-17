from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 知识库
class KBCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "book"
    embedding_model: str = "text-embedding-3-small"

class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None

class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    embedding_model: str
    doc_count: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 文档
class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_msg: str
    created_at: datetime

    class Config:
        from_attributes = True

# 对话
class ConversationCreate(BaseModel):
    kb_ids: List[str]
    title: str = "新对话"
    llm_model: str = "gpt-4o"

class ConversationResponse(BaseModel):
    id: str
    kb_ids: List[str]
    title: str
    llm_model: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 消息
class MessageCreate(BaseModel):
    content: str

class SourceInfo(BaseModel):
    doc_id: str
    filename: str
    text: str
    score: float

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[SourceInfo]
    created_at: datetime

    class Config:
        from_attributes = True

# 模型配置
class ModelConfigCreate(BaseModel):
    type: str  # embedding/llm
    provider: str
    name: str
    model_id: str
    api_key: str = ""
    base_url: str = ""
    is_default: bool = False

class ModelConfigResponse(BaseModel):
    id: str
    type: str
    provider: str
    name: str
    model_id: str
    base_url: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True
