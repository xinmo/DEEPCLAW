from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from models.base import Base

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

    documents = relationship("KBDocument", back_populates="knowledge_base", cascade="all, delete-orphan")

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
    error_msg = Column(Text, default="")
    mineru_batch_id = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")

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
