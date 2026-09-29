# Agent team and hierarchy (DRAFT, for discussion)

> **Status: proposal.** Nothing here is implemented yet. No `.claude/agents/`
> files exist. We will decide the roster together, then build it.

## Design principles

1. **Roles follow the phase.** Most work right now is research, so most active
   agents are research agents. Architecture/engineering agents stay *dormant*
   until Phase 4.
2. **Separation of powers.** The agent that produces a finding is not the one
   that approves it. This is the same reason a code author does not approve
   their own PR.
3. **Least privilege.** Most agents are read-only. Few can write, and only one
   role commits.
4. **The human is the final authority** on gates, decisions (ADRs), licensing
   and anything irreversible.

## Proposed hierarchy

```text
                         ┌──────────────────────────┐
                         │  Project Lead (you)      │  final say: gates, ADRs,
                         │                          │  merges, legal/licensing
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │  Orchestrator            │  plans, delegates, integrates,
                         │  (main Claude session)   │  only role that commits/pushes
                         └────┬───────────┬─────────┘
            ┌─────────────────┘           └──────────────────┐
   ┌────────▼─────────┐                            ┌─────────▼──────────┐
   │  RESEARCH        │                            │  GOVERNANCE        │
   │  (produce)       │                            │  (check / veto)    │
   ├──────────────────┤                            ├────────────────────┤
   │ Format           │                            │ Evidence Auditor   │
   │   Archaeologist  │ ── findings ─────────────▶ │ Provenance &       │
   │ Skrit Analyst    │                            │   Clean-Room Guard │
   │ Runtime Observer │ ◀── rejected / needs more ─│ Scribe (registers) │
   └──────────────────┘                            └────────────────────┘

   ┌───────────────────────────────────────────────────────────────────┐
   │ DORMANT until Phase 4: Architect · Security Reviewer · Platform/   │
   │ Renderer · Input/UX (controller-first) · Test Engineer             │
   └───────────────────────────────────────────────────────────────────┘
```

## Roster

### Active in Phases 0–3

| Agent | Mission | Can | Cannot | Runs where |
| --- | --- | --- | --- | --- |
| **Orchestrator** | Break down work, delegate, merge results, prepare gate reviews | Read, write, commit, push to feature branches | Push to `main`, accept ADRs, move a phase gate | Main Claude Code session |
| **Format Archaeologist** | Tank, GAS, ASP, PRS, terrain, save formats; writes research scripts | Read, write under `docs/research/` and research `tools/` | Commit; mark a claim *Verified* | Claude subagent (Linux/WSL) |
| **Skrit Analyst** | Skrit language/semantics, call-surface classification, event model | Read, write research notes | Commit; declare a native API | Claude subagent |
| **Runtime Observer** | Black-box transactions TX-A…E, save diffs | Run the game, capture, write EV drafts | Patch/inject/hook/modify memory | Codex on native Windows (and/or you) |
| **Evidence Auditor** | Reviews every EV record and claim change. Enforces confidence levels and negative-result classes | Read; approve/reject; downgrade claims | Write findings of its own (avoids self-review) | Claude subagent, **read-only** |
| **Provenance & Clean-Room Guard** | Content policy, licenses, leaked-source risk, AI-disclosure accuracy | Read; **veto** a commit | Make legal conclusions | Claude subagent, read-only |
| **Scribe** | Keeps the claims register, open questions, CHANGELOG, handoffs in sync | Write docs | Change a claim's confidence without Auditor approval | Claude subagent |

### Dormant until Phase 4

| Agent | Mission when activated |
| --- | --- |
| Architect | Draft architecture ADRs from the Phase 3 boundary map |
| Security Reviewer | Import-boundary threat model; review of parsers of untrusted data |
| Platform / Renderer | Rendering, windowing, Steam Deck/Linux, frame pacing |
| Input / UX | Native controller-first interaction model |
| Test Engineer | Behavior tests ("given content X, when state Y, then Z") |

## Standard flow for a finding

```text
Researcher drafts EV record ─▶ Evidence Auditor reviews ─▶ Provenance Guard checks
        ▲                              │ reject                     │ veto
        └──────────────────────────────┘                            ▼
                                            Scribe updates registers ─▶ Orchestrator commits
                                                                        ─▶ PR ─▶ you merge
```

## Escalate to the Project Lead when

- a phase gate is ready for review, or an ADR is proposed
- a finding contradicts an existing *Strong* claim
- anything touches licensing, legal risk, or third-party code reuse
- an agent wants to exceed its permissions
- agents disagree and the Auditor cannot resolve it

## Decisions we need to make together

1. Is this roster the right size? It has seven active roles. A leaner option
   merges Scribe into Orchestrator and Skrit into Format, which gives five.
2. What does Codex do: only the Windows Runtime Observer, or a second reviewer
   (cross-model check) as well?
3. Is the "only the Orchestrator commits" rule acceptable?
4. Should the Auditor have a hard veto, or only advise while you decide?
5. Do you want a named persona/voice for each agent, or strictly functional ones?
