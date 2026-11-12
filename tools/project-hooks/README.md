# Project hooks

This folder holds project-only developer tooling. It is outside every SDD component and outside the framework machinery in `tools/hooks/`.

## after-edit.mjs

A Claude Code PostToolUse hook for `Edit`, `Write` and `MultiEdit`. It acts only on `.py` files under `src/` or `tests/`, and runs every step through `uv run --no-sync` in the project root (`CLAUDE_PROJECT_DIR`, else the hook input's `cwd`, else the current directory).

For a file under `src/`:

1. `ruff check --fix --force-exclude <file>` (safe fixes only, never `--unsafe-fixes`)
2. `ruff format --force-exclude <file>`
3. `ruff check --force-exclude <file>` (whatever could not be fixed)
4. `mypy` with no path arguments, so `pyproject.toml` decides the files and strictness
5. `pytest -q -x <targets>` for the tests mapped to the module

For a file under `tests/` the same steps run without mypy, and pytest runs that one test file.

Tests are mapped by name. `sources/<name>.py` maps to `tests/sources/<name>/`, to `tests/unit/sources/test_<name>*.py` and always to `tests/unit/sources/test_adapter_imports.py`. `<pkg>/<module>.py` maps to `test_<module>*.py` under `tests/unit/<pkg>/` and `tests/<pkg>/`. A top-level `<module>.py` maps to `test_<module>*.py` under `tests/unit/` and `tests/integration/`. Edits to `secrets.py`, `redact.py`, `http.py`, `stores.py`, `app.py` and `shim.py` also run `tests/security/`. Edits under `mcp_app/` and to `core/models.py`, `core/envelope.py` and `core/errors.py` also run `tests/contract/`. Targets that do not exist are dropped. When nothing maps, pytest is skipped and the success line says `no tests mapped`.

Every step runs even when an earlier one failed. Each step has a 90 s timeout; a step that times out counts as failed.

### Exit codes and output

- `0`: every step passed, or the edit was ignored. One stdout line starting with `after-edit:` lists the steps and the pytest targets.
- `2`: at least one step failed. Stderr has one header per failed step, naming the step and its exact command (plus `timed out` when it hit the limit), followed by the last 60 lines of that step's output.

When the hook has nothing to do it still prints one `after-edit:` line naming the reason and exits 0: invalid JSON, a missing or non-string `file_path`, another tool, a non-Python file, a Python file outside `src/` and `tests/`, a missing `uv` or `.venv`, or an unexpected error inside the hook.

Set `RESEARCH_MCP_EDIT_HOOK=off` to turn it off. It then exits 0 with no output at all and runs nothing.

### Manual test

```sh
echo '{"tool_name":"Edit","tool_input":{"file_path":"src/research_mcp/platform/redact.py"}}' | node tools/project-hooks/after-edit.mjs; echo $?
```

The unit tests start no real tool:

```sh
node --test tools/project-hooks/after-edit.test.mjs
```

### Registration (owner step)

This unit does not register the hook; the unit sandbox cannot write `.claude/settings.json`. The owner adds this entry under `hooks.PostToolUse`, next to the existing `gate.mjs` and `protect-approved.mjs` entries, which stay unchanged:

```json
{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command", "command": "node \"$CLAUDE_PROJECT_DIR/tools/project-hooks/after-edit.mjs\"", "timeout": 120}]}
```

### CI

`tools/ci.sh` does not run these tests. Its step list is fixed by LLD-platform-v3 (PLAT-FR-52), so adding a `node --test tools/project-hooks/after-edit.test.mjs` step is a deliberate follow-up (owner note 2026-11-11T21:36Z). Until a later LLD version adds that step, the standalone commands above are the only gate.
