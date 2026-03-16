"""
RAG策略单元测试
TDD: 先写测试，再实现
"""

import pytest
import sys
import os
import importlib.util

# 直接加载rag_strategies模块，避免触发__init__.py的其他依赖
_module_path = os.path.join(
    os.path.dirname(__file__), '..', 'src', 'services', 'knowledge', 'rag_strategies.py'
)
_spec = importlib.util.spec_from_file_location("rag_strategies", _module_path)
_rag_strategies = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rag_strategies)

# 从模块中导入需要的类和函数
ChineseTokenizer = _rag_strategies.ChineseTokenizer
ChunkingStrategy = _rag_strategies.ChunkingStrategy
RetrievalStrategy = _rag_strategies.RetrievalStrategy
RAGConfig = _rag_strategies.RAGConfig
ContextualRetrieval = _rag_strategies.ContextualRetrieval
QueryRewriter = _rag_strategies.QueryRewriter
SemanticChunker = _rag_strategies.SemanticChunker
ParentDocumentChunker = _rag_strategies.ParentDocumentChunker
GraphRAGExtractor = _rag_strategies.GraphRAGExtractor
RAGStrategyFactory = _rag_strategies.RAGStrategyFactory
Entity = _rag_strategies.Entity
Relationship = _rag_strategies.Relationship



# ============== P0: BM25中文分词测试 ==============

class TestChineseTokenizer:
    """测试中文分词器"""

    def test_tokenize_chinese_text(self):
        """测试中文文本分词"""
        text = "公司去年营收增长"
        tokens = ChineseTokenizer.tokenize(text, use_chinese=True)

        # 应该分成多个词，而不是一个整体
        assert len(tokens) > 1
        assert isinstance(tokens, list)
        # 验证关键词被正确分出
        assert any("公司" in t for t in tokens) or any("营收" in t for t in tokens)

    def test_tokenize_english_text(self):
        """测试英文文本分词"""
        text = "The company revenue increased"
        tokens = ChineseTokenizer.tokenize(text, use_chinese=True)

        assert len(tokens) >= 4
        assert "company" in tokens or "The" in tokens

    def test_tokenize_mixed_text(self):
        """测试中英混合文本"""
        text = "Apple公司2024年Q3财报"
        tokens = ChineseTokenizer.tokenize(text, use_chinese=True)

        assert len(tokens) > 1
        # 应该包含Apple和中文词
        token_str = ''.join(tokens)
        assert "Apple" in token_str or "apple" in token_str.lower()

    def test_tokenize_without_chinese_mode(self):
        """测试非中文模式（空格分词）"""
        text = "hello world test"
        tokens = ChineseTokenizer.tokenize(text, use_chinese=False)

        assert tokens == ["hello", "world", "test"]

    def test_tokenize_empty_text(self):
        """测试空文本"""
        tokens = ChineseTokenizer.tokenize("", use_chinese=True)
        assert tokens == []

    def test_tokenize_whitespace_only(self):
        """测试纯空白文本"""
        tokens = ChineseTokenizer.tokenize("   \n\t  ", use_chinese=True)
        assert tokens == []

    def test_fallback_tokenize(self):
        """测试降级分词"""
        text = "测试文本ABC"
        tokens = ChineseTokenizer._fallback_tokenize(text)

        assert len(tokens) > 0
        assert isinstance(tokens, list)


# ============== P1: Contextual Retrieval测试 ==============

class TestContextualRetrieval:
    """测试上下文检索"""

    def test_generate_context_prefix_without_llm(self):
        """测试无LLM时的上下文前缀生成"""
        chunk = "这是一段测试文本"
        prefix = ContextualRetrieval.generate_context_prefix(
            chunk=chunk,
            doc_title="测试文档",
            doc_summary="这是摘要",
            llm_service=None
        )

        assert "[文档: 测试文档]" in prefix

    def test_generate_context_prefix_empty_title(self):
        """测试空标题时的处理"""
        prefix = ContextualRetrieval.generate_context_prefix(
            chunk="测试",
            doc_title="",
            doc_summary="",
            llm_service=None
        )

        assert prefix == ""

    @pytest.mark.asyncio
    async def test_generate_context_prefix_async_without_llm(self):
        """测试异步版本无LLM"""
        prefix = await ContextualRetrieval.generate_context_prefix_async(
            chunk="测试内容",
            doc_title="异步测试",
            llm_service=None
        )

        assert "异步测试" in prefix


# ============== P2: Query改写测试 ==============

class TestQueryRewriter:
    """测试Query改写器"""

    def test_hyde_prompt_format(self):
        """测试HyDE prompt格式"""
        query = "公司去年赚了多少钱"
        prompt = QueryRewriter.HYDE_PROMPT.format(query=query)

        assert query in prompt
        assert "假设性" in prompt

    def test_multi_query_prompt_format(self):
        """测试Multi-Query prompt格式"""
        query = "如何提高销售额"
        prompt = QueryRewriter.MULTI_QUERY_PROMPT.format(query=query, count=3)

        assert query in prompt
        assert "3" in prompt


