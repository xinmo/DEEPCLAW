"""MCP 配置管理路由。

提供对 ~/.deepagents/.mcp.json 的读写 API，
前端 MCP 管理页面通过此接口增删改 MCP 服务器配置。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_MCP_CONFIG_DIR = Path.home() / ".deepagents"
_MCP_CONFIG_PATH = _MCP_CONFIG_DIR / ".mcp.json"


def _read_mcp_config() -> dict[str, Any]:
    """读取 MCP 配置文件，不存在时返回空配置。"""
    if not _MCP_CONFIG_PATH.exists():
        return {"mcpServers": {}}
    try:
        content = _MCP_CONFIG_PATH.read_text(encoding="utf-8")
        data = json.loads(content)
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read MCP config: %s", exc)
        return {"mcpServers": {}}


def _write_mcp_config(data: dict[str, Any]) -> None:
    """将 MCP 配置写入文件（原子写入）。"""
    _MCP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = _MCP_CONFIG_PATH.with_suffix(".json.tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(_MCP_CONFIG_PATH)
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        raise exc


class MCPConfigBody(BaseModel):
    mcpServers: dict[str, Any]


@router.get("/mcp")
async def get_mcp_config() -> dict[str, Any]:
    """获取当前 MCP 配置。"""
    return _read_mcp_config()


@router.put("/mcp")
async def save_mcp_config(body: MCPConfigBody) -> dict[str, Any]:
    """保存 MCP 配置（整体替换）。"""
    # 简单校验每个服务器配置
    for name, config in body.mcpServers.items():
        if not isinstance(config, dict):
            raise HTTPException(
                status_code=422,
                detail=f"服务器 '{name}' 的配置必须是对象",
            )
        server_type = config.get("type") or config.get("transport", "stdio")
        if server_type == "stdio":
            if "command" not in config:
                raise HTTPException(
                    status_code=422,
                    detail=f"stdio 服务器 '{name}' 缺少必填字段 'command'",
                )
        elif server_type in ("sse", "http"):
            if "url" not in config:
                raise HTTPException(
                    status_code=422,
                    detail=f"{server_type} 服务器 '{name}' 缺少必填字段 'url'",
                )
        else:
            raise HTTPException(
                status_code=422,
                detail=f"服务器 '{name}' 的 type 不支持: {server_type!r}，支持: stdio, sse, http",
            )

    data = {"mcpServers": body.mcpServers}
    try:
        _write_mcp_config(data)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"写入 MCP 配置失败: {exc}") from exc

    return {"success": True, "mcpServers": body.mcpServers}
