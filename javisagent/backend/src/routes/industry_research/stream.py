import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.models import SessionLocal, get_db
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
            except json.JSONDecodeError:
                logger.warning("SSE event JSON parse error, skipping chunk")
                continue
            etype = event.get("type")
            data = event.get("data", {})
            try:
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
            except Exception as e:
                logger.warning("SSE DB persist error (event=%s): %s", etype, e)
                db.rollback()
    except Exception:
        if research:
            try:
                research.status = "failed"
                db.commit()
            except Exception:
                db.rollback()
        raise


@router.get("/{research_id}/stream")
async def stream_research(research_id: str, db: Session = Depends(get_db)):
    research = db.query(IndustryResearch).filter(IndustryResearch.id == research_id).first()
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    # Extract values before Session closes
    r_query = research.query
    r_depth = research.depth

    async def generate():
        with SessionLocal() as stream_db:
            gen = run_industry_research(research_id, r_query, r_depth)
            async for chunk in _persist_and_forward(research_id, gen, stream_db):
                yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/deep/{deep_id}/stream")
async def stream_deep_research(deep_id: str, db: Session = Depends(get_db)):
    deep = db.query(DeepResearch).filter(DeepResearch.id == deep_id).first()
    if not deep:
        raise HTTPException(status_code=404, detail="Deep research not found")
    research = db.query(IndustryResearch).filter(IndustryResearch.id == deep.research_id).first()
    # Extract values before Session closes
    context = research.query if research else ""
    d_node_name = deep.node_name
    d_research_id = deep.research_id

    async def generate():
        with SessionLocal() as stream_db:
            deep_record = stream_db.query(DeepResearch).filter(DeepResearch.id == deep_id).first()
            if not deep_record:
                return
            async for chunk in run_deep_research(deep_id, d_node_name, context):
                yield chunk
                if not chunk.startswith("data: "):
                    continue
                try:
                    event = json.loads(chunk[6:])
                except json.JSONDecodeError:
                    logger.warning("Deep SSE JSON parse error, skipping chunk")
                    continue
                etype = event.get("type")
                try:
                    if etype == "report_chunk":
                        deep_record.report = (deep_record.report or "") + event["data"].get("chunk", "")
                    elif etype == "deep_data":
                        deep_record.deep_data = event["data"]
                    elif etype == "done":
                        deep_record.status = "completed"
                    stream_db.commit()
                except Exception as e:
                    logger.warning("Deep SSE DB persist error (event=%s): %s", etype, e)
                    stream_db.rollback()

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)
