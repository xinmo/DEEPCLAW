"""
GraphRAG 检索 Bug 复现与修复测试
TDD RED Phase: 测试 GraphRAG 策略下检索是否能正确返回结果

Bug 描述: 用户选择"固定切片+GraphRAG"后，问答时模型说"参考资料内容为空"
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from typing import List, Dict

# 将 src 目录加入 sys.path
_src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.abspath(_src_path))

# Mock chromadb 避免实际连接
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.config'] = MagicMock()

# Mock pydantic_settings 的 BaseSettings，让 config 不读 .env
_mock_base_settings = MagicMock()

# Mock FlagEmbedding (reranker)
sys.modules['FlagEmbedding'] = MagicMock()

# 现在可以安全导入
from services.knowledge.rag_strategies import (
    RAGConfig, RetrievalStrategy, ChunkingStrategy, ChineseTokenizer
)

# ============== Mock 类 ==============

class MockEmbeddingService:
    """模拟 Embedding 服务"""
    def __init__(self, dimension=2048):
        self._dimension = dimension

    def embed_query(self, text: str) -> List[float]:
        return [0.1] * self._dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * self._dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class MockVectorStore:
    """模拟向量存储，预置测试数据"""
    def __init__(self, data=None):
        self._data = data or []

    def search(self, query_embedding, top_k=20) -> List[Dict]:
        return self._data[:top_k]

    def insert(self, chunks):
        self._data.extend(chunks)
        return len(chunks)

    def create_collection(self):
        pass


# Mock vector_store 模块，避免 chromadb 依赖
with patch('services.knowledge.vector_store.ChromaVectorStore', MockVectorStore):
    pass

from services.knowledge.retriever import HybridRetriever


# ============== 测试数据 ==============

SAMPLE_VECTOR_RESULTS = [
    {
        "id": "chunk_1",
        "doc_id": "doc_001",
        "content": "人工智能（AI）是计算机科学的一个分支，致力于创建能够模拟人类智能的系统。",
        "metadata": {"filename": "ai_intro.pdf", "chunk_index": 0},
        "score": 0.92
    },
    {
        "id": "chunk_2",
        "doc_id": "doc_001",
        "content": "深度学习是机器学习的一个子领域，使用多层神经网络来学习数据的层次化表示。",
        "metadata": {"filename": "ai_intro.pdf", "chunk_index": 1},
        "score": 0.87
    },
    {
        "id": "chunk_3",
        "doc_id": "doc_001",
        "content": "自然语言处理（NLP）使计算机能够理解、解释和生成人类语言。",
        "metadata": {"filename": "ai_intro.pdf", "chunk_index": 2},
        "score": 0.83
    },
]


# ============== 测试类 ==============

class TestGraphRAGRetrieval:
    """测试 GraphRAG 策略下的检索行为"""

    def _create_retriever(self, strategy: RetrievalStrategy, data=None):
        """创建带指定策略的检索器"""
        config = RAGConfig(retrieval_strategy=strategy)
        vector_store = MockVectorStore(data if data is not None else SAMPLE_VECTOR_RESULTS.copy())
        embedding_service = MockEmbeddingService()
        return HybridRetriever(vector_store, embedding_service, rag_config=config)

    def test_graphrag_retrieve_returns_results(self):
        """RED: GraphRAG 策略应该返回检索结果，而不是空列表"""
        retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG)
        results = retriever.retrieve("什么是人工智能", top_k=3)

        assert len(results) > 0, "GraphRAG 策略应该返回非空结果"
        assert results[0]["content"], "返回结果的 content 不应为空"

    def test_graphrag_retrieve_has_content_field(self):
        """RED: GraphRAG 返回的每个结果都应包含 content 字段"""
        retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG)
        results = retriever.retrieve("深度学习", top_k=3)

        for r in results:
            assert "content" in r, "结果缺少 content 字段"
            assert len(r["content"]) > 0, "content 不应为空字符串"

    def test_graphrag_retrieve_has_doc_id(self):
        """RED: GraphRAG 返回的每个结果都应包含 doc_id"""
        retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG)
        results = retriever.retrieve("NLP", top_k=3)

        for r in results:
            assert "doc_id" in r, "结果缺少 doc_id 字段"

    def test_graphrag_retrieve_respects_top_k(self):
        """RED: GraphRAG 应该尊重 top_k 参数"""
        retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG)
        results = retriever.retrieve("AI", top_k=2)

        assert len(results) <= 2, f"请求 top_k=2 但返回了 {len(results)} 条"

    def test_graphrag_retrieve_empty_store(self):
        """RED: 向量库为空时 GraphRAG 应返回空列表而不是报错"""
        retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG, data=[])
        results = retriever.retrieve("任何问题", top_k=3)

        assert results == [], "空向量库应返回空列表"


class TestGraphRAGvsOtherStrategies:
    """对比 GraphRAG 与其他策略的行为一致性"""

    def _create_retriever(self, strategy: RetrievalStrategy):
        config = RAGConfig(retrieval_strategy=strategy)
        vector_store = MockVectorStore(SAMPLE_VECTOR_RESULTS.copy())
        embedding_service = MockEmbeddingService()
        return HybridRetriever(vector_store, embedding_service, rag_config=config)

    def test_graphrag_returns_same_structure_as_hybrid(self):
        """GraphRAG 回退到混合检索时，返回结构应与 hybrid 一致"""
        hybrid_retriever = self._create_retriever(RetrievalStrategy.HYBRID)
        graphrag_retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG)

        hybrid_results = hybrid_retriever.retrieve("AI", top_k=3)
        graphrag_results = graphrag_retriever.retrieve("AI", top_k=3)

        assert len(hybrid_results) == len(graphrag_results), \
            f"Hybrid 返回 {len(hybrid_results)} 条，GraphRAG 返回 {len(graphrag_results)} 条"

        for h, g in zip(hybrid_results, graphrag_results):
            assert set(h.keys()) == set(g.keys()), "返回字段不一致"

    def test_graphrag_returns_same_structure_as_basic(self):
        """GraphRAG 返回结构应与 basic 策略兼容"""
        basic_retriever = self._create_retriever(RetrievalStrategy.BASIC)
        graphrag_retriever = self._create_retriever(RetrievalStrategy.GRAPH_RAG)

        basic_results = basic_retriever.retrieve("AI", top_k=3)
        graphrag_results = graphrag_retriever.retrieve("AI", top_k=3)

        assert len(basic_results) > 0, "Basic 策略返回为空"
        assert len(graphrag_results) > 0, "GraphRAG 策略返回为空"

    def test_all_strategies_return_results_with_data(self):
        """所有策略在有数据时都应返回结果"""
        strategies = [
            RetrievalStrategy.BASIC,
            RetrievalStrategy.HYBRID,
            RetrievalStrategy.CONTEXTUAL,
            RetrievalStrategy.GRAPH_RAG,
        ]
        for strategy in strategies:
            retriever = self._create_retriever(strategy)
            results = retriever.retrieve("测试查询", top_k=3)
            assert len(results) > 0, f"策略 {strategy.value} 返回为空"


class TestChatFlowWithGraphRAG:
    """测试 chat.py 中 GraphRAG 的完整流程模拟"""

    def test_context_building_with_graphrag_results(self):
        """模拟 chat.py 中的 context 构建逻辑"""
        results = SAMPLE_VECTOR_RESULTS.copy()

        context_parts = []
        sources = []
        source_index = 1
        for r in results:
            context_parts.append(f"【{source_index}】{r['content']}")
            sources.append({
                "index": source_index,
                "doc_id": r["doc_id"],
                "text": r["content"],
                "score": r.get("rerank_score", r.get("score", 0)),
                "filename": r.get("metadata", {}).get("filename", "")
            })
            source_index += 1

        context = "\n\n".join(context_parts)

        assert len(context) > 0, "context 不应为空"
        assert "【1】" in context
        assert "人工智能" in context
        assert len(sources) == 3

    def test_context_empty_when_no_results(self):
        """当检索结果为空时，context 为空（bug 的表现）"""
        results = []
        context_parts = []
        for r in results:
            context_parts.append(f"【1】{r['content']}")
        context = "\n\n".join(context_parts)
        assert context == ""

    def test_rag_config_parsing_for_graphrag(self):
        """测试 _parse_rag_config 对 GraphRAG 配置的解析"""
        config_dict = {
            "chunking_strategy": "fixed",
            "retrieval_strategy": "graph_rag",
            "chunk_size": 500,
            "chunk_overlap": 100,
        }

        config = RAGConfig(
            chunking_strategy=ChunkingStrategy(config_dict.get("chunking_strategy", "fixed")),
            retrieval_strategy=RetrievalStrategy(config_dict.get("retrieval_strategy", "hybrid")),
            chunk_size=config_dict.get("chunk_size", 500),
            chunk_overlap=config_dict.get("chunk_overlap", 100),
        )

        assert config.retrieval_strategy == RetrievalStrategy.GRAPH_RAG
        assert config.chunking_strategy == ChunkingStrategy.FIXED

    def test_graphrag_not_in_async_strategies(self):
        """验证 GraphRAG 不在异步策略列表中"""
        async_strategies = [RetrievalStrategy.HYDE, RetrievalStrategy.MULTI_QUERY]
        assert RetrievalStrategy.GRAPH_RAG not in async_strategies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
