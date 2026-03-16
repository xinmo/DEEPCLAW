import logging
from typing import List, Optional
from .config import get_knowledge_settings

logger = logging.getLogger("services.knowledge.embedding")
settings = get_knowledge_settings()

# 模型ID到provider的映射
MODEL_PROVIDER_MAP = {
    "text-embedding-v4": "dashscope",
}

class EmbeddingService:
    """多模型 Embedding 服务适配器"""

    def __init__(self, model_id: str = "text-embedding-v4",
                 provider: Optional[str] = None,
                 api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model_id = model_id
        # 自动推断 provider，如果未指定
        self.provider = provider or MODEL_PROVIDER_MAP.get(model_id, "dashscope")
        logger.info(f"[Embedding] 初始化 | model={model_id} | provider={self.provider} | dimension={self.dimension}")
        self.embeddings = self._create_embeddings(self.provider, model_id, api_key, base_url)

    def _create_embeddings(self, provider: str, model_id: str,
                           api_key: Optional[str], base_url: Optional[str]):
        if provider == "dashscope":
            from langchain_community.embeddings import DashScopeEmbeddings
            return DashScopeEmbeddings(
                model=model_id,
                dashscope_api_key=api_key or settings.dashscope_api_key
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def _get_max_input_length(self) -> int:
        """获取模型的最大输入长度限制"""
        length_map = {
            "text-embedding-v4": 2048,  # 通义千问
        }
        return length_map.get(self.model_id, 2048)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        logger.info(f"[Embedding] 批量向量化 | model={self.model_id} | 文本数量={len(texts)}")

        # 安全截断：确保文本不超过模型限制
        max_length = self._get_max_input_length()
        truncated_texts = []
        truncated_count = 0

        for i, text in enumerate(texts):
            if len(text) > max_length:
                truncated_text = text[:max_length]
                truncated_texts.append(truncated_text)
                truncated_count += 1
                logger.warning(f"[Embedding] 文本 {i} 超长被截断 | 原长度={len(text)} | 截断后={len(truncated_text)}")
            else:
                truncated_texts.append(text)

        if truncated_count > 0:
            logger.warning(f"[Embedding] 共有 {truncated_count}/{len(texts)} 个文本被截断")

        result = self.embeddings.embed_documents(truncated_texts)
        logger.info(f"[Embedding] 批量向量化完成 | 返回 {len(result)} 个向量")
        return result

    def embed_query(self, text: str) -> List[float]:
        logger.debug(f"[Embedding] 查询向量化 | model={self.model_id} | 文本长度={len(text)}")
        # 查询也需要截断保护
        max_length = self._get_max_input_length()
        if len(text) > max_length:
            logger.warning(f"[Embedding] 查询文本超长被截断 | 原长度={len(text)} | 截断后={max_length}")
            text = text[:max_length]
        return self.embeddings.embed_query(text)

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        dim_map = {
            "text-embedding-v4": 2048,  # 通义
        }
        return dim_map.get(self.model_id, 2048)
