from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CLAW_USER_HOME = Path.home()
CLAW_AGENT_DIR = CLAW_USER_HOME / ".agents"
CLAW_SKILLS_DIR = CLAW_AGENT_DIR / "skills"
CLAW_SKILLS_CONFIG_FILE = CLAW_AGENT_DIR / "skills-config.json"

_FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)",
    re.DOTALL,
)
_VERSION_SUFFIX_PATTERN = re.compile(r"-(?:\d+\.)*\d+$")
RESERVED_SLASH_COMMANDS = frozenset(
    {
        "help",
        "clear",
        "compact",
        "mcp",
        "model",
        "reload",
        "remember",
        "tokens",
        "threads",
        "trace",
        "changelog",
        "docs",
        "feedback",
        "version",
        "quit",
        "q",
    }
)


def ensure_skill_storage() -> None:
    CLAW_AGENT_DIR.mkdir(parents=True, exist_ok=True)
    CLAW_SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def _load_skill_config() -> dict[str, list[str]]:
    ensure_skill_storage()
    if not CLAW_SKILLS_CONFIG_FILE.exists():
        return {"disabled_skills": []}

    try:
        raw = json.loads(CLAW_SKILLS_CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"disabled_skills": []}

    if not isinstance(raw, dict):
        return {"disabled_skills": []}

    disabled_raw = raw.get("disabled_skills", [])
    if not isinstance(disabled_raw, list):
        return {"disabled_skills": []}

    disabled_skills = sorted(
        {str(value).strip() for value in disabled_raw if str(value).strip()}
    )
    return {"disabled_skills": disabled_skills}


def _write_skill_config(config: dict[str, list[str]]) -> None:
    ensure_skill_storage()
    payload = {
        "disabled_skills": sorted(
            {str(value).strip() for value in config.get("disabled_skills", []) if str(value).strip()}
        )
    }
    CLAW_SKILLS_CONFIG_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_skill_content(skill_dir: Path) -> str:
    return (skill_dir / "SKILL.md").read_text(encoding="utf-8")


