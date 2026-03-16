"""
GraphStore - 知识图谱存储服务
封装实体和关系的 CRUD 操作
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import numpy as np

from src.models.knowledge import Entity, Relationship, KnowledgeBase

logger = logging.getLogger(__name__)


class GraphStore:
    """知识图谱存储服务"""

    def __init__(self, db: Session, kb_id: str):
        self.db = db
        self.kb_id = kb_id

    # ==================== 实体操作 ====================

    def add_entity(
        self,
        name: str,
        type: str,
        description: str = "",
        doc_id: str = None,
        properties: dict = None,
        embedding: List[float] = None
    ) -> Entity:
        """添加实体"""
        entity = Entity(
            kb_id=self.kb_id,
            doc_id=doc_id,
            name=name,
            type=type,
            description=description,
            properties=properties or {},
            embedding=embedding
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        logger.debug(f"[GraphStore] 添加实体: {name} ({type})")
        return entity

    def add_entities_batch(self, entities_data: List[Dict]) -> List[Entity]:
        """批量添加实体"""
        entities = []
        for data in entities_data:
            entity = Entity(
                kb_id=self.kb_id,
                doc_id=data.get("doc_id"),
                name=data["name"],
                type=data["type"],
                description=data.get("description", ""),
                properties=data.get("properties", {}),
                embedding=data.get("embedding")
            )
            entities.append(entity)

        self.db.add_all(entities)
        self.db.commit()
        for e in entities:
            self.db.refresh(e)
        logger.info(f"[GraphStore] 批量添加 {len(entities)} 个实体")
        return entities

    def find_entity_by_name(
        self,
        name: str,
        type: str = None,
        fuzzy: bool = False
    ) -> List[Entity]:
        """根据名称查找实体"""
        query = self.db.query(Entity).filter(Entity.kb_id == self.kb_id)

        if fuzzy:
            query = query.filter(Entity.name.ilike(f"%{name}%"))
        else:
            query = query.filter(func.lower(Entity.name) == name.lower())

        if type:
            query = query.filter(Entity.type == type)

        return query.all()

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据 ID 获取实体"""
        return self.db.query(Entity).filter(
            and_(Entity.id == entity_id, Entity.kb_id == self.kb_id)
        ).first()

    def get_all_entities(self, type: str = None, limit: int = 1000) -> List[Entity]:
        """获取所有实体"""
        query = self.db.query(Entity).filter(Entity.kb_id == self.kb_id)
        if type:
            query = query.filter(Entity.type == type)
        return query.limit(limit).all()

    def get_entity_count(self) -> int:
        """获取实体数量"""
        return self.db.query(Entity).filter(Entity.kb_id == self.kb_id).count()

    def update_entity_embedding(self, entity_id: str, embedding: List[float]) -> bool:
        """更新实体向量"""
        entity = self.get_entity_by_id(entity_id)
        if entity:
            entity.embedding = embedding
            self.db.commit()
            return True
        return False

    def delete_entity(self, entity_id: str) -> bool:
        """删除实体"""
        entity = self.get_entity_by_id(entity_id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False

    # ==================== 关系操作 ====================

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        description: str = "",
        weight: float = 1.0,
        properties: dict = None
    ) -> Optional[Relationship]:
        """添加关系"""
        # 验证实体存在
        source = self.get_entity_by_id(source_id)
        target = self.get_entity_by_id(target_id)
        if not source or not target:
            logger.warning(f"[GraphStore] 添加关系失败: 实体不存在 source={source_id}, target={target_id}")
            return None

        rel = Relationship(
            kb_id=self.kb_id,
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type=relation_type,
            description=description,
            weight=weight,
            properties=properties or {}
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        logger.debug(f"[GraphStore] 添加关系: {source.name} --[{relation_type}]--> {target.name}")
        return rel

    def add_relationships_batch(self, relationships_data: List[Dict]) -> List[Relationship]:
        """批量添加关系"""
        relationships = []
        for data in relationships_data:
            rel = Relationship(
                kb_id=self.kb_id,
                source_entity_id=data["source_id"],
                target_entity_id=data["target_id"],
                relation_type=data["relation_type"],
                description=data.get("description", ""),
                weight=data.get("weight", 1.0),
                properties=data.get("properties", {})
            )
            relationships.append(rel)

        self.db.add_all(relationships)
        self.db.commit()
        logger.info(f"[GraphStore] 批量添加 {len(relationships)} 个关系")
        return relationships

    def get_relationship_count(self) -> int:
        """获取关系数量"""
        return self.db.query(Relationship).filter(Relationship.kb_id == self.kb_id).count()

    def get_all_relationships(self, limit: int = 1000) -> List[Relationship]:
        """获取所有关系"""
        return self.db.query(Relationship).filter(
            Relationship.kb_id == self.kb_id
        ).limit(limit).all()

    # ==================== 图查询操作 ====================

    def get_entity_neighbors(
        self,
        entity_id: str,
        relation_types: List[str] = None,
        direction: str = "both",  # "out", "in", "both"
        max_hops: int = 1
    ) -> List[Dict]:
        """获取实体的邻居节点"""
        visited = set()
        results = []
        self._traverse_neighbors(entity_id, relation_types, direction, max_hops, 0, visited, results)
        return results

    def _traverse_neighbors(
        self,
        entity_id: str,
        relation_types: List[str],
        direction: str,
        max_hops: int,
        current_hop: int,
        visited: set,
        results: List[Dict]
    ):
        """递归遍历邻居"""
        if current_hop >= max_hops or entity_id in visited:
            return
        visited.add(entity_id)

        # 出边 (当前实体 -> 目标实体)
        if direction in ("out", "both"):
            query = self.db.query(Relationship).filter(
                and_(
                    Relationship.kb_id == self.kb_id,
                    Relationship.source_entity_id == entity_id
                )
            )
            if relation_types:
                query = query.filter(Relationship.relation_type.in_(relation_types))

            for rel in query.all():
                target = self.get_entity_by_id(rel.target_entity_id)
                if target and target.id not in visited:
                    results.append({
                        "entity": {
                            "id": target.id,
                            "name": target.name,
                            "type": target.type,
                            "description": target.description
                        },
                        "relation": {
                            "type": rel.relation_type,
                            "direction": "out",
                            "description": rel.description,
                            "weight": rel.weight
                        },
                        "hop": current_hop + 1
                    })
                    self._traverse_neighbors(
                        target.id, relation_types, direction, max_hops,
                        current_hop + 1, visited, results
                    )

        # 入边 (源实体 -> 当前实体)
        if direction in ("in", "both"):
            query = self.db.query(Relationship).filter(
                and_(
                    Relationship.kb_id == self.kb_id,
                    Relationship.target_entity_id == entity_id
                )
            )
            if relation_types:
                query = query.filter(Relationship.relation_type.in_(relation_types))

            for rel in query.all():
                source = self.get_entity_by_id(rel.source_entity_id)
                if source and source.id not in visited:
                    results.append({
                        "entity": {
                            "id": source.id,
                            "name": source.name,
                            "type": source.type,
                            "description": source.description
                        },
                        "relation": {
                            "type": rel.relation_type,
                            "direction": "in",
                            "description": rel.description,
                            "weight": rel.weight
                        },
                        "hop": current_hop + 1
                    })
                    self._traverse_neighbors(
                        source.id, relation_types, direction, max_hops,
                        current_hop + 1, visited, results
                    )

    def get_subgraph(
        self,
        entity_ids: List[str],
        max_hops: int = 1
    ) -> Dict:
        """获取子图 (包含指定实体及其邻居)"""
        all_entities = {}
        all_relations = []
        visited_relations = set()

        for entity_id in entity_ids:
            entity = self.get_entity_by_id(entity_id)
            if entity:
                all_entities[entity.id] = {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description
                }

            neighbors = self.get_entity_neighbors(entity_id, max_hops=max_hops)
            for neighbor in neighbors:
                ent = neighbor["entity"]
                all_entities[ent["id"]] = ent

        # 获取这些实体之间的所有关系
        entity_id_list = list(all_entities.keys())
        if entity_id_list:
            relations = self.db.query(Relationship).filter(
                and_(
                    Relationship.kb_id == self.kb_id,
                    Relationship.source_entity_id.in_(entity_id_list),
                    Relationship.target_entity_id.in_(entity_id_list)
                )
            ).all()

            for rel in relations:
                rel_key = (rel.source_entity_id, rel.target_entity_id, rel.relation_type)
                if rel_key not in visited_relations:
                    visited_relations.add(rel_key)
                    source_name = all_entities.get(rel.source_entity_id, {}).get("name", "")
                    target_name = all_entities.get(rel.target_entity_id, {}).get("name", "")
                    all_relations.append({
                        "source_id": rel.source_entity_id,
                        "source_name": source_name,
                        "target_id": rel.target_entity_id,
                        "target_name": target_name,
                        "relation_type": rel.relation_type,
                        "description": rel.description,
                        "weight": rel.weight
                    })

        return {
            "entities": list(all_entities.values()),
            "relationships": all_relations
        }

    def search_entities_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        type_filter: str = None
    ) -> List[Tuple[Entity, float]]:
        """基于向量相似度搜索实体"""
        query = self.db.query(Entity).filter(
            and_(
                Entity.kb_id == self.kb_id,
                Entity.embedding.isnot(None)
            )
        )
        if type_filter:
            query = query.filter(Entity.type == type_filter)

        entities = query.all()
        if not entities:
            return []

        # 计算余弦相似度
        query_vec = np.array(query_embedding)
        results = []

        for entity in entities:
            if entity.embedding:
                entity_vec = np.array(entity.embedding)
                similarity = np.dot(query_vec, entity_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(entity_vec) + 1e-8
                )
                results.append((entity, float(similarity)))

        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ==================== 统计和清理 ====================

    def get_statistics(self) -> Dict:
        """获取图统计信息"""
        entity_count = self.get_entity_count()
        relationship_count = self.get_relationship_count()

        # 按类型统计实体
        type_stats = self.db.query(
            Entity.type, func.count(Entity.id)
        ).filter(Entity.kb_id == self.kb_id).group_by(Entity.type).all()

        # 按类型统计关系
        rel_type_stats = self.db.query(
            Relationship.relation_type, func.count(Relationship.id)
        ).filter(Relationship.kb_id == self.kb_id).group_by(Relationship.relation_type).all()

        return {
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "entity_types": {t: c for t, c in type_stats},
            "relationship_types": {t: c for t, c in rel_type_stats}
        }

    def clear_all(self) -> Tuple[int, int]:
        """清空知识库的所有图数据"""
        rel_count = self.db.query(Relationship).filter(
            Relationship.kb_id == self.kb_id
        ).delete()
        entity_count = self.db.query(Entity).filter(
            Entity.kb_id == self.kb_id
        ).delete()
        self.db.commit()
        logger.info(f"[GraphStore] 清空图数据: {entity_count} 实体, {rel_count} 关系")
        return entity_count, rel_count

    def clear_by_document(self, doc_id: str) -> Tuple[int, int]:
        """清空指定文档的图数据"""
        # 先获取该文档的实体 ID
        entity_ids = [e.id for e in self.db.query(Entity).filter(
            Entity.doc_id == doc_id
        ).all()]

        rel_count = 0
        if entity_ids:
            # 删除相关关系
            rel_count = self.db.query(Relationship).filter(
                or_(
                    Relationship.source_entity_id.in_(entity_ids),
                    Relationship.target_entity_id.in_(entity_ids)
                )
            ).delete(synchronize_session=False)

        # 删除实体
        entity_count = self.db.query(Entity).filter(
            Entity.doc_id == doc_id
        ).delete()

        self.db.commit()
        logger.info(f"[GraphStore] 清空文档 {doc_id} 图数据: {entity_count} 实体, {rel_count} 关系")
        return entity_count, rel_count
