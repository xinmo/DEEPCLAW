from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from .config import get_knowledge_settings

settings = get_knowledge_settings()

class EmbeddingService:
    """多模型 Embedding 服务适配器"""

    def __init__(self, provider: str = "openai", model_id: str = "text-embedding-3-small",
                 api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.provider = provider
        self.model_id = model_id
        self.embeddings = self._create_embeddings(provider, model_id, api_key, base_url)

    def _create_embeddings(self, provider: str, model_id: str,
                           api_key: Optional[str], base_url: Optional[str]):
        if provider == "openai":
            return OpenAIEmbeddings(
                model=model_id,
                openai_api_key=api_key or settings.openai_api_key,
                openai_api_base=base_url or settings.openai_base_url
            )
        elif provider == "zhipu":
            from langchain_community.embeddings import ZhipuAIEmbeddings
            return ZhipuAIEmbeddings(
                model=model_id,
                api_key=api_key or settings.zhipu_api_key
            )
        elif provider == "dashscope":
            from langchain_community.embeddings import DashScopeEmbeddings
            return DashScopeEmbeddings(
                model=model_id,
                dashscope_api_key=api_key or settings.dashscope_api_key
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        dim_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "embedding-2": 1024,  # 智谱
            "text-embedding-v2": 1536,  # 通义
        }
        return dim_map.get(self.model_id, 1536)
