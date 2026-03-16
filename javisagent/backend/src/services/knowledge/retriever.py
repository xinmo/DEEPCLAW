"""
混合检索器：支持多种RAG优化策略
P0: BM25中文分词优化
P1: Contextual Retrieval
P2: Query改写 (HyDE/Multi-Query)
P3-P5: 通过配置启用
"""

import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from .vector_store import MilvusVectorStore
from .embedding import EmbeddingService
from .rag_strategies import (
    RAGConfig,
    RetrievalStrategy,
    ChineseTokenizer,
    QueryRewriter,
)
from .graph_store import GraphStore
from .graph_query import GraphQueryEngine
from src.models.knowledge import Entity

logger = logging.getLogger("services.knowledge.retriever")


class HybridRetriever:
    """混合检索器：向量检索 + BM25 + Rerank + RAG优化策略"""

    def __init__(
        self,
        vector_store: MilvusVectorStore,
        embedding_service: EmbeddingService,
        rag_config: Optional[RAGConfig] = None,
        llm_service: Optional[Any] = None,
        db_session: Optional[Session] = None,
        kb_id: Optional[str] = None
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.rag_config = rag_config or RAGConfig()
        self.llm_service = llm_service
        self.db_session = db_session
        self.kb_id = kb_id
        self._reranker: Optional[object] = None
        # 父文档映射 (P4: Parent Document Retriever)
        self._parent_doc_map: Dict[str, str] = {}

        # 初始化时记录完整配置
        logger.info(f"[HybridRetriever] 初始化 | 检索策略={self.rag_config.retrieval_strategy.value} | "
                     f"切片策略={self.rag_config.chunking_strategy.value} | "
                     f"LLM可用={llm_service is not None}")
        logger.info(f"[HybridRetriever] 策略标志 | "
                     f"P0-中文分词={self.rag_config.use_chinese_tokenizer} | "
                     f"P1-上下文增强={self.rag_config.use_contextual_embedding} | "
                     f"P2-HyDE={self.rag_config.use_hyde} | "
                     f"P2-MultiQuery={self.rag_config.use_multi_query} | "
                     f"P5-GraphRAG={self.rag_config.use_graph_rag}")

    def set_parent_doc_map(self, parent_map: Dict[str, str]):
        """设置父文档映射 (P4)"""
        self._parent_doc_map = parent_map

    @property
    def reranker(self):
        """延迟加载 reranker，避免启动时导入错误"""
        if self._reranker is None:
            try:
                from FlagEmbedding import FlagReranker
                self._reranker = FlagReranker('BAAI/bge-reranker-base', use_fp16=True)
                logger.info("[Reranker] 加载成功: BAAI/bge-reranker-base (fp16)")
            except Exception as e:
                logger.warning(f"[Reranker] 加载失败，已禁用: {e}")
                self._reranker = False
        return self._reranker if self._reranker is not False else None

    def retrieve(self, query: str, top_k: int = 5, vector_top_k: int = 20) -> List[Dict]:
        """
        执行检索
        Args:
            query: 用户查询
            top_k: 返回结果数量
            vector_top_k: 向量检索候选数量
        Returns:
            检索结果列表
        """
        config = self.rag_config
        strategy = config.retrieval_strategy.value
        logger.info(f"[检索] ========== 开始同步检索 ==========")
        logger.info(f"[检索] 策略={strategy} | query='{query[:50]}...' | top_k={top_k} | vector_top_k={vector_top_k}")
        retrieve_start = time.time()

        # 根据检索策略选择不同的检索方式
        if config.retrieval_strategy == RetrievalStrategy.BASIC:
            logger.info(f"[检索] >>> 进入 BASIC 基础向量检索路径")
            results = self._basic_retrieve(query, top_k, vector_top_k)
        elif config.retrieval_strategy == RetrievalStrategy.HYBRID:
            logger.info(f"[检索] >>> 进入 HYBRID 混合检索路径 (向量+BM25+RRF+Rerank)")
            results = self._hybrid_retrieve(query, top_k, vector_top_k)
        elif config.retrieval_strategy == RetrievalStrategy.CONTEXTUAL:
            logger.info(f"[检索] >>> 进入 CONTEXTUAL 上下文检索路径 (P1)")
            results = self._hybrid_retrieve(query, top_k, vector_top_k)
        elif config.retrieval_strategy == RetrievalStrategy.HYDE:
            logger.info(f"[检索] >>> 进入 HyDE 假设文档检索路径 (P2)")
            results = self._hyde_retrieve(query, top_k, vector_top_k)
        elif config.retrieval_strategy == RetrievalStrategy.MULTI_QUERY:
            logger.info(f"[检索] >>> 进入 MULTI_QUERY 多查询改写检索路径 (P2)")
            results = self._multi_query_retrieve(query, top_k, vector_top_k)
        elif config.retrieval_strategy == RetrievalStrategy.GRAPH_RAG:
            logger.info(f"[检索] >>> 进入 GRAPH_RAG 知识图谱增强检索路径 (P5)")
            logger.info(f"[GraphRAG] 配置: use_graph_rag={config.use_graph_rag}")

            # 检查是否有图数据和必要的依赖
            if self.db_session and self.kb_id:
                entity_count = self.db_session.query(Entity).filter(Entity.kb_id == self.kb_id).count()
                if entity_count > 0:
                    logger.info(f"[GraphRAG] 知识库有 {entity_count} 个实体，使用图增强检索")
                    results = self._graph_rag_retrieve(query, top_k, vector_top_k)
                else:
                    logger.warning(f"[GraphRAG] 知识库无实体数据，降级为混合检索")
                    results = self._hybrid_retrieve(query, top_k, vector_top_k)
            else:
                logger.warning(f"[GraphRAG] 缺少数据库会话或知识库ID，降级为混合检索")
                results = self._hybrid_retrieve(query, top_k, vector_top_k)
        else:
            logger.warning(f"[检索] 未知策略 '{strategy}'，降级为混合检索")
            results = self._hybrid_retrieve(query, top_k, vector_top_k)

        total_time = time.time() - retrieve_start
        logger.info(f"[检索] ========== 检索完成 ========== | 策略={strategy} | 返回 {len(results)} 条结果 | 总耗时={total_time:.2f}s")
        return results

    async def aretrieve(self, query: str, top_k: int = 5, vector_top_k: int = 20) -> List[Dict]:
        """
        异步检索（支持HyDE和Multi-Query）
        """
        config = self.rag_config
        strategy = config.retrieval_strategy.value
        logger.info(f"[检索] 开始异步检索 | 策略={strategy} | query='{query[:50]}...' | top_k={top_k}")

        if config.retrieval_strategy == RetrievalStrategy.HYDE and self.llm_service:
            logger.info("[HyDE] 使用 HyDE 假设文档策略进行异步检索")
            results = await self._hyde_retrieve_async(query, top_k, vector_top_k)
        elif config.retrieval_strategy == RetrievalStrategy.MULTI_QUERY and self.llm_service:
            logger.info(f"[Multi-Query] 使用多查询改写策略 | 改写数量={config.multi_query_count}")
            results = await self._multi_query_retrieve_async(query, top_k, vector_top_k)
        else:
            if config.retrieval_strategy in [RetrievalStrategy.HYDE, RetrievalStrategy.MULTI_QUERY]:
                logger.warning(f"[检索] 策略={strategy} 需要 LLM 但未提供，降级为同步检索")
            results = self.retrieve(query, top_k, vector_top_k)

        logger.info(f"[检索] 异步检索完成 | 策略={strategy} | 返回 {len(results)} 条结果")
        return results

    def _basic_retrieve(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """基础向量检索"""
        logger.info("[Basic] 执行基础向量检索")
        query_embedding = self.embedding_service.embed_query(query)
        results = self.vector_store.search(query_embedding, top_k=top_k)
        logger.info(f"[Basic] 向量检索返回 {len(results)} 条结果")
        return self._apply_parent_expansion(results)

    def _hybrid_retrieve(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """混合检索：向量 + BM25 + RRF + Rerank"""
        logger.info(f"[Hybrid] ---- 开始混合检索 ---- | 中文分词={self.rag_config.use_chinese_tokenizer}")

        # 1. 向量检索
        embed_start = time.time()
        query_embedding = self.embedding_service.embed_query(query)
        logger.info(f"[Hybrid] 查询向量化完成 | 耗时={time.time()-embed_start:.3f}s")

        vector_start = time.time()
        vector_results = self.vector_store.search(query_embedding, top_k=vector_top_k)
        logger.info(f"[Hybrid] 步骤1-向量检索 | 返回 {len(vector_results)} 条候选 | 耗时={time.time()-vector_start:.3f}s")
        if vector_results:
            top_scores = [r.get("score", 0) for r in vector_results[:3]]
            logger.info(f"[Hybrid]   向量检索 Top3 分数: {[f'{s:.4f}' for s in top_scores]}")

        if not vector_results:
            logger.warning("[Hybrid] 向量检索无结果，终止")
            return []

        # 2. BM25 检索 (P0: 使用中文分词)
        bm25_start = time.time()
        corpus = [r["content"] for r in vector_results]
        tokenized_corpus = [
            ChineseTokenizer.tokenize(doc, self.rag_config.use_chinese_tokenizer)
            for doc in corpus
        ]
        tokenized_query = ChineseTokenizer.tokenize(
            query, self.rag_config.use_chinese_tokenizer
        )
        logger.info(f"[Hybrid] 步骤2-BM25 | 查询分词结果: {tokenized_query[:10]}{'...' if len(tokenized_query) > 10 else ''}")

        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(tokenized_query)
        bm25_time = time.time() - bm25_start

        # BM25 分数分布
        if len(bm25_scores) > 0:
            scores_sorted = sorted(bm25_scores, reverse=True)
            logger.info(f"[Hybrid]   BM25 分数分布 | max={scores_sorted[0]:.4f} | "
                         f"min={scores_sorted[-1]:.4f} | "
                         f"Top3={[f'{s:.4f}' for s in scores_sorted[:3]]} | 耗时={bm25_time:.3f}s")

        # 3. RRF 融合
        rrf_start = time.time()
        rrf_results = self._rrf_merge(vector_results, bm25_scores)
        logger.info(f"[Hybrid] 步骤3-RRF融合 | 候选数={len(rrf_results)} | 耗时={time.time()-rrf_start:.3f}s")
        if rrf_results:
            logger.info(f"[Hybrid]   RRF Top3: {[f'rrf={r.get('rrf_score', 0):.4f} vec_rank={r.get('vector_rank', 0)} bm25={r.get('bm25_score', 0):.4f}' for r in rrf_results[:3]]}")

        # 4. Rerank 重排序
        reranker = self.reranker
        if len(rrf_results) > 0 and reranker is not None:
            rerank_count = min(len(rrf_results), 20)
            logger.info(f"[Hybrid] 步骤4-Rerank重排序 | 候选数={rerank_count}")
            rerank_start = time.time()
            try:
                pairs = [[query, r["content"]] for r in rrf_results[:20]]
                rerank_scores = reranker.compute_score(pairs)
                if not isinstance(rerank_scores, list):
                    rerank_scores = [rerank_scores]
                for i, score in enumerate(rerank_scores):
                    if isinstance(score, (int, float)):
                        rrf_results[i]["rerank_score"] = score
                rrf_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                rerank_time = time.time() - rerank_start
                logger.info(f"[Hybrid]   Rerank 完成 | 耗时={rerank_time:.3f}s")
                logger.info(f"[Hybrid]   Rerank Top3 分数: {[f'{r.get('rerank_score', 0):.4f}' for r in rrf_results[:3]]}")
            except Exception as e:
                logger.warning(f"[Hybrid] Rerank 失败，跳过重排序: {e}")
        else:
            logger.info(f"[Hybrid] 步骤4-跳过Rerank | reranker可用={reranker is not None} | 候选数={len(rrf_results)}")

        results = rrf_results[:top_k]

        # 5. P4: 父文档扩展
        results = self._apply_parent_expansion(results)
        logger.info(f"[Hybrid] ---- 混合检索完成 ---- | 最终返回 {len(results)} 条")
        for i, r in enumerate(results):
            logger.info(f"[Hybrid]   最终结果[{i+1}]: score={r.get('rerank_score', r.get('rrf_score', r.get('score', 0))):.4f} | "
                         f"doc_id={r.get('doc_id', 'N/A')} | 内容='{r['content'][:50]}...'")
        return results

    def _hyde_retrieve(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """
        HyDE检索 (P2): 同步版本
        注意：完整的HyDE需要LLM，这里提供降级方案
        """
        if self.llm_service is None:
            # 无LLM时降级为混合检索
            return self._hybrid_retrieve(query, top_k, vector_top_k)

        # 同步场景下无法调用async LLM，降级处理
        return self._hybrid_retrieve(query, top_k, vector_top_k)

    async def _hyde_retrieve_async(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """
        HyDE检索 (P2): 异步版本
        使用LLM生成假设文档，用假设文档的embedding进行检索
        """
        if self.llm_service is None:
            logger.warning("[HyDE] 无 LLM 服务，降级为混合检索")
            return self._hybrid_retrieve(query, top_k, vector_top_k)

        # 生成假设文档
        logger.info("[HyDE] 正在生成假设文档...")
        hyde_doc = await QueryRewriter.generate_hyde_document(query, self.llm_service)
        logger.info(f"[HyDE] 假设文档生成完成 | 长度={len(hyde_doc)} 字符 | 内容预览='{hyde_doc[:80]}...'")

        # 使用假设文档的embedding检索
        hyde_embedding = self.embedding_service.embed_query(hyde_doc)
        vector_results = self.vector_store.search(hyde_embedding, top_k=vector_top_k)
        logger.info(f"[HyDE] 向量检索返回 {len(vector_results)} 条候选")

        if not vector_results:
            return []

        # 同时用原始query做BM25
        corpus = [r["content"] for r in vector_results]
        tokenized_corpus = [
            ChineseTokenizer.tokenize(doc, self.rag_config.use_chinese_tokenizer)
            for doc in corpus
        ]
        tokenized_query = ChineseTokenizer.tokenize(
            query, self.rag_config.use_chinese_tokenizer
        )

        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(tokenized_query)

        rrf_results = self._rrf_merge(vector_results, bm25_scores)

        # Rerank使用原始query
        reranker = self.reranker
        if len(rrf_results) > 0 and reranker is not None:
            logger.info(f"[HyDE] 开始 Rerank 重排序 | 候选数={min(len(rrf_results), 20)}")
            try:
                pairs = [[query, r["content"]] for r in rrf_results[:20]]
                rerank_scores = reranker.compute_score(pairs)
                if not isinstance(rerank_scores, list):
                    rerank_scores = [rerank_scores]
                for i, score in enumerate(rerank_scores):
                    if isinstance(score, (int, float)):
                        rrf_results[i]["rerank_score"] = score
                rrf_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                logger.info(f"[HyDE] Rerank 完成")
            except Exception as e:
                logger.warning(f"[HyDE] Rerank 失败，跳过重排序: {e}")
        else:
            logger.info(f"[HyDE] 跳过 Rerank | reranker可用={reranker is not None}")

        return self._apply_parent_expansion(rrf_results[:top_k])

    def _multi_query_retrieve(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """Multi-Query检索 (P2): 同步版本"""
        if self.llm_service is None:
            return self._hybrid_retrieve(query, top_k, vector_top_k)
        return self._hybrid_retrieve(query, top_k, vector_top_k)

    async def _multi_query_retrieve_async(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """
        Multi-Query检索 (P2): 异步版本
        生成多个查询变体，合并检索结果
        """
        if self.llm_service is None:
            logger.warning("[Multi-Query] 无 LLM 服务，降级为混合检索")
            return self._hybrid_retrieve(query, top_k, vector_top_k)

        # 生成多个查询
        logger.info(f"[Multi-Query] 正在生成 {self.rag_config.multi_query_count} 个查询变体...")
        queries = await QueryRewriter.generate_multi_queries(
            query, self.llm_service, self.rag_config.multi_query_count
        )
        logger.info(f"[Multi-Query] 生成 {len(queries)} 个查询: {queries}")

        # 对每个查询进行检索
        all_results: Dict[str, Dict] = {}  # id -> result

        for q in queries:
            query_embedding = self.embedding_service.embed_query(q)
            results = self.vector_store.search(query_embedding, top_k=vector_top_k // len(queries))
            logger.info(f"[Multi-Query] 子查询 '{q[:30]}...' 返回 {len(results)} 条结果")

            for r in results:
                rid = r.get("id", r.get("content", "")[:50])
                if rid not in all_results:
                    all_results[rid] = r
                    all_results[rid]["query_hits"] = 1
                else:
                    all_results[rid]["query_hits"] = all_results[rid].get("query_hits", 1) + 1

        # 按命中次数和分数排序
        merged_results = list(all_results.values())
        merged_results.sort(
            key=lambda x: (x.get("query_hits", 1), x.get("score", 0)),
            reverse=True
        )

        # BM25 + RRF
        if merged_results:
            corpus = [r["content"] for r in merged_results]
            tokenized_corpus = [
                ChineseTokenizer.tokenize(doc, self.rag_config.use_chinese_tokenizer)
                for doc in corpus
            ]
            tokenized_query = ChineseTokenizer.tokenize(
                query, self.rag_config.use_chinese_tokenizer
            )

            bm25 = BM25Okapi(tokenized_corpus)
            bm25_scores = bm25.get_scores(tokenized_query)

            rrf_results = self._rrf_merge(merged_results, bm25_scores)

            # Rerank
            if self.reranker is not None:
                try:
                    pairs = [[query, r["content"]] for r in rrf_results[:20]]
                    rerank_scores = self.reranker.compute_score(pairs)
                    if not isinstance(rerank_scores, list):
                        rerank_scores = [rerank_scores]
                    for i, score in enumerate(rerank_scores):
                        if isinstance(score, (int, float)):
                            rrf_results[i]["rerank_score"] = score
                    rrf_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Rerank 失败，跳过重排序: {e}")

            return self._apply_parent_expansion(rrf_results[:top_k])

        return []

    def _apply_parent_expansion(self, results: List[Dict]) -> List[Dict]:
        """
        P4: 父文档扩展
        如果检索到的是子chunk，返回对应的父chunk内容
        """
        if not self._parent_doc_map:
            logger.debug("[P4] 无父文档映射，跳过父文档扩展")
            return results

        expanded_count = 0
        for r in results:
            child_id = r.get("id", "")
            if child_id in self._parent_doc_map:
                # 保留原始子chunk内容用于高亮
                r["child_content"] = r["content"]
                # 替换为父chunk内容
                r["content"] = self._parent_doc_map[child_id]
                r["is_expanded"] = True
                expanded_count += 1

        if expanded_count > 0:
            logger.info(f"[P4] 父文档扩展 | 扩展了 {expanded_count}/{len(results)} 条结果")

        return results

    def _rrf_merge(self, vector_results: List[Dict], bm25_scores: List[float], k: int = 60) -> List[Dict]:
        """RRF (Reciprocal Rank Fusion) 融合"""
        logger.debug(f"[RRF] 开始融合 | 向量结果数={len(vector_results)} | BM25分数数={len(bm25_scores)} | k={k}")

        # 向量排名
        for i, r in enumerate(vector_results):
            r["vector_rank"] = i + 1
            r["bm25_score"] = bm25_scores[i] if i < len(bm25_scores) else 0

        # BM25 排名
        bm25_ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
        bm25_rank_map = {idx: rank + 1 for rank, idx in enumerate(bm25_ranked)}

        # RRF 分数
        for i, r in enumerate(vector_results):
            vector_rrf = 1 / (k + r["vector_rank"])
            bm25_rrf = 1 / (k + bm25_rank_map.get(i, len(vector_results)))
            r["rrf_score"] = vector_rrf + bm25_rrf

        merged = sorted(vector_results, key=lambda x: x["rrf_score"], reverse=True)

        # 记录融合前后排名变化
        if len(merged) >= 3:
            logger.debug(f"[RRF] 融合后 Top3 排名变化:")
            for i, r in enumerate(merged[:3]):
                logger.debug(f"[RRF]   #{i+1}: vec_rank={r['vector_rank']} | bm25_score={r['bm25_score']:.4f} | rrf_score={r['rrf_score']:.6f}")

        return merged

    def _graph_rag_retrieve(self, query: str, top_k: int, vector_top_k: int) -> List[Dict]:
        """
        GraphRAG 图增强检索 (P5)
        融合向量检索和图查询结果
        """
        logger.info(f"[GraphRAG] ---- 开始图增强检索 ----")
        graph_start = time.time()

        # 1. 向量检索 (基础)
        vector_start = time.time()
        query_embedding = self.embedding_service.embed_query(query)
        vector_results = self.vector_store.search(query_embedding, top_k=vector_top_k)
        logger.info(f"[GraphRAG] 步骤1-向量检索 | 返回 {len(vector_results)} 条 | 耗时={time.time()-vector_start:.3f}s")

        # 2. 图查询
        graph_query_start = time.time()
        graph_store = GraphStore(self.db_session, self.kb_id)
        graph_results = self._sync_graph_query(query, graph_store, top_k)
        logger.info(f"[GraphRAG] 步骤2-图查询 | 返回 {len(graph_results)} 条 | 耗时={time.time()-graph_query_start:.3f}s")

        # 3. 结果融合
        if graph_results:
            fused_results = self._rrf_fusion_multi([
                ("vector", vector_results, 0.6),
                ("graph", graph_results, 0.4)
            ])
            logger.info(f"[GraphRAG] 步骤3-RRF融合 | 融合后 {len(fused_results)} 条")
        else:
            logger.info(f"[GraphRAG] 无图查询结果，仅使用向量检索")
            fused_results = vector_results

        # 4. BM25 + Rerank (可选)
        if fused_results:
            corpus = [r.get("content", "") for r in fused_results]
            tokenized_corpus = [
                ChineseTokenizer.tokenize(doc, self.rag_config.use_chinese_tokenizer)
                for doc in corpus
            ]
            tokenized_query = ChineseTokenizer.tokenize(
                query, self.rag_config.use_chinese_tokenizer
            )

            bm25 = BM25Okapi(tokenized_corpus)
            bm25_scores = bm25.get_scores(tokenized_query)

            for i, score in enumerate(bm25_scores):
                if i < len(fused_results):
                    fused_results[i]["bm25_score"] = score

            # Rerank
            reranker = self.reranker
            if reranker is not None and len(fused_results) > 0:
                logger.info(f"[GraphRAG] 步骤4-Rerank重排序")
                try:
                    pairs = [[query, r.get("content", "")] for r in fused_results[:20]]
                    rerank_scores = reranker.compute_score(pairs)
                    if not isinstance(rerank_scores, list):
                        rerank_scores = [rerank_scores]
                    for i, score in enumerate(rerank_scores):
                        if isinstance(score, (int, float)) and i < len(fused_results):
                            fused_results[i]["rerank_score"] = score
                    fused_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                except Exception as e:
                    logger.warning(f"[GraphRAG] Rerank 失败: {e}")

        results = fused_results[:top_k]
        results = self._apply_parent_expansion(results)

        total_time = time.time() - graph_start
        logger.info(f"[GraphRAG] ---- 图增强检索完成 ---- | 返回 {len(results)} 条 | 总耗时={total_time:.2f}s")
        return results

    def _sync_graph_query(self, query: str, graph_store: GraphStore, top_k: int) -> List[Dict]:
        """同步图查询 (不使用 LLM 实体提取)"""
        import re

        # 简单关键词提取
        stopwords = {'的', '是', '在', '有', '和', '与', '了', '等', '为', '被', '这', '那', '什么', '怎么', '如何'}
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,10}', query)
        english_words = re.findall(r'[a-zA-Z]{3,}', query)
        keywords = [w for w in chinese_words + english_words if w.lower() not in stopwords][:10]

        if not keywords:
            return []

        # 在图中查找匹配实体
        matched_entities = []
        for keyword in keywords:
            entities = graph_store.find_entity_by_name(keyword, fuzzy=True)
            matched_entities.extend(entities[:3])

        if not matched_entities:
            return []

        # 获取子图
        entity_ids = list(set(e.id for e in matched_entities))[:10]
        subgraph = graph_store.get_subgraph(entity_ids, max_hops=2)

        # 格式化为检索结果
        contexts = []
        for entity in subgraph.get("entities", []):
            entity_id = entity.get("id")
            entity_name = entity.get("name", "")
            entity_type = entity.get("type", "")
            entity_desc = entity.get("description", "")

            # 获取该实体的关系
            relations = [r for r in subgraph.get("relationships", []) if r.get("source_id") == entity_id]

            context_parts = [f"【{entity_type}】{entity_name}"]
            if entity_desc:
                context_parts.append(f"描述: {entity_desc}")
            if relations:
                context_parts.append("相关关系:")
                for rel in relations[:5]:
                    context_parts.append(f"  - {rel.get('relation_type', '')} → {rel.get('target_name', '')}")

            contexts.append({
                "id": entity_id,
                "content": "\n".join(context_parts),
                "source": "graph",
                "score": 0.8,  # 图结果的基础分数
                "metadata": {
                    "entity_name": entity_name,
                    "entity_type": entity_type
                }
            })

        return contexts[:top_k * 2]

    def _rrf_fusion_multi(
        self,
        result_lists: List[Tuple[str, List[Dict], float]],
        k: int = 60
    ) -> List[Dict]:
        """
        多源 RRF 融合
        Args:
            result_lists: [(source_name, results, weight), ...]
            k: RRF 参数
        """
        scores = {}

        for source, results, weight in result_lists:
            for rank, result in enumerate(results):
                # 使用 content 的前50字符作为唯一标识
                doc_key = result.get("id") or result.get("content", "")[:50]
                if doc_key not in scores:
                    scores[doc_key] = {"result": result.copy(), "rrf_score": 0, "sources": []}

                rrf_contribution = weight * (1 / (k + rank + 1))
                scores[doc_key]["rrf_score"] += rrf_contribution
                scores[doc_key]["sources"].append(source)

                # 合并元数据
                if "metadata" in result:
                    if "metadata" not in scores[doc_key]["result"]:
                        scores[doc_key]["result"]["metadata"] = {}
                    scores[doc_key]["result"]["metadata"].update(result.get("metadata", {}))

        # 按 RRF 分数排序
        sorted_results = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)

        # 返回结果并添加融合信息
        final_results = []
        for item in sorted_results:
            result = item["result"]
            result["rrf_score"] = item["rrf_score"]
            result["fusion_sources"] = item["sources"]
            final_results.append(result)

        return final_results
