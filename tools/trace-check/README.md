# trace-check

Checks the links between requirements, tests and code. Node 20 or later, no dependencies; git is optional (staleness and reach use it when present).

```bash
node tools/trace-check/trace-check.mjs                    # exit 1 on errors
node tools/trace-check/trace-check.mjs --write            # regenerate docs/trace/coverage.md and the trace index
node tools/trace-check/trace-check.mjs --results reports/junit.xml  # passing and failing states from a JUnit XML report
node tools/trace-check/trace-check.mjs --base origin/main # annotation reach for files changed since main
node tools/trace-check/trace-check.mjs --advisory --json
```

## How links are made

Tests and code cite the acceptance criteria they satisfy in a comment, in any language:

```ts
// @spec TECH-2
it("TECH-2: invalidates cached grants when a role is revoked", () => { /* ... */ });
```

```python
# @spec TECH-2, TECH-4
def revoke_role(user_id, role): ...
```

Put the annotation on the test that exercises the behavior and on the entry point of the behavior in code (the topmost function or handler that owns it), not on every helper. Files under `paths.testRoots` in `sdd.config.json`, or named like `*.test.*`, `*.spec.*`, `*_test.*` or `test_*`, count as tests.

## What it checks

| Check | Result |
| --- | --- |
| Reverse orphan: `@spec` cites an ID no PRD defines | Error |
| A criterion in an approved PRD has no test citing it, is not deferred or excepted, and a milestone plan exists for its component | Error |
| The same, before any plan exists, and the test plan and LLD do not map it to planned tests | Warning |
| A linked test failed in the JUnit report | Error |
| A P1 criterion is listed in the test plan's `deferred:` | Error |
| Hollow status: `docs/trace/coverage.md` says `test linked`, `passing` or `failing` but no test cites the ID | Error (fixed by `--write`) |
| Drift recorded for a criterion in the trace index | Warning |
| A governing artifact (parent PRD, component PRD, SPEC, LLD, test plan) was approved or changed after the component's last audit | Warning |
| A criterion has a test but no code entry point cites it | Warning |
| `@spec` cites a story, requirement or NFR instead of a criterion | Warning |
| A component changed since `audited_sha`, or was audited more than `trace.staleAfterDays` ago | Warning |
| Annotation reach below `trace.reachWarnBelow` (share of source files with at least one `@spec`) | Warning |
| Criteria in draft PRDs without tests | Info only |

Reach is measured per file, which is an approximation: it shows when new code lands with no link to any requirement.

## Evidence states

`planned`, `test linked`, `passing`, `failing`, `deferred`, `excepted`, `drifted` and `gap`. A link is structural evidence: it shows that a test cites the criterion, not that the test checks what the criterion means. The tests in a JUnit report are matched to criteria by the ID in their title.

## Status lives in derived files

`--write` regenerates `docs/trace/coverage.md` (the path in `paths.coverage`) and, per component in `docs/trace/index.yaml`, the governing artifact versions (`artifacts`) and the counts (`criteria`, `linked`, `passing`, `failing`, `planned`, `deferred`, `excepted`, `drifted`, `gaps`). It never edits the test plan, which keeps the strategy, the gaps and the `deferred:` list. Approved documents never carry status. The verifier persona maintains the audit record: `status`, `scope`, `owner`, `sampled`, `audited`, `audited_sha`, `findings`, `disposition`, `drift` (a list of criterion IDs) and `next`.
