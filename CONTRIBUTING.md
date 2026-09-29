# Contributing to Re-Sieged

Re-Sieged is a clean-room project in its research phase. The most useful
contributions right now are **verified observations** about how Dungeon Siege II
and Broken World behave. Code is not the priority yet.

## Clean-room rules

- Work only from your own legitimately owned copy of the game, public
  documentation, and openly licensed community tools.
- Never use, read for reference, or link to leaked source code.
- Never commit game content (see [ADR-0002](docs/decisions/0002-repository-content-policy.md)).
  `.gitignore` blocks the common formats, but you are still responsible for what
  you commit.
- If a finding came from another project's code or docs, record it in
  [docs/research/ecosystem.md](docs/research/ecosystem.md).

## Submitting a finding

1. Check the [claims register](docs/research/claims-register.md) and
   [open questions](docs/research/open-questions.md) first.
2. Write an evidence record using the template in
   [docs/research/README.md](docs/research/README.md). Include your game version
   (e.g. `DS2 2.30.0.0, Steam build 21154`) and the exact method you used.
3. Update the claim's confidence, or add a new claim, and link the record.
4. If a negative result, say which kind it is: environment limitation, search
   limitation, evidence of absence, or observed absence.

## Analysis scripts

Scripts that scan a local game install must:

- read game files from a path the user supplies, and never from inside the repo;
- write raw output to `local/` (git-ignored);
- produce committable output that contains only **derived facts** such as
  counts, identifiers, structure, and hashes, not copied content;
- be deterministic, so someone else with the same game version gets the same
  result.

## Commits and pushes

First, once per clone: `git config core.hooksPath .githooks` (requires Python 3).

Subject format: `<Area>: <imperative summary>`. Areas: `Docs`, `Research`,
`Decision`, `Tools`, `Repo`, `Planning`, `Process`. Never push to `main`; open a
pull request. The full rules and the reasons for them are in
[docs/process/workflow.md](docs/process/workflow.md).
