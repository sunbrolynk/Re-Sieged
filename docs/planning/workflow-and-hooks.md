# Workflow rules and enforcement hooks (DRAFT, for discussion)

> **Status: proposal.** No hooks are installed yet. This describes what we would
> enforce, and where each check would run.

## Why three enforcement layers

| Layer | Covers | Weakness |
| --- | --- | --- |
| **Claude Code hooks** (`.claude/settings.json`) | Claude sessions only; can block a tool call *before* it happens | Codex and humans bypass it |
| **Git hooks** (`.githooks/`, enabled via `git config core.hooksPath .githooks`) | Anyone committing on a machine where they are enabled | Opt-in per clone; `--no-verify` skips them |
| **CI on GitHub** (Actions + branch protection) | Everything that reaches GitHub | Only catches problems after the push |

Rules that matter, such as "no game content", go into **all three**. The same
check script (`tools/checks/…`) would be called from each layer, so the logic
lives in one place.

## Proposed branch and push rules

1. `main` is protected: no direct pushes, PRs only, you merge.
2. Work happens on `claude/…`, `codex/…` or `<you>/…` branches.
3. One topic per branch/PR, e.g. "Tank format evidence".
4. Commit message format: `<Area>: <imperative summary>`, where Area is one of
   `Docs|Research|Decision|Tools|Repo|Planning`.
5. AI-assisted commits carry attribution trailers (see [AI-DISCLOSURE](../../AI-DISCLOSURE.md)).
6. PRs that change `docs/research/claims-register.md` must link an EV record.

## Proposed checks

| # | Check | Blocks? | Claude hook | Git hook | CI |
| --- | --- | --- | --- | --- | --- |
| H1 | No proprietary file types staged (`.ds2res`, `.exe`, `.dll`, `.asp`, `.prs`, …) | Yes | PreToolUse on `git commit` | pre-commit | ✓ |
| H2 | No large binary files (e.g. over 1 MB) without an explicit allowlist | Yes | PreToolUse | pre-commit | ✓ |
| H3 | Content heuristics: GAS/Skrit block patterns pasted in bulk (e.g. many `[t:template` lines) | Warn → Yes | PreToolUse | pre-commit | ✓ |
| H4 | `docs/handoff/` files are immutable after being added | Yes | PreToolUse on Write/Edit | pre-commit | ✓ |
| H5 | Commit message format and AI trailer present when AI-authored | Yes | PreToolUse | commit-msg | ✓ |
| H6 | No push to `main`, no force-push | Yes | PreToolUse on `git push` | pre-push | branch protection |
| H7 | Accepted ADRs are not edited, only superseded | Warn | PreToolUse | pre-commit | ✓ |
| H8 | CHANGELOG touched when `docs/` or `tools/` change | Warn | Stop hook reminder | — | ✓ (warn) |
| H9 | Markdown links resolve | Warn | — | — | ✓ |
| H10 | Session start: print current phase, open P1 questions, and branch | Info | SessionStart | — | — |

## Decisions we need to make together

1. Do we build all three layers now, or start with Claude hooks + CI and add
   git hooks later?
2. Which checks block, and which only warn?
3. Should Claude be allowed to open PRs on its own, or only push branches for
   you to open them?
4. What language should the check scripts use? Python works everywhere
   (WSL/Windows/CI); bash does not run natively on Windows.
5. Do you want signed commits?
