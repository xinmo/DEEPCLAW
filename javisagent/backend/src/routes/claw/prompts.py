from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.claw.prompt_registry import (
    get_prompt_detail,
    list_prompt_infos,
    reset_prompt,
    save_prompt,
)

router = APIRouter()


class PromptUpdateRequest(BaseModel):
    content: str


@router.get("/prompts")
async def get_prompts() -> dict[str, list[dict[str, str]]]:
    return {"prompts": list_prompt_infos()}


@router.get("/prompts/{prompt_id}")
async def get_prompt_detail_route(prompt_id: str) -> dict[str, object]:
    try:
        return get_prompt_detail(prompt_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.put("/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, request: PromptUpdateRequest) -> dict[str, object]:
    try:
        save_prompt(prompt_id, request.content)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save prompt: {exc}") from exc

    return {"success": True, "message": "Saved successfully."}


@router.post("/prompts/{prompt_id}/reset")
async def reset_prompt_route(prompt_id: str) -> dict[str, object]:
    try:
        content = reset_prompt(prompt_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reset prompt: {exc}") from exc

    return {"success": True, "content": content}
