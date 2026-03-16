import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String, UniqueConstraint

from src.models.base import Base


class ChannelConfig(Base):
    __tablename__ = "channel_configs"

    name = Column(String(50), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    config_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelSession(Base):
    __tablename__ = "channel_sessions"
    __table_args__ = (
        UniqueConstraint(
            "channel_name",
            "chat_id",
            name="uq_channel_sessions_channel_chat",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_name = Column(String(50), nullable=False)
    chat_id = Column(String(255), nullable=False)
    sender_id = Column(String(255), nullable=False)
    conversation_id = Column(
        String,
        ForeignKey("claw_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    extra_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
