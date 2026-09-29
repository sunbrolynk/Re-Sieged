# Research plan

This plan covers ROADMAP phases 0–3. Its goal is to establish the
authored-content ↔ native-service boundary **empirically**, so that the
Phase 4 architecture rests on evidence.

## Guiding rules

1. Verify before building on a claim. Anything *Reported* is a lead.
2. Scripts over one-off greps. Every static scan that supports a claim should
   be rerunnable (see [CONTRIBUTING](../../CONTRIBUTING.md#analysis-scripts)).
3. Observe behavior, not implementation. Runtime work is black-box.
4. Classify every negative result ([method](README.md#classifying-negative-results)).
5. Work on one actor or system end-to-end before going broad.

## Environments

| Environment | Use for | Notes |
| --- | --- | --- |
| **Native Windows** (primary) | Static analysis against the local install, scripts, runtime observation, save diffs | Windows is the first target platform. Earlier WSL→Windows interop failures (`UtilBindVsockAnyPort`) were an environment limitation; WSL is no longer used |
| Cloud (Claude Code on the web) | Docs, planning, repository tooling | No game files available |

## Workstreams

### WS-1: Static verification (Phase 1)

| Task | Resolves | Output |
| --- | --- | --- |
| Hash and PE-summary script for the executables | CLM-001…006 | EV record + committed summary |
| Enumerate Tank files, headers and sizes | CLM-010, 011 | EV record |
| Document the Tank container from our own observation, then cross-check against Siege Control/DS2 Tank Editor behavior | Q-020 | `docs/research/formats/tank.md` |
| Skrit corpus scanner (calls, namespaces, events, handlers) | CLM-030…034 | Script + derived counts |
| Classify each Skrit call target: defined in authored Skrit, or unresolved (so native-side) | Q-004 | Candidate native surface list, labeled *lexical* |
| GAS parser prototype (research tool only), used to resolve template inheritance | CLM-020, 021, 040–046 | Rebuilt hero dependency graph |
| Scan all chore prefixes against PRS paths | Q-003 | EV record |
| Broken World inventory and diff against DS2 | Q-024, CLM-080/081 | `docs/research/broken-world.md` |

> Research tools are throwaway-grade on purpose, not production code. They may
> later inform real importers, but they carry no architectural commitment.

### WS-2: Runtime observation (Phase 2, native Windows)

The Project Lead plays the game. The `runtime-observer` agent writes each
protocol beforehand and analyzes the captures afterwards
([team](../process/agent-team.md)).

Allowed: normal play, screenshots/video, save inspection, passive process
observation (e.g. loaded modules), controlled input.
Not allowed in this phase: patching, injection, hooks, trainers, memory
modification, changes to the executable.

| Transaction | Chain observed | Resolves |
| --- | --- | --- |
| **TX-A** Equipment → animation | unarmed / dagger / bow / 2H → walk & idle animation | Q-002, Q-003 |
| **TX-B** Movement → animation | input → movement → velocity → animation (start/stop/turn/speed) | Q-007 |
| **TX-C** Damage → death | damage → life → death transition → job/animation → persistence | Q-008 |
| TX-D Interaction (optional) | target → approach → use → effect | CLM-064 |
| TX-E AI/job (optional) | brain → job → MCP → action → completion | Q-009 |
| Save diffs | save before and after a single controlled change | Q-023 |

Each transaction produces one evidence record: a protocol (exact steps and
inputs), captures, observations, and classified negatives.

**Open design point:** how do we tell which PRS stance is playing, without
reading memory? Candidates: visual comparison with PRS files rendered by a
research tool, or community tools that already visualize PRS. Decide this before
running TX-A.

### WS-3: Boundary synthesis (Phase 3)

Fill the semantic matrix (from H§27) with **verified** entries:

| Area | Authored supplies | Runtime must provide (observable contract) | Compatibility level needed | Evidence |
| --- | --- | --- | --- | --- |
| Initialization | | | | |
| Equipment | | | | |
| Movement | | | | |
| Animation | | | | |
| Life / death | | | | |
| Interaction | | | | |
| AI / jobs | | | | |
| Effects | | | | |
| World / map | | | | |
| Saves | | | | |

Then answer Q-001 and draft recommendations for Q-040, Q-041 and Q-042.

### WS-4: Ecosystem, legal and provenance (runs alongside the others)

- Verify each project's license, repo URL and last-commit date ([ecosystem.md](ecosystem.md))
- Research clean-room precedent (OpenSiege, SiegeFX, OpenMW/OpenRA-style import models)
- Security threat model for the import boundary (H§38), written down as
  requirements before any importer exists

## Suggested order

1. WS-4 license verification (small; it unblocks Q-043)
2. WS-1: executable + Tank facts → Tank format doc → Skrit scanner → call classification
3. WS-1: GAS inheritance tool → re-trace hero → chore/PRS scan
4. WS-1: Broken World diff
5. WS-2: TX-A → TX-B → TX-C → save diffs
6. WS-3 synthesis → gate review → Phase 4
