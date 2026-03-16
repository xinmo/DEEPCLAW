from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from deepagents.backends.local_shell import LocalShellBackend
from deepagents_cli.local_context import LocalContextMiddleware


_LOCAL_CONTEXT_EXCLUDES = {
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".coverage",
    ".eggs",
    "dist",
    "build",
}


def _run_command(command: list[str], *, cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None

    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or None


def _detect_project_language(cwd: Path) -> str | None:
    if (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
        return "python"
    if (cwd / "package.json").exists():
        return "javascript/typescript"
    if (cwd / "Cargo.toml").exists():
        return "rust"
    if (cwd / "go.mod").exists():
        return "go"
    if (cwd / "pom.xml").exists() or (cwd / "build.gradle").exists():
        return "java"
    return None


def _detect_package_manager(cwd: Path) -> str | None:
    packages: list[str] = []
    pyproject = cwd / "pyproject.toml"
    pyproject_text = pyproject.read_text(encoding="utf-8") if pyproject.exists() else ""

    if (cwd / "uv.lock").exists():
        packages.append("Python: uv")
    elif (cwd / "poetry.lock").exists():
        packages.append("Python: poetry")
    elif (cwd / "Pipfile.lock").exists() or (cwd / "Pipfile").exists():
        packages.append("Python: pipenv")
    elif pyproject.exists():
        if "[tool.uv]" in pyproject_text:
            packages.append("Python: uv")
        elif "[tool.poetry]" in pyproject_text:
            packages.append("Python: poetry")
        else:
            packages.append("Python: pip")
    elif (cwd / "requirements.txt").exists():
        packages.append("Python: pip")

    if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
        packages.append("Node: bun")
    elif (cwd / "pnpm-lock.yaml").exists():
        packages.append("Node: pnpm")
    elif (cwd / "yarn.lock").exists():
        packages.append("Node: yarn")
    elif (cwd / "package-lock.json").exists() or (cwd / "package.json").exists():
        packages.append("Node: npm")

    if not packages:
        return None
    return ", ".join(packages)


def _detect_runtimes() -> str | None:
    runtimes: list[str] = []

    python_bin = shutil.which("python")
    if python_bin:
        version = _run_command([python_bin, "--version"])
        if version:
            runtimes.append(version.replace("Python ", "Python "))

    node_bin = shutil.which("node")
    if node_bin:
        version = _run_command([node_bin, "--version"])
        if version:
            runtimes.append(f"Node {version.lstrip('v')}")

    if not runtimes:
        return None
    return ", ".join(runtimes)


def _detect_test_command(cwd: Path) -> str | None:
    makefile = cwd / "Makefile"
    if makefile.exists():
        try:
            makefile_text = makefile.read_text(encoding="utf-8")
        except OSError:
            makefile_text = ""
        if "test:" in makefile_text or "tests:" in makefile_text:
            return "make test"

    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        try:
            pyproject_text = pyproject.read_text(encoding="utf-8")
        except OSError:
            pyproject_text = ""
        if (
            "[tool.pytest" in pyproject_text
            or (cwd / "pytest.ini").exists()
            or (cwd / "tests").exists()
            or (cwd / "test").exists()
        ):
            return "pytest"

    package_json = cwd / "package.json"
    if package_json.exists():
        try:
            package_data = package_json.read_text(encoding="utf-8")
        except OSError:
            package_data = ""
        if '"test"' in package_data:
            return "npm test"

    return None


def _list_files_section(cwd: Path) -> list[str]:
    try:
        items = sorted(
            (
                item.name
                for item in cwd.iterdir()
                if item.name not in _LOCAL_CONTEXT_EXCLUDES
            ),
            key=str.lower,
        )
    except OSError:
        return []

    if not items:
        return []

    shown_items = items[:20]
    lines = [f"**Files** ({len(shown_items)} shown):"]
    for name in shown_items:
        suffix = "/" if (cwd / name).is_dir() else ""
        lines.append(f"- {name}{suffix}")
    if len(items) > len(shown_items):
        lines.append(f"... ({len(items) - len(shown_items)} more files)")
    lines.append("")
    return lines


def _makefile_section(cwd: Path, git_root: Path | None) -> list[str]:
    candidates = [cwd / "Makefile"]
    if git_root is not None and git_root != cwd:
        candidates.append(git_root / "Makefile")

    for candidate in candidates:
        if not candidate.exists():
            continue

        try:
            lines = candidate.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        header = f"**Makefile** (`{candidate}`, first 20 lines):"
        body = ["```makefile", *lines[:20]]
        if len(lines) > 20:
            body.append("... (truncated)")
        body.extend(["```", ""])
        return [header, *body]

    return []


def _build_windows_local_context(cwd: Path) -> str:
    git_root_output = _run_command(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    git_root = Path(git_root_output) if git_root_output else None
    in_git = git_root is not None

    lines = [
        "## Local Context",
        "",
        f"**Current Directory**: `{cwd}`",
        "",
    ]

    project_language = _detect_project_language(cwd)
    monorepo = any(
        (
            (cwd / "lerna.json").exists(),
            (cwd / "pnpm-workspace.yaml").exists(),
            (cwd / "packages").is_dir(),
            (cwd / "workspaces").is_dir(),
            (cwd / "libs").is_dir() and (cwd / "apps").is_dir(),
        )
    )
    envs = []
    if (cwd / ".venv").is_dir() or (cwd / "venv").is_dir():
        envs.append(".venv")
    if (cwd / "node_modules").is_dir():
        envs.append("node_modules")

    if project_language or monorepo or envs or (git_root is not None and git_root != cwd):
        lines.append("**Project**:")
        if project_language:
            lines.append(f"- Language: {project_language}")
        if git_root is not None and git_root != cwd:
            lines.append(f"- Project root: `{git_root}`")
        if monorepo:
            lines.append("- Monorepo: yes")
        if envs:
            lines.append(f"- Environments: {', '.join(envs)}")
        lines.append("")

    package_manager = _detect_package_manager(cwd)
    if package_manager:
        lines.extend([f"**Package Manager**: {package_manager}", ""])

    runtimes = _detect_runtimes()
    if runtimes:
        lines.extend([f"**Runtimes**: {runtimes}", ""])

    if in_git:
        branch = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
        git_line = f"**Git**: Current branch `{branch or 'unknown'}`"
        available_branches = _run_command(["git", "branch", "--format=%(refname:short)"], cwd=cwd)
        if available_branches:
            mains = [name for name in available_branches.splitlines() if name in {"main", "master"}]
            if mains:
                git_line += ", main branch available: " + ", ".join(f"`{name}`" for name in mains)
        status_lines = _run_command(["git", "status", "--porcelain"], cwd=cwd)
        if status_lines:
            change_count = len(status_lines.splitlines())
            suffix = "change" if change_count == 1 else "changes"
            git_line += f", {change_count} uncommitted {suffix}"
        lines.extend([git_line, ""])

    test_command = _detect_test_command(cwd)
    if test_command:
        lines.extend([f"**Run Tests**: `{test_command}`", ""])

    lines.extend(_list_files_section(cwd))
    lines.extend(_makefile_section(cwd, git_root))

    return "\n".join(lines).strip()


class ClawLocalContextMiddleware(LocalContextMiddleware):
    """Local-context middleware with a Windows-safe fallback for local shell backends."""

    def _run_detect_script(self) -> str | None:
        if os.name == "nt" and isinstance(self.backend, LocalShellBackend):
            return _build_windows_local_context(self.backend.cwd)
        return super()._run_detect_script()
