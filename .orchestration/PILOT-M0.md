# M0 run guide

Milestone M0 ([M0 plan](../docs/build/M0-plan-v3.md): 23 units in 12 waves; M0-01 to M0-05 merged in `rm-m0b`, so a run builds 18 units from slice 4) delivered by the agent team under ECC, following TEAM-DELIVERY v5 (agent-control-plane-infra).

## Providers

Claude is the only provider. It writes code and plays every team role: PR reviewer, security reviewer, verifier, architect, designer, delivery lead and product owners (`.orchestration/config.yaml`, `team.json`). Independence comes from each role's persona and its own session, not from a different provider (`review_independence: persona` in `config.yaml`; TEAM-DELIVERY v3). The model follows the unit's class: Haiku, Sonnet or Opus (`cli_models`). Every unit applies the build skills in `.agents/skills` (AGENTS.md) in the author's own session, so the separate skills pass is off.

## Roles and personas

Each ECC role plays an SDD persona: its prompt starts with the persona file in `.claude/agents/` (`personas` in `team.json`). The coder is the `implementer`; the PR reviewer and the QA verifier are the `verifier`; the security reviewer is the `security-reviewer`; the architect is the `architect`; the product owners are the `product-writer`; the learning steward is the `doc-steward`. The designer and the delivery lead keep ECC's own prompts. ECC stops before a run if an assigned persona file is missing.

## SDD gates before a run

The documents follow the SDD framework (ADR 0013). Agents never approve, so before a run the owner approves, in order: the problem framing in [PRD v8](../docs/prd/PRD-v8.md) and the [vision](../docs/vision/vision-v2.md) (intake checkpoint), the PRDs (Gate 1), [SPEC v5](../docs/spec/SPEC-v5.md) (Gate 2) and the v2 LLD of each component the plan builds (Gate 3, approved 2026-10-23; [M0 plan v3](../docs/build/M0-plan-v3.md), which the owner approves before the run). The doc map (`docs/README.md`, `node tools/sdd/cli.mjs docmap`) shows each document's status, and `/sdd-status` in Claude Code summarizes it.

## Before the first run

1. The `ecc` shell function (keys come from the Keychain through `with-keychain-secrets`):

   ```sh
   export PATH="$(dirname "$(nvm which default)"):$PATH"
   ecc() { ~/Documents/GitHub/openclaw-ecc-orchestrator/bin/with-keychain-secrets ~/Documents/GitHub/openclaw-ecc-orchestrator/bin/ecc "$@" --config ~/Documents/GitHub/research-mcp/.orchestration/ecc.json; }
   ```

2. `ecc catalog-refresh`, then `ecc preflight --runner claude`. Preflight must pass for Claude Code before a run.

## Run

```sh
cd ~/Documents/GitHub/research-mcp
ecc create-run --run-id rm-m0e --plan .orchestration/plan-m0.json
ecc drive --run-id rm-m0e
```

The drive checks the plan (architect), then builds, reviews, verifies and merges units wave by wave. Agents merge into `main` locally; nothing is pushed.

## When the drive stops

It stops only when no unit can move after the delivery lead's own recoveries (TEAM-DELIVERY v5 7.1). The output lists `next:` lines: run them in order; the last one continues the drive. `ecc status --run-id rm-m0e` shows every unit.

## Done

The drive ends with the product owners' report under the ECC state folder (`reports/`). M0 is complete when both accept; then push `main`.
