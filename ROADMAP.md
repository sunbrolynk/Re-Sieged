# Roadmap

Re-Sieged moves through **gated phases**. A phase ends when its exit criteria
are met, not on a date. Each gate is recorded as a decision in
[`docs/decisions/`](docs/decisions/README.md).

```text
Phase 0  Research foundation      ◀── we are here
Phase 1  Static verification
Phase 2  Runtime observation
Phase 3  Semantic boundary map
Phase 4  Architecture definition
Phase 5  Implementation scaffold
```

---

## Phase 0: Research foundation

Turn the prior handoff into a durable, checkable research system.

- [x] Archive the original handoff unedited in `docs/handoff/`
- [x] Research method: confidence levels, evidence record format, failure classification
- [x] Claims register seeded from the handoff (every claim marked *reported, unverified*)
- [x] Open-questions register
- [x] Research plan with workstreams and runtime transactions
- [x] Content policy and research-first decisions (ADR-0001, ADR-0002)
- [ ] Verify ecosystem project licenses and record them with dates/commits

**Exit:** a new agent or contributor can learn what is known, how confident we
are, and what to do next without the chat history.

## Phase 1: Static verification

Re-check the handoff's claims against a real install using **reproducible
scripts** whose committed output contains only derived facts.

- Re-verify executable identity (hashes, PE facts, imports)
- Tank container: header and index structure, documented from our own observations
- Re-run the Skrit corpus survey as a script (calls, events, namespaces)
- Re-trace the `hero_human_male` dependency closure
- Inventory Broken World resources and diff them against base DS2

**Exit:** every *Strong* claim in the register cites a reproducible method, or
has been downgraded.

## Phase 2: Runtime observation

Black-box observation on native Windows. No patching or injection.

- Transactions A–C (equipment→animation, movement→animation, damage→death)
- Optional D–E (interaction, AI/job)
- Save file structure observed before and after controlled actions

**Exit:** the priority unknowns in `open-questions.md` are each resolved or
explicitly classified as unobservable by black-box methods.

## Phase 3: Semantic boundary map

For each area (initialization, equipment, movement, animation, life/death,
interaction, AI, effects, world, saves), write down:

- what the authored content supplies,
- what the runtime must provide (as an observable contract, not an
  implementation), and
- how compatible Re-Sieged needs to be: data, asset, script, save, behavioral,
  or native plugin.

**Exit:** a minimum runtime semantic surface we can state with evidence behind
it, plus a recommended content/import model (direct, import, hybrid,
executable-assisted, or other).

## Phase 4: Architecture definition

Only now: runtime language/platform choices, module boundaries, Skrit strategy
(VM, translation, or reauthoring), rendering and input boundaries, security
model at the import boundary, and project license. Each gets an ADR.

**Exit:** architecture reviewed and accepted.

## Phase 5: Implementation scaffold

Build system, CI, first vertical slice. The likely first slice is to
load one actor from a user-supplied install and show it animating. The slice
will be chosen by Phase 3 evidence.

---

## Product targets (unchanged; guide research priorities, not architecture)

Modern renderer · 4K/ultrawide/high refresh · resolution-independent UI ·
**native controller-first interaction** (not rebinding) · Steam Deck/Linux ·
x86 handhelds · better frame pacing · modern saves/settings/audio/loading ·
modern combat feedback · possible future consoles.
