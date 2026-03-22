# ruff: noqa: E501  # Long prompt strings in MEMORY_SYSTEM_PROMPT
"""Middleware for loading agent memory/context from AGENTS.md files.

This module implements support for the AGENTS.md specification (https://agents.md/),
loading memory/context from configurable sources and injecting into the system prompt.

## Overview

AGENTS.md files provide project-specific context and instructions to help AI agents
work effectively. Unlike skills (which are on-demand workflows), memory is always
loaded and provides persistent context.

## Usage

```python
from deepagents import MemoryMiddleware
from deepagents.backends.filesystem import FilesystemBackend

# Security: FilesystemBackend allows reading/writing from the entire filesystem.
# Either ensure the agent is running within a sandbox OR add human-in-the-loop (HIL)
# approval to file operations.
backend = FilesystemBackend(root_dir="/")

middleware = MemoryMiddleware(
    backend=backend,
    sources=[
        "~/.deepagents/AGENTS.md",
        "./.deepagents/AGENTS.md",
    ],
)

agent = create_deep_agent(middleware=[middleware])
```

## Memory Sources

Sources are simply paths to AGENTS.md files that are loaded in order and combined.
Multiple sources are concatenated in order, with all content included.
Later sources appear after earlier ones in the combined prompt.

## File Format

AGENTS.md files are standard Markdown with no required structure.
Common sections include:
- Project overview
- Build/test commands
- Code style guidelines
- Architecture notes
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from langchain_core.runnables import RunnableConfig
    from langgraph.runtime import Runtime

    from deepagents.backends.protocol import BACKEND_TYPES, BackendProtocol

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    PrivateStateAttr,
    ResponseT,
)
from langchain.tools import ToolRuntime

from deepagents.middleware._utils import append_to_system_message

logger = logging.getLogger(__name__)


class MemoryState(AgentState):
    """State schema for `MemoryMiddleware`.

    Attributes:
        memory_contents: Dict mapping source paths to their loaded content.
            Marked as private so it's not included in the final agent state.
    """

    memory_contents: NotRequired[Annotated[dict[str, str], PrivateStateAttr]]


class MemoryStateUpdate(TypedDict):
    """State update for `MemoryMiddleware`."""

    memory_contents: dict[str, str]


MEMORY_SYSTEM_PROMPT = """<agent_memory>
{agent_memory}
</agent_memory>

