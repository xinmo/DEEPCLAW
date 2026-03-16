from typing import Optional, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .config import get_knowledge_settings

settings = get_knowledge_settings()

# 模型 ID 到提供商的映射
MODEL_PROVIDER_MAP = {
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-3.5-turbo": "openai",
    # Claude
    "claude-3-5-sonnet-20241022": "claude",
    "claude-3-opus-20240229": "claude",
    "claude-3-sonnet-20240229": "claude",
    # 智谱
    "glm-4": "zhipu",
    "glm-4-plus": "zhipu",
    "glm-3-turbo": "zhipu",
    # 通义
    "qwen-max": "dashscope",
    "qwen-plus": "dashscope",
    "qwen-turbo": "dashscope",
    # DeepSeek
    "deepseek-chat": "deepseek",
    "deepseek-coder": "deepseek",
}

class LLMService:
    """多模型 LLM 服务适配器"""

    def __init__(self, provider: Optional[str] = None, model_id: str = "gpt-4o",
                 api_key: Optional[str] = None, base_url: Optional[str] = None):
        # 如果没有指定 provider，根据 model_id 自动检测
        if provider is None:
            provider = MODEL_PROVIDER_MAP.get(model_id, "openai")
        self.provider = provider
        self.model_id = model_id
        self.llm = self._create_llm(provider, model_id, api_key, base_url)

    def _create_llm(self, provider: str, model_id: str,
                    api_key: Optional[str], base_url: Optional[str]):
        if provider == "openai":
            return ChatOpenAI(
                model=model_id,
                api_key=api_key or settings.openai_api_key,
                base_url=base_url or settings.openai_base_url,
                streaming=True
            )
        elif provider == "claude":
            return ChatAnthropic(
                model=model_id,
                api_key=api_key or settings.anthropic_api_key,
                streaming=True
            )
        elif provider == "zhipu":
            # 优先使用 langchain-zhipu 专用包
            try:
                from langchain_zhipu import ChatZhipuAI
            except ImportError:
                from langchain_community.chat_models import ChatZhipuAI
            return ChatZhipuAI(
                model=model_id,
                api_key=api_key or settings.zhipu_api_key,
                streaming=True
            )
        elif provider == "dashscope":
            # 优先使用 langchain-dashscope 专用包
            try:
                from langchain_dashscope import ChatDashScope
                return ChatDashScope(
                    model=model_id,
                    api_key=api_key or settings.dashscope_api_key,
                    streaming=True
                )
            except ImportError:
                from langchain_community.chat_models import ChatTongyi
                return ChatTongyi(
                    model=model_id,
                    dashscope_api_key=api_key or settings.dashscope_api_key,
                    streaming=True
                )
        elif provider == "deepseek":
            # DeepSeek 兼容 OpenAI API
            return ChatOpenAI(
                model=model_id,
                api_key=api_key or settings.deepseek_api_key,
                base_url=base_url or settings.deepseek_base_url,
                streaming=True
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def astream(self, prompt: str, system: str = "") -> AsyncGenerator[str, None]:
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield chunk.content
