from pydantic_settings import BaseSettings
from functools import lru_cache


class KnowledgeSettings(BaseSettings):
    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_knowledge_settings() -> KnowledgeSettings:
    return KnowledgeSettings()
