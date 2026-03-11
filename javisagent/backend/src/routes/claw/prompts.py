from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import os

router = APIRouter()

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "system_prompt.txt"

# 从 agent.py 导入默认提示词
from ...services.claw.agent import SYSTEM_PROMPT_TEMPLATE


class PromptUpdateRequest(BaseModel):
    content: str


class PromptInfo(BaseModel):
    id: str
    name: str
    description: str


class PromptDetail(BaseModel):
    id: str
    name: str
    content: str
    default_content: str


def get_current_system_prompt() -> str:
    """读取当前系统提示词，优先从配置文件读取，不存在则使用默认"""
    if SYSTEM_PROMPT_FILE.exists():
        try:
            return SYSTEM_PROMPT_FILE.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            return SYSTEM_PROMPT_TEMPLATE
    return SYSTEM_PROMPT_TEMPLATE


@router.get("/prompts")
async def get_prompts():
    """获取所有可管理的提示词列表"""
    return {
        "prompts": [
            {
                "id": "system_prompt",
                "name": "系统提示词",
                "description": "Claw 智能体的默认系统提示词"
            }
        ]
    }


@router.get("/prompts/{prompt_id}")
async def get_prompt_detail(prompt_id: str):
    """获取指定提示词的详细内容"""
    if prompt_id != "system_prompt":
        raise HTTPException(status_code=404, detail="Prompt not found")

    current_content = get_current_system_prompt()

    return {
        "id": "system_prompt",
        "name": "系统提示词",
        "content": current_content,
        "default_content": SYSTEM_PROMPT_TEMPLATE
    }


@router.put("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, request: PromptUpdateRequest):
    """更新指定提示词"""
    if prompt_id != "system_prompt":
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")

    try:
        # 确保配置目录存在
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # 写入配置文件
        SYSTEM_PROMPT_FILE.write_text(request.content, encoding='utf-8')

        return {"success": True, "message": "保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/prompts/{prompt_id}/reset")
async def reset_prompt(prompt_id: str):
    """重置为默认提示词"""
    if prompt_id != "system_prompt":
        raise HTTPException(status_code=404, detail="Prompt not found")

    try:
        # 删除配置文件，回退到默认
        if SYSTEM_PROMPT_FILE.exists():
            SYSTEM_PROMPT_FILE.unlink()

        return {"success": True, "content": SYSTEM_PROMPT_TEMPLATE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")
