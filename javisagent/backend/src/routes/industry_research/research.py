import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models import get_db
from src.models.industry_research import DeepResearch, IndustryResearch

router = APIRouter(prefix="/api/industry-research", tags=["industry-research"])


class StartResearchRequest(BaseModel):
    query: str
    depth: Literal["quick", "standard", "deep"] = "standard"


class StartDeepRequest(BaseModel):
    nodeId: str
    nodeName: str


@router.post("/start")
def start_research(req: StartResearchRequest, db: Session = Depends(get_db)):
    research = IndustryResearch(
        id=str(uuid.uuid4()),
        query=req.query,
        depth=req.depth,
        status="running",
        progress=0,
    )
    db.add(research)
    db.commit()
    return {"researchId": research.id}


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    items = db.query(IndustryResearch).order_by(IndustryResearch.created_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "query": r.query,
            "depth": r.depth,
            "status": r.status,
            "progress": r.progress,
            "nodeCount": len(r.nodes),
            "companyCount": sum(len(n.companies or []) for n in r.nodes),
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in items
    ]


@router.get("/{research_id}/graph")
def get_graph(research_id: str, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    nodes = [
        {
            "id": n.node_key,
            "label": n.label,
            "layer": n.layer,
            "status": n.status,
            "competitionType": n.competition_type,
            "nationalizationRate": n.nationalization_rate,
            "companies": n.companies or [],
            "overview": n.overview or "",
            "upstreamDeps": n.upstream_deps or [],
            "latestNews": n.latest_news or [],
        }
        for n in sorted(research.nodes, key=lambda x: x.sort_order)
    ]
    edges = [{"source": e.source, "target": e.target} for e in research.edges]
    return {"nodes": nodes, "edges": edges}


@router.post("/{research_id}/deep")
def start_deep_research(research_id: str, req: StartDeepRequest, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    deep = DeepResearch(
        id=str(uuid.uuid4()),
        research_id=research_id,
        node_key=req.nodeId,
        node_name=req.nodeName,
        status="running",
    )
    db.add(deep)
    db.commit()
    return {"deepId": deep.id}