# ============== P3: 语义切片测试 ==============

class MockEmbeddingService:
    """模拟Embedding服务"""

    def embed_documents(self, texts):
        """返回模拟的embeddings"""
        import random
        return [[random.random() for _ in range(10)] for _ in texts]

    def embed_query(self, text):
        import random
        return [random.random() for _ in range(10)]


class TestSemanticChunker:
    """测试语义切片器"""

    def test_chunk_single_sentence(self):
        """测试单句文本"""
        chunker = SemanticChunker(MockEmbeddingService(), threshold=0.5)
        text = "这是一个简单的句子。"
        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        assert chunks[0] == text.strip() or "简单" in chunks[0]

    def test_chunk_multiple_sentences(self):
        """测试多句文本"""
        chunker = SemanticChunker(MockEmbeddingService(), threshold=0.3)
        text = "第一个句子。第二个句子。第三个句子。第四个句子。"
        chunks = chunker.chunk(text, min_chunk_size=5)

        assert len(chunks) >= 1
        # 所有原文内容应该被保留
        combined = ''.join(chunks)
        assert "第一" in combined

    def test_chunk_empty_text(self):
        """测试空文本"""
        chunker = SemanticChunker(MockEmbeddingService())
        chunks = chunker.chunk("")

        assert chunks == []

    def test_split_sentences_chinese(self):
        """测试中文句子分割"""
        chunker = SemanticChunker(MockEmbeddingService())
        text = "这是第一句。这是第二句！这是第三句？"
        sentences = chunker._split_sentences(text)

        assert len(sentences) == 3

    def test_split_sentences_english(self):
        """测试英文句子分割"""
        chunker = SemanticChunker(MockEmbeddingService())
        text = "First sentence. Second sentence! Third sentence?"
        sentences = chunker._split_sentences(text)

        assert len(sentences) == 3

    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        chunker = SemanticChunker(MockEmbeddingService())

        # 相同向量相似度为1
        vec = [1.0, 0.0, 0.0]
        assert abs(chunker._cosine_similarity(vec, vec) - 1.0) < 0.001

        # 正交向量相似度为0
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert abs(chunker._cosine_similarity(vec1, vec2)) < 0.001

    def test_cosine_similarity_zero_vector(self):
        """测试零向量"""
        chunker = SemanticChunker(MockEmbeddingService())
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        assert chunker._cosine_similarity(vec1, vec2) == 0.0


# ============== P4: Parent Document Retriever测试 ==============

class TestParentDocumentChunker:
    """测试父子文档切片器"""

    def test_chunk_basic(self):
        """测试基本切片"""
        chunker = ParentDocumentChunker(
            parent_chunk_size=100,
            child_chunk_size=20,
            child_overlap=5
        )

        text = "A" * 200  # 200字符文本
        child_chunks, parent_map = chunker.chunk(text, "doc1")

        assert len(child_chunks) > 0
        assert len(parent_map) > 0

        # 每个child都应该有对应的parent
        for child in child_chunks:
            assert child["id"] in parent_map

    def test_chunk_preserves_content(self):
        """测试内容完整性"""
        chunker = ParentDocumentChunker(
            parent_chunk_size=50,
            child_chunk_size=10
        )

        text = "这是一段测试文本，用于验证父子文档切片的正确性。"
        child_chunks, parent_map = chunker.chunk(text, "test_doc")

        # 合并所有child内容应该覆盖原文
        all_content = ''.join(c["content"] for c in child_chunks)
        # 由于overlap，可能有重复，但关键内容应该存在
        assert "测试" in all_content or "文本" in all_content

    def test_chunk_metadata(self):
        """测试元数据"""
        chunker = ParentDocumentChunker(parent_chunk_size=100, child_chunk_size=20)
        text = "A" * 150
        child_chunks, _ = chunker.chunk(text, "doc1")

        for chunk in child_chunks:
            assert "id" in chunk
            assert "content" in chunk
            assert "parent_id" in chunk
            assert "metadata" in chunk
            assert "parent_index" in chunk["metadata"]
            assert "child_index" in chunk["metadata"]

    def test_chunk_empty_text(self):
        """测试空文本"""
        chunker = ParentDocumentChunker()
        child_chunks, parent_map = chunker.chunk("", "doc1")

        assert child_chunks == []
        assert parent_map == {}

    def test_split_text(self):
        """测试文本分割"""
        chunker = ParentDocumentChunker()
        text = "ABCDEFGHIJ"
        chunks = chunker._split_text(text, chunk_size=3, overlap=1)

        assert len(chunks) > 0
        assert chunks[0] == "ABC"


# ============== P5: GraphRAG测试 ==============

