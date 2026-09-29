# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Research-phase documentation system: method, claims register, open questions,
  research plan and ecosystem/provenance tracker (`docs/research/`).
- Decision records ADR-0001 (research before architecture) and ADR-0002
  (repository content policy).
- Archived the original Codex research handoff unedited in `docs/handoff/`.
- Content for README, ROADMAP, TODO, CONTRIBUTING and agent instructions.
- `AI-DISCLOSURE.md`.
- Five-role agent team with hierarchy (`docs/process/agent-team.md`) and
  subagent definitions in `.claude/agents/`.
- Repository policy rules H1–H9, enforced by one script (`tools/checks/policy.py`)
  through three layers: Claude Code hooks (`.claude/settings.json`), git hooks
  (`.githooks/`) and CI (`.github/workflows/policy.yml`).
- Staged PR handover plan (`docs/process/pr-handover.md`) and PR template.
- `.gitattributes` forcing LF line endings for hooks and scripts, so they work on Windows.
- `.gitignore` that blocks proprietary game formats and local research output.

### Changed
- Moved `.claude/AGENTS.md` to the repository root under the tool-neutral name.
  `CLAUDE.md` imports it.
- Native Windows is the primary environment and the first target platform;
  WSL is no longer used.
- Codex is no longer part of the project. Runtime observation is done by the
  project lead using Runtime Observer protocols.

## 0.0.0 - Initial scaffold
- Empty placeholder files (`70c9f84`).