def _parse_frontmatter(content: str) -> dict[str, Any]:
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}

    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_skill_alias(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().lstrip("/")
    return normalized or None


def _strip_version_suffix(value: str) -> str:
    return _VERSION_SUFFIX_PATTERN.sub("", value)


def _build_skill_aliases(
    canonical_name: str,
    declared_name: str | None,
    slug: str | None,
) -> list[str]:
    candidates = [
        slug,
        _strip_version_suffix(canonical_name),
        declared_name,
        canonical_name,
    ]
    aliases: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = _normalize_skill_alias(candidate)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        aliases.append(normalized)
    return aliases


def _coerce_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _coerce_allowed_tools(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip(",") for item in value.split() if item.strip(",")]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _build_skill_record(skill_dir: Path, disabled_skills: set[str]) -> dict[str, Any]:
    skill_file = skill_dir / "SKILL.md"
    content = _read_skill_content(skill_dir)
    frontmatter = _parse_frontmatter(content)
    declared_name = _coerce_optional_str(frontmatter.get("name"))
    slug = _coerce_optional_str(frontmatter.get("slug"))
    updated_at = datetime.fromtimestamp(
        skill_file.stat().st_mtime,
        tz=UTC,
    )

    return {
        "name": skill_dir.name,
        "declared_name": declared_name,
        "description": _coerce_optional_str(frontmatter.get("description"))
        or "No description provided.",
        "enabled": skill_dir.name not in disabled_skills,
        "aliases": _build_skill_aliases(skill_dir.name, declared_name, slug),
        "path": str(skill_dir),
        "skill_file_path": str(skill_file),
        "updated_at": updated_at,
        "version": _coerce_optional_str(frontmatter.get("version")),
        "compatibility": _coerce_optional_str(frontmatter.get("compatibility")),
        "license": _coerce_optional_str(frontmatter.get("license")),
        "allowed_tools": _coerce_allowed_tools(frontmatter.get("allowed-tools")),
        "metadata": _coerce_metadata(frontmatter.get("metadata")),
        "content": content,
    }


def _iter_skill_directories() -> list[Path]:
    ensure_skill_storage()
    return sorted(
        (
            item
            for item in CLAW_SKILLS_DIR.iterdir()
            if item.is_dir() and (item / "SKILL.md").is_file()
        ),
        key=lambda item: item.name.lower(),
    )


def list_skills() -> list[dict[str, Any]]:
    config = _load_skill_config()
    disabled_skills = set(config["disabled_skills"])
    skills = [_build_skill_record(skill_dir, disabled_skills) for skill_dir in _iter_skill_directories()]
    return [
        {
            key: value
            for key, value in skill.items()
            if key != "content"
        }
        for skill in skills
    ]


def get_skill_detail(skill_name: str) -> dict[str, Any]:
    config = _load_skill_config()
    disabled_skills = set(config["disabled_skills"])
    skill_dir = CLAW_SKILLS_DIR / skill_name
    skill_file = skill_dir / "SKILL.md"
    if not skill_dir.is_dir() or not skill_file.is_file():
        msg = f"Unknown skill: {skill_name}"
        raise KeyError(msg)
    return _build_skill_record(skill_dir, disabled_skills)


def set_skill_enabled(skill_name: str, enabled: bool) -> dict[str, Any]:
    detail = get_skill_detail(skill_name)
    config = _load_skill_config()
    disabled_skills = set(config["disabled_skills"])
    if enabled:
        disabled_skills.discard(skill_name)
    else:
        disabled_skills.add(skill_name)
    _write_skill_config({"disabled_skills": sorted(disabled_skills)})
    return {
        key: value
        for key, value in get_skill_detail(skill_name).items()
        if key != "content"
    }


def get_enabled_skill_sources() -> list[str]:
    return [
        f"/skills/{skill['name']}"
        for skill in list_skills()
        if skill["enabled"]
    ]


def resolve_skill_reference(
    skill_reference: str,
    *,
    enabled_only: bool = True,
) -> dict[str, Any]:
    normalized_reference = _normalize_skill_alias(skill_reference)
    if normalized_reference is None:
        msg = "Skill reference cannot be empty."
        raise KeyError(msg)

    if normalized_reference in RESERVED_SLASH_COMMANDS:
        msg = f"'{skill_reference}' is reserved for slash commands."
        raise KeyError(msg)

    skills = list_skills()
    if enabled_only:
        skills = [skill for skill in skills if skill["enabled"]]

    exact_name_matches = [
        skill
        for skill in skills
        if _normalize_skill_alias(skill["name"]) == normalized_reference
    ]
    if exact_name_matches:
        return exact_name_matches[0]

    exact_declared_matches = [
        skill
        for skill in skills
        if _normalize_skill_alias(skill.get("declared_name")) == normalized_reference
    ]
    if len(exact_declared_matches) == 1:
        return exact_declared_matches[0]
    if len(exact_declared_matches) > 1:
        names = ", ".join(sorted(skill["name"] for skill in exact_declared_matches))
        msg = f"Ambiguous skill reference '{skill_reference}'. Matches: {names}"
        raise ValueError(msg)

    alias_matches = [
        skill
        for skill in skills
        if normalized_reference in {
            _normalize_skill_alias(alias)
            for alias in skill.get("aliases", [])
        }
    ]
    if len(alias_matches) == 1:
        return alias_matches[0]
    if len(alias_matches) > 1:
        names = ", ".join(sorted(skill["name"] for skill in alias_matches))
        msg = f"Ambiguous skill reference '{skill_reference}'. Matches: {names}"
        raise ValueError(msg)

    msg = f"Unknown skill: {skill_reference}"
    raise KeyError(msg)


def extract_slash_skill_command(
    content: str,
    *,
    enabled_only: bool = True,
) -> tuple[dict[str, Any] | None, str]:
    stripped_content = content.strip()
    if not stripped_content.startswith("/") or stripped_content.startswith("//"):
        return None, stripped_content

    match = re.match(r"^/(?P<skill>\S+)(?:\s+(?P<remainder>.*))?$", stripped_content, re.DOTALL)
    if match is None:
        return None, stripped_content
    skill_reference = match.group("skill")
    remainder = match.group("remainder") or ""

    try:
        skill = resolve_skill_reference(skill_reference, enabled_only=enabled_only)
    except KeyError:
        return None, stripped_content

    return skill, remainder.lstrip()


def get_skill_stats() -> dict[str, int]:
    skills = list_skills()
    enabled_count = sum(1 for skill in skills if skill["enabled"])
    return {
        "total": len(skills),
        "enabled": enabled_count,
        "disabled": len(skills) - enabled_count,
    }
