---
name: cli-anything-mood-tracker
description: Use this CLI to inspect and operate a `mood-tracker` repository through its real `sync-data.js` backend, including project creation, encrypted data inspection, mood send, and mood undo workflows.
---

# cli-anything-mood-tracker

This harness wraps the `Huzhiwen1208/mood-tracker` GitHub Pages app. It uses the
real Node backend for `send` and `undo`, and it decodes `data/moods.json` with a
Python implementation that matches the app's JavaScript UTF-16 XOR behavior.

## Prerequisites

- Python 3.10+
- Node.js in `PATH`
- A local checkout or copy of a `mood-tracker` repository

## Install

```bash
cd /path/to/mood-tracker/agent-harness
pip install -e .[dev]
```

## Core workflow

```bash
cli-anything-mood-tracker project new \
  --repo-root /path/to/mood-tracker \
  -o /tmp/mood-project.json

cli-anything-mood-tracker --project /tmp/mood-project.json mood list
cli-anything-mood-tracker --project /tmp/mood-project.json mood send "Today felt calmer." --tag "😌"
cli-anything-mood-tracker --project /tmp/mood-project.json mood undo
cli-anything-mood-tracker --project /tmp/mood-project.json mood send "今天心情不错" --tag "😊" --push
```

## Command groups

### `project`

- `project new --repo-root PATH -o FILE`: create a harness project file that points at a mood-tracker repo
- `project info`: show repo paths, password settings, and current mood count
- `project refresh`: reload the cached project view from encrypted storage
- `project set-password --stored-password TEXT`: persist a password in the harness project file
- `project set-password --clear`: remove the stored password

### `mood`

- `mood list [--limit N]`: list decrypted mood entries
- `mood show MOOD_ID`: show one mood entry by id
- `mood send TEXT --tag TAG`: call `node sync-data.js send` with the selected tag
- `mood send TEXT --tag TAG --push`: send and then git-push `data/moods.json` plus `data/actions.log`
- `mood undo`: call `node sync-data.js undo`
- `mood undo --push`: undo and then git-push the changed data files
- `mood stats`: summarize total moods, counts by tag, and whether the latest entry is still undoable

### `data`

- `data inspect`: report encrypted file metadata and the latest mood
- `data decrypt`: print the decrypted mood array
- `data log [--lines N]`: read recent lines from `data/actions.log`

### `repl`

- `cli-anything-mood-tracker` or `cli-anything-mood-tracker repl`: start the interactive shell

## JSON mode

Use `--json` for machine-readable output:

```bash
cli-anything-mood-tracker --json --project /tmp/mood-project.json mood list
cli-anything-mood-tracker --json --project /tmp/mood-project.json data inspect
```

## Password resolution

The harness resolves the encryption password in this order:

1. `--password`
2. the environment variable named in the project file, defaulting to `MOOD_PASSWORD`
3. the stored password in the harness project file
4. the fallback password in the harness project file

## Backend limits

- The upstream app supports undo for the latest mood only, within 24 hours.
- There is no backend redo command, so the harness does not invent one.
- One-shot mutations auto-save refreshed project metadata unless `--dry-run` is set.
- `--push` requires a working git remote and valid push credentials on the target branch.

## For AI agents

- Prefer `--json` for parsing.
- Use absolute paths for `--repo-root` and `--project`.
- Treat `mood send` and `mood undo` as real backend mutations to repo data.
- Verify `data/actions.log` or `data decrypt` after mutations when correctness matters.
