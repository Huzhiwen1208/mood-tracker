from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .crypto import read_encrypted_json

DEFAULT_PASSWORD = "test_123_for_mood"
DEFAULT_PASSWORD_ENV = "MOOD_PASSWORD"
ALLOWED_TAGS = ["😊", "😌", "😢", "😤", "🤔", "🥳"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProjectState:
    schema_version: int
    software: str
    repo_root: str
    backend_script: str
    data_file: str
    log_file: str
    password_env: str = DEFAULT_PASSWORD_ENV
    password: str | None = None
    fallback_password: str = DEFAULT_PASSWORD
    moods: list[dict[str, Any]] = field(default_factory=list)
    last_refresh: str | None = None
    last_action: str | None = None
    action_log_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def clone(self) -> "ProjectState":
        return ProjectState(**deepcopy(self.to_dict()))


def _canonical(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def _require_repo(repo_root: str | Path) -> tuple[Path, Path, Path, Path]:
    root = Path(repo_root).expanduser().resolve()
    backend = root / "sync-data.js"
    data_file = root / "data" / "moods.json"
    log_file = root / "data" / "actions.log"
    index_file = root / "index.html"
    missing = [str(p) for p in (backend, data_file.parent, index_file) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Repo root does not look like mood-tracker. Missing: " + ", ".join(missing)
        )
    return root, backend, data_file, log_file


def resolve_password(project: ProjectState, password: str | None = None) -> str:
    if password:
        return password
    env_name = project.password_env or DEFAULT_PASSWORD_ENV
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    if project.password:
        return project.password
    if project.fallback_password:
        return project.fallback_password
    raise RuntimeError(
        f"No password available. Set {env_name}, pass --password, or store a password in the project file."
    )


def load_action_log(project: ProjectState, lines: int | None = None) -> list[str]:
    log_path = Path(project.log_file)
    if not log_path.exists():
        return []
    content = log_path.read_text(encoding="utf-8").splitlines()
    if lines is None or lines >= len(content):
        return content
    return content[-lines:]


def refresh_project_state(
    project: ProjectState,
    password: str | None = None,
    action_name: str | None = None,
) -> ProjectState:
    resolved = resolve_password(project, password)
    data_path = Path(project.data_file)
    if data_path.exists() and data_path.read_text(encoding="utf-8").strip():
        moods = read_encrypted_json(data_path, resolved)
    else:
        moods = []
    logs = load_action_log(project)
    project.moods = moods
    project.last_refresh = utc_now()
    project.action_log_count = len(logs)
    if action_name:
        project.last_action = action_name
    elif logs:
        project.last_action = logs[-1]
    return project


def create_project(
    repo_root: str | Path,
    password: str | None = None,
    password_env: str = DEFAULT_PASSWORD_ENV,
    fallback_password: str = DEFAULT_PASSWORD,
) -> ProjectState:
    root, backend, data_file, log_file = _require_repo(repo_root)
    project = ProjectState(
        schema_version=1,
        software="mood-tracker",
        repo_root=str(root),
        backend_script=str(backend),
        data_file=str(data_file),
        log_file=str(log_file),
        password_env=password_env,
        password=password,
        fallback_password=fallback_password,
    )
    return refresh_project_state(project, password=password, action_name="project created")


def load_project(path: str | Path) -> ProjectState:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    project = ProjectState(**payload)
    _require_repo(project.repo_root)
    return project


def save_project(project: ProjectState, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(project.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def project_summary(project: ProjectState) -> dict[str, Any]:
    latest = project.moods[0] if project.moods else None
    return {
        "software": project.software,
        "repo_root": _canonical(project.repo_root),
        "backend_script": _canonical(project.backend_script),
        "data_file": _canonical(project.data_file),
        "log_file": _canonical(project.log_file),
        "mood_count": len(project.moods),
        "latest_mood_id": latest["id"] if latest else None,
        "latest_mood_time": latest["t"] if latest else None,
        "latest_mood_tag": latest["tag"] if latest else None,
        "password_env": project.password_env,
        "has_stored_password": bool(project.password),
        "fallback_password": project.fallback_password,
        "last_refresh": project.last_refresh,
        "last_action": project.last_action,
        "action_log_count": project.action_log_count,
    }
