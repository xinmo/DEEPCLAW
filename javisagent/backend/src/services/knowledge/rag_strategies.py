"""
RAG优化策略模块
P0-P5 实现：
- P0: BM25中文分词优化
- P1: Contextual Retrieval 上下文检索
- P2: Query改写 (HyDE/Multi-Query)
- P3: 语义切片 (Semantic Chunking)
- P4: Parent Document Retriever
- P5: GraphRAG 知识图谱增强
"""

from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import re


class ChunkingStrategy(str, Enum):
    """切片策略枚举"""
    FIXED = "fixed"                    # 固定字符切片（默认）
    SEMANTIC = "semantic"              # 语义切片 (P3)
    PARENT_CHILD = "parent_child"      # 父子文档切片 (P4)


class RetrievalStrategy(str, Enum):
    """检索策略枚举"""
    BASIC = "basic"                    # 基础向量检索
    HYBRID = "hybrid"                  # 混合检索（向量+BM25）
    CONTEXTUAL = "contextual"          # 上下文检索 (P1)
    HYDE = "hyde"                      # HyDE假设文档 (P2)
    MULTI_QUERY = "multi_query"        # 多查询改写 (P2)
    GRAPH_RAG = "graph_rag"            # 知识图谱增强 (P5)


@dataclass
class RAGConfig:
    """RAG配置"""
    # 切片配置
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.FIXED
    chunk_size: int = 500
    chunk_overlap: int = 100
    # 父子文档配置 (P4)
    parent_chunk_size: int = 2000
    child_chunk_size: int = 200
    # 语义切片配置 (P3)
    semantic_threshold: float = 0.5

    # 检索配置
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 5
    vector_top_k: int = 20

    # BM25配置 (P0)
    use_chinese_tokenizer: bool = True

    # 上下文检索配置 (P1)
    use_contextual_embedding: bool = False
    context_window: int = 3  # 上下文窗口大小

    # Query改写配置 (P2)
    use_hyde: bool = False
    use_multi_query: bool = False
    multi_query_count: int = 3

    # GraphRAG配置 (P5)
    use_graph_rag: bool = False
    extract_entities: bool = False
    community_detection: bool = False
    # GraphRAG 实体抽取使用的 LLM 模型
    graph_rag_llm_model: str = "gpt-4o"


# ============== P0: BM25中文分词优化 ==============

class ChineseTokenizer:
    """中文分词器，支持jieba分词"""

    _jieba_initialized = False

    @classmethod
    def _ensure_jieba(cls):
        """确保jieba已初始化"""
        if not cls._jieba_initialized:
            try:
                import jieba
                jieba.initialize()
                cls._jieba_initialized = True
            except ImportError:
                pass

    @staticmethod
    def tokenize(text: str, use_chinese: bool = True) -> List[str]:
        """
        分词函数
        Args:
            text: 输入文本
            use_chinese: 是否使用中文分词
        Returns:
            分词结果列表
        """
        if not use_chinese:
            return text.split()

        try:
            import jieba
            ChineseTokenizer._ensure_jieba()
            # 使用精确模式分词
            tokens = list(jieba.cut(text, cut_all=False))
            # 过滤空白和单字符标点
            tokens = [t.strip() for t in tokens if t.strip() and len(t.strip()) > 0]
            return tokens
        except ImportError:
            # 降级到简单分词：按空格和中文字符分割
            return ChineseTokenizer._fallback_tokenize(text)

    @staticmethod
    def _fallback_tokenize(text: str) -> List[str]:
        """降级分词方案"""
        # 按空格分割英文，按字符分割中文
        tokens = []
        current_token = ""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                if current_token:
                    tokens.extend(current_token.split())
                    current_token = ""
                tokens.append(char)
            else:
                current_token += char
        if current_token:
            tokens.extend(current_token.split())
        return [t for t in tokens if t.strip()]


# ============== P1: Contextual Retrieval ==============

