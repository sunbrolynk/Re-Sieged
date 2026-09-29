# CLAUDE.md

All agent rules live in [AGENTS.md](AGENTS.md) so that Claude and Codex follow
the same instructions.

@AGENTS.md

## Claude-specific notes

- Prior research sessions are **not** remembered between sessions. Treat
  `docs/research/` as the memory, and update it when you learn something.
- The user is a newer programmer who wants production-quality architecture and
  wants to understand the reasons behind it. When you propose a structure,
  explain which boundary it enforces (ownership, lifetime, dependency direction,
  testability, security, provenance, and so on).
