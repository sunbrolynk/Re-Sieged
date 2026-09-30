# Agent instructions

This file is the single source of rules for AI agents in this repository.
`CLAUDE.md` imports it. It lives at the root under the tool-neutral
`AGENTS.md` name, so any future agent tool finds the same rules.

## Team and process

- You work inside a defined team: [docs/process/agent-team.md](docs/process/agent-team.md).
  The main session is the **Orchestrator**. Subagents live in `.claude/agents/`.
- Findings go Researcher/Runtime Observer → **Evidence Auditor** → **Provenance
  Guard** → Orchestrator prepares the change. Never skip the reviews for research content.
- **Agents never commit, push, merge, tag or rebase (H15).** Every commit and
  push is made by the Project Lead, as their GitHub user. The Orchestrator
  stages the change, then hands over the exact commands and a short commit
  message written in the Project Lead's voice (see Working conventions).
- Repository rules H1–H15 are enforced by hooks and CI:
  [docs/process/workflow.md](docs/process/workflow.md). If a hook blocks you,
  fix the cause or raise it with the Project Lead. Never bypass it.
- Pull requests follow [docs/process/pr-handover.md](docs/process/pr-handover.md).
- **Internal docs are local-only** (`docs/`, `TODO.md`; git-ignored) until they
  are rolled up into public guides. Agent files (`AGENTS.md`, `CLAUDE.md`,
  `.claude/`) are committed.
- **Memory:** record work in Mandrel (the Re-Sieged project binding) and in the
  local docs, as in the Project Lead's other projects. The local docs remain
  the source of truth; the pipeline must work without Mandrel.

## Project phase

Re-Sieged is in the **research phase** ([ROADMAP.md](ROADMAP.md)). Unless the
user explicitly asks otherwise:

- Do **not** scaffold engine/runtime source code, module trees, build systems or
  class hierarchies.
- Do produce research documents, evidence records, reproducible analysis
  scripts, and decision records.
- Adding a directory needs a reason. Only create one when you have real content
  to put in it.

## When building starts (Phase 5+)

- **Every code change ships with tests.** New behavior gets a test that would
  fail without it. A bug fix gets a test that reproduces the bug first. Tests
  use synthetic fixtures, never game files (ADR-0002).
- Code merges only after the **gate review team** has reviewed it. The roster
  is being defined (see [agent-team.md](docs/process/agent-team.md#gate-review-team-to-be-defined)).

## Hard rules

1. **Never commit proprietary content.** That includes game executables, DLLs,
   `.ds2res`/`.ds2map`/Tank files, extracted assets, maps, audio, video, ISOs,
   leaked or proprietary source, and bulk extracted text such as whole GAS or
   Skrit files. Short quotations (an identifier, a field name, a line or two)
   are allowed in research notes when needed to cite evidence.
2. **Never use leaked source** or proprietary SDK material as a basis for
   anything.
3. **No code from another project** without a provenance entry in
   [docs/research/ecosystem.md](docs/research/ecosystem.md) (source, license,
   version/commit, how it was modified).
4. **No secrets or personal information.** No credentials or tokens, no
   personal paths (write `C:\Users\<you>`), and never the Project Lead's real
   name or personal email. Rules H10–H13 enforce this. Never ask to see or
   print the private-terms list. When porting material from the Project
   Lead's other projects, replace any personal name with "Project Lead".
5. **No legal conclusions.** You may record legal *questions* and *precedents*,
   but do not state that something is legal.

## Evidence discipline

- Every factual claim about DS2/BW belongs in the
  [claims register](docs/research/claims-register.md) with a confidence level:
  **Confirmed / Strong / Plausible / Unknown**.
- Do not turn a guess into a fact. The following are **not** proof of runtime
  behavior: filenames, comments in GAS/Skrit, lexical call counts, or what a
  name "sounds like".
- **A failed observation is not evidence of absence.** Classify every negative
  result as one of: *environment limitation*, *search limitation*,
  *evidence of absence*, or *observed absence*.
- Use the evidence record format in
  [docs/research/README.md](docs/research/README.md) for any new finding.
- Record anything unresolved in
  [open-questions.md](docs/research/open-questions.md). Do not quietly assume
  an answer.

## Specific traps (from prior research)

- `inventory.animstance` is not understood. The dagger→stance mapping is
  unknown.
- The 3,856 Skrit dotted calls are a lexical surface, **not** a native API spec.
- Broken World is a separate compatibility profile until proven otherwise.
- Do not assume the original executable is part of the final runtime.
- Do not assume one import/compatibility model, or yes/no mod compatibility.

## Environments

- **Native Windows (`C:\Dev\Re-Sieged`) is the primary environment** for all
  work: static analysis against the local game install, scripts, and runtime
  observation. Runtime observation is performed by the Project Lead using
  protocols from the Runtime Observer, with black-box methods only: no patching,
  injection, hooks, or memory modification (see [research plan](docs/research/plan.md)).
- **WSL is no longer used** (decision 2026-09-29).
- **Cloud sessions** (Claude Code on the web) have no game files. Use them
  for documentation, planning, and repository tooling only.
- Scripts must run on Windows: Python 3, `pathlib` paths, and no bash-only
  tooling for anything research depends on.

## Working conventions

- Commit messages are drafted **in the Project Lead's voice**: short subject
  in the form `<Area>: <Past-tense summary>` (e.g. `Docs: Added initial project
  scaffolding`), an optional body of a few plain lines, nothing else. **No
  `Co-Authored-By`, no "Generated with", no AI mention of any kind** in commits,
  code, comments or PRs (H5). AI use is disclosed once, in `AI-DISCLOSURE.md`.
- Keep commits small: one logical change each. Split anything the size check
  warns about (H5) before handing it over.
- Update `CHANGELOG.md` under *Unreleased* for notable documentation or process
  changes.
- Keep `docs/handoff/` files unedited. They are historical. Put corrections in
  the claims register.

## AI-specific rule

Your own trained "knowledge" of DS2 internals is **not evidence**. Any such
claim needs an observation-backed evidence record. See
[AI-DISCLOSURE.md](AI-DISCLOSURE.md).

