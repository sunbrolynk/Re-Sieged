# Gate review team and goal ownership (PROPOSAL)

- **Status:** Proposed (2026-09-29). Under discussion with the Project Lead.
- **Applies from:** Phase 5 (code). Research-phase roles are unchanged
  ([agent-team.md](agent-team.md)).
- **Sources:** the agent fleets of two earlier projects by the Project Lead (an
  audiobook manager with 38 agents and a metadata API with 27), plus a smaller
  4-agent project. Their shared pipeline is adopted almost unchanged. Their
  domain agents are dropped. Re-Sieged-specific gaps are added.

## 1. The pipeline (adopted)

Proven across both earlier projects:

```text
1. Spec        Orchestrator: scope, lanes, seam contracts, done-criteria.
               Spec-stage consults: architect, security-architect, and any
               goal owner whose goal the change touches (section 4).
2. Implement   Lane specialists, one lane each. Never two agents in one file.
3. Test        test-engineer writes tests in the same slice.
4. Panel       Reviewers run in parallel, read-only, blind to each other.
               Always-on panel + reviewers routed by the files actually touched.
               Strict AND: any red blocks. One flagged instance means the owner
               sweeps the whole slice for that class of problem.
5. Local gate  Lint, types, tests, security scans. Regressions are measured as
               before/after deltas, never eyeballed.
6. Present     Evidence to the Project Lead: files, why, gate results, panel
               verdicts, manual-check list.
7. Commit/PR   Per pr-handover.md.
8. Record      Registers, CHANGELOG, decision records.
```

Carried-over lessons:
- **Subagents cannot spawn subagents.** Only the main session dispatches. A
  "lead" agent plans a dispatch; it cannot run one.
- **Briefs end with:** "If anything is red or unfinished, say so explicitly. A
  report listing only passing checks reads as a green gate."
- **Model tiering:** orchestration, architecture and security design on the
  strongest model; focused reviewers on a lighter one.

## 2. Always-on panel (every code change)

| Agent | Origin | Change for Re-Sieged |
| --- | --- | --- |
| `bug-hunter` | both | none |
| `security-reviewer` | both | adds parser-of-untrusted-data focus |
| `lint-reviewer` | both | language set chosen in Phase 4 |
| `comment-reviewer` | both | none |
| `test-engineer` | both | synthetic fixtures only (ADR-0002). The only panel member that edits, and only test files |
| `stub-hunter` | ABM | none. Honesty gate: no fake "computed" values |
| `dry` | ABM `dry` + Libex `factoring` | merged: corpus-wide duplication + in-file extraction |
| `provenance-guard` | Re-Sieged | extended from research to **code**: clean-room, licenses, no leaked-source tells |
| `fidelity-guardian` | **new** | see section 4 |

## 3. Routed reviewers and consults (adopted or adapted)

| Agent | Kind | Origin → adaptation |
| --- | --- | --- |
| `architect` | spec consult + gate | both → unchanged in spirit |
| `security-architect` | spec consult | both → import boundary, parsers, mods, networking |
| `data-integrity` | gate | both → **save files, settings, import cache**: never break a user's saves, additive evolution only |
| `performance` | gate | ABM → **frame-time budget**, frame pacing, load/stream times |
| `logging` | gate | both → diagnostics without logging personal paths or content |
| `docs` / `readme` | gate | both → unchanged |
| `version` | gate | both → unchanged |
| `privacy` | gate | Libex → crash reports/telemetry (if any are ever added) |
| `deployment` + `packaging` | lane | both → Windows installer/Steam; later Linux/Deck builds; **release-artifact scan** (nothing proprietary ships) |
| `contribution-reviewer` | intake | Libex → dormant until outside contributors arrive |
| `accessibility`, `ux-visual`, `design-system`, `i18n` | gates | ABM → activated when UI work starts |

