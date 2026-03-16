from __future__ import annotations

import os
from typing import Optional


def create_claw_agent(*args, **kwargs):
    from .agent import create_claw_agent as _create_claw_agent

    return _create_claw_agent(*args, **kwargs)


def validate_working_directory(path: str) -> tuple[bool, Optional[str]]:
    if not path:
        return False, "路径不能为空"
    if not os.path.exists(path):
        return False, "目录不存在"
    if not os.path.isdir(path):
        return False, "路径不是目录"
    if not os.access(path, os.R_OK):
        return False, "没有读取权限"
    return True, None


__all__ = ["create_claw_agent", "validate_working_directory"]
