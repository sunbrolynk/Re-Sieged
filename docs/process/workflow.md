# Workflow: branches, commits, pushes and enforcement

- **Status:** Accepted (2026-09-29): all three enforcement layers active.

## The rules

| # | Rule | Enforced by |
| --- | --- | --- |
| H1 | Proprietary game file types are never committed (`.ds2res`, `.ds2map`, `.exe`, `.dll`, `.asp`, `.prs`, `.dds`, …) | Claude · Git · CI |
| H2 | No single file over 1 MB | Git · CI |
| H3 | No bulk-pasted GAS/Skrit (15+ template headers or Skrit-style lines added to one file) | Git · CI |
| H4 | Files in `docs/handoff/` may be added, never changed | Claude · Git · CI |
| H5 | Commit subject is `<Area>: <summary>`. Area is one of `Docs`, `Research`, `Decision`, `Tools`, `Repo`, `Planning`, `Process`. AI-made commits carry a `Co-Authored-By:` trailer | Git · CI |
| H6 | No direct push to `main`, no force-push, no `--no-verify`. Agents do not commit on `main` | Claude · Git · GitHub branch protection |
| H7 | Accepted ADRs are superseded, not edited | Git · CI (warning) |
| H8 | `CHANGELOG.md` is updated when `docs/` or `tools/` change | CI (warning) |
| H9 | Relative Markdown links resolve | CI (warning) |

## Why three layers

| Layer | File(s) | Protects against | Can be bypassed by |
| --- | --- | --- | --- |
| **Claude hooks** | `.claude/settings.json` | Claude doing something *before* it happens (runs on every Bash/Write/Edit call) | Anyone not using Claude |
| **Git hooks** | `.githooks/*` | Anyone committing on a clone where hooks are enabled | `--no-verify`, or hooks not enabled |
| **CI** | `.github/workflows/policy.yml` | Everything that reaches GitHub | Nothing, once branch protection requires it |

All three call **one script**, [`tools/checks/policy.py`](../../tools/checks/policy.py).
A rule is therefore written once and cannot drift between layers. That is the
architectural point: *single source of truth, multiple enforcement points*.

## One-time setup (you)

1. **Enable git hooks in your clone** (`C:\Dev\Re-Sieged`):
   ```sh
   git config core.hooksPath .githooks
   ```
   Claude sessions do this automatically through the SessionStart hook.
   Requires Python 3 on the PATH.
2. **Protect `main` on GitHub:** Settings → Branches → Add rule for `main`:
   - Require a pull request before merging
   - Require status checks to pass → select **Repository policy / policy**
   - Do not allow force pushes or deletions

   Until you do this, CI reports problems but cannot block a merge.

## Day-to-day flow

```text
1. Branch      git switch -c <you>/<topic>      (Claude uses claude/<topic>)
2. Work        small commits, each with a proper subject
3. Push        git push -u origin <branch>      (hooks run first)
4. PR          see pr-handover.md for who writes it at your current stage
5. CI          "Repository policy" must be green
6. Review      Claude reviews your PRs; you review Claude's
7. Merge       only you merge to main
```

## When a hook blocks you

Read the `[H#]` code and fix the cause. If you believe the rule is wrong for
this case, say so and we change the rule in `policy.py` in its own PR. Do not
bypass it with `--no-verify`.
