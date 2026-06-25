from __future__ import annotations

import json
import os
from dataclasses import asdict

from .project import ProjectState


def _locked_save_json(path: str, data, **dump_kwargs) -> None:
    try:
        handle = open(path, "r+", encoding="utf-8")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        handle = open(path, "w", encoding="utf-8")
    with handle:
        locked = False
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            handle.seek(0)
            handle.truncate()
            json.dump(data, handle, **dump_kwargs)
            handle.write("\n")
            handle.flush()
        finally:
            if locked:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class HarnessSession:
    def __init__(self) -> None:
        self.project: ProjectState | None = None
        self.project_path: str | None = None
        self._modified = False

    def set_project(self, project: ProjectState, path: str | None) -> None:
        self.project = project
        self.project_path = path
        self._modified = False

    def has_project(self) -> bool:
        return self.project is not None

    def mark_modified(self) -> None:
        self._modified = True

    def save_session(self) -> None:
        if not self.project or not self.project_path:
            return
        _locked_save_json(
            self.project_path,
            asdict(self.project),
            ensure_ascii=False,
            indent=2,
        )
        self._modified = False