class TestGraphRAGExtractor:
    """测试GraphRAG抽取器"""

    def test_extract_prompt_format(self):
        """测试抽取prompt格式"""
        text = "张三是ABC公司的CEO"
        prompt = GraphRAGExtractor.EXTRACT_PROMPT.format(text=text)

        assert text in prompt
        assert "entities" in prompt
        assert "relationships" in prompt
        assert "JSON" in prompt

    def test_entity_dataclass(self):
        """测试Entity数据类"""
        entity = Entity(
            id="e1",
            name="张三",
            type="人物",
            description="CEO"
        )

        assert entity.id == "e1"
        assert entity.name == "张三"
        assert entity.type == "人物"

    def test_relationship_dataclass(self):
        """测试Relationship数据类"""
        rel = Relationship(
            source_id="e1",
            target_id="e2",
            relation_type="任职于",
            description="CEO职位"
        )

        assert rel.source_id == "e1"
        assert rel.target_id == "e2"
        assert rel.relation_type == "任职于"


# ============== RAGConfig测试 ==============

class TestRAGConfig:
    """测试RAG配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = RAGConfig()

        assert config.chunking_strategy == ChunkingStrategy.FIXED
        assert config.retrieval_strategy == RetrievalStrategy.HYBRID
        assert config.chunk_size == 500
        assert config.use_chinese_tokenizer == True

    def test_custom_config(self):
        """测试自定义配置"""
        config = RAGConfig(
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            retrieval_strategy=RetrievalStrategy.HYDE,
            chunk_size=1000,
            use_hyde=True
        )

        assert config.chunking_strategy == ChunkingStrategy.SEMANTIC
        assert config.retrieval_strategy == RetrievalStrategy.HYDE
        assert config.chunk_size == 1000
        assert config.use_hyde == True

    def test_parent_child_config(self):
        """测试父子文档配置"""
        config = RAGConfig(
            chunking_strategy=ChunkingStrategy.PARENT_CHILD,
            parent_chunk_size=2000,
            child_chunk_size=200
        )

        assert config.parent_chunk_size == 2000
        assert config.child_chunk_size == 200


# ============== 策略工厂测试 ==============

class TestRAGStrategyFactory:
    """测试策略工厂"""

    def test_get_tokenizer_chinese(self):
        """测试获取中文分词器"""
        config = RAGConfig(use_chinese_tokenizer=True)
        tokenizer = RAGStrategyFactory.get_tokenizer(config)

        tokens = tokenizer("测试文本")
        assert isinstance(tokens, list)

    def test_get_tokenizer_english(self):
        """测试获取英文分词器"""
        config = RAGConfig(use_chinese_tokenizer=False)
        tokenizer = RAGStrategyFactory.get_tokenizer(config)

        tokens = tokenizer("hello world")
        assert tokens == ["hello", "world"]

    def test_get_chunker_fixed(self):
        """测试获取固定切片器"""
        config = RAGConfig(chunking_strategy=ChunkingStrategy.FIXED)
        chunker = RAGStrategyFactory.get_chunker(config)

        # 固定切片返回None，使用默认
        assert chunker is None

    def test_get_chunker_semantic(self):
        """测试获取语义切片器"""
        config = RAGConfig(chunking_strategy=ChunkingStrategy.SEMANTIC)
        embedding_service = MockEmbeddingService()
        chunker = RAGStrategyFactory.get_chunker(config, embedding_service)

        assert isinstance(chunker, SemanticChunker)

    def test_get_chunker_semantic_without_embedding_raises(self):
        """测试语义切片无embedding服务时报错"""
        config = RAGConfig(chunking_strategy=ChunkingStrategy.SEMANTIC)

        with pytest.raises(ValueError):
            RAGStrategyFactory.get_chunker(config, None)

    def test_get_chunker_parent_child(self):
        """测试获取父子文档切片器"""
        config = RAGConfig(chunking_strategy=ChunkingStrategy.PARENT_CHILD)
        chunker = RAGStrategyFactory.get_chunker(config)

        assert isinstance(chunker, ParentDocumentChunker)


# ============== 枚举测试 ==============

class TestEnums:
    """测试枚举类型"""

    def test_chunking_strategy_values(self):
        """测试切片策略枚举值"""
        assert ChunkingStrategy.FIXED.value == "fixed"
        assert ChunkingStrategy.SEMANTIC.value == "semantic"
        assert ChunkingStrategy.PARENT_CHILD.value == "parent_child"

    def test_retrieval_strategy_values(self):
        """测试检索策略枚举值"""
        assert RetrievalStrategy.BASIC.value == "basic"
        assert RetrievalStrategy.HYBRID.value == "hybrid"
        assert RetrievalStrategy.CONTEXTUAL.value == "contextual"
        assert RetrievalStrategy.HYDE.value == "hyde"
        assert RetrievalStrategy.MULTI_QUERY.value == "multi_query"
        assert RetrievalStrategy.GRAPH_RAG.value == "graph_rag"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
