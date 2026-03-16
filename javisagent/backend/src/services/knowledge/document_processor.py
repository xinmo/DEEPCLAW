"""
文档处理服务：解析 + 切片 + 向量化
支持多种切片策略 (P1, P3, P4)
"""

import os
import uuid
import time
import logging
from typing import List, Dict, Optional, Any, Tuple, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.services.mineru import mineru_client
from .config import get_knowledge_settings
from .embedding import EmbeddingService
from .vector_store import MilvusVectorStore
from .rag_strategies import (
    RAGConfig,
    ChunkingStrategy,
    RetrievalStrategy,
    SemanticChunker,
    ParentDocumentChunker,
    ContextualRetrieval,
    GraphRAGExtractor,
)
from .graph_store import GraphStore

logger = logging.getLogger("services.knowledge.document_processor")
settings = get_knowledge_settings()

TEXT_EXTENSIONS = {'.txt', '.md'}
HTML_EXTENSIONS = {'.html', '.htm'}


class DocumentProcessor:
    """文档处理服务：解析 + 切片 + 向量化"""

    def __init__(
        self,
        kb_id: str,
        embedding_service: EmbeddingService,
        rag_config: Optional[Dict[str, Any]] = None,
        llm_service: Optional[Any] = None,
        progress_callback: Optional[callable] = None,
        db_session: Optional[Any] = None
    ):
        self.kb_id = kb_id
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.progress_callback = progress_callback
        self.db_session = db_session
        self.graph_rag_warning = ""

        # 解析RAG配置
        self.rag_config = self._parse_rag_config(rag_config)

        logger.info(f"[DocumentProcessor] 初始化 | kb_id={kb_id}")
        logger.info(f"[DocumentProcessor] RAG配置: "
                     f"切片策略={self.rag_config.chunking_strategy.value}, "
                     f"检索策略={self.rag_config.retrieval_strategy.value}, "
                     f"chunk_size={self.rag_config.chunk_size}, "
                     f"chunk_overlap={self.rag_config.chunk_overlap}, "
                     f"上下文增强(P1)={self.rag_config.use_contextual_embedding}, "
                     f"GraphRAG(P5)={self.rag_config.use_graph_rag}")
        if self.rag_config.chunking_strategy == ChunkingStrategy.SEMANTIC:
            logger.info(f"[DocumentProcessor] 语义切片阈值={self.rag_config.semantic_threshold}")
        elif self.rag_config.chunking_strategy == ChunkingStrategy.PARENT_CHILD:
            logger.info(f"[DocumentProcessor] 父子文档: 父chunk={self.rag_config.parent_chunk_size}, "
                         f"子chunk={self.rag_config.child_chunk_size}")

        self.vector_store = MilvusVectorStore(kb_id, embedding_service.dimension)

        # 根据配置创建切片器
        self._init_chunkers()

        # 父文档映射 (P4)
        self._parent_doc_map: Dict[str, str] = {}

    def _update_progress(self, stage: str, progress: int, message: str = ""):
        """更新处理进度"""
        if self.progress_callback:
            self.progress_callback(stage, progress, message)

    def _parse_rag_config(self, config_dict: Optional[Dict]) -> RAGConfig:
        """解析RAG配置字典为RAGConfig对象"""
        if not config_dict:
            logger.info(f"[DocumentProcessor] 未提供RAG配置，使用默认配置")
            return RAGConfig()

        logger.info(f"[DocumentProcessor] 解析RAG配置原始数据: {config_dict}")

        retrieval_strategy = RetrievalStrategy(config_dict.get("retrieval_strategy", "hybrid"))

        # 当检索策略为 graph_rag 时，自动启用 use_graph_rag
        use_graph_rag = config_dict.get("use_graph_rag", False)
        if retrieval_strategy == RetrievalStrategy.GRAPH_RAG:
            use_graph_rag = True
            logger.info(f"[DocumentProcessor] 检索策略为 graph_rag，自动启用 use_graph_rag=True")

        return RAGConfig(
            chunking_strategy=ChunkingStrategy(config_dict.get("chunking_strategy", "fixed")),
            retrieval_strategy=retrieval_strategy,
            chunk_size=config_dict.get("chunk_size", 500),
            chunk_overlap=config_dict.get("chunk_overlap", 100),
            parent_chunk_size=config_dict.get("parent_chunk_size", 2000),
            child_chunk_size=config_dict.get("child_chunk_size", 200),
            semantic_threshold=config_dict.get("semantic_threshold", 0.5),
            use_chinese_tokenizer=config_dict.get("use_chinese_tokenizer", True),
            use_contextual_embedding=config_dict.get("use_contextual_embedding", False),
            use_hyde=config_dict.get("use_hyde", False),
            use_multi_query=config_dict.get("use_multi_query", False),
            multi_query_count=config_dict.get("multi_query_count", 3),
            use_graph_rag=use_graph_rag,
        )

    def _init_chunkers(self):
        """初始化切片器"""
        config = self.rag_config

        # 默认切片器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )

        # P3: 语义切片器
        self.semantic_chunker = None
        if config.chunking_strategy == ChunkingStrategy.SEMANTIC:
            self.semantic_chunker = SemanticChunker(
                self.embedding_service,
                config.semantic_threshold
            )

        # P4: 父子文档切片器
        self.parent_child_chunker = None
        if config.chunking_strategy == ChunkingStrategy.PARENT_CHILD:
            self.parent_child_chunker = ParentDocumentChunker(
                config.parent_chunk_size,
                config.child_chunk_size,
                config.chunk_overlap
            )

    def get_parent_doc_map(self) -> Dict[str, str]:
        """获取父文档映射，用于检索时扩展"""
        return self._parent_doc_map

    async def process_file(self, file_path: str, doc_id: str, filename: str) -> Dict:
        """处理单个文件：解析 → 切片 → 向量化 → 存储"""
        ext = os.path.splitext(filename)[1].lower()
        logger.info(f"[DocumentProcessor] 开始处理文件 | doc_id={doc_id} | filename={filename} | ext={ext}")

        # 1. 获取文本内容
        if ext in TEXT_EXTENSIONS:
            logger.info(f"[DocumentProcessor] 文本文件，直接读取内容")
            content = self._read_text_file(file_path)
            logger.info(f"[DocumentProcessor] 读取完成 | 内容长度={len(content)} 字符")
            return await self._process_content(content, doc_id, filename)
        else:
            # 使用 MinerU 解析，返回 batch_id 用于异步轮询
            logger.info(f"[DocumentProcessor] 非文本文件，提交到 MinerU 异步解析")
            batch_id = await self._submit_to_mineru(file_path, filename, doc_id)
            logger.info(f"[DocumentProcessor] MinerU 任务已提交 | batch_id={batch_id}")
            return {"status": "processing", "batch_id": batch_id}

    def _read_text_file(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            logger.warning(f"[DocumentProcessor] UTF-8 解码失败，尝试 GBK 编码 | file={file_path}")
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()

    async def _submit_to_mineru(self, file_path: str, filename: str, doc_id: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        model_version = 'MinerU-HTML' if ext in HTML_EXTENSIONS else 'vlm'

        files = [{'name': filename, 'data_id': doc_id}]
        upload_response = mineru_client.get_upload_urls(files, model_version=model_version)

        if upload_response.get('code') != 0:
            raise Exception(f"MinerU API error: {upload_response.get('msg')}")

        batch_id = upload_response.get('data', {}).get('batch_id')
        upload_urls = upload_response.get('data', {}).get('file_urls', [])

        if upload_urls:
            mineru_client.upload_file(upload_urls[0], file_path)

        return batch_id

    async def process_mineru_result(self, doc_id: str, markdown: str, filename: str) -> Dict:
        """处理 MinerU 解析完成后的结果"""
        logger.info(f"[DocumentProcessor] MinerU 解析完成，开始处理结果 | doc_id={doc_id} | markdown长度={len(markdown)} 字符")
        return await self._process_content(markdown, doc_id, filename)

    async def _process_content(self, content: str, doc_id: str, filename: str) -> Dict:
        """处理文本内容：切片 → 向量化 → 存储"""
        config = self.rag_config
        start_time = time.time()

        logger.info(f"[DocumentProcessor] ===== 开始处理文档内容 =====")
        logger.info(f"[DocumentProcessor] doc_id={doc_id} | filename={filename} | 内容长度={len(content)} 字符")
        logger.info(f"[DocumentProcessor] 切片策略: {config.chunking_strategy.value}")

        # 切片阶段
        self._update_progress("chunking", 50, "正在切分文本...")
        chunk_start = time.time()

        # 2. 根据策略切片
        if config.chunking_strategy == ChunkingStrategy.SEMANTIC and self.semantic_chunker:
            # P3: 语义切片
            logger.info(f"[DocumentProcessor] 使用 P3-语义切片 | 阈值={config.semantic_threshold}")
            chunks = self.semantic_chunker.chunk(content, min_chunk_size=100)
            logger.info(f"[DocumentProcessor] 语义切片完成 | 生成 {len(chunks)} 个chunks | 耗时={time.time()-chunk_start:.2f}s")
            chunk_data = await self._prepare_chunks(chunks, doc_id, filename)

        elif config.chunking_strategy == ChunkingStrategy.PARENT_CHILD and self.parent_child_chunker:
            # P4: 父子文档切片
            logger.info(f"[DocumentProcessor] 使用 P4-父子文档切片 | 父chunk={config.parent_chunk_size} | 子chunk={config.child_chunk_size}")
            child_chunks, parent_map = self.parent_child_chunker.chunk(content, doc_id)
            self._parent_doc_map.update(parent_map)
            logger.info(f"[DocumentProcessor] 父子切片完成 | 子chunks={len(child_chunks)} | 父映射={len(parent_map)} | 耗时={time.time()-chunk_start:.2f}s")
            chunk_data = await self._prepare_parent_child_chunks(child_chunks, doc_id, filename)

        else:
            # 默认: 固定切片
            logger.info(f"[DocumentProcessor] 使用固定切片 | chunk_size={config.chunk_size} | overlap={config.chunk_overlap}")
            chunks = self.text_splitter.split_text(content)
            logger.info(f"[DocumentProcessor] 固定切片完成 | 生成 {len(chunks)} 个chunks | 耗时={time.time()-chunk_start:.2f}s")
            chunk_data = await self._prepare_chunks(chunks, doc_id, filename)

        # 存储阶段
        self._update_progress("storing", 90, "正在存储到知识库...")
        store_start = time.time()

        # 4. 存储到向量库
        if chunk_data:
            self.vector_store.insert(chunk_data)
            logger.info(f"[DocumentProcessor] 向量存储完成 | 存入 {len(chunk_data)} 条 | 耗时={time.time()-store_start:.2f}s")

        # 5. GraphRAG 实体抽取 (P5)
        entity_count = 0
        rel_count = 0
        graph_warning = ""
        if config.use_graph_rag and self.llm_service and self.db_session:
            logger.info(f"[DocumentProcessor] P5-GraphRAG 实体抽取已启用")
            self._update_progress("storing", 92, "正在抽取实体和关系...")
            entity_count, rel_count = await self._extract_and_store_entities(
                chunks=[c["content"] for c in chunk_data],
                doc_id=doc_id
            )
            graph_warning = self.graph_rag_warning
        elif config.use_graph_rag:
            graph_warning = "GraphRAG 已启用，但实体抽取服务未就绪"
            logger.warning(f"[DocumentProcessor] {graph_warning}")

        total_time = time.time() - start_time
        self._update_progress("completed", 100, "处理完成")
        logger.info(f"[DocumentProcessor] ===== 文档处理完成 ===== | doc_id={doc_id} | chunks={len(chunk_data)} | 实体={entity_count} | 关系={rel_count} | 总耗时={total_time:.2f}s")
        return {
            "status": "completed",
            "chunk_count": len(chunk_data),
            "entity_count": entity_count,
            "relationship_count": rel_count,
            "graph_warning": graph_warning,
        }

    async def _prepare_chunks(
        self,
        chunks: List[str],
        doc_id: str,
        filename: str
    ) -> List[Dict]:
        """准备chunk数据（支持P1上下文增强）"""
        config = self.rag_config
        chunk_data = []

        logger.info(f"[DocumentProcessor] 准备chunks | 数量={len(chunks)} | P1上下文增强={config.use_contextual_embedding}")

        # 记录chunk大小分布
        chunk_sizes = [len(c) for c in chunks]
        if chunk_sizes:
            logger.info(f"[DocumentProcessor] chunk大小分布 | "
                         f"min={min(chunk_sizes)} | max={max(chunk_sizes)} | "
                         f"avg={sum(chunk_sizes)//len(chunk_sizes)} 字符")
            # 记录前3个chunk的预览
            for i, chunk in enumerate(chunks[:3]):
                logger.info(f"[DocumentProcessor]   chunk[{i}]: 长度={len(chunk)} | 预览='{chunk[:80]}...'")

        for i, chunk in enumerate(chunks):
            # P1: 上下文增强
            if config.use_contextual_embedding and self.llm_service:
                if i == 0:
                    logger.info(f"[DocumentProcessor] P1-上下文增强已启用，开始为每个chunk生成上下文前缀")
                context_prefix = await ContextualRetrieval.generate_context_prefix_async(
                    chunk=chunk,
                    doc_title=filename,
                    doc_summary="",
                    llm_service=self.llm_service
                )
                enhanced_chunk = context_prefix + chunk
                if i < 3:
                    logger.debug(f"[DocumentProcessor] P1 chunk[{i}] 上下文前缀: {context_prefix[:80]}...")
            else:
                enhanced_chunk = chunk

            chunk_data.append({
                "id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "content": chunk,  # 存储原始内容
                "enhanced_content": enhanced_chunk,  # 用于embedding
                "metadata": {"filename": filename, "chunk_index": i}
            })

        # 向量化阶段
        self._update_progress("embedding", 60, f"正在生成向量 (0/{len(chunk_data)})...")
        embed_start = time.time()
        logger.info(f"[DocumentProcessor] 开始向量化 | 模型={self.embedding_service.model_id} | 维度={self.embedding_service.dimension} | 数量={len(chunk_data)}")

        # 3. 向量化（使用增强内容）
        contents_to_embed = [c.get("enhanced_content", c["content"]) for c in chunk_data]
        embeddings = self.embedding_service.embed_documents(contents_to_embed)
        logger.info(f"[DocumentProcessor] 向量化完成 | 耗时={time.time()-embed_start:.2f}s")

        for i, emb in enumerate(embeddings):
            chunk_data[i]["embedding"] = emb
            # 移除enhanced_content，不存储到向量库
            chunk_data[i].pop("enhanced_content", None)
            # 更新进度
            if i % 10 == 0 or i == len(embeddings) - 1:
                progress = 60 + int((i + 1) / len(chunk_data) * 30)
                self._update_progress("embedding", progress, f"正在生成向量 ({i+1}/{len(chunk_data)})...")

        return chunk_data

    async def _prepare_parent_child_chunks(
        self,
        child_chunks: List[Dict],
        doc_id: str,
        filename: str
    ) -> List[Dict]:
        """准备父子文档chunk数据"""
        config = self.rag_config
        chunk_data = []

        logger.info(f"[DocumentProcessor] 准备父子文档chunks | 子chunk数量={len(child_chunks)} | P1上下文增强={config.use_contextual_embedding}")

        for child in child_chunks:
            content = child["content"]

            # P1: 上下文增强
            if config.use_contextual_embedding and self.llm_service:
                context_prefix = await ContextualRetrieval.generate_context_prefix_async(
                    chunk=content,
                    doc_title=filename,
                    doc_summary="",
                    llm_service=self.llm_service
                )
                enhanced_content = context_prefix + content
            else:
                enhanced_content = content

            chunk_data.append({
                "id": child["id"],
                "doc_id": doc_id,
                "content": content,
                "enhanced_content": enhanced_content,
                "metadata": {
                    "filename": filename,
                    "chunk_index": child["metadata"]["child_index"],
                    "parent_id": child["parent_id"],
                    "parent_index": child["metadata"]["parent_index"]
                }
            })

        # 向量化阶段
        self._update_progress("embedding", 60, f"正在生成向量 (0/{len(chunk_data)})...")
        embed_start = time.time()
        logger.info(f"[DocumentProcessor] 父子文档向量化 | 模型={self.embedding_service.model_id} | 数量={len(chunk_data)}")

        # 向量化
        contents_to_embed = [c.get("enhanced_content", c["content"]) for c in chunk_data]
        embeddings = self.embedding_service.embed_documents(contents_to_embed)
        logger.info(f"[DocumentProcessor] 父子文档向量化完成 | 耗时={time.time()-embed_start:.2f}s")

        for i, emb in enumerate(embeddings):
            chunk_data[i]["embedding"] = emb
            chunk_data[i].pop("enhanced_content", None)
            # 更新进度
            if i % 10 == 0 or i == len(embeddings) - 1:
                progress = 60 + int((i + 1) / len(chunk_data) * 30)
                self._update_progress("embedding", progress, f"正在生成向量 ({i+1}/{len(chunk_data)})...")

        return chunk_data

    def delete_document(self, doc_id: str):
        """删除文档"""
        self.vector_store.delete_by_doc_id(doc_id)
        # 清理父文档映射
        keys_to_remove = [k for k in self._parent_doc_map if k.startswith(f"{doc_id}_")]
        for k in keys_to_remove:
            del self._parent_doc_map[k]
        # 清理图数据
        if self.db_session:
            graph_store = GraphStore(self.db_session, self.kb_id)
            graph_store.clear_by_document(doc_id)

    async def _extract_and_store_entities(
        self,
        chunks: List[str],
        doc_id: str
    ) -> Tuple[int, int]:
        """从文档切片中抽取实体和关系并存储"""
        logger.info(f"[GraphRAG] 开始实体抽取 | 切片数={len(chunks)}")
        extract_start = time.time()

        all_entities = []
        all_relationships = []
        batch_errors: List[str] = []
        self.graph_rag_warning = ""

        # 批量处理切片 (每5个切片合并处理以减少LLM调用)
        batch_size = 5
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for i in range(0, len(chunks), batch_size):
            batch_num = i // batch_size + 1
            batch_chunks = chunks[i:i+batch_size]
            combined_text = "\n\n---\n\n".join(batch_chunks)

            # 更新进度：92% - 98% 之间
            progress = 92 + int((batch_num / total_batches) * 6)
            self._update_progress("storing", progress, f"正在抽取实体 ({batch_num}/{total_batches})...")

            # 跳过太短的文本
            if len(combined_text) < 100:
                continue

            try:
                entities, relationships = await GraphRAGExtractor.extract_entities_and_relations(
                    combined_text, self.llm_service
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)
                logger.debug(f"[GraphRAG] 批次 {batch_num} 抽取完成 | 实体={len(entities)} | 关系={len(relationships)}")
            except Exception as e:
                logger.warning(f"[GraphRAG] 批次 {batch_num} 抽取失败: {e}")
                batch_errors.append(f"批次 {batch_num}: {str(e)}")
                continue

        if not all_entities:
            if batch_errors:
                self.graph_rag_warning = f"GraphRAG 抽取失败，{batch_errors[0]}"
            else:
                self.graph_rag_warning = "GraphRAG 未抽取到实体"
            logger.info(f"[GraphRAG] 未抽取到实体")
            return 0, 0

        # 实体去重和合并
        self._update_progress("storing", 98, "正在存储实体和关系...")
        merged_entities = self._merge_entities(all_entities)
        logger.info(f"[GraphRAG] 实体去重完成 | 原始={len(all_entities)} | 合并后={len(merged_entities)}")

        # 存储到数据库
        graph_store = GraphStore(self.db_session, self.kb_id)

        # 建立名称到数据库ID的映射
        entity_name_to_db_id = {}
        stored_entities = 0

        for entity in merged_entities:
            # 检查是否已存在同名实体
            existing = graph_store.find_entity_by_name(entity.name, entity.type)
            if existing:
                # 使用已存在的实体
                entity_name_to_db_id[entity.name] = existing[0].id
            else:
                # 创建新实体
                db_entity = graph_store.add_entity(
                    name=entity.name,
                    type=entity.type,
                    description=entity.description,
                    doc_id=doc_id
                )
                entity_name_to_db_id[entity.name] = db_entity.id
                stored_entities += 1

        # 存储关系
        stored_relationships = 0
        for rel in all_relationships:
            # 通过原始实体ID找到名称，再找到数据库ID
            source_name = next((e.name for e in all_entities if e.id == rel.source_id), None)
            target_name = next((e.name for e in all_entities if e.id == rel.target_id), None)

            if source_name and target_name:
                source_db_id = entity_name_to_db_id.get(source_name)
                target_db_id = entity_name_to_db_id.get(target_name)

                if source_db_id and target_db_id:
                    graph_store.add_relationship(
                        source_id=source_db_id,
                        target_id=target_db_id,
                        relation_type=rel.relation_type,
                        description=rel.description
                    )
                    stored_relationships += 1

        if batch_errors:
            self.graph_rag_warning = f"GraphRAG 部分批次抽取失败，{batch_errors[0]}"

        logger.info(f"[GraphRAG] 实体抽取完成 | 新增实体={stored_entities} | 新增关系={stored_relationships} | 耗时={time.time()-extract_start:.2f}s")
        return stored_entities, stored_relationships

    def _merge_entities(self, entities) -> List:
        """合并重复实体"""
        entity_map = {}

        for entity in entities:
            key = (entity.name.lower().strip(), entity.type)
            if key in entity_map:
                # 合并描述
                existing = entity_map[key]
                if entity.description and entity.description not in existing.description:
                    existing.description = f"{existing.description}; {entity.description}" if existing.description else entity.description
            else:
                entity_map[key] = entity

        return list(entity_map.values())
