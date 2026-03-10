import os
from typing import Optional
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
import logging

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """你是一个专业的编程助手，可以帮助用户完成各种编程任务。

你可以使用以下工具：
- 文件系统工具：读取、写入、编辑、搜索文件
- Shell 命令：执行任何命令行操作
- 规划工具：分解复杂任务为可执行步骤
- 子智能体：创建专门的子任务智能体

工作目录：{working_directory}

请始终：
1. 在执行操作前说明你的计划
2. 使用工具时提供清晰的描述
3. 遇到错误时提供解决方案
4. 完成任务后总结结果

注意：
- 所有文件操作都相对于工作目录进行
- Shell 命令在工作目录中执行
- 请确保操作的安全性
"""


def create_claw_agent(
    working_directory: str,
    llm_model: str = "claude-opus-4-6",
    conversation_id: Optional[str] = None
):
    """
    创建 Claw Deep Agent 实例

    Args:
        working_directory: 工作目录路径
        llm_model: LLM 模型名称
        conversation_id: 对话 ID（用于会话持久化）

    Returns:
        Deep Agent 实例
    """
    try:
        # 验证工作目录
        if not os.path.exists(working_directory):
            raise ValueError(f"工作目录不存在: {working_directory}")

        if not os.path.isdir(working_directory):
            raise ValueError(f"路径不是目录: {working_directory}")

        # 配置系统提示词
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            working_directory=working_directory
        )

        # 创建 Agent
        agent = create_deep_agent(
            model=llm_model,
            system_prompt=system_prompt,
            checkpointer=MemorySaver(),
            # 启用所有工具
            enable_filesystem=True,
            enable_shell=True,
            enable_planning=True,
            enable_subagents=True,
            # 设置工作目录
            working_directory=working_directory,
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
