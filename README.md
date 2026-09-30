# Re-Sieged

> Make **Dungeon Siege II + Broken World** feel like a modern, native action RPG
> while keeping DS2/BW's identity, content, systems, progression and spirit.

Re-Sieged aims to be a modern runtime for Dungeon Siege II. You supply your own
legally owned copy of the game. Re-Sieged prepares what it needs from that copy
on your machine and runs the game with a modern renderer, a controller-first
interaction model, and support for Steam Deck, Linux and current PCs.

## Status: research phase

**There is no runnable code yet, and that is on purpose.**

Earlier reconnaissance showed that DS2 is not just a pile of assets drawn by a
Direct3D 9 executable. It is layered:

```text
Tank resources  →  GAS templates/components  →  Skrit behavior  →  native services  →  live world
```

The hardest open question is where the **authored content** (GAS, Skrit, maps)
ends and the **native engine services** begin. Re-Sieged's architecture depends
on that boundary, so we are mapping it from evidence before designing anything.
Research notes are kept locally for now and will be published as guides once
they are verified.

## What this repository contains

| Path | Purpose |
| --- | --- |
| [`ROADMAP.md`](ROADMAP.md) | Phases and the gates between them |
| [`tools/checks/`](tools/checks/policy.py) | Repository policy checks (used by Claude hooks, git hooks and CI) |
| [`.claude/agents/`](.claude/agents/) | The AI agent team definitions |
| [`AGENTS.md`](AGENTS.md) | Rules for AI agents working in this repo |
| [`AI-DISCLOSURE.md`](AI-DISCLOSURE.md) | How AI is used, and the clean-room safeguards |

## What this repository will never contain

It will never contain original game executables, DLLs, Tank archives
(`.ds2res`, `.ds2map`), extracted assets, maps, audio, video, or any leaked or
proprietary source code.

## Relationship to other projects

Re-Sieged is a clean-room project. It is not affiliated with Gas Powered Games,
Microsoft or any rights holder. Related community projects are tracked internally
along with their licenses. No external code has been adopted yet.

## License

**Not yet chosen.** This decision is tracked as an open question because it
limits which reference implementations (GPL, AGPL, MIT) we can reuse.
