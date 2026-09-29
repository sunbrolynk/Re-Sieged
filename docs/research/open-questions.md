# Open questions

These are explicit unknowns. **Do not answer them by assumption.** Each entry
says what would resolve it and which phase is expected to do so.

Priority: **P1** blocks architecture · **P2** shapes it · **P3** can wait.

## The north-star question

> **Q-000:** What is the smallest clean-room runtime semantic surface that
> preserves the behavior of DS2/BW authored content, while replacing the
> platform, rendering, input and runtime pieces?

Every question below feeds into this one.

## Runtime semantics

| ID | Pri | Question | Resolved by | Phase |
| --- | --- | --- | --- | --- |
| Q-001 | P1 | Is the native semantic layer small and well defined, or do ordinary actors depend on large amounts of opaque native logic? | Boundary map across areas (TX A–E + static survey) | 3 |
| Q-002 | P1 | How is `inventory.animstance` derived from equipment? What stance does the dagger give? Unarmed? Bow? | TX-A | 2 |
| Q-003 | P2 | Is the `prefix + stance + key → PRS` lookup exactly as it appears? What happens when a resource is missing? | TX-A + static scan of all chore prefixes | 1–2 |
| Q-004 | P1 | How are Skrit calls bound to native services? Which parts of the lexical call surface are native, and which are authored? | Static classification of calls vs. authored definitions; black-box behavior | 1–3 |
| Q-005 | P2 | Component construction and initialization order | Static (component schemas) + runtime observation | 2 |
| Q-006 | P2 | How is the player/party actor created? (It is not map-placed.) | Static search of party/creation GAS & Skrit; runtime observation | 1–2 |
| Q-007 | P2 | How do movement, velocity and animation interact (blending, start/stop, turning, animation rate)? | TX-B | 2 |
| Q-008 | P2 | Damage → life → death: timing, events, effect on jobs and movement, persistence | TX-C | 2 |
| Q-009 | P3 | How does the job scheduler and MCP lifecycle work? | TX-E | 2 |
| Q-010 | P3 | Collision/physics behavior | Runtime observation | 2+ |

## Content and formats

| ID | Pri | Question | Resolved by | Phase |
| --- | --- | --- | --- | --- |
| Q-020 | P1 | Tank format: header, index, paths, compression, and override/precedence rules between multiple Tanks | Our own format documentation, cross-checked against a tool | 1 |
| Q-021 | P2 | ASP (mesh), PRS (animation), texture and terrain node formats | Format research; existing DS1 tools as leads | 1 |
| Q-022 | P2 | Semantics of the world/map binary data (regions, nodes, triggers) | Static research | 1–3 |
| Q-023 | P2 | Save schema and serialization (`.ds2party`, `.ds2world`, component order) | Diff saves before and after controlled actions | 2 |
| Q-024 | P1 | How do Broken World resources relate to base DS2 (override layer, separate world, executable differences)? | Inventory the BW install; diff it against DS2 | 1 |

## Product, legal, strategy

| ID | Pri | Question | Resolved by | Phase |
| --- | --- | --- | --- | --- |
| Q-040 | P1 | Distribution/import model: direct compatibility, local import, hybrid, executable-assisted, or another | Phase 3 boundary map + legal research | 3–4 |
| Q-041 | P1 | Skrit strategy: compatible VM, translation, hybrid, or reauthoring | Q-001, Q-004 | 4 |
| Q-042 | P2 | Which compatibility levels to promise: data, asset, script, save, behavioral, native plugin | Phase 3 | 3–4 |
| Q-043 | P2 | Project license. It limits reuse of GPL-3.0 (OpenSiege, SiegeFX), AGPL-3.0 (Siege Control app) and MIT sources | Decision after the ecosystem license review | 0–4 |
| Q-044 | P3 | Is multiplayer in scope? If so, what model? | Product decision | 4+ |
| Q-045 | P3 | Does the game load controller support dynamically (CLM-005)? | Runtime observation (loaded modules) | 2 |
| Q-046 | P3 | What do the "Dungeon Siege 2 Resurrected" and other community projects actually cover? Under what license? | Ecosystem review | 0 |

## Resolved

Move questions here with the date and evidence link when answered.

_None yet._
