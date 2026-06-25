# Mood Tracker Harness Notes

## Source

- Repository: `Huzhiwen1208/mood-tracker`
- Frontend: `index.html`
- Backend script: `sync-data.js`
- Storage: `data/moods.json` (encrypted), `data/actions.log`

## Backend mapping  

- `send` button in the UI corresponds to `node sync-data.js send`
  with `MOOD_TEXT`, `MOOD_TAG`, and `MOOD_PASSWORD`.
- `undo` in the UI corresponds to `node sync-data.js undo`.
- Timeline inspection reads and decrypts `data/moods.json`.
- The repo uses a JavaScript XOR + Base64 routine that operates on UTF-16
  code units, so harness decoding must mirror JavaScript semantics exactly.

## Project model

The harness treats a mood-tracker repository root as the authoritative backend
project and stores a lightweight JSON project file containing:

- repo root and key file paths
- password resolution settings
- cached decrypted moods for inspection
- last refresh metadata

## Command domains

- `project`: create and inspect harness project files
- `mood`: list, inspect, send, undo, and summarize mood entries
- `data`: inspect encrypted storage and action logs
- `repl`: interactive shell for repeated operations

## Backend truthfulness

- Mood mutations use the real Node backend instead of reimplementing send/undo.
- Read-only inspection uses a Python decoder that matches the JavaScript
  UTF-16 XOR behavior so encrypted repo data remains compatible with the app.
