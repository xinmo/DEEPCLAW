import importlib.util
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SKILL_REGISTRY_PATH = BACKEND_ROOT / "src" / "services" / "claw" / "skill_registry.py"
skill_registry_spec = importlib.util.spec_from_file_location(
    "test_claw_skill_registry_module",
    SKILL_REGISTRY_PATH,
)
assert skill_registry_spec is not None and skill_registry_spec.loader is not None
skill_registry = importlib.util.module_from_spec(skill_registry_spec)
skill_registry_spec.loader.exec_module(skill_registry)


def _write_skill(
    skill_root: Path,
    name: str,
    description: str,
    version: str,
    *,
    declared_name: str | None = None,
    slug: str | None = None,
) -> None:
    skill_dir = skill_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = [
        "---",
        f"name: {declared_name or name}",
        f"description: {description}",
        f"version: {version}",
    ]
    if slug:
        frontmatter.append(f"slug: {slug}")
    frontmatter.extend(
        [
            "allowed-tools: read_file edit_file",
            "---",
            "",
            f"# {name}",
            "",
            "Skill body.",
            "",
        ]
    )
    (skill_dir / "SKILL.md").write_text(
        "\n".join(frontmatter),
        encoding="utf-8",
    )


def test_skill_registry_lists_and_toggles_skills(monkeypatch):
    tmp_root = BACKEND_ROOT / "tests" / ".tmp" / f"claw-skills-{uuid.uuid4().hex}"
    agent_dir = tmp_root / ".agents"
    skills_dir = agent_dir / "skills"
    config_file = agent_dir / "skills-config.json"
    skills_dir.mkdir(parents=True, exist_ok=True)

    _write_skill(skills_dir, "alpha-skill", "Alpha description", "1.0.0")
    _write_skill(skills_dir, "beta-skill", "Beta description", "2.0.0")

    monkeypatch.setattr(skill_registry, "CLAW_AGENT_DIR", agent_dir)
    monkeypatch.setattr(skill_registry, "CLAW_SKILLS_DIR", skills_dir)
    monkeypatch.setattr(skill_registry, "CLAW_SKILLS_CONFIG_FILE", config_file)

    skills = skill_registry.list_skills()
    assert [skill["name"] for skill in skills] == ["alpha-skill", "beta-skill"]
    assert all(skill["enabled"] for skill in skills)
    assert skills[0]["description"] == "Alpha description"
    assert skills[0]["version"] == "1.0.0"
    assert skills[0]["aliases"] == ["alpha-skill"]

    detail = skill_registry.get_skill_detail("alpha-skill")
    assert detail["content"].startswith("---")
    assert detail["allowed_tools"] == ["read_file", "edit_file"]

    skill_registry.set_skill_enabled("beta-skill", False)

    updated_skills = skill_registry.list_skills()
    beta_skill = next(skill for skill in updated_skills if skill["name"] == "beta-skill")
    assert beta_skill["enabled"] is False
    assert skill_registry.get_enabled_skill_sources() == ["/skills/alpha-skill"]


def test_skill_registry_resolves_aliases_and_slash_commands(monkeypatch):
    tmp_root = BACKEND_ROOT / "tests" / ".tmp" / f"claw-skill-alias-{uuid.uuid4().hex}"
    agent_dir = tmp_root / ".agents"
    skills_dir = agent_dir / "skills"
    config_file = agent_dir / "skills-config.json"
    skills_dir.mkdir(parents=True, exist_ok=True)

    _write_skill(
        skills_dir,
        "brainstorming-0.1.0",
        "Brainstorm before implementation.",
        "0.1.0",
        declared_name="Brainstorming",
        slug="brainstorming",
    )
    _write_skill(
        skills_dir,
        "skill-creator",
        "Create skills.",
        "1.0.0",
        declared_name="Skill Creator",
    )
    _write_skill(
        skills_dir,
        "skill-creator-0.1.0",
        "Legacy skill creator.",
        "0.1.0",
        declared_name="Skill Creator Legacy",
    )

    monkeypatch.setattr(skill_registry, "CLAW_AGENT_DIR", agent_dir)
    monkeypatch.setattr(skill_registry, "CLAW_SKILLS_DIR", skills_dir)
    monkeypatch.setattr(skill_registry, "CLAW_SKILLS_CONFIG_FILE", config_file)

    resolved = skill_registry.resolve_skill_reference("brainstorming")
    assert resolved["name"] == "brainstorming-0.1.0"
    assert resolved["aliases"] == ["brainstorming", "brainstorming-0.1.0"]

    slash_skill, remainder = skill_registry.extract_slash_skill_command(
        "/brainstorming build a login page"
    )
    assert slash_skill is not None
    assert slash_skill["name"] == "brainstorming-0.1.0"
    assert remainder == "build a login page"

    canonical = skill_registry.resolve_skill_reference("skill-creator")
    assert canonical["name"] == "skill-creator"

    try:
        skill_registry.resolve_skill_reference("help")
    except KeyError as exc:
        assert "reserved for slash commands" in exc.args[0]
    else:
        raise AssertionError("Expected reserved slash command lookup to fail")
