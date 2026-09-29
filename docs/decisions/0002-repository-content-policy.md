# ADR-0002: Repository content policy

- **Status:** Proposed
- **Date:** 2026-09-29

## Context

Re-Sieged ships software. The user supplies the game. Committing game content,
even by accident, creates legal risk and undermines the clean-room position.

## Decision

The repository may contain: original code, documentation, schemas, tests with
synthetic fixtures, research notes with minimal quotations, and derived facts
(counts, identifiers, structure, hashes).

The repository must never contain: game executables/DLLs, Tank files,
extracted assets (models, textures, audio, video, maps), bulk extracted
GAS/Skrit, ISOs, leaked or proprietary source, or unrelated proprietary
content.

Enforcement: `.gitignore` is the convenience layer. Claude hooks, git hooks and
CI enforce rules H1–H3 ([workflow](../process/workflow.md)).

## Consequences

- Test fixtures must be synthetic, e.g. a hand-built tiny Tank file.
- Research scripts write raw output to the git-ignored `local/` directory.
