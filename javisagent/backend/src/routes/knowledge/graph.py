"""
知识图谱 API 路由
提供实体、关系的查询和管理接口
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.models.knowledge import KnowledgeBase, Entity, Relationship
from src.services.knowledge.graph_store import GraphStore
from src.models import get_db

logger = logging.getLogger("routes.knowledge.graph")

router = APIRouter(prefix="/api/kb", tags=["knowledge-graph"])


# ==================== Schema ====================

class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    description: str
    doc_id: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class RelationshipResponse(BaseModel):
    id: str
    source_entity_id: str
    source_name: str
    target_entity_id: str
    target_name: str
    relation_type: str
    description: str
    weight: float

    class Config:
        from_attributes = True


class GraphStatistics(BaseModel):
    entity_count: int
    relationship_count: int
    entity_types: dict
    relationship_types: dict


class SubgraphResponse(BaseModel):
    entities: List[dict]
    relationships: List[dict]


# ==================== 实体 API ====================

@router.get("/{kb_id}/graph/entities", response_model=List[EntityResponse])
async def list_entities(
    kb_id: str,
    type: Optional[str] = Query(None, description="按实体类型筛选"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取知识库的实体列表"""
    logger.info(f"[Graph] 获取实体列表 | kb_id={kb_id} | type={type} | limit={limit}")
    # 验证知识库存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    graph_store = GraphStore(db, kb_id)
    entities = graph_store.get_all_entities(type=type, limit=limit)
    logger.info(f"[Graph] 获取到 {len(entities)} 个实体")

    return [
        EntityResponse(
            id=e.id,
            name=e.name,
            type=e.type,
            description=e.description or "",
            doc_id=e.doc_id,
            created_at=e.created_at.isoformat() if e.created_at else ""
        )
        for e in entities
    ]


@router.get("/{kb_id}/graph/entities/{entity_id}")
async def get_entity_detail(
    kb_id: str,
    entity_id: str,
    max_hops: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db)
):
    """获取实体详情及其关系"""
    logger.info(f"[Graph] 获取实体详情 | kb_id={kb_id} | entity_id={entity_id} | max_hops={max_hops}")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    graph_store = GraphStore(db, kb_id)
    entity = graph_store.get_entity_by_id(entity_id)
    if not entity:
        logger.warning(f"[Graph] 实体不存在 | entity_id={entity_id}")
        raise HTTPException(status_code=404, detail="实体不存在")

    neighbors = graph_store.get_entity_neighbors(entity_id, max_hops=max_hops)
    logger.info(f"[Graph] 获取到实体详情 | name={entity.name} | neighbors={len(neighbors)}")

    return {
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "description": entity.description or "",
            "doc_id": entity.doc_id,
            "created_at": entity.created_at.isoformat() if entity.created_at else ""
        },
        "neighbors": neighbors
    }


# ==================== 关系 API ====================

@router.get("/{kb_id}/graph/relationships", response_model=List[RelationshipResponse])
async def list_relationships(
    kb_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取知识库的关系列表"""
    logger.info(f"[Graph] 获取关系列表 | kb_id={kb_id} | limit={limit}")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    graph_store = GraphStore(db, kb_id)
    relationships = graph_store.get_all_relationships(limit=limit)
    logger.info(f"[Graph] 获取到 {len(relationships)} 个关系")

    result = []
    for r in relationships:
        source = graph_store.get_entity_by_id(r.source_entity_id)
        target = graph_store.get_entity_by_id(r.target_entity_id)
        result.append(RelationshipResponse(
            id=r.id,
            source_entity_id=r.source_entity_id,
            source_name=source.name if source else "",
            target_entity_id=r.target_entity_id,
            target_name=target.name if target else "",
            relation_type=r.relation_type,
            description=r.description or "",
            weight=r.weight or 1.0
        ))

    return result


# ==================== 子图 API ====================

@router.get("/{kb_id}/graph/subgraph", response_model=SubgraphResponse)
async def get_subgraph(
    kb_id: str,
    entity_ids: str = Query(..., description="逗号分隔的实体ID列表"),
    max_hops: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db)
):
    """获取子图"""
    logger.info(f"[Graph] 获取子图 | kb_id={kb_id} | entity_ids={entity_ids} | max_hops={max_hops}")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    entity_id_list = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
    if not entity_id_list:
        logger.warning(f"[Graph] 未提供实体ID")
        raise HTTPException(status_code=400, detail="请提供至少一个实体ID")

    graph_store = GraphStore(db, kb_id)
    subgraph = graph_store.get_subgraph(entity_id_list, max_hops=max_hops)
    logger.info(f"[Graph] 获取到子图 | entities={len(subgraph.get('entities', []))} | relationships={len(subgraph.get('relationships', []))}")

    return SubgraphResponse(
        entities=subgraph.get("entities", []),
        relationships=subgraph.get("relationships", [])
    )


# ==================== 统计 API ====================

@router.get("/{kb_id}/graph/statistics", response_model=GraphStatistics)
async def get_graph_statistics(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """获取图统计信息"""
    logger.info(f"[Graph] 获取图统计信息 | kb_id={kb_id}")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    graph_store = GraphStore(db, kb_id)
    stats = graph_store.get_statistics()
    logger.info(f"[Graph] 统计信息 | entities={stats.get('entity_count', 0)} | relationships={stats.get('relationship_count', 0)}")

    return GraphStatistics(**stats)


# ==================== 管理 API ====================

@router.delete("/{kb_id}/graph")
async def clear_graph_data(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """清空知识库的所有图数据"""
    logger.info(f"[Graph] 清空图数据 | kb_id={kb_id}")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    graph_store = GraphStore(db, kb_id)
    entity_count, rel_count = graph_store.clear_all()
    logger.info(f"[Graph] 图数据已清空 | deleted_entities={entity_count} | deleted_relationships={rel_count}")

    return {
        "message": "图数据已清空",
        "deleted_entities": entity_count,
        "deleted_relationships": rel_count
    }


@router.post("/{kb_id}/graph/search")
async def search_entities(
    kb_id: str,
    keyword: str = Query(..., description="搜索关键词"),
    fuzzy: bool = Query(True, description="是否模糊匹配"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """搜索实体"""
    logger.info(f"[Graph] 搜索实体 | kb_id={kb_id} | keyword={keyword} | fuzzy={fuzzy} | limit={limit}")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        logger.warning(f"[Graph] 知识库不存在 | kb_id={kb_id}")
        raise HTTPException(status_code=404, detail="知识库不存在")

    graph_store = GraphStore(db, kb_id)
    entities = graph_store.find_entity_by_name(keyword, fuzzy=fuzzy)
    logger.info(f"[Graph] 搜索到 {len(entities)} 个实体")

    return [
        {
            "id": e.id,
            "name": e.name,
            "type": e.type,
            "description": e.description or ""
        }
        for e in entities[:limit]
    ]
