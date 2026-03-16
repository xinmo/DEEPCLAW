from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.claw.skill_registry import (
    get_skill_detail,
    get_skill_stats,
    list_skills,
    set_skill_enabled,
)

router = APIRouter()


class SkillStatusUpdateRequest(BaseModel):
    enabled: bool


@router.get("/skills")
async def get_skills() -> dict[str, object]:
    return {
        "skills": list_skills(),
        "stats": get_skill_stats(),
    }


@router.get("/skills/{skill_name}")
async def get_skill_detail_route(skill_name: str) -> dict[str, object]:
    try:
        return get_skill_detail(skill_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.put("/skills/{skill_name}/status")
async def update_skill_status(
    skill_name: str,
    request: SkillStatusUpdateRequest,
) -> dict[str, object]:
    try:
        skill = set_skill_enabled(skill_name, request.enabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update skill state: {exc}") from exc

    return {
        "success": True,
        "skill": skill,
    }
