import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class IndustryResearch(Base):
    __tablename__ = "industry_research"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    query = Column(String(500), nullable=False)
    depth = Column(Enum("quick", "standard", "deep"), nullable=False, default="standard")
    status = Column(Enum("running", "completed", "failed"), nullable=False, default="running")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    nodes = relationship("IndustryNode", back_populates="research", cascade="all, delete-orphan")
    edges = relationship("IndustryEdge", back_populates="research", cascade="all, delete-orphan")
    deep_researches = relationship("DeepResearch", back_populates="research", cascade="all, delete-orphan")


class IndustryNode(Base):
    __tablename__ = "industry_node"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    research_id = Column(String(36), ForeignKey("industry_research.id"), nullable=False)
    node_key = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)
    layer = Column(String(50))
    status = Column(Enum("done", "in_progress", "pending"), default="pending")
    competition_type = Column(Enum("domestic", "foreign", "balanced"), default="balanced")
    nationalization_rate = Column(Float, default=0.0)
    companies = Column(JSON, default=list)
    overview = Column(Text)
    upstream_deps = Column(JSON, default=list)
    latest_news = Column(JSON, default=list)
    sort_order = Column(Integer, default=0)

    research = relationship("IndustryResearch", back_populates="nodes")


class IndustryEdge(Base):
    __tablename__ = "industry_edge"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    research_id = Column(String(36), ForeignKey("industry_research.id"), nullable=False)
    source = Column(String(100), nullable=False)
    target = Column(String(100), nullable=False)

    research = relationship("IndustryResearch", back_populates="edges")


class DeepResearch(Base):
    __tablename__ = "deep_research"

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    research_id = Column(String(36), ForeignKey("industry_research.id"), nullable=False)
    node_key = Column(String(100), nullable=False)
    node_name = Column(String(200), nullable=False)
    status = Column(Enum("running", "completed", "failed"), default="running")
    report = Column(Text, default="")
    deep_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    research = relationship("IndustryResearch", back_populates="deep_researches")
