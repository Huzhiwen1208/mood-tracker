# cli-anything-mood-tracker

CLI harness for the `mood-tracker` GitHub Pages project. The harness uses the
real `sync-data.js` backend for `send` and `undo`, and it can inspect the
encrypted `data/moods.json` store without opening the browser UI.

## What it manages

- repo-backed mood timelines
- encrypted storage inspection
- action-log inspection
- project files for repeatable agent workflows
- one-shot commands and an interactive REPL

## Prerequisites

- Python 3.10+
- Node.js in `PATH`

## Install

```bash
cd agent-harness
pip install -e .
```

## Quick start

```bash
cli-anything-mood-tracker project new \
  --repo-root /path/to/mood-tracker \
  -o /tmp/mood-project.json

cli-anything-mood-tracker --project /tmp/mood-project.json mood list
cli-anything-mood-tracker --project /tmp/mood-project.json mood send "Today felt calmer." --tag "😌"
cli-anything-mood-tracker --project /tmp/mood-project.json mood send "Publish this too." --tag "🥳" --push
cli-anything-mood-tracker --project /tmp/mood-project.json data log --lines 5
```

## One-command sync to GitHub Pages

If your local repo already has a working `origin` remote and push credentials,
you can write the mood data and publish it in one command:

```bash
cli-anything-mood-tracker --project /tmp/mood-project.json \
  mood send "今天心情不错" --tag "😊" --push
```

The `--push` flow:

1. calls the real `sync-data.js` backend
2. stages only `data/moods.json` and `data/actions.log`
3. creates a git commit
4. runs `git pull --rebase origin <current-branch>`
5. pushes to the remote

Use `--remote` or `--branch` when you need non-default targets. Use
`--no-pull-rebase` if you explicitly want to skip the pull step.

## Password resolution

The harness resolves the encryption password in this order:

1. `--password` for the current command
2. `MOOD_PASSWORD` from the environment
3. password stored in the harness project file
4. fallback password recorded in the project file

This mirrors how `sync-data.js` resolves `MOOD_PASSWORD` while still letting the
harness inspect encrypted data outside GitHub Actions.

## Command groups

- `project`: create, refresh, inspect, and update harness project files
- `mood`: list, show, send, undo, summarize moods, and optionally push data to the remote repo
- `data`: inspect ciphertext metadata, decrypt the current store, and read logs
- `repl`: interactive shell that wraps the same commands
