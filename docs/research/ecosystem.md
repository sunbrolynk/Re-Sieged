# Ecosystem and provenance

External projects relevant to Re-Sieged. **No external code has been adopted.**
License details below are *as reported* in the handoff (H§6) and must be
verified (with the repo URL, commit and date) before anyone relies on them.

## Projects

| Project | Scope | License (reported) | Relevance | Verified |
| --- | --- | --- | --- | --- |
| OpenSiege | Open engine for DS1 + Legends of Aranna | GPL-3.0 | Precedent for a DS1 runtime; not DS2 | ☐ |
| glampert/dungeon-siege-re | DS1/LoA Tank, RAW, partial ASP/SNO conversion | MIT | Format reference | ☐ |
| Siege Control | DS1/DS2 Tank browse/extract; tested on DS2 2.30.0.0 | App AGPL-3.0; contains Lampert-derived MIT code; NetMiniZ MIT | Tank structure reference | ☐ |
| DS2 Tank Editor | DS2 Tank extract/create | ? | Tank reference | ☐ |
| DS2 Enhancement Proxy | D3D9 proxy (filtering, view distance, borderless) | ? | Shows visuals can be layered around the original | ☐ |
| Enhanced Shaders for DS2 | dgVoodoo2 + ReShade | ? | Visual precedent | ☐ |
| OpenSpy / DS2 MP restoration | GameSpy replacement | ? | Networking reference | ☐ |
| Dungeon Siege 2 Resurrected | Community restoration | ? | **Unverified lead** | ☐ |
| SiegeFX | Clean-room DS1 runtime, C# | GPL-3.0-only | Clean-room method precedent; excludes leaked DS1 source | ☐ |

## Why licenses matter now

If we reuse code from a GPL-3.0 or AGPL-3.0 project, Re-Sieged's own license
must be compatible with it (Q-043). Reading a project's *documentation* for
format facts is a different matter from copying its *code*. Either way, record
what was used.

## Provenance log

Add an entry for **every** borrowed piece of code, algorithm or non-trivial
fact taken from another project:

| Date | What | From (URL @ commit) | License | Used how (copied / adapted / reference only) | Where in Re-Sieged |
| --- | --- | --- | --- | --- | --- |
| _none yet_ | | | | | |
