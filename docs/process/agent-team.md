# Agent team and hierarchy

- **Status:** Accepted (2026-09-29): lean five-role team; Codex no longer involved.
- **Applies to:** Phases 0–3 (research). Reviewed again at the Phase 3 → 4 gate.

## Principles

1. **Roles follow the phase.** The work is research, so the team is a research
   team. Engineering roles are dormant until Phase 4.
2. **Separation of powers.** The agent that produces a finding never approves it.
   This is the same reason a code author does not approve their own PR.
3. **Least privilege.** Reviewers get read-only tools. Only the Orchestrator
   commits and pushes.
4. **The Project Lead (you) is the final authority** on phase gates, ADRs,
   licensing, merges to `main`, and anything irreversible.

## Hierarchy

```text
                       ┌─────────────────────────────┐
                       │  PROJECT LEAD (human)       │  gates · ADRs · merges ·
                       │                             │  licensing · runs the game
                       └──────────────┬──────────────┘
                                      │
                       ┌──────────────▼──────────────┐
                       │  ORCHESTRATOR               │  main Claude session:
                       │  (+ keeps the registers)    │  plans, delegates, integrates,
                       └──────┬───────────────┬──────┘  sole committer/pusher
                 produce      │               │      check
          ┌───────────────────┘               └────────────────────┐
┌─────────▼──────────┐ ┌────────────────────┐   ┌──────────────────▼─┐ ┌────────────────────┐
│ RESEARCHER         │ │ RUNTIME OBSERVER   │   │ EVIDENCE AUDITOR   │ │ PROVENANCE GUARD   │
│ formats · GAS ·    │ │ writes TX protocols│   │ reviews findings · │ │ content policy ·   │
│ Skrit · scripts    │ │ analyzes captures  │   │ confidence levels  │ │ licenses · AI      │
│ (read + write)     │ │ (read + write)     │   │ (read-only)        │ │ disclosure (r/o)   │
└────────────────────┘ └────────────────────┘   └────────────────────┘ └────────────────────┘
```

## Roles

| Role | Where defined | Mission | Tools | Must not |
| --- | --- | --- | --- | --- |
| **Orchestrator** | Main session; [AGENTS.md](../../AGENTS.md) | Break work down, delegate, integrate, update registers/CHANGELOG, commit, push, prepare PRs and gate reviews | All | Push to `main`; accept ADRs or pass gates; skip reviews |
| **Researcher** | [.claude/agents/researcher.md](../../.claude/agents/researcher.md) | Static research: Tank/GAS/ASP/PRS/save formats, Skrit semantics and call classification, reproducible analysis scripts, draft EV records | Read, search, Bash, write | Commit; mark claims *Verified*; treat model memory as evidence |
| **Runtime Observer** | [.claude/agents/runtime-observer.md](../../.claude/agents/runtime-observer.md) | Design black-box transaction protocols (TX-A…E, save diffs) for **you** to run on Windows; analyze the captures you return; draft EV records | Read, search, Bash, write | Propose patching, injection, hooks, trainers or memory reading |
| **Evidence Auditor** | [.claude/agents/evidence-auditor.md](../../.claude/agents/evidence-auditor.md) | Review every EV record and claim change: confidence justified? negatives classified? "Does NOT prove" honest? | Read-only | Write findings (no self-review) |
| **Provenance Guard** | [.claude/agents/provenance-guard.md](../../.claude/agents/provenance-guard.md) | Content policy (ADR-0002), licenses/provenance, leaked-source risk, accuracy of AI-DISCLOSURE | Read-only | Give legal conclusions |

### Who runs the game?

Codex is no longer part of the project, so **you** perform runtime work on native
Windows: launching the game, following protocol steps, capturing
screenshots/video/saves. The Runtime Observer prepares the protocol before you
play, and analyzes what you capture afterwards. This also keeps a human in the
loop for every runtime observation.

### Dormant until Phase 4

Architect · Security Reviewer · Platform/Renderer · Input/UX (controller-first)
· Test Engineer. These will be defined when the Phase 3 → 4 gate is reviewed.

## Gate review team (to be defined)

Required before any code is merged, from Phase 5 on (Project Lead decision,
2026-09-29). Draft roster, pipeline and goal ownership:
[gate-team-proposal.md](gate-team-proposal.md) (Proposed).
Testing is mandatory for all code (see [AGENTS.md](../../AGENTS.md)).

## Standard flow for a finding

```text
Researcher / Runtime Observer ── draft EV record ──▶ Evidence Auditor
        ▲                                                │
        └──────────── changes requested ─────────────────┤
                                                         ▼ approved
                                                Provenance Guard
                                                         │ cleared (or veto ▶ back)
                                                         ▼
                        Orchestrator updates registers, commits, pushes branch
                                                         ▼
                                    PR (see pr-handover.md) ─▶ you review & merge
```

The Auditor and Guard give **verdicts, not vetoes over you**. A rejection sends
work back to its author. A disagreement that the agents cannot settle goes to
you.

## Escalate to the Project Lead when

- a phase gate or ADR is ready for review
- a finding contradicts an existing *Strong* claim
- anything touches licensing, legal risk, or third-party code reuse
- an agent would need to exceed its permissions or bypass a hook
- the Auditor/Guard and a producer disagree

## Honest limits of this setup

- "Read-only" for the Auditor and Guard is **enforced**: their agent
  definitions grant no Write/Edit/Bash tools.
- "Only the Orchestrator commits" is **by instruction**. Subagents that have Bash
  could technically run `git commit`. Any commit still goes through the git and
  CI checks.
