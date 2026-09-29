# Agent instructions (Claude, Codex, and others)

This file is the single source of rules for AI agents in this repository.
`CLAUDE.md` imports it. It lives at the repository root because that is where
Codex looks for it.

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
4. **No legal conclusions.** You may record legal *questions* and *precedents*,
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

- **Linux/WSL/cloud:** static analysis, scripting, documentation. There is no
  game install here unless the user provides one.
- **Native Windows (`C:\Dev\Re-Sieged`):** runtime observation only. Use
  black-box methods: no patching, injection, hooks, or memory modification
  (see [research plan](docs/research/plan.md)).

## Working conventions

- Commit messages: `<Area>: <imperative summary>` (e.g. `Research: Add Tank header evidence record`).
- Update `CHANGELOG.md` under *Unreleased* for notable documentation or process
  changes.
- Keep `docs/handoff/` files unedited. They are historical. Put corrections in
  the claims register.

## AI-specific rule

Your own trained "knowledge" of DS2 internals is **not evidence**. Any such
claim needs an observation-backed evidence record. See
[AI-DISCLOSURE.md](AI-DISCLOSURE.md).

## Planning drafts (not yet in force)

The agent roster and hierarchy ([docs/planning/agent-team.md](docs/planning/agent-team.md))
and the enforcement hooks ([docs/planning/workflow-and-hooks.md](docs/planning/workflow-and-hooks.md))
are proposals. Do not implement them until they are accepted.
