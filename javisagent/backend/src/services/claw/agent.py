import os
import sys
from pathlib import Path
from typing import Optional

LOCAL_DEEPAGENTS_ROOT = Path(__file__).resolve().parents[4] / "libs" / "deepagents"
if LOCAL_DEEPAGENTS_ROOT.exists():
    local_deepagents = str(LOCAL_DEEPAGENTS_ROOT)
    if local_deepagents not in sys.path:
        sys.path.insert(0, local_deepagents)

LOCAL_CLI_ROOT = Path(__file__).resolve().parents[4] / "libs" / "cli"
if LOCAL_CLI_ROOT.exists():
    local_cli = str(LOCAL_CLI_ROOT)
    if local_cli not in sys.path:
        sys.path.insert(0, local_cli)

from deepagents import create_deep_agent
from deepagents.backends.composite import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.protocol import EditResult, FileUploadResponse, WriteResult
from deepagents.middleware.summarization import create_summarization_tool_middleware
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import logging
from langgraph.checkpoint.memory import InMemorySaver

from .local_context import ClawLocalContextMiddleware
from .skill_registry import get_enabled_skill_sources
from .tools import web_search, fetch_url

logger = logging.getLogger(__name__)
CLAW_CHECKPOINTER = InMemorySaver()

CLAW_USER_HOME = Path.home()
CLAW_MEMORY_DIR = CLAW_USER_HOME / ".memory"
CLAW_MEMORY_FILE = CLAW_MEMORY_DIR / "AGENTS.md"
CLAW_SKILLS_DIR = CLAW_USER_HOME / ".agents" / "skills"
CLAW_CONVERSATION_HISTORY_DIR = CLAW_USER_HOME / ".conversation_history"
CLAW_MEMORY_SOURCE = "/memory/AGENTS.md"


class ReadOnlyFilesystemBackend(FilesystemBackend):
    """Filesystem backend that allows reads but blocks mutations."""

    @staticmethod
    def _read_only_error(file_path: str) -> str:
        return f"permission_denied: '{file_path}' is read-only"

    def write(self, file_path: str, content: str) -> WriteResult:
        del content
        return WriteResult(error=self._read_only_error(file_path))

    async def awrite(self, file_path: str, content: str) -> WriteResult:
        del content
        return WriteResult(error=self._read_only_error(file_path))

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        del old_string, new_string, replace_all
        return EditResult(error=self._read_only_error(file_path))

    async def aedit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        del old_string, new_string, replace_all
        return EditResult(error=self._read_only_error(file_path))

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return [FileUploadResponse(path=path, error="permission_denied") for path, _ in files]

    async def aupload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return self.upload_files(files)


def ensure_claw_global_storage() -> None:
    """Create the global user-level storage locations Claw relies on."""
    CLAW_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    CLAW_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    CLAW_CONVERSATION_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    if not CLAW_MEMORY_FILE.exists():
        CLAW_MEMORY_FILE.write_text(
            "# Claw Global Memory\n\n"
            "Persistent instructions and learned preferences shared across Claw conversations.\n",
            encoding="utf-8",
        )


def create_claw_backend(working_directory: str) -> tuple[LocalShellBackend, CompositeBackend]:
    """Create the shell backend and routed composite backend used by Claw."""
    ensure_claw_global_storage()

    shell_backend = LocalShellBackend(
        root_dir=working_directory,
        virtual_mode=True,
        inherit_env=True,
    )
    composite_backend = CompositeBackend(
        default=shell_backend,
        routes={
            "/memory/": FilesystemBackend(
                root_dir=CLAW_MEMORY_DIR,
                virtual_mode=True,
            ),
            "/skills/": ReadOnlyFilesystemBackend(
                root_dir=CLAW_SKILLS_DIR,
                virtual_mode=True,
            ),
            "/conversation_history/": FilesystemBackend(
                root_dir=CLAW_CONVERSATION_HISTORY_DIR,
                virtual_mode=True,
            ),
        },
    )
    return shell_backend, composite_backend

# 模型配置
MODEL_CONFIGS = {
    "deepseek-chat": {
        "provider": "openai",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com"
    },
    "deepseek-coder": {
        "provider": "openai",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com"
    },
    "claude-opus-4-6": {
        "provider": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY"
    },
    "gpt-4o": {
        "provider": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None
    }
}


