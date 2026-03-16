from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# RAG配置
class RAGConfigSchema(BaseModel):
    """RAG优化配置"""
    # 切片策略: fixed(固定)/semantic(语义)/parent_child(父子文档)
    chunking_strategy: str = "fixed"
    # 检索策略: basic/hybrid/contextual/hyde/multi_query/graph_rag
    retrieval_strategy: str = "hybrid"
    chunk_size: int = 500
    chunk_overlap: int = 100
    # P4: 父子文档配置
    parent_chunk_size: int = 2000
    child_chunk_size: int = 200
    # P3: 语义切片阈值
    semantic_threshold: float = 0.5
    # P0: 中文分词
    use_chinese_tokenizer: bool = True
    # P1: 上下文嵌入
    use_contextual_embedding: bool = False
    # P2: HyDE
    use_hyde: bool = False
    # P2: Multi-Query
    use_multi_query: bool = False
    multi_query_count: int = 3
    # P5: GraphRAG
    use_graph_rag: bool = False
    # GraphRAG 实体抽取使用的 LLM 模型
    graph_rag_llm_model: str = "gpt-4o"


# 知识库
class KBCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "book"
    embedding_model: str = "text-embedding-3-small"
    rag_config: Optional[RAGConfigSchema] = None

class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    rag_config: Optional[RAGConfigSchema] = None

class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    embedding_model: str
    doc_count: int
    chunk_count: int
    rag_config: Optional[Dict[str, Any]] = None
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
    processing_stage: str = ""
    processing_progress: int = 0
    processing_message: str = ""
    error_msg: str
    created_at: datetime

    class Config:
        from_attributes = True

# 对话
class ConversationCreate(BaseModel):
    kb_ids: List[str]
    title: str = "新对话"
    llm_model: str = "gpt-4o"

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    kb_ids: Optional[List[str]] = None
    llm_model: Optional[str] = None

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
