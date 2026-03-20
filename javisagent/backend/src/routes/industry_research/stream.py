import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.models import get_db
from src.models.industry_research import DeepResearch, IndustryEdge, IndustryNode, IndustryResearch
from src.services.industry_research.agent_team import run_industry_research
from src.services.industry_research.deep_researcher import run_deep_research

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/industry-research", tags=["industry-research-stream"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


async def _persist_and_forward(
    research_id: str,
    generator: AsyncGenerator[str, None],
    db: Session,
) -> AsyncGenerator[str, None]:
    """Forward SSE events from agent generator, persisting graph data to DB."""
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    sort_counter = 0
    try:
        async for chunk in generator:
            yield chunk
            if not chunk.startswith("data: "):
                continue
            try:
                event = json.loads(chunk[6:])
                etype = event.get("type")
                data = event.get("data", {})
                if etype == "graph_node":
                    node_key = data.get("id")
                    existing = db.query(IndustryNode).filter(
                        IndustryNode.research_id == research_id,
                        IndustryNode.node_key == node_key,
                    ).first()
                    if existing:
                        existing.status = data.get("status", "pending")
                        existing.competition_type = data.get("competitionType", "balanced")
                        existing.nationalization_rate = data.get("nationalizationRate", 0)
                        existing.companies = data.get("companies", [])
                        existing.overview = data.get("overview", "")
                        existing.upstream_deps = data.get("upstreamDeps", [])
                        existing.latest_news = data.get("latestNews", [])
                    else:
                        db.add(IndustryNode(
                            research_id=research_id,
                            node_key=node_key,
                            label=data.get("label", ""),
                            layer=data.get("layer", ""),
                            status=data.get("status", "pending"),
                            competition_type=data.get("competitionType", "balanced"),
                            nationalization_rate=data.get("nationalizationRate", 0),
                            companies=data.get("companies", []),
                            overview=data.get("overview", ""),
                            upstream_deps=data.get("upstreamDeps", []),
                            latest_news=data.get("latestNews", []),
                            sort_order=sort_counter,
                        ))
                        sort_counter += 1
                    db.commit()
                elif etype == "graph_edge":
                    db.add(IndustryEdge(
                        research_id=research_id,
                        source=data.get("source", ""),
                        target=data.get("target", ""),
                    ))
                    db.commit()
                elif etype == "progress" and research:
                    research.progress = data.get("percent", 0)
                    db.commit()
                elif etype == "done" and research:
                    research.status = "completed"
                    research.progress = 100
                    db.commit()
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("SSE persist error: %s", e)
    except Exception:
        if research:
            research.status = "failed"
            db.commit()
        raise


@router.get("/{research_id}/stream")
def stream_research(research_id: str, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")

    async def generate():
        gen = run_industry_research(research_id, research.query, research.depth)
        async for chunk in _persist_and_forward(research_id, gen, db):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/deep/{deep_id}/stream")
def stream_deep_research(deep_id: str, db: Session = Depends(get_db)):
    deep = db.query(DeepResearch).filter(DeepResearch.id == deep_id).first()
    if not deep:
        raise HTTPException(status_code=404, detail="Deep research not found")
    research = db.query(IndustryResearch).filter(IndustryResearch.id == deep.research_id).first()
    context = research.query if research else ""

    async def generate():
        async for chunk in run_deep_research(deep_id, deep.node_name, context):
            yield chunk
            if not chunk.startswith("data: "):
                continue
            try:
                event = json.loads(chunk[6:])
                etype = event.get("type")
                if etype == "report_chunk":
                    deep.report = (deep.report or "") + event["data"].get("chunk", "")
                elif etype == "deep_data":
                    deep.deep_data = event["data"]
                elif etype == "done":
                    deep.status = "completed"
                db.commit()
            except Exception as e:
                logger.warning("Deep SSE persist error: %s", e)

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)
