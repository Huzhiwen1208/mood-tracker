from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .project import ProjectState


@dataclass
class GitSyncResult:
    branch: str
    remote: str
    commit_message: str | None
    commit_sha: str | None
    pushed: bool

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "branch": self.branch,
            "remote": self.remote,
            "commit_message": self.commit_message,
            "commit_sha": self.commit_sha,
            "pushed": self.pushed,
        }


def find_git() -> str:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git is required but `git` was not found in PATH.")
    return git


def _run_git(repo_root: str, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    git = find_git()
    proc = subprocess.run(
        [git, *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(detail)
    return proc


def _strip(value: str) -> str:
    return value.strip()


def _path_exists_or_tracked(repo_root: str, rel_path: str) -> bool:
    if (Path(repo_root) / rel_path).exists():
        return True
    proc = _run_git(repo_root, ["ls-files", "--error-unmatch", "--", rel_path], check=False)
    return proc.returncode == 0


def ensure_git_repo(repo_root: str) -> None:
    proc = _run_git(repo_root, ["rev-parse", "--show-toplevel"])
    top = _strip(proc.stdout)
    if Path(top).resolve() != Path(repo_root).resolve():
        raise RuntimeError(f"Project repo root is not the git toplevel: {repo_root}")


def sync_repo_data(
    project: ProjectState,
    *,
    action: str,
    remote: str = "origin",
    branch: str | None = None,
    pull_rebase: bool = True,
) -> GitSyncResult:
    ensure_git_repo(project.repo_root)
    if branch is None:
        branch = _strip(_run_git(project.repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout)
    repo_root = Path(project.repo_root).resolve()
    data_rel = Path(project.data_file).resolve().relative_to(repo_root).as_posix()
    log_rel = Path(project.log_file).resolve().relative_to(repo_root).as_posix()

    add_paths = [path for path in (data_rel, log_rel) if _path_exists_or_tracked(project.repo_root, path)]
    if not add_paths:
        return GitSyncResult(
            branch=branch,
            remote=remote,
            commit_message=None,
            commit_sha=None,
            pushed=False,
        )

    _run_git(project.repo_root, ["add", "--", *add_paths])
    staged = _run_git(project.repo_root, ["diff", "--cached", "--name-only", "--", *add_paths], check=False)
    staged_paths = [line for line in staged.stdout.splitlines() if line.strip()]
    if not staged_paths:
        return GitSyncResult(
            branch=branch,
            remote=remote,
            commit_message=None,
            commit_sha=None,
            pushed=False,
        )

    commit_message = f"sync: {action} mood data"
    _run_git(
        project.repo_root,
        [
            "-c",
            "user.name=cli-anything-mood-tracker",
            "-c",
            "user.email=cli-anything-mood-tracker@local",
            "commit",
            "-m",
            commit_message,
        ],
    )
    commit_sha = _strip(_run_git(project.repo_root, ["rev-parse", "HEAD"]).stdout)
    if pull_rebase:
        _run_git(project.repo_root, ["pull", "--rebase", remote, branch])
    _run_git(project.repo_root, ["push", remote, branch])
    return GitSyncResult(
        branch=branch,
        remote=remote,
        commit_message=commit_message,
        commit_sha=commit_sha,
        pushed=True,
    )