class ContextualRetrieval:
    """上下文检索：为每个chunk添加文档上下文"""

    CONTEXT_PROMPT = """请为以下文档片段生成一个简短的上下文描述，说明这段内容在整个文档中的位置和作用。

文档标题: {title}
文档摘要: {summary}

当前片段:
{chunk}

请用一句话描述这个片段的上下文（不超过100字）:"""

    @staticmethod
    def generate_context_prefix(
        chunk: str,
        doc_title: str = "",
        doc_summary: str = "",
        llm_service: Any = None
    ) -> str:
        """
        为chunk生成上下文前缀
        Args:
            chunk: 文档片段
            doc_title: 文档标题
            doc_summary: 文档摘要
            llm_service: LLM服务实例
        Returns:
            上下文前缀
        """
        if llm_service is None:
            # 无LLM时使用简单前缀
            prefix = ""
            if doc_title:
                prefix += f"[文档: {doc_title}] "
            return prefix

        # 使用LLM生成上下文
        prompt = ContextualRetrieval.CONTEXT_PROMPT.format(
            title=doc_title or "未知",
            summary=doc_summary or "无摘要",
            chunk=chunk[:500]  # 限制长度
        )

        # 同步调用LLM（简化处理）
        try:
            context = ""
            # 这里需要异步转同步，实际使用时应该用async版本
            return f"[{doc_title}] " if doc_title else ""
        except Exception:
            return f"[{doc_title}] " if doc_title else ""

    @staticmethod
    async def generate_context_prefix_async(
        chunk: str,
        doc_title: str = "",
        doc_summary: str = "",
        llm_service: Any = None
    ) -> str:
        """异步版本的上下文生成"""
        if llm_service is None:
            prefix = ""
            if doc_title:
                prefix += f"[文档: {doc_title}] "
            return prefix

        prompt = ContextualRetrieval.CONTEXT_PROMPT.format(
            title=doc_title or "未知",
            summary=doc_summary or "无摘要",
            chunk=chunk[:500]
        )

        try:
            context = ""
            async for token in llm_service.astream(prompt):
                context += token
            return context.strip()[:100] + " | "
        except Exception:
            return f"[{doc_title}] " if doc_title else ""


# ============== P2: Query改写 ==============

class QueryRewriter:
    """Query改写器：HyDE和Multi-Query"""

    HYDE_PROMPT = """请根据以下问题，写一段假设性的答案文档。这段文档应该包含回答这个问题所需的关键信息。

问题: {query}

假设性答案文档（200-300字）:"""

    MULTI_QUERY_PROMPT = """请将以下问题改写成{count}个不同的表述方式，以便更好地检索相关文档。
每个改写应该从不同角度表达相同的信息需求。

原始问题: {query}

请输出{count}个改写后的问题，每行一个:"""

    @staticmethod
    async def generate_hyde_document(query: str, llm_service: Any) -> str:
        """
        生成HyDE假设文档
        Args:
            query: 用户查询
            llm_service: LLM服务
        Returns:
            假设性文档
        """
        prompt = QueryRewriter.HYDE_PROMPT.format(query=query)

        hyde_doc = ""
        async for token in llm_service.astream(prompt):
            hyde_doc += token

        return hyde_doc.strip()

    @staticmethod
    async def generate_multi_queries(
        query: str,
        llm_service: Any,
        count: int = 3
    ) -> List[str]:
        """
        生成多个查询变体
        Args:
            query: 原始查询
            llm_service: LLM服务
            count: 生成数量
        Returns:
            查询变体列表
        """
        prompt = QueryRewriter.MULTI_QUERY_PROMPT.format(query=query, count=count)

        response = ""
        async for token in llm_service.astream(prompt):
            response += token

        # 解析多个查询
        queries = [query]  # 包含原始查询
        for line in response.strip().split('\n'):
            line = line.strip()
            # 移除序号前缀
            line = re.sub(r'^[\d]+[.、)\]]\s*', '', line)
            if line and line != query:
                queries.append(line)

        return queries[:count + 1]  # 原始 + count个改写


# ============== P3: 语义切片 ==============

class SemanticChunker:
    """语义切片器：基于语义相似度切分文档"""

    def __init__(self, embedding_service: Any, threshold: float = 0.5):
        """
        Args:
            embedding_service: Embedding服务
            threshold: 相似度阈值，低于此值则切分
        """
        self.embedding_service = embedding_service
        self.threshold = threshold

    def chunk(self, text: str, min_chunk_size: int = 100) -> List[str]:
        """
        语义切片
        Args:
            text: 输入文本
            min_chunk_size: 最小chunk大小
        Returns:
            切片列表
        """
        # 先按句子分割
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [text] if text.strip() else []

        # 计算句子embeddings
        embeddings = self.embedding_service.embed_documents(sentences)

        # 基于相似度切分
        chunks = []
        current_chunk = [sentences[0]]

        for i in range(1, len(sentences)):
            # 计算与前一句的相似度
            similarity = self._cosine_similarity(embeddings[i-1], embeddings[i])

            if similarity < self.threshold:
                # 相似度低，开始新chunk
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= min_chunk_size:
                    chunks.append(chunk_text)
                else:
                    # chunk太小，合并到下一个
                    current_chunk.append(sentences[i])
                    continue
                current_chunk = [sentences[i]]
            else:
                current_chunk.append(sentences[i])

        # 添加最后一个chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割"""
        # 中英文句子分割
        pattern = r'(?<=[。！？.!?])\s*'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


# ============== P4: Parent Document Retriever ==============

