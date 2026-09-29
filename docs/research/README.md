# Research method

This directory holds everything Re-Sieged knows about DS2/BW, and how
confident we are in it.

| File | What it is |
| --- | --- |
| [plan.md](plan.md) | Workstreams, priorities, runtime transactions |
| [claims-register.md](claims-register.md) | Every factual claim, with its confidence and source (`CLM-###`) |
| [open-questions.md](open-questions.md) | Explicit unknowns, and what would resolve each (`Q-###`) |
| [ecosystem.md](ecosystem.md) | External projects, their licenses, and provenance of any reuse |
| `evidence/` | Detailed evidence records (`EV-###`), added as findings are made |

## The research chain

Architecture must come out of evidence, in this order:

```text
OBSERVED DATA → REFERENCE → SEMANTIC MEANING → NATIVE DEPENDENCY → RE-SIEGED REQUIREMENT
```

Skipping a link, for example going from a filename straight to a module design,
is the main failure mode this system exists to prevent.

## Confidence levels

| Level | Meaning |
| --- | --- |
| **Confirmed** | Directly observed in this project with a recorded, reproducible method |
| **Strong** | Several independent observations agree; small room for a different reading |
| **Plausible** | Consistent with the evidence, but not directly established |
| **Unknown** | Not established. Do not build on it |

Verification status is tracked **separately** from confidence:

- **Reported:** comes from the 2026-09 handoff and has not been re-checked yet.
- **Verified:** re-established in this repository with an evidence record.

A *Reported / Strong* claim is a good lead. It is not a foundation.

## Classifying negative results

Always say which kind of negative result you have. These four are **not** interchangeable:

| Class | Example |
| --- | --- |
| Environment limitation | WSL interop failed, so the game could not be launched |
| Search limitation | grep found no stance assignment in the files we scanned |
| Evidence of absence | A complete, verified scan of all 510 Skrit files finds no X |
| Observed absence | At runtime, the behavior clearly does not occur |

## Evidence record template

Save as `evidence/EV-###-short-slug.md`:

```markdown
# EV-###: <title>

- **Date:** YYYY-MM-DD
- **Game version:** DS2 2.30.0.0 (Steam build 21154) / BW …
- **Environment:** Windows 10.0.26200 / …
- **Related:** CLM-###, Q-###

## Finding
What was observed.

## Source
Exact file / resource path / tool + version / location.

## Method
How it was established. Link to the script if one was used.

## Confidence
Confirmed / Strong / Plausible / Unknown, with the reason.

## Implication
What this means for Re-Sieged.

## Does NOT prove
Important limits on what this shows.

## Next verification
What would settle the remaining uncertainty.
```

## Quoting game content

Keep quotations minimal: identifiers, paths, field names, a line or two when
the exact text matters. Never paste whole files. Summaries, counts and
structure are always fine.
