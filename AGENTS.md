# Agent instructions

This file is the single source of rules for AI agents in this repository.
`CLAUDE.md` imports it. It lives at the root under the tool-neutral
`AGENTS.md` name, so any future agent tool finds the same rules.

## Team and process

- You work inside a defined team: [docs/process/agent-team.md](docs/process/agent-team.md).
  The main session is the **Orchestrator**. Subagents live in `.claude/agents/`.
- Findings go Researcher/Runtime Observer → **Evidence Auditor** → **Provenance
  Guard** → Orchestrator commits. Never skip the reviews for research content.
- Branch, commit, and push rules (H1–H13) are enforced by hooks:
  [docs/process/workflow.md](docs/process/workflow.md). If a hook blocks you,
  fix the cause or raise it with the Project Lead. Never bypass it.
- Pull requests follow the staged handover in
  [docs/process/pr-handover.md](docs/process/pr-handover.md). Check the current
  stage before opening or drafting a PR.

## Project phase

Re-Sieged is in the **research phase** ([ROADMAP.md](ROADMAP.md)). Unless the
user explicitly asks otherwise:

- Do **not** scaffold engine/runtime source code, module trees, build systems or
  class hierarchies.
- Do produce research documents, evidence records, reproducible analysis
  scripts, and decision records.
- Adding a directory needs a reason. Only create one when you have real content
  to put in it.

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
   print the private-terms list.
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

- Commit messages: `<Area>: <imperative summary>` (e.g. `Research: Add Tank header evidence record`),
  plus a `Co-Authored-By:` trailer on AI-made commits.
- Update `CHANGELOG.md` under *Unreleased* for notable documentation or process
  changes.
- Keep `docs/handoff/` files unedited. They are historical. Put corrections in
  the claims register.

## AI-specific rule

Your own trained "knowledge" of DS2 internals is **not evidence**. Any such
claim needs an observation-backed evidence record. See
[AI-DISCLOSURE.md](AI-DISCLOSURE.md).

