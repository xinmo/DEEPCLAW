import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class IndustryResearch(Base):
    __tablename__ = "industry_research"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(String, nullable=False)
    depth = Column(Enum("quick", "standard", "deep", name="research_depth"), nullable=False, default="standard")
    status = Column(Enum("running", "completed", "failed", name="research_status"), nullable=False, default="running")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    nodes = relationship("IndustryNode", back_populates="research", cascade="all, delete-orphan")
    edges = relationship("IndustryEdge", back_populates="research", cascade="all, delete-orphan")


class IndustryNode(Base):
    __tablename__ = "industry_node"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    research_id = Column(String, ForeignKey("industry_research.id"), nullable=False)
    node_key = Column(String, nullable=False)
    label = Column(String, nullable=False)
    layer = Column(String)
    status = Column(Enum("done", "in_progress", "pending", name="node_status"), default="pending")
    competition_type = Column(Enum("domestic", "foreign", "balanced", name="competition_type"), default="balanced")
    nationalization_rate = Column(Float, default=0.0)
    companies = Column(JSON, default=list)
    overview = Column(Text)
    upstream_deps = Column(JSON, default=list)
    latest_news = Column(JSON, default=list)
    sort_order = Column(Integer, default=0)

    research = relationship("IndustryResearch", back_populates="nodes")


class IndustryEdge(Base):
    __tablename__ = "industry_edge"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    research_id = Column(String, ForeignKey("industry_research.id"), nullable=False)
    source = Column(String, nullable=False)
    target = Column(String, nullable=False)

    research = relationship("IndustryResearch", back_populates="edges")


class DeepResearch(Base):
    __tablename__ = "deep_research"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    research_id = Column(String, ForeignKey("industry_research.id"), nullable=False)
    node_key = Column(String, nullable=False)
    node_name = Column(String, nullable=False)
    status = Column(Enum("running", "completed", "failed", name="deep_status"), default="running")
    report = Column(Text, default="")
    deep_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
