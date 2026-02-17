from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from .config import get_knowledge_settings

settings = get_knowledge_settings()


class MilvusVectorStore:
    """Milvus 向量存储服务"""

    def __init__(self, kb_id: str, dimension: int = 1536):
        self.kb_id = kb_id
        self.collection_name = f"kb_{kb_id.replace('-', '_')}"
        self.dimension = dimension
        self._connect()

    def _connect(self):
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port
        )

    def create_collection(self):
        if utility.has_collection(self.collection_name):
            return Collection(self.collection_name)

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=36),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]
        schema = CollectionSchema(fields, description=f"Knowledge base {self.kb_id}")
        collection = Collection(self.collection_name, schema)

        # 创建索引
        index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 1024}}
        collection.create_index("embedding", index_params)
        return collection

    def insert(self, chunks: List[Dict[str, Any]]) -> int:
        collection = self.create_collection()
        data = [
            [c["id"] for c in chunks],
            [c["doc_id"] for c in chunks],
            [c["content"] for c in chunks],
            [c["embedding"] for c in chunks],
            [c.get("metadata", {}) for c in chunks],
        ]
        collection.insert(data)
        collection.flush()
        return len(chunks)

    def search(self, query_embedding: List[float], top_k: int = 20) -> List[Dict]:
        collection = Collection(self.collection_name)
        collection.load()
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["id", "doc_id", "content", "metadata"]
        )
        return [
            {"id": hit.id, "doc_id": hit.entity.get("doc_id"), "content": hit.entity.get("content"),
             "metadata": hit.entity.get("metadata"), "score": hit.score}
            for hit in results[0]
        ]

    def delete_by_doc_id(self, doc_id: str):
        collection = Collection(self.collection_name)
        collection.delete(f'doc_id == "{doc_id}"')

    def drop_collection(self):
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
