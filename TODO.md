# TODO

Near-term tasks. For phases and gates see [ROADMAP.md](ROADMAP.md). For the
research workstreams see [docs/research/plan.md](docs/research/plan.md).

## Process (now; you)
- [x] Agent roster and hierarchy: [docs/process/agent-team.md](docs/process/agent-team.md)
- [x] Workflow rules and hooks: [docs/process/workflow.md](docs/process/workflow.md)
- [x] AI disclosure: [AI-DISCLOSURE.md](AI-DISCLOSURE.md)
- [ ] Protect `main` with a ruleset ([how](docs/process/workflow.md#one-time-setup-you))
- [ ] Noreply commit email, private-terms list, GitHub secret scanning ([how](docs/process/workflow.md#one-time-setup-you))
- [ ] Enable git hooks in `C:\Dev\Re-Sieged`: `git config core.hooksPath .githooks`
- [ ] Decide on the personal email in the first `main` commit (keep or rewrite)
- [ ] Review and merge the first PR (PR handover stage 1)
- [ ] Define the gate review team (from existing project agent rosters + Re-Sieged gaps)
- [ ] Accept or revise ADR-0001 and ADR-0002

## Phase 0: Research foundation
- [ ] Verify ecosystem project licenses/URLs/commits (Q-043, Q-046)
- [ ] Decide how TX-A will identify the active PRS stance without memory access

## Phase 1: Static verification (needs access to a local install)
- [ ] Executable hash + PE summary script (CLM-001…006)
- [ ] Tank file enumeration + header evidence (CLM-010, 011)
- [ ] Tank container format doc (Q-020)
- [ ] Skrit corpus scanner (CLM-030…034)
- [ ] Skrit call classification: authored vs. unresolved (Q-004)
- [ ] GAS inheritance tool + re-trace hero graph (CLM-040…046)
- [ ] Chore prefix ↔ PRS scan (Q-003)
- [ ] Broken World inventory + diff (Q-024)
