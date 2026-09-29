# Pull requests: gradual handover to the Project Lead

- **Status:** Accepted (2026-09-29).
- **Goal:** you start by watching Claude make PRs and end by making them
  yourself, with Claude reviewing, so you stay honest and correct.

## Why a PR is more than a button

A PR is a claim: *"this change is correct, complete, and what I say it is."*
The skills involved are: scoping one topic per PR, writing a description that
says what was **not** done, checking the diff yourself, reading CI, and
responding to review. We hand these over one at a time.

## The stages

| Stage | Who opens the PR | Who writes the description | Who reviews | Your focus while learning |
| --- | --- | --- | --- | --- |
| **1. Watch** | Claude | Claude | You approve & merge; Claude explains each part as it goes | What a good description contains; reading a diff; what CI checks |
| **2. Assist** | You, following Claude's step-by-step instructions | Claude drafts, you edit | You merge after Claude points out what to check | Branch → push → open PR mechanics; using the template |
| **3. Lead** | You | You | Claude reviews for accuracy and honesty; you fix and merge | Scoping; stating limits honestly; the honesty checklist |
| **4. Own** | You | You | Claude reviews on request, or for research/claims PRs | Independent judgment. Claude still flags anything overstated |

**Current stage: 1 (Watch).**

## Moving to the next stage

You decide when to move up. Suggested signal: **three PRs in a row** at the
current stage where Claude's review found no *substantive* issue. A substantive
issue is a wrong fact, an overstated claim, a missing limitation, or content
that should not be there. Typos don't count. You can move back a stage at any
time with no penalty.

Record each change of stage here:

| Date | From → To | Note |
| --- | --- | --- |
| 2026-09-29 | — → 1 | Starting point |

## What Claude checks when reviewing your PRs (stages 3–4)

1. Does the description match the diff? Nothing missing, nothing extra.
2. Are claims stated at the right confidence, with negatives classified?
3. Is what was *not* done or verified stated?
4. Is the honesty checklist in the PR template honestly ticked?
5. Content policy and provenance.
6. Is CI green, and if not, is the reason understood?

Claude reviews **candidly**. The point is to catch mistakes before they become
"facts" in the project, not to be polite.
