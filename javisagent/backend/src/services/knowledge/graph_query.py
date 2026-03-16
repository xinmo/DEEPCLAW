"""
GraphQueryEngine - 图查询引擎
支持基于实体的图查询和向量相似度查询
"""
import logging
import re
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from .graph_store import GraphStore
from .embedding import EmbeddingService
from .rag_strategies import GraphRAGExtractor

logger = logging.getLogger("services.knowledge.graph_query")


class GraphQueryEngine:
    """图查询引擎"""

    def __init__(
        self,
        db: Session,
        kb_id: str,
        embedding_service: EmbeddingService,
        llm_service: Optional[Any] = None
    ):
        self.db = db
        self.kb_id = kb_id
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.graph_store = GraphStore(db, kb_id)

    async def query(
        self,
        query: str,
        top_k: int = 5,
        max_hops: int = 2
    ) -> List[Dict]:
        """
        基于查询进行图检索
        1. 从查询中识别实体
        2. 在图中查找匹配实体
        3. 获取相关子图
        4. 格式化为上下文
        """
        logger.info(f"[GraphQuery] 开始图查询 | query='{query[:50]}...' | top_k={top_k}")

        # 1. 从查询中提取实体关键词
        query_entities = await self._extract_query_entities(query)
        logger.info(f"[GraphQuery] 查询实体识别 | 识别到 {len(query_entities)} 个实体: {query_entities}")

        # 2. 在图中查找匹配实体
        matched_entities = []
        for entity_name in query_entities:
            # 精确匹配
            entities = self.graph_store.find_entity_by_name(entity_name)
            if entities:
                matched_entities.extend(entities)
            else:
                # 模糊匹配
                entities = self.graph_store.find_entity_by_name(entity_name, fuzzy=True)
                matched_entities.extend(entities[:3])  # 限制模糊匹配数量

        logger.info(f"[GraphQuery] 实体匹配 | 匹配到 {len(matched_entities)} 个实体")

        # 3. 如果有匹配实体，获取子图
        if matched_entities:
            entity_ids = list(set(e.id for e in matched_entities))[:10]  # 限制数量
            subgraph = self.graph_store.get_subgraph(entity_ids, max_hops=max_hops)
            contexts = self._format_subgraph_context(subgraph)
            logger.info(f"[GraphQuery] 子图检索完成 | 实体={len(subgraph.get('entities', []))} | 关系={len(subgraph.get('relationships', []))}")
            return contexts[:top_k]

        # 4. 如果没有精确匹配，使用向量相似度搜索实体
        logger.info(f"[GraphQuery] 无精确匹配，使用向量相似度搜索")
        query_embedding = self.embedding_service.embed_query(query)
        similar_entities = self.graph_store.search_entities_by_embedding(
            query_embedding, top_k=top_k * 2
        )

        if similar_entities:
            entity_ids = [e.id for e, _ in similar_entities[:5]]
            subgraph = self.graph_store.get_subgraph(entity_ids, max_hops=1)
            contexts = self._format_subgraph_context(subgraph)
            logger.info(f"[GraphQuery] 向量相似度检索完成 | 结果数={len(contexts)}")
            return contexts[:top_k]

        logger.info(f"[GraphQuery] 未找到相关图数据")
        return []

    async def _extract_query_entities(self, query: str) -> List[str]:
        """从查询中提取实体关键词"""
        # 方法1: 如果有 LLM，使用 LLM 提取
        if self.llm_service:
            try:
                entities, _ = await GraphRAGExtractor.extract_entities_and_relations(
                    query, self.llm_service
                )
                return [e.name for e in entities]
            except Exception as e:
                logger.warning(f"[GraphQuery] LLM 实体提取失败: {e}")

        # 方法2: 简单的关键词提取 (基于规则)
        return self._extract_keywords(query)

    def _extract_keywords(self, text: str) -> List[str]:
        """基于规则的关键词提取"""
        # 移除常见停用词
        stopwords = {
            '的', '是', '在', '有', '和', '与', '了', '等', '为', '被',
            '这', '那', '什么', '怎么', '如何', '哪些', '哪个', '请问',
            'the', 'is', 'are', 'what', 'how', 'which', 'where', 'when'
        }

        # 提取中文词汇 (2-10个字符)
        chinese_pattern = r'[\u4e00-\u9fa5]{2,10}'
        chinese_words = re.findall(chinese_pattern, text)

        # 提取英文词汇
        english_pattern = r'[a-zA-Z]{3,}'
        english_words = re.findall(english_pattern, text)

        # 过滤停用词
        keywords = []
        for word in chinese_words + english_words:
            if word.lower() not in stopwords and word not in stopwords:
                keywords.append(word)

        return list(set(keywords))[:10]  # 限制数量

    def _format_subgraph_context(self, subgraph: Dict) -> List[Dict]:
        """将子图格式化为检索上下文"""
        contexts = []
        entities = subgraph.get("entities", [])
        relationships = subgraph.get("relationships", [])

        # 构建实体ID到关系的映射
        entity_relations = {}
        for rel in relationships:
            source_id = rel.get("source_id")
            if source_id not in entity_relations:
                entity_relations[source_id] = []
            entity_relations[source_id].append(rel)

        # 为每个实体生成上下文
        for entity in entities:
            entity_id = entity.get("id")
            entity_name = entity.get("name", "")
            entity_type = entity.get("type", "")
            entity_desc = entity.get("description", "")

            # 构建上下文文本
            context_parts = [f"【{entity_type}】{entity_name}"]
            if entity_desc:
                context_parts.append(f"描述: {entity_desc}")

            # 添加关系信息
            relations = entity_relations.get(entity_id, [])
            if relations:
                context_parts.append("相关关系:")
                for rel in relations[:5]:  # 限制关系数量
                    rel_type = rel.get("relation_type", "")
                    target_name = rel.get("target_name", "")
                    rel_desc = rel.get("description", "")
                    rel_text = f"  - {rel_type} → {target_name}"
                    if rel_desc:
                        rel_text += f" ({rel_desc})"
                    context_parts.append(rel_text)

            context_text = "\n".join(context_parts)

            contexts.append({
                "id": entity_id,
                "content": context_text,
                "source": "graph",
                "metadata": {
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "relation_count": len(relations)
                }
            })

        return contexts

    def get_entity_context(self, entity_id: str, max_hops: int = 1) -> Optional[Dict]:
        """获取单个实体的上下文"""
        entity = self.graph_store.get_entity_by_id(entity_id)
        if not entity:
            return None

        neighbors = self.graph_store.get_entity_neighbors(entity_id, max_hops=max_hops)

        context_parts = [f"【{entity.type}】{entity.name}"]
        if entity.description:
            context_parts.append(f"描述: {entity.description}")

        if neighbors:
            context_parts.append("相关实体:")
            for neighbor in neighbors[:10]:
                ent = neighbor["entity"]
                rel = neighbor["relation"]
                direction = "→" if rel["direction"] == "out" else "←"
                context_parts.append(f"  - {rel['type']} {direction} {ent['name']} ({ent['type']})")

        return {
            "id": entity_id,
            "content": "\n".join(context_parts),
            "source": "graph",
            "metadata": {
                "entity_name": entity.name,
                "entity_type": entity.type,
                "neighbor_count": len(neighbors)
            }
        }
