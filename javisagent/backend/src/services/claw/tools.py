"""Web search and URL fetching tools for Claw agent."""

from typing import Any, Literal

_UNSET = object()
_tavily_client: Any | object | None = _UNSET


def _get_tavily_client() -> Any | None:
    """获取或初始化 Tavily 客户端单例。

    Returns:
        TavilyClient 实例，如果未配置 API Key 则返回 None
    """
    global _tavily_client
    if _tavily_client is not _UNSET:
        return _tavily_client

    import os
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if tavily_api_key:
        try:
            from tavily import TavilyClient
            _tavily_client = TavilyClient(api_key=tavily_api_key)
        except ImportError:
            _tavily_client = None
    else:
        _tavily_client = None

    return _tavily_client


def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> dict[str, Any]:
    """使用 Tavily 搜索网络获取最新信息和文档。

    此工具搜索网络并返回相关结果。收到结果后，必须将信息综合成自然、有用的回复。

    Args:
        query: 搜索查询（要具体和详细）
        max_results: 返回结果数量（默认：5）
        topic: 搜索主题类型 - "general" 用于大多数查询，"news" 用于时事
        include_raw_content: 包含完整页面内容（警告：使用更多 token）

    Returns:
        包含以下内容的字典：
        - results: 搜索结果列表，每个包含：
            - title: 页面标题
            - url: 页面 URL
            - content: 页面相关摘录
            - score: 相关性分数（0-1）
        - query: 原始搜索查询

    重要提示：使用此工具后：
    1. 阅读每个结果的 'content' 字段
    2. 提取回答用户问题的相关信息
    3. 将其综合成清晰的自然语言回复
    4. 通过提及页面标题或 URL 来引用来源
    5. 永远不要向用户显示原始 JSON - 始终提供格式化的回复
    """
    try:
        import requests
        from tavily import (
            BadRequestError,
            InvalidAPIKeyError,
            MissingAPIKeyError,
            UsageLimitExceededError,
        )
        from tavily.errors import ForbiddenError, TimeoutError as TavilyTimeoutError
    except ImportError as exc:
        return {
            "error": f"未安装所需包: {exc.name}. 使用以下命令安装: pip install tavily-python",
            "query": query,
        }

    client = _get_tavily_client()
    if client is None:
        return {
            "error": "未配置 Tavily API Key. 请设置 TAVILY_API_KEY 环境变量。",
            "query": query,
        }

    try:
        return client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
    except (
        requests.exceptions.RequestException,
        ValueError,
        TypeError,
        BadRequestError,
        ForbiddenError,
        InvalidAPIKeyError,
        MissingAPIKeyError,
        TavilyTimeoutError,
        UsageLimitExceededError,
    ) as e:
        return {"error": f"网络搜索错误: {str(e)}", "query": query}


def fetch_url(url: str, timeout: int = 30) -> dict[str, Any]:
    """从 URL 获取内容并转换为 markdown 格式。

    此工具获取网页内容并将其转换为干净的 markdown 文本，
    使 HTML 内容易于阅读和处理。收到 markdown 后，
    必须将信息综合成自然、有用的回复。

    Args:
        url: 要获取的 URL（必须是有效的 HTTP/HTTPS URL）
        timeout: 请求超时时间（秒）（默认：30）

    Returns:
        包含以下内容的字典：
        - success: 请求是否成功
        - url: 重定向后的最终 URL
        - markdown_content: 转换为 markdown 的页面内容
        - status_code: HTTP 状态码
        - content_length: markdown 内容的字符长度

    重要提示：使用此工具后：
    1. 阅读 markdown 内容
    2. 提取回答用户问题的相关信息
    3. 将其综合成清晰的自然语言回复
    4. 除非特别要求，否则永远不要向用户显示原始 markdown
    """
    try:
        import requests
        from markdownify import markdownify
    except ImportError as exc:
        return {
            "error": f"未安装所需包: {exc.name}. 使用以下命令安装: pip install requests markdownify",
            "url": url,
        }

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; JavisAgent/1.0)"},
        )
        response.raise_for_status()

        # 转换 HTML 内容为 markdown
        markdown_content = markdownify(response.text)

        return {
            "url": str(response.url),
            "markdown_content": markdown_content,
            "status_code": response.status_code,
            "content_length": len(markdown_content),
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"获取 URL 错误: {str(e)}", "url": url}
