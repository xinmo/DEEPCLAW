from __future__ import annotations

import sys
from pathlib import Path


def ensure_local_dependency_paths() -> None:
    project_root = Path(__file__).resolve().parents[4]
    for relative_path in ("libs/deepagents", "libs/cli"):
        candidate = project_root / relative_path
        if not candidate.exists():
            continue

        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
