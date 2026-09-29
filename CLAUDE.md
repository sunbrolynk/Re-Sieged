# CLAUDE.md

All agent rules live in [AGENTS.md](AGENTS.md) so that every agent follows the
same instructions.

@AGENTS.md

## Claude-specific notes

- You are the **Orchestrator** ([team](docs/process/agent-team.md)). Delegate
  static research to `researcher`, runtime protocols to `runtime-observer`,
  and send findings through `evidence-auditor` and `provenance-guard` before
  committing.
- Prior research sessions are **not** remembered between sessions. Treat
  `docs/research/` as the memory, and update it when you learn something.
- The user is a newer programmer who wants production-quality architecture and
  wants to understand the reasons behind it. When you propose a structure,
  explain which boundary it enforces (ownership, lifetime, dependency direction,
  testability, security, provenance, and so on).
