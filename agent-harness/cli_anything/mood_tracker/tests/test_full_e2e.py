from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from cli_anything.mood_tracker.core.crypto import read_encrypted_json


def _resolve_cli(name: str) -> list[str]:
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.mood_tracker.mood_tracker_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-mood-tracker")
    SOURCE_REPO = Path(__file__).resolve().parents[4]

    def _run(self, args: list[str], check: bool = True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def _make_backend_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "mood-tracker-repo"
        data_dir = repo / "data"
        data_dir.mkdir(parents=True)
        for name in ("sync-data.js", "index.html", "package.json"):
            shutil.copy2(self.SOURCE_REPO / name, repo / name)
        (data_dir / "moods.json").write_text("", encoding="utf-8")
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
        print(f"\n  Repo: {repo}")
        print(f"  Data: {data_dir / 'moods.json'}")
        return repo

    def _make_remote_for_repo(self, repo: Path, tmp_path: Path) -> Path:
        bare = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True, text=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo, check=True, capture_output=True, text=True)
        return bare

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "mood-tracker" in result.stdout

    def test_project_new_and_empty_list_json(self, tmp_path: Path):
        repo = self._make_backend_repo(tmp_path)
        project_path = tmp_path / "project.json"

        new_result = self._run(
            [
                "--json",
                "project",
                "new",
                "--repo-root",
                str(repo),
                "-o",
                str(project_path),
            ]
        )
        payload = json.loads(new_result.stdout)
        assert payload["ok"] is True
        assert project_path.exists()

        list_result = self._run(["--json", "--project", str(project_path), "mood", "list"])
        list_payload = json.loads(list_result.stdout)
        assert list_payload["count"] == 0

    def test_send_and_decrypt_workflow(self, tmp_path: Path):
        repo = self._make_backend_repo(tmp_path)
        project_path = tmp_path / "project.json"
        self._run(["project", "new", "--repo-root", str(repo), "-o", str(project_path)])

        send_result = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "mood",
                "send",
                "Today feels steady.",
                "--tag",
                "😌",
            ]
        )
        payload = json.loads(send_result.stdout)
        assert payload["ok"] is True
        assert payload["latest_mood"]["text"] == "Today feels steady."
        assert payload["latest_mood"]["tag"] == "😌"

        moods = read_encrypted_json(repo / "data" / "moods.json", "test_123_for_mood")
        assert len(moods) == 1
        assert moods[0]["text"] == "Today feels steady."
        assert moods[0]["tag"] == "😌"

        decrypt_result = self._run(["--json", "--project", str(project_path), "data", "decrypt"])
        decrypt_payload = json.loads(decrypt_result.stdout)
        assert decrypt_payload["count"] == 1

    def test_send_then_undo_workflow(self, tmp_path: Path):
        repo = self._make_backend_repo(tmp_path)
        project_path = tmp_path / "project.json"
        self._run(["project", "new", "--repo-root", str(repo), "-o", str(project_path)])
        self._run(["--project", str(project_path), "mood", "send", "One more entry", "--tag", "😊"])

        undo_result = self._run(["--json", "--project", str(project_path), "mood", "undo"])
        payload = json.loads(undo_result.stdout)
        assert payload["ok"] is True
        assert payload["mood_count"] == 0

        moods = read_encrypted_json(repo / "data" / "moods.json", "test_123_for_mood")
        assert moods == []

        log_result = self._run(["--json", "--project", str(project_path), "data", "log", "--lines", "5"])
        log_payload = json.loads(log_result.stdout)
        assert any("undo: removed latest" in line for line in log_payload["lines"])

    def test_send_with_push_updates_remote_repo(self, tmp_path: Path):
        repo = self._make_backend_repo(tmp_path)
        remote = self._make_remote_for_repo(repo, tmp_path)
        project_path = tmp_path / "project.json"
        self._run(["project", "new", "--repo-root", str(repo), "-o", str(project_path)])

        send_result = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "mood",
                "send",
                "Push me online.",
                "--tag",
                "🥳",
                "--push",
                "--remote",
                "origin",
                "--branch",
                "main",
            ]
        )
        payload = json.loads(send_result.stdout)
        assert payload["ok"] is True
        assert payload["git_sync"]["pushed"] is True
        assert payload["git_sync"]["branch"] == "main"

        clone_path = tmp_path / "remote-clone"
        subprocess.run(["git", "clone", "-b", "main", str(remote), str(clone_path)], check=True, capture_output=True, text=True)
        moods = read_encrypted_json(clone_path / "data" / "moods.json", "test_123_for_mood")
        assert moods[0]["text"] == "Push me online."
