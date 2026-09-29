# ADR-0001: Research before architecture

- **Status:** Proposed
- **Date:** 2026-09-29

## Context

Re-Sieged's hardest question is how much DS2 behavior lives in authored
content (GAS, Skrit, maps) and how much lives in opaque native services. Prior
research made progress but left key points unknown: how `inventory.animstance`
is derived, how Skrit binds to native code, how actors are constructed, and
what the save schema is. An architecture designed now would have to guess at
exactly the boundary that matters most.

## Decision

No runtime/engine source scaffold, module tree or build system until the
ROADMAP Phase 3 exit criteria are met and a Phase 4 architecture is accepted.
Throwaway research tools are allowed and are explicitly not architecture.

## Consequences

- Progress looks slow at first, because the output is documents and evidence.
- Architecture decisions will cite evidence (`CLM`/`EV`/`Q` IDs).
- We avoid a "generic engine" drifting away from DS2's real behavior.

## Alternatives considered

- **Scaffold from the feature list now:** rejected. Its boundaries would come
  from feature names, not from DS2 semantics.
- **Prototype a renderer first:** deferred. It is useful for motivation, but it
  says nothing about the semantic boundary.
