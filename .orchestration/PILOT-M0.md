# M0 run guide

Milestone M0 (SPEC v2 section 12.3: 16 units in 10 waves) delivered by the agent team under ECC, following TEAM-DELIVERY v5 (agent-control-plane-infra).

## Providers

Codex and Claude write code; Codex, Claude and Gemini review, verify and play the architect, delivery lead and product owners (`.orchestration/config.yaml`, `team.json`). Gemini uses Flash-Lite for standard roles and Gemini Pro for advanced ones. Every unit applies the build skills in `.agents/skills` (AGENTS.md); after a unit written by Codex, a Claude Code skills pass runs `/simplify`, `/verify` and `/code-review` on it before the gates (TEAM-DELIVERY v6).

## Before the first run

1. The `ecc` shell function (keys come from the Keychain through `with-keychain-secrets`):

   ```sh
   export PATH="$(dirname "$(nvm which default)"):$PATH"
   ecc() { ~/Documents/GitHub/openclaw-ecc-orchestrator/bin/with-keychain-secrets ~/Documents/GitHub/openclaw-ecc-orchestrator/bin/ecc "$@" --config ~/Documents/GitHub/research-mcp/.orchestration/ecc.json; }
   ```

2. `ecc catalog-refresh`, then `ecc preflight`. Preflight must pass for both coding CLIs before a run.

## Run

```sh
cd ~/Documents/GitHub/research-mcp
ecc create-run --run-id rm-m0b --plan .orchestration/plan-m0.json
ecc drive --run-id rm-m0b
```

The drive checks the plan (architect), then builds, reviews, verifies and merges units wave by wave. Agents merge into `main` locally; nothing is pushed.

## When the drive stops

It stops only when no unit can move after the delivery lead's own recoveries (TEAM-DELIVERY v5 7.1). The output lists `next:` lines: run them in order; the last one continues the drive. `ecc status --run-id rm-m0b` shows every unit.

## Done

The drive ends with the product owners' report under the ECC state folder (`reports/`). M0 is complete when both accept; then push `main`.
