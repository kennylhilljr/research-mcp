# Hooks

Claude Code hooks registered in [`.claude/settings.json`](../../.claude/settings.json) (and in [`hooks.json`](hooks.json) when the framework is installed as a plugin). Both scripts exit 0 on every unexpected error, so a broken hook never breaks a session; they exit 2 only to block on purpose, and Claude Code shows the reason to the agent.

| Hook | Event and matcher | What it does | Switch off |
| --- | --- | --- | --- |
| [`gate.mjs`](gate.mjs) | `PreToolUse` on `Skill`, and `UserPromptSubmit` | Blocks `sdd-hld` until a PRD is approved (Gate 1); `sdd-lld <component>` until the SPEC (Gate 2) and that component's PRD are approved; `sdd-tasks <component>` until that component's LLD is approved (Gate 3); `sdd-implement <milestone>` until that plan exists and every component it covers has an approved LLD. With several components and none named, it asks for one. The skill name is read from `tool_input.skill` (or `name` or `command`); the component and milestone from the skill's arguments | `features.gateHook: false` |
| [`protect-approved.mjs`](protect-approved.mjs) | `PreToolUse` on `Edit\|Write\|MultiEdit` | Blocks edits to documents whose status is `approved`, `superseded` or a final ADR status, and points to `sdd new --next`; for an accepted ADR it suggests a new ADR that supersedes it | `features.protectApprovedDocs: false` |

Feature flags live in `sdd.config.json`. Switching a hook off loses no data and changes no tool list.

## Notes

- A document is approved when a person sets `status: approved` (with `approved_by` and `approved`) in its front matter. Agents never do this. The hook reads status only; who approved is proved by code review and `CODEOWNERS`, not by the hook.
- These hooks are Claude Code adapters. Other agents follow the gates procedurally unless an equivalent adapter is installed; both scripts read JSON on stdin and exit 2 to block, so they can be wired into another agent's hooks.
- `gate.mjs` reads the skill name from `tool_input.skill`, falling back to `name` or `command`; it does not search free text. Typed slash commands (`/sdd-lld ...`) are caught by the `UserPromptSubmit` hook.
- To test a hook by hand (bash): `echo '{"tool_name":"Skill","tool_input":{"skill":"sdd-lld","args":"tech"}}' | node tools/hooks/gate.mjs; echo $?`
- In PowerShell: `'{"tool_name":"Skill","tool_input":{"skill":"sdd-lld","args":"tech"}}' | node tools/hooks/gate.mjs; $LASTEXITCODE`
