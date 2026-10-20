---
name: security-review
description: Security review for changes to secrets, redaction, HTTP, stores, the app, the shim, auth, tests/security or .orchestration. Use for high-risk units and whenever a change handles credentials, untrusted content or network access.
---

# Security review

Review the unit's diff with an attacker's view. For each item, either show it holds or report a finding (`severity | file:line | issue | fix`).

1. **Secrets** (SPEC 3.1, ADR 0003): values never reach argv, logs, exceptions, reprs, fixtures or the handoff; Keychain writes go through `security -i` on stdin; references are validated before use, so no control character or newline reaches the `security` script.
2. **Redaction** (3.2): every registered secret is masked in every output path, including structured logs and error envelopes.
3. **Network** (3.3, NFR-09): loopback only for listeners; outbound calls use the scoped client; tests cannot reach the network (connect, sendto, sendmsg, DNS lookups).
4. **Untrusted content** (3.7, ADR 0009): fetched text is marked untrusted, never interpolated into SQL, shell, paths or prompts without validation.
5. **Storage** (3.5): parameterized SQL only; migrations cannot be skipped or reordered; file paths are normalized before containment checks.
6. **Auth** (M0-15, 10.5): local tokens compared in constant time; the stdio shim and HTTP endpoints refuse unauthenticated callers.
7. **Supply chain**: no new dependency outside SPEC 12.1; actions pinned by SHA.

Blockers stop the merge. Report what you could not check and why.
