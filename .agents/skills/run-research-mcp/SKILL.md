---
name: run-research-mcp
description: How to build, launch and drive Research MCP v2 in an isolated scratch setup, so a change can be watched working. Use before verify-change, and whenever you need to run the server, the CLI, the stdio shim or a module by hand.
---

# Run Research MCP v2

Never touch the owner's real setup: no real `~/.config/research-mcp`, `~/Library/Application Support/research-mcp`, Keychain, launchd or client configs. Every run below uses a scratch home and fakes.

## 1. Build

```sh
uv sync --frozen
```

## 2. Isolate

```sh
export SCRATCH="$(mktemp -d)"
export RESEARCH_MCP_PATHS__STATE_DIR="$SCRATCH/state"
export RESEARCH_MCP_PATHS__DATA_DIR="$SCRATCH/cache"
export RESEARCH_MCP_PATHS__MODEL_CACHE_DIR="$SCRATCH/models"
export RESEARCH_MCP_PATHS__LOG_DIR="$SCRATCH/logs"
export RESEARCH_MCP_SERVER__PORT=17319      # a free loopback port, not the real 7319
```

Settings come from `config.toml` then `RESEARCH_MCP_*` overrides (SPEC section 2). The host is always `127.0.0.1`.

## 3. Drive what exists

Pick the highest level that exists on your branch (check with `ls src/research_mcp`).

| What exists | How to drive it |
|---|---|
| Only modules (M0-02 to M0-13) | `uv run python - <<'PY'` with a short script that imports the public API named in the SPEC section and exercises the change with fakes from `research_mcp.testing` (`FakeProvider`, `FakeClock`, recorded fixtures). Print the results you expect to see. |
| The MCP app (M0-14) | An in-memory MCP client against `build_mcp` (`mcp.shared.memory`), calling the tool you changed and printing the envelope. |
| The daemon and shim (M0-15) | `uv run research-mcpd` in the background (scratch env above), then `uv run research-mcp stdio` or HTTP calls to `http://127.0.0.1:<port>/healthz` and `/readyz`. Stop it when done. |
| The CLI (M0-16) | `uv run research-mcp --help`, then the subcommand you changed (`doctor --json`, `sources --markdown`, `config get <key>`). |

Network stays blocked unless the owner runs a `live` test: use recorded fixtures, never real upstreams.

## 4. Clean up

Stop any process you started and `rm -rf "$SCRATCH"`.
