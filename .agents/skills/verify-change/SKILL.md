---
name: verify-change
description: Confirm a change actually works end to end, not only that tests and types pass. Use after the acceptance commands and tools/ci.sh --python-only pass, before review or handoff.
---

# Verify a change

Tests passing is necessary, not sufficient. This skill checks the behavior itself.

1. **State the claim.** From your unit's SPEC sections and its acceptance test ids, write down in one or two sentences what must now be true (for example "a malformed `keychain:` reference raises `ValueError` before any `security` call").
2. **Run the gates.** Your unit's acceptance commands, then `tools/ci.sh --python-only`. Stop here if either fails.
3. **Exercise it directly.** Follow the run-research-mcp skill and drive the changed behavior the way a caller would (the module API, the MCP tool, the CLI), including at least one input that must be refused. Use fakes and fixtures; the network stays blocked.
4. **Check SPEC 0.6.** If your unit has a row in SPEC section 0.6, exercise each case it names.
5. **Record the evidence.** In your handoff's `commands`, list what you ran and what you saw. If something did not behave as the claim says, fix it or report it in `unresolved_failures`; never report success you did not observe.
