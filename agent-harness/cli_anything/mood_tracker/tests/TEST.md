# Test Plan: cli-anything-mood-tracker

## Test Inventory Plan

- `test_core.py`: 6 unit tests planned
- `test_full_e2e.py`: 5 E2E tests planned

## Unit Test Plan

### `core/crypto.py`

- Functions: `xor_js_string`, `encode_payload`, `decode_payload`
- Coverage:
  - round-trip JSON payloads
  - emoji tag preservation across the JavaScript-compatible UTF-16 XOR flow
  - ciphertext shape differs from plaintext JSON
- Expected tests: 2

### `core/project.py`

- Functions: `create_project`, `refresh_project_state`, `resolve_password`, `load_action_log`
- Coverage:
  - repo validation and project creation
  - loading encrypted mood data from `data/moods.json`
  - password precedence: explicit, env, stored, fallback
- action-log tailing and empty-log behavior
- Expected tests: 3

### `core/git_sync.py`

- Functions: `sync_repo_data`
- Coverage:
  - no-op sync when tracked data files have no staged changes
  - stage only mood data files for commit/push
- Expected tests: 1

## E2E Test Plan

### Real backend workflows

- Build isolated temporary mood-tracker repos by copying `sync-data.js` and `index.html`
- Create harness project files through the installed CLI
- Run `send` and `undo` through the real Node backend
- Verify encrypted output by decrypting `data/moods.json`
- Verify log output by reading `data/actions.log`

### CLI subprocess coverage

- Resolve the installed `cli-anything-mood-tracker` command with `_resolve_cli()`
- Verify `--help`
- Verify JSON output for project creation and list operations
- Verify full send/undo workflows without relying on current working directory
- Verify `mood send --push` against a local bare git remote

## Realistic Workflow Scenarios

### Workflow name: Fresh project bootstrap

- Simulates: an agent onboarding a new mood-tracker repo for repeatable automation
- Operations chained:
  - create isolated repo copy
  - create harness project with `project new`
  - inspect project with `project info`
  - list moods with `mood list --json`
- Verified:
  - project JSON is created
  - repo paths are correct
  - empty store reports zero moods

### Workflow name: Mood send and encrypted persistence

- Simulates: recording a new mood entry through the real backend
- Operations chained:
  - create harness project
  - run `mood send`
  - inspect `data decrypt`
  - inspect `data log`
- Verified:
  - backend subprocess exits successfully
  - encrypted store decrypts to the expected mood entry
  - emoji tags survive the round trip
  - action log records the send

### Workflow name: Undo latest mood

- Simulates: reverting the most recent mood inside the 24-hour undo window
- Operations chained:
  - create harness project
  - send a mood
  - run `mood undo`
  - inspect decrypted data and logs
- Verified:
  - backend subprocess exits successfully
  - mood list becomes empty again
  - action log records the undo

## Test Results

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-8.4.2, pluggy-1.6.0 -- /Users/jackhu/Documents/Codex/2026-06-25/c/work/mood-tracker/agent-harness/.venv/bin/python3.14
cachedir: .pytest_cache
rootdir: /Users/jackhu/Documents/Codex/2026-06-25/c/work/mood-tracker/agent-harness
collecting ... collected 11 items

cli_anything/mood_tracker/tests/test_core.py::test_encode_decode_round_trip_preserves_emoji PASSED [ 11%]
cli_anything/mood_tracker/tests/test_core.py::test_create_project_reads_existing_mood_store PASSED [ 22%]
cli_anything/mood_tracker/tests/test_core.py::test_refresh_project_state_handles_empty_store PASSED [ 33%]
cli_anything/mood_tracker/tests/test_core.py::test_resolve_password_precedence PASSED [ 44%]
cli_anything/mood_tracker/tests/test_core.py::test_load_action_log_returns_tail PASSED [ 55%]
cli_anything/mood_tracker/tests/test_core.py::test_sync_repo_data_returns_no_commit_when_nothing_changed PASSED [ 54%]
cli_anything/mood_tracker/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 63%]
cli_anything/mood_tracker/tests/test_full_e2e.py::TestCLISubprocess::test_project_new_and_empty_list_json PASSED [ 72%]
cli_anything/mood_tracker/tests/test_full_e2e.py::TestCLISubprocess::test_send_and_decrypt_workflow PASSED [ 81%]
cli_anything/mood_tracker/tests/test_full_e2e.py::TestCLISubprocess::test_send_then_undo_workflow PASSED [ 90%]
cli_anything/mood_tracker/tests/test_full_e2e.py::TestCLISubprocess::test_send_with_push_updates_remote_repo PASSED [100%]

============================== 11 passed in 1.01s ===============================
```

## Summary Statistics

- Total tests: 11
- Pass rate: 100%
- Execution time: 1.01s

## Coverage Notes

- Covered the JavaScript-compatible encryption round trip, including emoji tags.
- Covered installed-command subprocess execution with `CLI_ANYTHING_FORCE_INSTALLED=1`.
- Covered real backend `send` and `undo` flows against isolated temporary repos.
- Covered one-command `--push` sync against a local bare git remote.
- Not covered: interactive REPL key handling and live GitHub-hosted remote pushes, because those depend on manual terminal interaction or real remote credentials/state.
