from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .base import Base

def generate_uuid():
    return str(uuid.uuid4())

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    icon = Column(String(50), default="book")
    embedding_model = Column(String(100), default="text-embedding-3-small")
    doc_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # RAG优化配置 (P0-P5)
    rag_config = Column(JSON, default=lambda: {
        "chunking_strategy": "fixed",       # fixed/semantic/parent_child
        "retrieval_strategy": "hybrid",     # basic/hybrid/contextual/hyde/multi_query/graph_rag
        "chunk_size": 500,
        "chunk_overlap": 100,
        "parent_chunk_size": 2000,          # P4: 父文档大小
        "child_chunk_size": 200,            # P4: 子文档大小
        "semantic_threshold": 0.5,          # P3: 语义切片阈值
        "use_chinese_tokenizer": True,      # P0: 中文分词
        "use_contextual_embedding": False,  # P1: 上下文嵌入
        "use_hyde": False,                  # P2: HyDE
        "use_multi_query": False,           # P2: Multi-Query
        "multi_query_count": 3,             # P2: 查询变体数量
        "use_graph_rag": False,             # P5: GraphRAG
    })

    documents = relationship("KBDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="knowledge_base", cascade="all, delete-orphan")
    relationships = relationship("Relationship", back_populates="knowledge_base", cascade="all, delete-orphan")

class KBDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    kb_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, default=0)
    file_path = Column(String(500), default="")
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    processing_stage = Column(String(20), default="")  # uploading/parsing/chunking/embedding/storing
    processing_progress = Column(Integer, default=0)   # 0-100 进度百分比
    processing_message = Column(String(200), default="")  # 当前处理步骤的描述信息
    error_msg = Column(Text, default="")
    mineru_batch_id = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    entities = relationship("Entity", back_populates="document", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    kb_ids = Column(JSON, default=list)
    title = Column(String(200), default="新对话")
    llm_model = Column(String(100), default="gpt-4o")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user/assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    type = Column(String(20), nullable=False)  # embedding/llm
    provider = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    model_id = Column(String(100), nullable=False)
    api_key = Column(Text, default="")
    base_url = Column(String(500), default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Entity(Base):
    """知识图谱实体"""
    __tablename__ = "entities"
    __table_args__ = (
        Index('ix_entities_kb_id', 'kb_id'),
        Index('ix_entities_name_type', 'name', 'type'),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    kb_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    doc_id = Column(String(36), ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 人物/组织/地点/概念/事件/技术
    description = Column(Text, default="")
    properties = Column(JSON, default=dict)  # 额外属性
    embedding = Column(JSON, nullable=True)  # 实体向量 (存储为 JSON 数组)
    created_at = Column(DateTime, default=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="entities")
    document = relationship("KBDocument", back_populates="entities")

    # 作为源实体的关系
    outgoing_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    # 作为目标实体的关系
    incoming_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )


class Relationship(Base):
    """知识图谱关系"""
    __tablename__ = "relationships"
    __table_args__ = (
        Index('ix_relationships_kb_id', 'kb_id'),
        Index('ix_relationships_source', 'source_entity_id'),
        Index('ix_relationships_target', 'target_entity_id'),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    kb_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    source_entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(100), nullable=False)
    description = Column(Text, default="")
    weight = Column(Float, default=1.0)  # 关系权重
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="relationships")
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], back_populates="outgoing_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], back_populates="incoming_relationships")
