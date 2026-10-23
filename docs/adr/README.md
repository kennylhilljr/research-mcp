# Architecture decision records

One file per decision, numbered once (`0001-<slug>.md`) and never versioned. A changed decision gets a new ADR that supersedes the old one. Create one with `node tools/sdd/cli.mjs new adr --name <slug>`.

| Status | Meaning |
| --- | --- |
| `proposed` | Options drafted (C); waiting for the owner |
| `accepted` | The owner chose an option; frozen |
| `rejected` | Considered and not taken; kept for the record |
| `superseded` | Replaced by a later ADR, which names it |
| `deprecated` | No longer applies, with no replacement |

The current list, with status and owner, is in the delivery artifact index of the [doc map](../README.md).