@dataclass
class ParentChildChunk:
    """父子文档chunk"""
    parent_id: str
    parent_content: str
    child_id: str
    child_content: str
    child_index: int


class ParentDocumentChunker:
    """父子文档切片器"""

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 200,
        child_overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap

    def chunk(self, text: str, doc_id: str) -> Tuple[List[Dict], Dict[str, str]]:
        """
        切分为父子文档
        Args:
            text: 输入文本
            doc_id: 文档ID
        Returns:
            (child_chunks, parent_map) - 子chunk列表和父chunk映射
        """
        import uuid

        # 1. 先切分为大的父chunk
        parent_chunks = self._split_text(text, self.parent_chunk_size, overlap=100)

        child_chunks = []
        parent_map = {}  # child_id -> parent_content

        for p_idx, parent_content in enumerate(parent_chunks):
            parent_id = f"{doc_id}_p{p_idx}"

            # 2. 每个父chunk切分为小的子chunk
            children = self._split_text(
                parent_content,
                self.child_chunk_size,
                self.child_overlap
            )

            for c_idx, child_content in enumerate(children):
                child_id = f"{parent_id}_c{c_idx}"
                child_chunks.append({
                    "id": child_id,
                    "content": child_content,
                    "parent_id": parent_id,
                    "metadata": {
                        "parent_index": p_idx,
                        "child_index": c_idx
                    }
                })
                parent_map[child_id] = parent_content

        return child_chunks, parent_map

    def _split_text(self, text: str, chunk_size: int, overlap: int = 0) -> List[str]:
        """简单文本切分"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap if overlap > 0 else end
        return chunks


# ============== P5: GraphRAG ==============

@dataclass
class Entity:
    """实体"""
    id: str
    name: str
    type: str
    description: str = ""


@dataclass
class Relationship:
    """关系"""
    source_id: str
    target_id: str
    relation_type: str
    description: str = ""


class GraphRAGExtractor:
    """GraphRAG实体关系抽取器"""

    EXTRACT_PROMPT = """请从以下文本中抽取实体和关系。

文本:
{text}

请按以下JSON格式输出:
{{
    "entities": [
        {{"name": "实体名", "type": "实体类型(人物/组织/地点/概念/事件)", "description": "简短描述"}}
    ],
    "relationships": [
        {{"source": "源实体名", "target": "目标实体名", "relation": "关系类型", "description": "关系描述"}}
    ]
}}

只输出JSON，不要其他内容:"""

    @staticmethod
    async def extract_entities_and_relations(
        text: str,
        llm_service: Any
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        从文本中抽取实体和关系
        Args:
            text: 输入文本
            llm_service: LLM服务
        Returns:
            (entities, relationships)
        """
        import json
        import uuid

        prompt = GraphRAGExtractor.EXTRACT_PROMPT.format(text=text[:2000])

        response = ""
        async for token in llm_service.astream(prompt):
            response += token

        # 解析JSON
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return [], []

            entities = []
            entity_name_to_id = {}

            for e in data.get("entities", []):
                entity_id = str(uuid.uuid4())[:8]
                entity = Entity(
                    id=entity_id,
                    name=e.get("name", ""),
                    type=e.get("type", "概念"),
                    description=e.get("description", "")
                )
                entities.append(entity)
                entity_name_to_id[entity.name] = entity_id

            relationships = []
            for r in data.get("relationships", []):
                source_name = r.get("source", "")
                target_name = r.get("target", "")
                if source_name in entity_name_to_id and target_name in entity_name_to_id:
                    rel = Relationship(
                        source_id=entity_name_to_id[source_name],
                        target_id=entity_name_to_id[target_name],
                        relation_type=r.get("relation", "相关"),
                        description=r.get("description", "")
                    )
                    relationships.append(rel)

            return entities, relationships

        except json.JSONDecodeError:
            return [], []


# ============== 策略工厂 ==============

class RAGStrategyFactory:
    """RAG策略工厂"""

    @staticmethod
    def get_tokenizer(config: RAGConfig) -> callable:
        """获取分词器"""
        return lambda text: ChineseTokenizer.tokenize(text, config.use_chinese_tokenizer)

    @staticmethod
    def get_chunker(config: RAGConfig, embedding_service: Any = None):
        """获取切片器"""
        if config.chunking_strategy == ChunkingStrategy.SEMANTIC:
            if embedding_service is None:
                raise ValueError("Semantic chunking requires embedding_service")
            return SemanticChunker(embedding_service, config.semantic_threshold)
        elif config.chunking_strategy == ChunkingStrategy.PARENT_CHILD:
            return ParentDocumentChunker(
                config.parent_chunk_size,
                config.child_chunk_size
            )
        else:
            # 返回None表示使用默认的RecursiveCharacterTextSplitter
            return None
