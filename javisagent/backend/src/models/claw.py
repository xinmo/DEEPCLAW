import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.models.base import Base
import enum


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ToolCallStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ClawConversation(Base):
    """Claw 对话会话"""
    __tablename__ = "claw_conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="新对话")
    working_directory = Column(String(512), nullable=False)
    llm_model = Column(String(100), nullable=False, default="deepseek-chat")
    system_prompt = Column(Text, nullable=True)  # 对话创建时使用的系统提示词
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    messages = relationship("ClawMessage", back_populates="conversation", cascade="all, delete-orphan", lazy="select")


class ClawMessage(Base):
    """Claw 消息记录"""
    __tablename__ = "claw_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("claw_conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("ClawConversation", back_populates="messages")
    tool_calls = relationship("ClawToolCall", back_populates="message", cascade="all, delete-orphan", lazy="select")


class ClawToolCall(Base):
    """工具调用记录"""
    __tablename__ = "claw_tool_calls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("claw_messages.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_input = Column(JSON, nullable=False)
    tool_output = Column(JSON)
    status = Column(Enum(ToolCallStatus), nullable=False, default=ToolCallStatus.RUNNING)
    duration = Column(Float)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    message = relationship("ClawMessage", back_populates="tool_calls")