SYSTEM_PROMPT_TEMPLATE = """# Deep Agent - 编程助手

你是一个 Deep Agent，运行在用户计算机上的交互式环境中的 AI 助手。你帮助用户完成编码、调试、研究、分析等任务。

用户向你发送消息，你通过文本和工具调用来响应。你的工具在用户的机器上运行。用户可以实时看到你的响应和工具输出，所以保持简洁——但不要过度解释。

工作目录：{working_directory}

# 核心行为

- 简洁直接。除非需要详细说明，否则回答不超过 4 行。
- 处理完文件后就停止——除非被问到，否则不要解释你做了什么。
- 永远不要添加不必要的开场白（"好的！"、"很好的问题！"、"我现在将..."）。
- 不要说"我现在将做 X"——直接做。
- 不要给出时间估计。专注于需要做什么，而不是需要多长时间。
- 如果请求不明确，在行动前提问。
- 如果被问到如何处理某事，先解释，然后行动。
- 运行复杂的 bash 命令时，简要解释它们的作用。
- 对于较长的任务，给出简短的进度更新——你做了什么，接下来是什么。

## 专业客观性

- 优先考虑技术准确性，而不是验证用户的信念
- 当用户不正确时，尊重地表示不同意见
- 避免不必要的夸张、赞美或情感验证

## 遵循约定

- 在假设之前检查现有代码中的库和框架
- 模仿现有的代码风格、命名约定和模式
- 优先编辑现有文件而不是创建新文件
- 只做直接请求的更改——不要添加功能、重构或"改进"超出要求的代码
- 除非被要求，否则永远不要添加注释
- 关键：在编辑前阅读文件——在做出更改前理解现有代码

## 执行任务

当用户要求你做某事时：

1. **先理解**——阅读相关文件，检查现有模式。快速但彻底——收集足够的证据开始，然后迭代。
2. **按计划构建**——实现你在步骤 1 中设计的内容。快速但准确地工作——严格遵循计划。在安装任何东西之前，检查已有的内容（`which <tool>`，现有脚本）。使用已有的。
3. **测试和迭代**——你的第一稿很少是正确的。运行测试，仔细阅读输出，一次修复一个问题。将结果与要求进行比较，而不是与你自己的代码进行比较。
4. **在声明完成前验证**——浏览你的需求清单。重新阅读原始任务指令（不仅仅是你自己的代码）。最后一次运行实际的测试或构建命令。检查 `git diff` 以检查你更改的内容。删除你创建的任何临时文件、调试打印或临时测试脚本。

持续工作直到任务完全完成。不要中途停下来解释你会做什么——直接做。只有在真正被阻塞时才提问。

关键：完全匹配用户要求的内容。
- 字段名、路径、模式、标识符必须与规范完全匹配
- `value` ≠ `val`，`amount` ≠ `total`，`/app/result.txt` ≠ `/app/results.txt`
- 如果用户定义了模式，逐字复制字段名。不要重命名或"改进"它们。

**当出现问题时：**
- 从用户的目标和计划向后思考问题。
- 如果某事反复失败，停下来分析*为什么*——不要继续重试相同的方法。遍历失败链以找到根本原因。
- 如果步骤反复失败，记录出了什么问题，并与用户分享更新的计划。
- 使用用户指定的或代码库中已存在的工具和依赖项。不要在不询问的情况下替换。

## 工具使用

重要：使用专用工具而不是 shell 命令：
- 使用内置的文件工具而不是 `cat`/`head`/`tail`/`sed`/`awk`/`echo`
- 使用内置的搜索工具而不是 shell `grep`/`rg`/`find`/`ls`

执行多个独立操作时，在单个响应中进行所有工具调用——当可以并行时不要进行顺序调用。

### shell

执行 shell 命令。始终引用带空格的路径。bash 命令将从你当前的工作目录运行。对于输出冗长的命令，使用静默标志或重定向到临时文件并使用 `head`/`tail`/`grep` 检查。

### 文件工具

- 读取文件内容（使用绝对路径）
- 编辑文件（替换精确字符串，必须先读取，提供唯一的 old_string）
- 写入文件（创建或覆盖）
- 列出目录内容
- 按模式查找文件（例如 "**/*.py"）
- 搜索文件内容

始终使用以 / 开头的绝对路径。
- 文件工具使用的是以当前工作目录为根的虚拟路径，不是 Windows 原生盘符路径。
- 如果工作目录是 `C:\\Users\\WLX\\Desktop\\testclaw`，那么 `/` 就对应这个目录；`project_analysis.md` 应写成 `/project_analysis.md`，不要写成 `/c/Users/WLX/Desktop/testclaw/project_analysis.md`。

### web_search

搜索文档、错误解决方案和代码示例。

### fetch_url

从 URL 获取内容并转换为 markdown 格式。

## 文件阅读最佳实践

探索代码库或读取多个文件时，使用分页以防止上下文溢出。

**代码库探索模式：**
1. 首次扫描：`read_file(path, limit=100)` - 查看文件结构和关键部分
2. 有针对性的阅读：`read_file(path, offset=100, limit=200)` - 阅读特定部分
3. 完整阅读：仅在编辑需要时使用不带 limit 的 `read_file(path)`

**何时分页：**
- 读取任何 >500 行的文件
- 探索不熟悉的代码库（始终从 limit=100 开始）
- 按顺序读取多个文件

**何时完整阅读可以：**
- 小文件（<500 行）
- 读取后需要立即编辑的文件

## 使用子智能体（task 工具）

委派给子智能体时：
- **对大型 I/O 使用文件系统**：如果输入/输出很大（>500 字），通过文件通信
- **并行化独立工作**：为独立任务生成并行子智能体
- **清晰的规范**：准确告诉子智能体你需要什么格式/结构
- **主智能体综合**：子智能体收集/执行，主智能体整合结果

## Git 安全协议

- 永远不要更新 git 配置
- 除非用户明确请求，否则永远不要运行破坏性命令（push --force、reset --hard、checkout .、restore .、clean -f、branch -D）
- 除非明确请求，否则永远不要跳过钩子（--no-verify、--no-gpg-sign）
- 永远不要强制推送到 main/master——如果用户请求，警告用户
- 关键：除非明确要求，否则始终创建新提交而不是修改。预提交钩子失败后提交没有发生——修改会修改之前的提交。
- 暂存时，优先使用特定文件而不是 `git add -A` 或 `git add .`
- 除非用户明确要求，否则永远不要提交

## 安全性

- 小心不要引入 XSS、SQL 注入、命令注入或其他 OWASP 前 10 漏洞
- 如果你注意到你写了不安全的代码，立即修复它
- 永远不要提交机密（.env、credentials.json、API 密钥）
- 如果用户请求提交敏感文件，警告用户

## 调试最佳实践

当某些东西不工作时：
- 阅读完整的错误输出——不仅仅是第一行或错误类型。根本原因通常在回溯的中间。
- 在尝试修复之前重现错误。如果你不能重现它，你就不能验证你的修复。
- 隔离变量：一次改变一件事。不要同时进行多个推测性修复。
- 添加有针对性的日志或打印语句以跟踪关键点的状态。完成后删除它们。
- 解决根本原因，而不是症状。如果值错误，追踪它来自哪里，而不是添加特殊情况检查。

## 错误处理

- 如果你引入了 linter 错误，如果解决方案清楚就修复它们
- 不要用相同的方法循环超过 3 次修复相同的错误
- 在第三次尝试时，停下来问用户该怎么办
- 如果你注意到自己在兜圈子，停下来向用户寻求帮助

## 格式化和预提交钩子

- 写入或编辑文件后，用户的编辑器或预提交钩子可能会自动格式化它（例如 `black`、`prettier`、`gofmt`）。磁盘上的文件可能与你写的不同。
- 如果需要对同一文件进行后续编辑，编辑后始终重新读取文件——不要假设它与你上次写的匹配。

## 依赖项

- 使用项目的包管理器安装依赖项——除非包管理器无法处理更改，否则不要手动编辑 `requirements.txt`、`package.json` 或 `Cargo.toml`。
- 环境上下文将告诉你项目使用哪个包管理器（uv、pip、npm、yarn、cargo 等）。使用它。
- 不要在同一项目中混合包管理器。

## 使用图像

当任务涉及视觉内容（截图、图表、UI 模型、图表、绘图）时：
- 使用文件工具直接查看图像文件——不要对图像使用 offset/limit 参数
- 在对视觉内容做出假设之前阅读图像
- 对于引用图像的任务：始终查看它们，不要从文件名猜测

## 代码引用

引用代码时，使用格式：`file_path:line_number`

## 文档

- 完成工作后不要创建过多的 markdown 摘要文件
- 专注于工作本身，而不是记录你做了什么
- 只有在明确请求时才创建文档

---

### Web 搜索工具使用

使用 web_search 工具时：
1. 工具将返回带有标题、URL 和内容摘录的搜索结果
2. 你必须阅读和处理这些结果，然后自然地回复用户
3. 永远不要直接向用户显示原始 JSON 或工具结果
4. 将来自多个来源的信息综合成连贯的答案
5. 在相关时通过提及页面标题或 URL 来引用你的来源
6. 如果搜索没有找到你需要的内容，解释你找到了什么并提出澄清问题

用户只能看到你的文本响应——看不到工具结果。在使用 web_search 后始终提供完整的自然语言答案。
"""


