from typing import List, Dict
from rank_bm25 import BM25Okapi
from FlagEmbedding import FlagReranker
from .vector_store import MilvusVectorStore
from .embedding import EmbeddingService

class HybridRetriever:
    """混合检索器：向量检索 + BM25 + Rerank"""

    def __init__(self, vector_store: MilvusVectorStore, embedding_service: EmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.reranker = FlagReranker('BAAI/bge-reranker-base', use_fp16=True)

    def retrieve(self, query: str, top_k: int = 5, vector_top_k: int = 20) -> List[Dict]:
        # 1. 向量检索
        query_embedding = self.embedding_service.embed_query(query)
        vector_results = self.vector_store.search(query_embedding, top_k=vector_top_k)

        if not vector_results:
            return []

        # 2. BM25 检索
        corpus = [r["content"] for r in vector_results]
        tokenized_corpus = [doc.split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(query.split())

        # 3. RRF 融合
        rrf_results = self._rrf_merge(vector_results, bm25_scores)

        # 4. Rerank 重排序
        if len(rrf_results) > 0:
            pairs = [[query, r["content"]] for r in rrf_results[:20]]
            rerank_scores = self.reranker.compute_score(pairs)
            if not isinstance(rerank_scores, list):
                rerank_scores = [rerank_scores]
            for i, score in enumerate(rerank_scores):
                rrf_results[i]["rerank_score"] = score
            rrf_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return rrf_results[:top_k]

    def _rrf_merge(self, vector_results: List[Dict], bm25_scores: List[float], k: int = 60) -> List[Dict]:
        """RRF (Reciprocal Rank Fusion) 融合"""
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

        return sorted(vector_results, key=lambda x: x["rrf_score"], reverse=True)
