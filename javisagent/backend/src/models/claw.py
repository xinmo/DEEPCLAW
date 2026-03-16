import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ToolCallStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ClawConversation(Base):
    __tablename__ = "claw_conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="New Conversation")
    working_directory = Column(String(512), nullable=False)
    llm_model = Column(String(100), nullable=False, default="deepseek-chat")
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "ClawMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="select",
    )
    prompt_snapshot = relationship(
        "ClawConversationPromptSnapshot",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="select",
        uselist=False,
    )


class ClawConversationPromptSnapshot(Base):
    __tablename__ = "claw_conversation_prompt_snapshots"

    conversation_id = Column(
        String,
        ForeignKey("claw_conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prompt_bundle = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("ClawConversation", back_populates="prompt_snapshot")


class ClawMessage(Base):
    __tablename__ = "claw_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String,
        ForeignKey("claw_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ClawConversation", back_populates="messages")
    tool_calls = relationship(
        "ClawToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="select",
    )
    process_events = relationship(
        "ClawProcessEvent",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="ClawProcessEvent.sequence",
    )


class ClawToolCall(Base):
    __tablename__ = "claw_tool_calls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(
        String,
        ForeignKey("claw_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_name = Column(String(100), nullable=False)
    tool_input = Column(JSON, nullable=False)
    tool_output = Column(JSON)
    status = Column(Enum(ToolCallStatus), nullable=False, default=ToolCallStatus.RUNNING)
    duration = Column(Float)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("ClawMessage", back_populates="tool_calls")


class ClawProcessEvent(Base):
    __tablename__ = "claw_process_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(
        String,
        ForeignKey("claw_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence = Column(Integer, nullable=False, default=0)
    kind = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    message = relationship("ClawMessage", back_populates="process_events")
