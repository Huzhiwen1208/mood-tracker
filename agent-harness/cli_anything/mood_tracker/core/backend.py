from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from .project import ALLOWED_TAGS, ProjectState, refresh_project_state, resolve_password


@dataclass
class BackendResult:
    action: str
    stdout: str
    stderr: str
    returncode: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "action": self.action,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
        }


def find_node() -> str:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required but `node` was not found in PATH.")
    return node


def run_backend_action(
    project: ProjectState,
    action: str,
    *,
    password: str | None = None,
    text: str | None = None,
    tag: str | None = None,
) -> BackendResult:
    if action not in {"send", "undo"}:
        raise ValueError(f"Unsupported backend action: {action}")
    if action == "send":
        if not text or not text.strip():
            raise ValueError("Mood text is required for send")
        if tag not in ALLOWED_TAGS:
            raise ValueError(f"Tag must be one of: {', '.join(ALLOWED_TAGS)}")

    node = find_node()
    env = os.environ.copy()
    env[project.password_env] = resolve_password(project, password)
    if text is not None:
        env["MOOD_TEXT"] = text
    if tag is not None:
        env["MOOD_TAG"] = tag

    proc = subprocess.run(
        [node, project.backend_script, action],
        cwd=project.repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    result = BackendResult(
        action=action,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        returncode=proc.returncode,
    )
    if proc.returncode != 0:
        detail = result.stderr or result.stdout or f"backend exited with code {proc.returncode}"
        raise RuntimeError(detail)
    refresh_project_state(project, password=password, action_name=action)
    return result


def send_mood(
    project: ProjectState,
    text: str,
    tag: str,
    *,
    password: str | None = None,
) -> BackendResult:
    return run_backend_action(project, "send", password=password, text=text, tag=tag)


def undo_mood(project: ProjectState, *, password: str | None = None) -> BackendResult:
    return run_backend_action(project, "undo", password=password)