<memory_guidelines>
    上面的 <agent_memory> 是从你文件系统中的文件加载的。当你从与用户的交互中学习时，可以通过调用 `edit_file` 工具保存新知识。

    **从反馈中学习：**
    - 你的主要优先事项之一是从与用户的交互中学习。这些学习可以是隐式的或显式的。这意味着将来你会记住这些重要信息。
    - 当你需要记住某事时，更新记忆必须是你的第一个、立即的行动 - 在回应用户之前、在调用其他工具之前、在做任何其他事情之前。立即更新记忆。
    - 当用户说某事更好/更差时，捕获原因并将其编码为模式。
    - 每次纠正都是永久改进的机会 - 不要只是修复眼前的问题，更新你的指令。
    - 更新记忆的一个好机会是当用户中断工具调用并提供反馈时。你应该在修改工具调用之前立即更新记忆。
    - 寻找纠正背后的基本原则，而不仅仅是具体的错误。
    - 用户可能不会明确要求你记住某事，但如果他们提供的信息对未来使用有用，你应该立即更新记忆。

    **询问信息：**
    - 如果你缺少执行操作的上下文（例如发送 Slack DM，需要用户 ID/电子邮件），你应该明确向用户询问此信息。
    - 你最好询问信息，不要假设你不知道的任何事情！
    - 当用户提供对未来使用有用的信息时，你应该立即更新记忆。

    **何时更新记忆：**
    - 当用户明确要求你记住某事时（例如"记住我的电子邮件"、"保存此偏好"）
    - 当用户描述你的角色或你应该如何行为时（例如"你是一个网络研究员"、"总是做 X"）
    - 当用户对你的工作提供反馈时 - 捕获错误的地方以及如何改进
    - 当用户提供工具使用所需的信息时（例如 slack 频道 ID、电子邮件地址）
    - 当用户提供对未来任务有用的上下文时，例如如何使用工具，或在特定情况下采取哪些行动
    - 当你发现新的模式或偏好时（编码风格、约定、工作流程）

    **何时不更新记忆：**
    - 当信息是临时的或短暂的时（例如"我要迟到了"、"我现在在用手机"）
    - 当信息是一次性任务请求时（例如"给我找个食谱"、"25 * 4 是多少？"）
    - 当信息是不揭示持久偏好的简单问题时（例如"今天是星期几？"、"你能解释 X 吗？"）
    - 当信息是确认或闲聊时（例如"听起来不错！"、"你好"、"谢谢"）
    - 当信息在未来对话中过时或不相关时
    - 永远不要在任何文件、记忆或系统提示中存储 API 密钥、访问令牌、密码或任何其他凭据。
    - 如果用户询问在哪里放置 API 密钥或提供 API 密钥，不要回显或保存它。

    **示例：**
    示例 1（记住用户信息）：
    用户：你能连接到我的 google 账户吗？
    智能体：当然，我会连接到你的 google 账户，你的 google 账户电子邮件是什么？
    用户：john@example.com
    智能体：让我把这个保存到我的记忆中。
    工具调用：edit_file(...) -> 记住用户的 google 账户电子邮件是 john@example.com

    示例 2（记住隐式用户偏好）：
    用户：你能给我写一个在 LangChain 中创建 deep agent 的示例吗？
    智能体：当然，我会给你写一个在 LangChain 中创建 deep agent 的示例 <Python 示例代码>
    用户：你能用 JavaScript 做这个吗
    智能体：让我把这个保存到我的记忆中。
    工具调用：edit_file(...) -> 记住用户更喜欢用 JavaScript 获取 LangChain 代码示例
    智能体：当然，这是 JavaScript 示例<JavaScript 示例代码>

    示例 3（不要记住短暂信息）：
    用户：我今晚要打篮球，所以我会离线几个小时。
    智能体：好的，我会在你的日历中添加一个时间段。
    工具调用：create_calendar_event(...) -> 只是调用工具，不提交任何内容到记忆，因为这是短暂信息