**Dropped** (tied to those projects' domains): abs-integration, arr-parity,
audible-services, audimeta-compat, region-reviewer, download-clients, indexers,
libex, metadata-parsing, api-routes, services, handlers, database, db-layer,
db-reviewer, cache-reviewer, background-tasks/jobs, validation, react,
state-query, mobile-native, observability, frontend-lead, backend-lead. Their
*patterns* (for example audimeta-compat's "the contract is sacred" reviewer)
inform the new agents below.

## 4. Goal ownership: every Project Lead goal has an owner

Each goal from the project brief is owned by one agent. That agent is consulted
at spec stage for any change touching the goal, and gates changes that could
regress it. Lane (implementer) agents are defined in Phase 4, once the
architecture exists; until then, owners hold the goal as **requirements and
review criteria**.

| Goal (from the brief) | Owner | Kind |
| --- | --- | --- |
| Preserve DS2/BW identity, content, systems, progression, spirit | `fidelity-guardian` | always-on gate. Asks whether this still plays and feels like DS2, and whether behavior is backed by evidence (CLM/EV), not invention |
| Behavior claiming DS2 semantics must trace to research | `evidence-auditor` (extended) | gate |
| Native controller-first UX: analog movement, targeting, abilities, inventory flows (not rebinding) | `input-ux` | spec consult + gate |
| Handheld-friendly UI, Steam Deck / x86 handhelds (text size, suspend/resume, battery) | `handheld` | gate |
| Modern renderer, 4K, ultrawide, high refresh, shaders, texture/material quality | `renderer` | lane + gate |
| Resolution-independent UI | `ux-visual` (adapted) | gate |
| Frame pacing, loading behavior | `performance` (adapted) | gate |
| Windows-first; Linux/Deck ports stay possible | `platform` | gate. Keeps Windows-only APIs inside the platform layer |
| Modern save and settings behavior | `data-integrity` (adapted) | gate |
| Modern audio behavior | `audio` | lane + gate |
| Modern combat feedback / game feel | `game-feel` | spec consult + gate |
| Point at your install and it "just works" (local import/conversion) | `importer` | lane + gate |
| Parsers of untrusted game and mod data (malformed archives, bombs, traversal) | `format-hardening` | always-on for parser code; fuzzing required |
| Mod compatibility by deliberate levels (data, asset, script, save, behavior) | `compat-contract` | gate. The "sacred contract" reviewer, modeled on audimeta-compat |
| Skrit/GAS runtime semantics | `script-runtime` | lane (after the Phase 4 Skrit strategy decision) |
| Clean-room, licensing, nothing proprietary shipped | `provenance-guard` (extended) | always-on gate |
| Multiplayer (if ever in scope) | `netcode` | dormant (Q-044) |

## 5. Automated gates (no agent needed)

From the earlier projects' pre-commit/CI setups, added in Phase 5 alongside
H1–H13:
- YAML/JSON validity, trailing whitespace, end-of-file newline
- **H14: a tracked file must not become empty** (a truncated `TODO.md` slipped
  through on 2026-09-29; this catches it)
- Language linters and type checks, per the Phase 4 stack choice
- Security linting (e.g. bandit for Python tooling)
- Dependency audit and hash-pinned lock files
- Fuzz-test runs for parsers

## 6. Open decisions (Project Lead)

1. **AI visibility.** The earlier projects keep Claude invisible; Re-Sieged
   currently discloses AI use (AI-DISCLOSURE.md, H5 trailers). Which applies here?
2. **Who commits.** The earlier projects have the Project Lead as sole
   committer; Re-Sieged has the Orchestrator committing plus a staged PR
   handover. Keep, or switch?
3. **Agent files.** The earlier projects keep `.claude/` and `CLAUDE.md`
   local-only; Re-Sieged commits them. Keep, or switch?
4. **External memory tool.** The earlier projects record work in an MCP memory
   service; Re-Sieged uses `docs/research/` and decision records. Add it?
5. **More goals.** Which goals are missing from section 4?
