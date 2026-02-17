from pydantic_settings import BaseSettings
from functools import lru_cache

class KnowledgeSettings(BaseSettings):
    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Claude
    anthropic_api_key: str = ""

    # 智谱
    zhipu_api_key: str = ""

    # 阿里通义
    dashscope_api_key: str = ""

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # 文件存储
    kb_upload_dir: str = "./uploads/knowledge"

    # 切片参数
    chunk_size: int = 500
    chunk_overlap: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_knowledge_settings() -> KnowledgeSettings:
    return KnowledgeSettings()