</memory_guidelines>
"""


class MemoryMiddleware(AgentMiddleware[MemoryState, ContextT, ResponseT]):
    """Middleware for loading agent memory from `AGENTS.md` files.

    Loads memory content from configured sources and injects into the system prompt.

    Supports multiple sources that are combined together.

    Args:
        backend: Backend instance or factory function for file operations.
        sources: List of `MemorySource` configurations specifying paths and names.
    """

    state_schema = MemoryState

    def __init__(
        self,
        *,
        backend: BACKEND_TYPES,
        sources: list[str],
        system_prompt_template: str = MEMORY_SYSTEM_PROMPT,
    ) -> None:
        """Initialize the memory middleware.

        Args:
            backend: Backend instance or factory function that takes runtime
                     and returns a backend. Use a factory for StateBackend.
            sources: List of memory file paths to load (e.g., `["~/.deepagents/AGENTS.md",
                     "./.deepagents/AGENTS.md"]`).

                     Display names are automatically derived from the paths.

                     Sources are loaded in order.
            system_prompt_template: Prompt template injected into the system
                message. Must include an `{agent_memory}` placeholder.
        """
        self._backend = backend
        self.sources = sources
        self.system_prompt_template = system_prompt_template

    def _get_backend(self, state: MemoryState, runtime: Runtime, config: RunnableConfig) -> BackendProtocol:
        """Resolve backend from instance or factory.

        Args:
            state: Current agent state.
            runtime: Runtime context for factory functions.
            config: Runnable config to pass to backend factory.

        Returns:
            Resolved backend instance.
        """
        if callable(self._backend):
            # Construct an artificial tool runtime to resolve backend factory
            tool_runtime = ToolRuntime(
                state=state,
                context=runtime.context,
                stream_writer=runtime.stream_writer,
                store=runtime.store,
                config=config,
                tool_call_id=None,
            )
            return self._backend(tool_runtime)  # ty: ignore[call-top-callable, invalid-argument-type]
        return self._backend

    def _format_agent_memory(self, contents: dict[str, str]) -> str:
        """Format memory with locations and contents paired together.

        Args:
            contents: Dict mapping source paths to content.

        Returns:
            Formatted string with location+content pairs wrapped in <agent_memory> tags.
        """
        if not contents:
            return self.system_prompt_template.format(agent_memory="(No memory loaded)")

        sections = [f"{path}\n{contents[path]}" for path in self.sources if contents.get(path)]

        if not sections:
            return self.system_prompt_template.format(agent_memory="(No memory loaded)")

        memory_body = "\n\n".join(sections)
        return self.system_prompt_template.format(agent_memory=memory_body)

    def before_agent(self, state: MemoryState, runtime: Runtime, config: RunnableConfig) -> MemoryStateUpdate | None:  # ty: ignore[invalid-method-override]
        """Load memory content before agent execution (synchronous).

        Loads memory from all configured sources and stores in state.
        Only loads if not already present in state.

        Args:
            state: Current agent state.
            runtime: Runtime context.
            config: Runnable config.

        Returns:
            State update with memory_contents populated.
        """
        # Skip if already loaded
        if "memory_contents" in state:
            return None

        backend = self._get_backend(state, runtime, config)
        contents: dict[str, str] = {}

        results = backend.download_files(list(self.sources))
        for path, response in zip(self.sources, results, strict=True):
            if response.error is not None:
                if response.error == "file_not_found":
                    continue
                msg = f"Failed to download {path}: {response.error}"
                raise ValueError(msg)
            if response.content is not None:
                contents[path] = response.content.decode("utf-8")
                logger.debug("Loaded memory from: %s", path)

        return MemoryStateUpdate(memory_contents=contents)

    async def abefore_agent(self, state: MemoryState, runtime: Runtime, config: RunnableConfig) -> MemoryStateUpdate | None:  # ty: ignore[invalid-method-override]
        """Load memory content before agent execution.

        Loads memory from all configured sources and stores in state.
        Only loads if not already present in state.

        Args:
            state: Current agent state.
            runtime: Runtime context.
            config: Runnable config.

        Returns:
            State update with memory_contents populated.
        """
        # Skip if already loaded
        if "memory_contents" in state:
            return None

        backend = self._get_backend(state, runtime, config)
        contents: dict[str, str] = {}

        results = await backend.adownload_files(list(self.sources))
        for path, response in zip(self.sources, results, strict=True):
            if response.error is not None:
                if response.error == "file_not_found":
                    continue
                msg = f"Failed to download {path}: {response.error}"
                raise ValueError(msg)
            if response.content is not None:
                contents[path] = response.content.decode("utf-8")
                logger.debug("Loaded memory from: %s", path)

        return MemoryStateUpdate(memory_contents=contents)

    def modify_request(self, request: ModelRequest[ContextT]) -> ModelRequest[ContextT]:
        """Inject memory content into the system message.

        Args:
            request: Model request to modify.

        Returns:
            Modified request with memory injected into system message.
        """
        contents = request.state.get("memory_contents", {})
        agent_memory = self._format_agent_memory(contents)

        new_system_message = append_to_system_message(request.system_message, agent_memory)

        return request.override(system_message=new_system_message)

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Wrap model call to inject memory into system prompt.

        Args:
            request: Model request being processed.
            handler: Handler function to call with modified request.

        Returns:
            Model response from handler.
        """
        modified_request = self.modify_request(request)
        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT]:
        """Async wrap model call to inject memory into system prompt.

        Args:
            request: Model request being processed.
            handler: Async handler function to call with modified request.

        Returns:
            Model response from handler.
        """
        modified_request = self.modify_request(request)
        return await handler(modified_request)
