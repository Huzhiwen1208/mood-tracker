from __future__ import annotations

import json
import shlex
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click

from . import __version__
from .core.backend import send_mood, undo_mood
from .core.git_sync import sync_repo_data
from .core.crypto import read_encrypted_json
from .core.project import (
    ALLOWED_TAGS,
    DEFAULT_PASSWORD,
    DEFAULT_PASSWORD_ENV,
    ProjectState,
    create_project,
    load_action_log,
    load_project,
    project_summary,
    refresh_project_state,
    resolve_password,
    save_project,
)
from .core.session import HarnessSession
from .utils.repl_skin import ReplSkin

_SESSION = HarnessSession()
_REPL_MODE = False


def get_session() -> HarnessSession:
    return _SESSION


def _ctx() -> dict[str, Any]:
    return click.get_current_context().obj


def _ensure_project() -> ProjectState:
    session = get_session()
    if not session.project:
        raise click.ClickException("Load a harness project first with --project or create one with project new.")
    return session.project


def _emit_json(payload: dict[str, Any]) -> None:
    click.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _emit(payload: dict[str, Any], human_lines: list[str]) -> None:
    if _ctx()["use_json"]:
        _emit_json(payload)
        return
    for line in human_lines:
        click.echo(line)


def _error_payload(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


def _refresh_loaded_project(mark_modified: bool = False) -> ProjectState:
    session = get_session()
    project = _ensure_project()
    refresh_project_state(project, password=_ctx().get("password"))
    if mark_modified:
        session.mark_modified()
    return project


def _project_name() -> str:
    session = get_session()
    if session.project_path:
        return Path(session.project_path).name
    return "no-project"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _undo_expired(mood: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    return now - _parse_time(mood["t"]) > timedelta(hours=24)


def _format_mood_line(mood: dict[str, Any], index: int) -> str:
    suffix = " (undoable)" if index == 0 and not _undo_expired(mood) else ""
    return f"{index + 1}. {mood['tag']} {mood['t']} {mood['id']} {mood['text']}{suffix}"


def _show_table(moods: list[dict[str, Any]]) -> None:
    skin = ReplSkin("mood_tracker", version=__version__)
    rows = []
    for index, mood in enumerate(moods):
        rows.append(
            [
                str(index + 1),
                mood["tag"],
                mood["t"],
                mood["id"],
                "yes" if index == 0 and not _undo_expired(mood) else "no",
                mood["text"],
            ]
        )
    skin.table(["#", "tag", "time", "id", "undo", "text"], rows)


def _maybe_push_repo(action: str, *, remote: str, branch: str | None, pull_rebase: bool) -> dict[str, Any] | None:
    project_state = _ensure_project()
    result = sync_repo_data(
        project_state,
        action=action,
        remote=remote,
        branch=branch,
        pull_rebase=pull_rebase,
    )
    return result.to_dict()


def _interactive_repl() -> None:
    global _REPL_MODE
    _REPL_MODE = True
    session = get_session()
    skin = ReplSkin("mood_tracker", version=__version__)
    pt_session = skin.create_prompt_session()
    skin.print_banner()
    skin.help(
        {
            "project info": "Show loaded project summary",
            "mood list": "List moods from the encrypted store",
            "mood send TEXT --tag TAG --push": "Send a mood and optionally git-push data files",
            "mood undo --push": "Undo the latest mood and optionally git-push data files",
            "data log --lines N": "Show recent action-log lines",
            "quit": "Exit the REPL",
        }
    )
    while True:
        try:
            line = skin.get_input(
                pt_session,
                project_name=_project_name(),
                modified=session._modified,
            )
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in {"quit", "exit"}:
            break
        if line == "help":
            skin.help(
                {
                    "project info": "Show loaded project summary",
                    "mood list": "List moods from the encrypted store",
                    "mood send TEXT --tag TAG --push": "Send a mood and optionally git-push data files",
                    "mood undo --push": "Undo the latest mood and optionally git-push data files",
                    "data log --lines N": "Show recent action-log lines",
                    "quit": "Exit the REPL",
                }
            )
            continue
        try:
            cli.main(args=shlex.split(line), prog_name="cli-anything-mood-tracker", standalone_mode=False)
        except SystemExit:
            continue
        except click.ClickException as exc:
            skin.error(exc.format_message())
        except Exception as exc:  # pragma: no cover - REPL safety net
            skin.error(str(exc))
    skin.print_goodbye()
    _REPL_MODE = False


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output structured JSON")
@click.option("--project", "project_path", type=click.Path(dir_okay=False), default=None, help="Path to a harness project JSON file")
@click.option("--dry-run", "dry_run", is_flag=True, default=False, help="Run without saving refreshed project state to disk")
@click.option("--password", "password", default=None, help="Override the encryption password for this invocation")
@click.pass_context
def cli(ctx: click.Context, use_json: bool, project_path: str | None, dry_run: bool, password: str | None) -> None:
    """CLI-Anything harness for mood-tracker."""
    ctx.ensure_object(dict)
    ctx.obj.update(
        {
            "use_json": use_json,
            "project_path": project_path,
            "dry_run": dry_run,
            "password": password,
        }
    )
    if project_path:
        project = load_project(project_path)
        refresh_project_state(project, password=password)
        get_session().set_project(project, project_path)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.result_callback()
def auto_save_on_exit(result, use_json: bool, project_path: str | None, dry_run: bool, password: str | None, **kwargs) -> None:
    if _REPL_MODE or dry_run:
        return
    session = get_session()
    if session.has_project() and session._modified and session.project_path:
        session.save_session()


@cli.group()
def project() -> None:
    """Create and inspect harness project files."""


@project.command("new")
@click.option("--repo-root", required=True, type=click.Path(file_okay=False), help="Path to the mood-tracker repository root")
@click.option("-o", "--output", required=True, type=click.Path(dir_okay=False), help="Path to write the harness project file")
@click.option("--password-env", default=DEFAULT_PASSWORD_ENV, show_default=True, help="Environment variable name used for the encryption password")
@click.option("--stored-password", default=None, help="Store a password in the harness project file")
@click.option("--fallback-password", default=DEFAULT_PASSWORD, show_default=True, help="Fallback password when env and stored values are absent")
def project_new(repo_root: str, output: str, password_env: str, stored_password: str | None, fallback_password: str) -> None:
    project_state = create_project(
        repo_root=repo_root,
        password=stored_password,
        password_env=password_env,
        fallback_password=fallback_password,
    )
    save_project(project_state, output)
    payload = {
        "ok": True,
        "project_path": str(Path(output).resolve()),
        "project": project_summary(project_state),
    }
    _emit(
        payload,
        [
            f"Created harness project: {Path(output).resolve()}",
            f"Repo root: {project_state.repo_root}",
            f"Moods loaded: {len(project_state.moods)}",
        ],
    )


@project.command("info")
def project_info() -> None:
    project_state = _refresh_loaded_project()
    payload = {"ok": True, "project": project_summary(project_state)}
    lines = [f"{key}: {value}" for key, value in payload["project"].items()]
    _emit(payload, lines)


@project.command("refresh")
def project_refresh() -> None:
    project_state = _refresh_loaded_project(mark_modified=True)
    payload = {"ok": True, "project": project_summary(project_state)}
    _emit(
        payload,
        [
            f"Refreshed project cache from {project_state.data_file}",
            f"Moods loaded: {len(project_state.moods)}",
            f"Action log lines: {project_state.action_log_count}",
        ],
    )


@project.command("set-password")
@click.option("--stored-password", default=None, help="New password to store in the project file")
@click.option("--clear", "clear_password", is_flag=True, help="Clear the stored password")
def project_set_password(stored_password: str | None, clear_password: bool) -> None:
    if clear_password and stored_password is not None:
        raise click.ClickException("Use either --stored-password or --clear, not both.")
    project_state = _ensure_project()
    project_state.password = None if clear_password else stored_password
    refresh_project_state(project_state, password=_ctx().get("password") or stored_password)
    get_session().mark_modified()
    payload = {
        "ok": True,
        "has_stored_password": bool(project_state.password),
        "password_env": project_state.password_env,
    }
    _emit(
        payload,
        [
            "Stored password updated.",
            f"Has stored password: {bool(project_state.password)}",
        ],
    )


@cli.group()
def mood() -> None:
    """Inspect and mutate mood entries."""


@mood.command("list")
@click.option("--limit", default=20, show_default=True, type=int, help="Maximum number of moods to print")
def mood_list(limit: int) -> None:
    project_state = _refresh_loaded_project()
    moods = project_state.moods[:limit]
    payload = {"ok": True, "count": len(moods), "moods": moods}
    if _ctx()["use_json"]:
        _emit_json(payload)
        return
    if not moods:
        click.echo("No moods found.")
        return
    _show_table(moods)


@mood.command("show")
@click.argument("mood_id")
def mood_show(mood_id: str) -> None:
    project_state = _refresh_loaded_project()
    mood_row = next((item for item in project_state.moods if item["id"] == mood_id), None)
    if not mood_row:
        raise click.ClickException(f"Mood not found: {mood_id}")
    payload = {"ok": True, "mood": mood_row}
    _emit(
        payload,
        [
            f"id: {mood_row['id']}",
            f"time: {mood_row['t']}",
            f"tag: {mood_row['tag']}",
            f"text: {mood_row['text']}",
        ],
    )


@mood.command("send")
@click.argument("text")
@click.option("--tag", default="😊", show_default=True, type=click.Choice(ALLOWED_TAGS), help="Mood tag")
@click.option("--push", "push_remote", is_flag=True, help="Commit and push changed mood data to the git remote")
@click.option("--remote", default="origin", show_default=True, help="Git remote to push to")
@click.option("--branch", default=None, help="Git branch to push; defaults to the current branch")
@click.option("--no-pull-rebase", "pull_rebase", flag_value=False, default=True, help="Skip git pull --rebase before push")
def mood_send(text: str, tag: str, push_remote: bool, remote: str, branch: str | None, pull_rebase: bool) -> None:
    project_state = _ensure_project()
    result = send_mood(project_state, text=text, tag=tag, password=_ctx().get("password"))
    get_session().mark_modified()
    git_sync = None
    if push_remote:
        git_sync = _maybe_push_repo("send", remote=remote, branch=branch, pull_rebase=pull_rebase)
    payload = {
        "ok": True,
        "backend": result.to_dict(),
        "git_sync": git_sync,
        "mood_count": len(project_state.moods),
        "latest_mood": project_state.moods[0] if project_state.moods else None,
    }
    lines = [
        f"Sent mood via backend: {result.stdout or 'ok'}",
        f"Latest mood: {_format_mood_line(project_state.moods[0], 0) if project_state.moods else 'none'}",
    ]
    if git_sync and git_sync["pushed"]:
        lines.append(f"Pushed to {git_sync['remote']}/{git_sync['branch']} at {git_sync['commit_sha']}")
    _emit(payload, lines)


@mood.command("undo")
@click.option("--push", "push_remote", is_flag=True, help="Commit and push changed mood data to the git remote")
@click.option("--remote", default="origin", show_default=True, help="Git remote to push to")
@click.option("--branch", default=None, help="Git branch to push; defaults to the current branch")
@click.option("--no-pull-rebase", "pull_rebase", flag_value=False, default=True, help="Skip git pull --rebase before push")
def mood_undo(push_remote: bool, remote: str, branch: str | None, pull_rebase: bool) -> None:
    project_state = _ensure_project()
    result = undo_mood(project_state, password=_ctx().get("password"))
    get_session().mark_modified()
    git_sync = None
    if push_remote:
        git_sync = _maybe_push_repo("undo", remote=remote, branch=branch, pull_rebase=pull_rebase)
    payload = {
        "ok": True,
        "backend": result.to_dict(),
        "git_sync": git_sync,
        "mood_count": len(project_state.moods),
        "latest_mood": project_state.moods[0] if project_state.moods else None,
    }
    lines = [
        f"Undo completed via backend: {result.stdout or 'ok'}",
        f"Moods remaining: {len(project_state.moods)}",
    ]
    if git_sync and git_sync["pushed"]:
        lines.append(f"Pushed to {git_sync['remote']}/{git_sync['branch']} at {git_sync['commit_sha']}")
    _emit(payload, lines)


@mood.command("stats")
def mood_stats() -> None:
    project_state = _refresh_loaded_project()
    by_tag: dict[str, int] = {}
    for row in project_state.moods:
        by_tag[row["tag"]] = by_tag.get(row["tag"], 0) + 1
    latest_undoable = bool(project_state.moods) and not _undo_expired(project_state.moods[0])
    payload = {
        "ok": True,
        "count": len(project_state.moods),
        "by_tag": by_tag,
        "latest_undoable": latest_undoable,
    }
    lines = [f"count: {payload['count']}", f"latest_undoable: {latest_undoable}"]
    lines.extend(f"{tag}: {count}" for tag, count in sorted(by_tag.items()))
    _emit(payload, lines)


@cli.group()
def data() -> None:
    """Inspect encrypted storage and logs."""


@data.command("inspect")
def data_inspect() -> None:
    project_state = _refresh_loaded_project()
    raw = Path(project_state.data_file).read_text(encoding="utf-8").strip()
    payload = {
        "ok": True,
        "data_file": project_state.data_file,
        "ciphertext_bytes": len(raw.encode("utf-8")),
        "mood_count": len(project_state.moods),
        "latest_mood": project_state.moods[0] if project_state.moods else None,
    }
    _emit(
        payload,
        [
            f"Data file: {project_state.data_file}",
            f"Ciphertext bytes: {payload['ciphertext_bytes']}",
            f"Mood count: {len(project_state.moods)}",
        ],
    )


@data.command("decrypt")
def data_decrypt() -> None:
    project_state = _ensure_project()
    resolved = resolve_password(project_state, _ctx().get("password"))
    moods = read_encrypted_json(project_state.data_file, resolved)
    payload = {"ok": True, "count": len(moods), "moods": moods}
    if _ctx()["use_json"]:
        _emit_json(payload)
        return
    if not moods:
        click.echo("No moods found.")
        return
    for index, mood_row in enumerate(moods):
        click.echo(_format_mood_line(mood_row, index))


@data.command("log")
@click.option("--lines", default=10, show_default=True, type=int, help="How many log lines to show")
def data_log(lines: int) -> None:
    project_state = _refresh_loaded_project()
    rows = load_action_log(project_state, lines=lines)
    payload = {"ok": True, "count": len(rows), "lines": rows}
    if _ctx()["use_json"]:
        _emit_json(payload)
        return
    if not rows:
        click.echo("No log lines found.")
        return
    for row in rows:
        click.echo(row)


@cli.command()
def repl() -> None:
    """Start the interactive REPL."""
    _interactive_repl()


def main() -> int:
    try:
        cli(standalone_mode=False)
        return 0
    except click.ClickException as exc:
        if "--json" in sys.argv:
            _emit_json(_error_payload(exc.format_message()))
        else:
            exc.show()
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - command-line safety net
        if "--json" in sys.argv:
            _emit_json(_error_payload(str(exc)))
        else:
            click.echo(f"Error: {exc}", err=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
