import os
import logging
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from .config import get_knowledge_settings

logger = logging.getLogger("services.knowledge.vector_store")
settings = get_knowledge_settings()


class ChromaVectorStore:
    """ChromaDB 向量存储服务 (Windows 兼容)"""

    _client = None  # 共享客户端实例

    def __init__(self, kb_id: str, dimension: int = 1536):
        self.kb_id = kb_id
        self.collection_name = f"kb_{kb_id.replace('-', '_')}"
        self.dimension = dimension
        self._connect()
        logger.debug(f"[VectorStore] 初始化 | collection={self.collection_name} | dimension={dimension}")

    def _connect(self):
        if ChromaVectorStore._client is None:
            # 确保目录存在
            persist_dir = settings.chroma_persist_dir
            os.makedirs(persist_dir, exist_ok=True)
            ChromaVectorStore._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
        self.client = ChromaVectorStore._client

    def create_collection(self):
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def insert(self, chunks: List[Dict[str, Any]]) -> int:
        collection = self.create_collection()

        ids = [c["id"] for c in chunks]
        embeddings = [c["embedding"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {
                "doc_id": c["doc_id"],
                "filename": c.get("metadata", {}).get("filename", ""),
                "chunk_index": c.get("metadata", {}).get("chunk_index", 0)
            }
            for c in chunks
        ]

        logger.info(f"[VectorStore] 插入数据 | collection={self.collection_name} | 数量={len(chunks)}")
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"[VectorStore] 插入完成 | 成功插入 {len(chunks)} 条")
        return len(chunks)

    def search(self, query_embedding: List[float], top_k: int = 20) -> List[Dict]:
        try:
            collection = self.client.get_collection(self.collection_name)
        except Exception:
            logger.warning(f"[VectorStore] 搜索失败: collection {self.collection_name} 不存在")
            return []

        logger.debug(f"[VectorStore] 搜索 | collection={self.collection_name} | top_k={top_k}")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        if not results["ids"] or not results["ids"][0]:
            logger.info(f"[VectorStore] 搜索无结果 | collection={self.collection_name}")
            return []

        result_list = [
            {
                "id": results["ids"][0][i],
                "doc_id": results["metadatas"][0][i].get("doc_id"),
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i]  # 转换为相似度分数
            }
            for i in range(len(results["ids"][0]))
        ]
        logger.info(f"[VectorStore] 搜索完成 | collection={self.collection_name} | 返回={len(result_list)} 条 | "
                     f"最高分={result_list[0]['score']:.4f} | 最低分={result_list[-1]['score']:.4f}")
        return result_list

    def delete_by_doc_id(self, doc_id: str):
        try:
            collection = self.client.get_collection(self.collection_name)
            collection.delete(where={"doc_id": doc_id})
            logger.info(f"[VectorStore] 删除文档chunks | collection={self.collection_name} | doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"[VectorStore] 删除失败 | doc_id={doc_id} | error={e}")

    def drop_collection(self):
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"[VectorStore] 删除collection | {self.collection_name}")
        except Exception as e:
            logger.warning(f"[VectorStore] 删除collection失败 | {self.collection_name} | error={e}")


# 别名，保持向后兼容
MilvusVectorStore = ChromaVectorStore
