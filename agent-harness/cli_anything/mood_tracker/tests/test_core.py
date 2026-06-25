from __future__ import annotations

import os
from pathlib import Path

from cli_anything.mood_tracker.core.git_sync import sync_repo_data
from cli_anything.mood_tracker.core.crypto import decode_payload, encode_payload
from cli_anything.mood_tracker.core.project import (
    DEFAULT_PASSWORD,
    ProjectState,
    create_project,
    load_action_log,
    refresh_project_state,
    resolve_password,
)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    data_dir = repo / "data"
    data_dir.mkdir(parents=True)
    (repo / "sync-data.js").write_text("console.log('stub')\n", encoding="utf-8")
    (repo / "index.html").write_text("<!doctype html><title>mood</title>\n", encoding="utf-8")
    (data_dir / "moods.json").write_text("", encoding="utf-8")
    return repo


def test_encode_decode_round_trip_preserves_emoji() -> None:
    payload = [{"id": "1", "text": "hello", "tag": "😊", "t": "2026-01-01T00:00:00.000Z"}]
    encoded = encode_payload(payload, DEFAULT_PASSWORD)
    decoded = decode_payload(encoded, DEFAULT_PASSWORD)
    assert decoded == payload
    assert encoded != str(payload)


def test_create_project_reads_existing_mood_store(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    payload = [{"id": "m1", "text": "first", "tag": "😌", "t": "2026-01-01T00:00:00.000Z"}]
    (repo / "data" / "moods.json").write_text(encode_payload(payload, DEFAULT_PASSWORD), encoding="utf-8")

    project = create_project(repo)

    assert project.repo_root == str(repo.resolve())
    assert project.moods == payload
    assert project.action_log_count == 0


def test_refresh_project_state_handles_empty_store(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    project = create_project(repo)
    refresh_project_state(project)
    assert project.moods == []
    assert project.last_refresh is not None


def test_resolve_password_precedence(monkeypatch) -> None:
    project = ProjectState(
        schema_version=1,
        software="mood-tracker",
        repo_root="/tmp/repo",
        backend_script="/tmp/repo/sync-data.js",
        data_file="/tmp/repo/data/moods.json",
        log_file="/tmp/repo/data/actions.log",
        password_env="MOOD_PASSWORD",
        password="stored-secret",
        fallback_password="fallback-secret",
    )

    assert resolve_password(project, "explicit-secret") == "explicit-secret"
    monkeypatch.setenv("MOOD_PASSWORD", "env-secret")
    assert resolve_password(project) == "env-secret"
    monkeypatch.delenv("MOOD_PASSWORD")
    assert resolve_password(project) == "stored-secret"
    project.password = None
    assert resolve_password(project) == "fallback-secret"


def test_load_action_log_returns_tail(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    log_path = repo / "data" / "actions.log"
    log_path.write_text("a\nb\nc\n", encoding="utf-8")
    project = create_project(repo)
    assert load_action_log(project, lines=2) == ["b", "c"]


def test_sync_repo_data_returns_no_commit_when_nothing_changed(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    bare = tmp_path / "remote.git"
    import subprocess

    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo, check=True, capture_output=True, text=True)
    project = create_project(repo)

    result = sync_repo_data(project, action="send")

    assert result.pushed is False
    assert result.commit_sha is None