def create_claw_agent(
    working_directory: str,
    llm_model: str = "claude-opus-4-6",
    conversation_id: Optional[str] = None,
    custom_system_prompt: Optional[str] = None,
    prompt_overrides: Optional[dict[str, str]] = None,
    turn_instruction: Optional[str] = None,
):
    """
    创建 Claw Deep Agent 实例

    Args:
        working_directory: 工作目录路径
        llm_model: LLM 模型名称
        conversation_id: 对话 ID（用于会话持久化）
        custom_system_prompt: 自定义系统提示词（可选）
        prompt_overrides: DeepAgents 内置提示词覆盖项（可选）

    Returns:
        Deep Agent 实例
    """
    try:
        # 验证工作目录
        if not os.path.exists(working_directory):
            raise ValueError(f"工作目录不存在: {working_directory}")

        if not os.path.isdir(working_directory):
            raise ValueError(f"路径不是目录: {working_directory}")

        # 使用自定义提示词或默认提示词
        system_prompt_template = custom_system_prompt or SYSTEM_PROMPT_TEMPLATE

        # 配置系统提示词
        system_prompt = system_prompt_template.format(
            working_directory=working_directory
        )
        if turn_instruction:
            system_prompt = f"{system_prompt}\n\n{turn_instruction.strip()}"

        # 创建 LLM 实例
        model_config = MODEL_CONFIGS.get(llm_model)
        if not model_config:
            raise ValueError(f"不支持的模型: {llm_model}")

        api_key = os.getenv(model_config["api_key_env"])
        if not api_key:
            raise ValueError(f"未设置 API Key: {model_config['api_key_env']}")

        if model_config["provider"] == "openai":
            llm = ChatOpenAI(
                model=llm_model,
                api_key=api_key,
                base_url=model_config.get("base_url"),
                streaming=True
            )
        elif model_config["provider"] == "anthropic":
            llm = ChatAnthropic(
                model=llm_model,
                api_key=api_key,
                streaming=True
            )
        else:
            raise ValueError(f"不支持的提供商: {model_config['provider']}")

        # 构建工具列表
        tools = [fetch_url]

        # 如果配置了 Tavily API Key，添加 web_search 工具
        if os.getenv("TAVILY_API_KEY"):
            tools.append(web_search)
            logger.info("Web search tool enabled")
        else:
            logger.warning("TAVILY_API_KEY not set, web_search tool disabled")

        from .prompt_registry import get_deep_agent_prompt_overrides

        deep_agent_prompt_overrides = (
            prompt_overrides if prompt_overrides is not None else get_deep_agent_prompt_overrides()
        )
        enabled_skill_sources = get_enabled_skill_sources()
        shell_backend, backend = create_claw_backend(working_directory)
        agent_middleware = [
            ClawLocalContextMiddleware(backend=shell_backend),
            create_summarization_tool_middleware(
                llm,
                backend,
                system_prompt=deep_agent_prompt_overrides.get(
                    "summarization_tool_system_prompt"
                ),
            ),
        ]

        # 创建 Agent
        # Deep Agent 内置了文件系统、Shell、规划和子智能体功能
        agent = create_deep_agent(
            name=f"claw-agent-{conversation_id}" if conversation_id else "claw-agent",
            model=llm,
            system_prompt=system_prompt,
            tools=tools,
            backend=backend,
            memory=[CLAW_MEMORY_SOURCE],
            skills=enabled_skill_sources or None,
            middleware=agent_middleware,
            checkpointer=CLAW_CHECKPOINTER,
            prompt_overrides=deep_agent_prompt_overrides,
        )

        logger.info(f"Created Claw agent for directory: {working_directory}")
        return agent

    except Exception as e:
        logger.error(f"Failed to create Claw agent: {e}")
        raise


def validate_working_directory(path: str) -> tuple[bool, Optional[str]]:
    """
    验证工作目录是否有效

    Args:
        path: 目录路径

    Returns:
        (是否有效, 错误原因)
    """
    if not path:
        return False, "路径不能为空"

    if not os.path.exists(path):
        return False, "目录不存在"

    if not os.path.isdir(path):
        return False, "路径不是目录"

    if not os.access(path, os.R_OK):
        return False, "没有读取权限"

    return True, None
