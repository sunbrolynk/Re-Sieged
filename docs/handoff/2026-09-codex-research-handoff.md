# Re-Sieged --- Project Research & Architecture Handoff

**Purpose:** This document is the complete research/archaeology handoff
for starting the Re-Sieged project with a fresh, essentially empty
repository. It consolidates the findings from the initial project
reconnaissance, Dungeon Siege II file archaeology, authored-content
dependency tracing, Skrit/API surface investigation, runtime-boundary
investigation, environment reconnaissance, and architectural
conclusions.

**Important:** Treat this document as an evidence-backed starting point,
not as a finished architecture or an instruction to begin implementation
immediately. Where something is marked **UNKNOWN**, it was deliberately
not inferred. Verify important conclusions against the original game
and/or additional primary evidence before building around them.

------------------------------------------------------------------------

# 1. Project Identity

## Project

**Name:** Re-Sieged

**Repository:** `https://github.com/Sunbrolynk/Re-Sieged`

**Local repositories previously used:** - WSL:
`/home/sunbrolynk/Re-Sieged` - Windows: `C:\Dev\Re-Sieged`

The intended clean starting point for the Claude handoff is the Git
repository containing only the initial project scaffold/0-byte-style
documentation copies. The research in this document is the durable
knowledge that should survive independently of the previous WSL working
artifacts.

## Product goal

> **Make Dungeon Siege II + Broken World feel like a modern native
> action RPG while preserving DS2/BW's identity, content, systems,
> progression, and spirit.**

This is not intended to turn Dungeon Siege II into a different game. The
goal is to modernize the experience and runtime while retaining the
authored game and its recognizable systems.

## Desired experience

The target is a modern, native-feeling action RPG experience, with
references to modern Diablo-like usability where useful, but without
copying Diablo's design.

Desired qualities include:

-   modern renderer
-   modern GPU support
-   high resolutions including 4K
-   ultrawide support
-   high-refresh support
-   modern shaders/effects where technically appropriate
-   improved/high-quality texture/material handling
-   resolution-independent UI
-   native controller-first UX
-   analog movement
-   controller-native targeting
-   controller-native abilities
-   modern inventory/equipment flows
-   handheld-friendly UI and interaction
-   Steam Deck/Linux support
-   x86 handheld PC support
-   PC support
-   possible future console support if feasible
-   better frame pacing
-   modern save/settings behavior
-   modern loading/audio behavior
-   modern combat feedback

### Critical UX distinction

The controller experience should **not** merely be the existing
mouse/keyboard game with controller bindings pasted on top.

The desired result is a **native controller-first interaction model**.

Likewise, "modern ARPG" describes the target experience, not a
predetermined architecture.

------------------------------------------------------------------------

# 2. Desired Distribution / Import Model

The intended user experience is broadly similar to the way some modern
reimplementation ecosystems work:

1.  User legally owns/acquires the original game.
2.  User points Re-Sieged at their legitimate game installation/files.
3.  Re-Sieged locally extracts/imports/converts/translates/prepares what
    it needs.
4.  Re-Sieged provides the modern runtime and experience.
5.  The user does not need to understand the technical conversion
    process.

The project should ship the **software**, not the original copyrighted
game content.

Do not assume the exact implementation model yet.

Potential models that were identified:

-   **A. Direct compatibility**
-   **B. Local import/conversion**
-   **C. Hybrid**
-   **D. Executable-assisted**
-   **E. Another model discovered during research**

The desired user experience is established; the technical distribution
model remains an architectural/legal research question.

### Explicit non-goals for repository contents

Do not put the following into the Git repository:

-   Dungeon Siege II executable
-   Broken World executable
-   original DLLs
-   Tank archives
-   extracted proprietary assets
-   original maps
-   original models
-   original textures
-   original audio
-   original video
-   ISO images
-   proprietary source code
-   leaked source
-   extracted copies of Nintendo/other unrelated proprietary content
-   other copyrighted game material

The repository should contain software, documentation, tooling,
clean-room research, schemas, tests, and other material that can legally
be distributed.

------------------------------------------------------------------------

# 3. Existing Repository State

The repository began essentially empty.

Initial scaffold consisted of:

-   `.claude/AGENTS.md`
-   `.gitignore`
-   `CHANGELOG.md`
-   `CLAUDE.md`
-   `CONTRIBUTING.md`
-   `README.md`
-   `ROADMAP.md`
-   `TODO.md`
-   `docs/`

At the relevant point:

-   `main` and `origin/main` were at commit `70c9f84`
-   commit message: `Docs: Added initial project scaffolding`

Previous archaeology created local/untracked material in WSL and
Windows, but that material is intentionally **not required for this
handoff**.

The important research findings are consolidated here so Claude can
begin from the clean repository.

------------------------------------------------------------------------

# 4. Architectural Philosophy

The user is a relatively new programmer but explicitly wants
**professional, serious, production-level architecture**.

The desired priority is:

1.  architecture
2.  organization
3.  convenience

The project should not be organized merely because a folder structure
"looks professional."

Every boundary should have an explainable purpose:

-   ownership
-   lifetime
-   dependency direction
-   responsibility
-   testability
-   security
-   provenance
-   compatibility
-   replaceability
-   platform abstraction
-   data flow

The user wants to understand the **why and what-for** of architecture
rather than blindly receiving a framework.

## Important constraint

Do **not** prematurely scaffold a giant architecture based only on the
desired feature list.

Architecture should emerge from evidence.

The preferred research chain is:

``` text
OBSERVED DATA
      ↓
REFERENCE
      ↓
SEMANTIC MEANING
      ↓
NATIVE DEPENDENCY
      ↓
RE-SIEGED REQUIREMENT
```

Do not infer architecture/classes/modules from filenames merely because
their names sound appropriate.

------------------------------------------------------------------------

# 5. Fundamental Technical Question

The most important question discovered during archaeology is:

> **Can Re-Sieged preserve enough DS2/BW game semantics---scripts,
> actors, state, maps, saves, and useful mod behavior---to let a new
> interaction/rendering model take over without ceasing to be
> recognizably DS2/BW?**

The key architectural issue is the size and shape of the native semantic
layer between authored game content and the original executable.

A useful conceptual model is:

``` text
DS2 native executable
  rendering
  networking
  saves
  object systems
  engine services
        ↓
engine APIs/services
        ↓
Skrit + GAS
  definitions
  formulas
  behavior
  events
  game-object interaction
        ↓
Tank/map resources
  world
  terrain
  objects
  logic
  sound
  voices
  movies
```

The central unknown is how much behavior lives in:

-   authored GAS
-   authored Skrit
-   resource formats
-   engine services
-   opaque native runtime behavior

If the native semantic layer is reasonably well-defined, Re-Sieged
increasingly resembles a clean-room runtime/reimplementation problem.

If ordinary actors depend heavily on opaque native behaviors that cannot
be reconstructed from authored content and observable behavior, the
project becomes significantly harder.

------------------------------------------------------------------------

# 6. Existing Ecosystem Research

The following projects/resources were identified during reconnaissance.

## OpenSiege

-   Open engine replacement for Dungeon Siege 1 + Legends of Aranna
-   GPL-3.0
-   DS1 focus
-   useful as ecosystem/reference precedent
-   not a DS2 runtime

## glampert/dungeon-siege-re

-   MIT
-   DS1/LoA Tank/RAW/partial ASP/SNO conversion work
-   useful format/reference material
-   no complete DS2 runtime

## Siege Control

-   DS1/DS2 Tank browsing/extraction tooling
-   tested against DS2 2.30.0.0
-   useful for understanding DS2 Tank structure
-   not a runtime
-   source is AGPL-3.0 for the application
-   contains a separate MIT notice for Lampert-derived code
-   NetMiniZ code is MIT
-   provenance/license tracking is required before reusing any code

## DS2 Tank Editor

-   DS2 Tank archive extraction/creation tooling
-   useful reference

## DS2 Enhancement Proxy

-   D3D9 proxy/plugin ecosystem
-   filtering/view distance/borderless/ReShade-style enhancements
-   useful evidence that substantial visual modernization can be layered
    around the original runtime
-   not a new runtime

## Enhanced Shaders for DS2

-   dgVoodoo2 + ReShade-oriented enhancement
-   useful precedent for visual modernization

## OpenSpy / DS2 multiplayer restoration

-   useful networking ecosystem/reference

## Dungeon Siege 2 Resurrected

-   community restoration project was identified
-   claims, source/license status, and technical coverage were not
    independently verified during the archaeology
-   treat as a research lead, not established technical fact

## SiegeFX

-   clean-room DS1 C# runtime
-   GPL-3.0-only
-   explicitly excludes leaked DS1 source
-   useful clean-room precedent

### Main ecosystem gap identified

There are tools and enhancement layers, but the major unsolved area
appears to be:

> **integration + behavioral compatibility**

Especially:

-   authored content semantics
-   runtime object behavior
-   Skrit/native API behavior
-   maps
-   saves
-   AI
-   controller-native interaction
-   modern rendering/runtime integration

------------------------------------------------------------------------

# 7. Dungeon Siege II Installation Evidence

Dungeon Siege II was installed from Steam and was available for
archaeology.

Previously observed executable:

``` text
C:\Program Files (x86)\Steam\steamapps\common\Dungeon Siege 2\DungeonSiege2.exe
```

Properties:

-   PE32
-   Intel 80386 / x86
-   Windows GUI
-   8,212,480 bytes
-   embedded version text:
    `Gas Powered Games Dungeon Siege II v2.30.0.0 * Configured as Retail`
-   Steam app ID: `39200`
-   Steam build ID: `21154`
-   PE timestamp metadata: `2011-01-12 17:33:39`
-   SHA-256:

``` text
0176da8839e7167cae59fa51200bf2c6c260e49a76cf9bf7c6c38c51052668ae
```

No game executable was modified.

## DS2VideoConfig.exe

Observed:

-   PE32 i386
-   1,769,472 bytes
-   SHA-256 begins:

``` text
6718a63c...
```

------------------------------------------------------------------------

# 8. Native Runtime Evidence

Dungeon Siege II is a 32-bit Windows application using Direct3D 9.

Observed imports included:

-   `d3d9.dll`
-   `d3dx9_29.dll`
-   `WSOCK32.dll`
-   `WINHTTP.dll`
-   `RASAPI32.dll`
-   `WINMM.dll`
-   `WINTRUST`
-   `USER32`
-   `ADVAPI32`
-   `SHELL32`
-   `ole32`
-   `OLEAUT32`
-   `VERSION`
-   `IMM32`
-   `GDI32`

It also references:

-   `mss32.dll`
-   `mssmp3.asi`
-   `msssoft.m3d`
-   `Msseax.m3d`
-   `binkw32.dll`

The PE image base was observed as:

``` text
0x00400000
```

The original runtime is therefore strongly tied to the
Windows/Direct3D9-era ABI.

### Controller caveat

No static `XInput` or `dinput8` import was found in the executable
during the initial scan.

This does **not** prove that controller support is absent; dynamic
loading or other mechanisms remain possible.

------------------------------------------------------------------------

# 9. DS2 Resource/Tank Evidence

The installed game contained:

``` text
Logic.ds2res
Movies1.ds2res
Movies2.ds2res
Objects.ds2res
Sound1.ds2res
Sound2.ds2res
Terrain.ds2res
Voices.ds2res
World.ds2map
```

Observed sizes:

``` text
Logic.ds2res    8,201,724
Movies1.ds2res  395,050,772
Movies2.ds2res  334,798,928
Objects.ds2res  252,058,884
Sound1.ds2res   372,936,868
Sound2.ds2res   74,783,360
Terrain.ds2res  469,455,976
Voices.ds2res   231,986,732
World.ds2map    222,243,176
```

All sampled first eight bytes were:

``` text
44 53 67 32 54 61 6e 6b
```

ASCII:

``` text
DSg2Tank
```

This establishes the common DS2 Tank signature.

------------------------------------------------------------------------

# 10. GAS Format Findings

GAS files are plain-text, structured data.

A representative `system_detail.gas` contains:

-   nested blocks
-   key/value fields
-   comments
-   rendering profiles
-   resolution settings
-   shader flags
-   shadow settings

Observed rendering profiles included:

-   `simple_render`
-   `shaders_on_default`
-   `no_standard_shaders`
-   `no_advanced_shaders`

GAS therefore appears to be an important authored-data layer for:

-   definitions
-   inheritance
-   configuration
-   gameplay values
-   component initialization
-   object templates

Do not assume every GAS field is interpreted entirely by Skrit. Some
fields clearly represent data consumed by native systems.

------------------------------------------------------------------------

# 11. Skrit Findings

Skrit is an authored scripting language/runtime layer.

Previous research found substantial evidence that Skrit is an
interpreted/scripted environment with engine-exposed functionality.

The executable references:

-   `*.skrit`
-   `autoexec.skrit`
-   `checkskrit`
-   `UISkritSupport`
-   `save_skrit_engine`
-   `world/contentdb/components/*.skrit`

Skrit interacts with native/game services through objects and APIs.

Important examples include:

-   `Mind`
-   `Inventory`
-   `MCPManager`
-   `Rules`
-   `GoDb`
-   `AIQuery`
-   `WorldTerrain`
-   `WorldFXMgr`
-   `QuestManager`
-   `Server`

------------------------------------------------------------------------

# 12. Skrit Corpus Survey

All **510 `.skrit` entries** in `Logic.ds2res` were extracted/scanned.

The scan found:

-   3,856 unique dotted call expressions

Important qualification:

> These are lexical call expressions, NOT a verified count of native
> APIs.

Examples of frequently used operations:

-   `MCPManager.MakeRequest`
-   `MCPManager.Flush`
-   `Mind.SDoJob`
-   `Inventory.SBeginUse`
-   `Inventory.SAutoUse`
-   `Inventory.SEndUse`
-   `Rules.ChangeLife`
-   `Rules.DamageGo`
-   `owner.UpdateBlender`
-   `owner.SetupStandardBoneAnimation`
-   Blender subanimation operations
-   `Inventory.GetAnimStance`
-   `Inventory.GetAnimStanceInt`
-   `GoDb.SMarkForDeletion`
-   `GoDb.StartWatching`
-   `GoDb.StopWatching`
-   `AIQuery.Get*`
-   `AIQuery.Is*`
-   `WorldTerrain.SRequestNode*`
-   `WorldFXMgr.Create*`
-   `WorldFXMgr.Attach*`
-   `WorldFXMgr.Destroy*`
-   world message operations
-   timers
-   multiplayer state

Lexical namespace method counts observed:

``` text
Mind          91
QuestManager  65
Inventory     57
WorldFXMgr    76
GoDb          31
Rules         32
AIQuery       28
WorldTerrain  10
MCPManager     9
Server        12
```

Again, these counts are useful for measuring the authored call surface,
not for declaring the final Re-Sieged API.

------------------------------------------------------------------------

# 13. Skrit Event / Message Surface

Scans found strong use of event/message-driven behavior.

Counts observed:

``` text
OnGoHandleMessage   770
OnTimer             574
OnWorldMessage      538
PostWorldMessage    156
SendWorldMessage    138
AnimEventBitTest    117
```

Frequently observed event tokens included:

``` text
WE_REQ_ACTIVATE
WE_REQ_DEACTIVATE
WE_REQ_USE
WE_REQ_CAST
WE_REQ_CAST_CHARGE

WE_ANIM_DONE
WE_ANIM_WEAPON_FIRE
WE_ANIM_SFX

WE_MCP_SECTION_COMPLETED
WE_MCP_DEPENDANCY_BROKEN
WE_MCP_INVALIDATED
WE_MCP_NODE_BLOCKED

WE_DAMAGED
WE_KILLED
WE_DESTRUCTED

WE_JOB_FINISHED
WE_JOB_DESTRUCTED
WE_REQ_JOB_END
```

A combined scan found roughly **232 unique** `WE_*`, `ANIMEVENT_*`,
`PL_*`, and `REQUEST_*` tokens.

This strongly suggests that an event/message semantic model is important
to the game.

------------------------------------------------------------------------

# 14. Skrit Binding Investigation

A dedicated search was performed for a definitive Skrit/native binding
layer.

Results:

-   no authoritative Skrit VM/API manual was found inside the inspected
    installation
-   no obvious dedicated native binding declaration file
-   no obvious `extern`/`builtin` declaration convention
-   no native method ID table
-   no generated binding table
-   no opcode/symbol registration table
-   no authoritative interface map for `Mind`, `Inventory`,
    `MCPManager`, etc.
-   no unresolved-symbol metadata
-   no complete native API documentation was found

The strongest documentation found was:

``` text
world/contentdb/components/components.gas
```

It documents the component system and indicates components can be
instantiated through engine/editor/native/script mechanisms.

It does **not** enumerate the native Skrit method binding surface.

The `k_*.skrit` files were checked as possible native wrappers. They are
authored Skrit wrappers, not proof of native binding.

### Current conclusion

The best classification is:

> **C --- indirect evidence only.**

There is a large and clearly runtime-facing Skrit surface, but the exact
binding mechanism remains unknown.

Do not invent a native API layer from the lexical method names alone.

------------------------------------------------------------------------

# 15. Actor Model Findings

Actor behavior appears component-based.

Component schema evidence suggests actors are assembled from components
such as:

-   aspect
-   attack
-   body
-   defend
-   physics
-   inventory
-   placement

GAS/template data provides component initialization inputs.

The exact runtime constructor/component creation order remains unknown.

This implies a probable boundary:

``` text
authored actor definition
        ↓
component initialization data
        ↓
native component/runtime construction
        ↓
live actor state
```

The last two stages need further observation/research.

------------------------------------------------------------------------

# 16. Milestone 1B --- Actor Chain

The first detailed actor investigation focused on:

``` text
good_a_heroes/farmboy
```

with concrete hero:

``` text
hero_human_male
```

Tank tooling used for extraction:

**Siege Control**

The source accepts the `DSg2Tank` signature, indexes entries,
reconstructs paths, and decompresses payloads.

Important limitation:

-   GAS/Skrit are mostly text-previewed
-   it is not a complete semantic parser/interpreter
-   it does not provide a complete PRS/ASP semantic runtime
-   it does not by itself establish game semantics

------------------------------------------------------------------------

# 17. Active Hero Inheritance

The active hero declaration was found in:

``` text
/world/contentdb/templates/actors/good/heroes_ds2.gas
```

Important correction:

`heroes.gas` contains a hero declaration inside a block comment. The
active declaration is in `heroes_ds2.gas`.

Observed inheritance:

``` text
hero_human_male
  → base_hero_human_male
  → hero
  → actor_good
  → actor
```

Observed values include:

``` text
avg_move_velocity = 4.5
initial_chore = chore_fidget
armor_version = gah_amr
armor_race = ma
helmet_race = hm
chore_prefix = a_c_gah_fb_fs
```

Bone translator entries were found for:

-   head
-   spine
-   pelvis
-   kill
-   shield
-   weapon bones

------------------------------------------------------------------------

# 18. Hero Animation Definitions

The hero's walk chore uses:

``` text
select_walk
```

with key:

``` text
rl
```

The fidget chore uses:

``` text
select_fidget
```

with:

``` text
cbt0 = dff
nrm0 = dff-02
```

The default chore uses:

``` text
simple_loop
```

with:

``` text
key = dff
```

The human base actor supports stance indices 0--10.

Comments label:

``` text
stance 0 = unarmed
stance 1 = melee / one-handed
```

However:

> These comments do not prove the runtime's final stance assignment
> rules.

------------------------------------------------------------------------

# 19. Hero Visual/Equipment Closure

Concrete hero data included:

``` text
model:
m_c_gah_amr_suit_ma_a1

custom_head:
m_c_gah_amr_hlmt_hm_head-01
```

Textures:

``` text
b_c_gah_hm_skin_01_01_npc
b_c_gah_amr_suit_ma_a1_011_01
```

Equipment:

``` text
amr_bdy_merc
amr_bot_merc
book_glb_magic_01
dg_1h_tutorial
```

Initial additional inventory:

``` text
spell_ice_tutorial
spell_fire_tutorial
bw_sh_tutorial
```

------------------------------------------------------------------------

# 20. Equipment Dependency Closure

## Armor body

``` text
amr_bdy_merc
  → amr_generic_sets.gas
  → base_armor_body
  → armor
```

Observed:

-   chest slot
-   defense 6

No direct model/animation stance was established in this definition.

## Armor boots

``` text
amr_bot_merc
  → amr_generic_sets.gas
  → base_armor_boots
  → armor
```

Observed:

-   feet slot
-   defense 2

No direct model/animation stance was established.

## Spellbook

``` text
book_glb_magic_01
  → trs_book_spell.gas
  → base_book_spell
  → spellbook
  → equippable
```

Base model:

``` text
m_i_glb_book-magic-02
```

## Tutorial dagger

``` text
dg_1h_tutorial
  → wpn_dagger.gas
  → base_dagger_template
  → weapon_melee
  → weapon
  → equippable
```

Observed:

``` text
attack class = ac_sword
weapon type = melee
model = m_w_dag_301-a
texture = b_w_dag_301-a
```

The actual model path was found as:

``` text
/art/meshes/weapons/dagger/m_w_dag_301-a.asp
```

The exact Tank path for the dagger texture remained unresolved.

No explicit authored `animstance` assignment was found.

## Tutorial spells

``` text
spell_ice_tutorial → base_spell_icebolt
spell_fire_tutorial → base_spell_embers
```

No direct Skrit was found in the inspected leaf definitions.

## Tutorial bow

``` text
bw_sh_tutorial
  → base_bow_template
```

Observed:

-   projectile weapon
-   two-handed

It was initial inventory, not the initially equipped hand weapon.

------------------------------------------------------------------------

# 21. Hero Animation Resource Resolution

The important Skrit is:

``` text
/art/animations/skrits/select_walk.skrit
```

It reads:

``` text
owner.goid.go.inventory.animstance
```

and uses that value to select the appropriate animation.

The relevant authored chain is:

``` text
hero_human_male
  → base_hero_human_male
  → chore_walk
  → select_walk
  → reads inventory.animstance
  → selects walk subanimation
  → key = rl
```

The hero prefix is:

``` text
a_c_gah_fb_fs
```

Matching PRS files were found:

``` text
/art/animations/characters/good_a_heroes/farmboy/fs0/a_c_gah_fb_fs0_rl.prs
/art/animations/characters/good_a_heroes/farmboy/fs1/a_c_gah_fb_fs1_rl.prs
```

This provides strong evidence for a naming/resource convention
equivalent to:

``` text
prefix + stance + key → PRS resource
```

but the exact runtime implementation of that lookup was not directly
established.

------------------------------------------------------------------------

# 22. Animation Runtime Services

`select_walk.skrit` uses native/runtime-facing facilities including:

-   `owner.blender`
-   `owner.UpdateBlender(delta_t)`
-   `m_Goid$.Go.Follower.GetCurrentVelocity`
-   `m_Goid$.go.aspect.RenderScale`
-   `owner.CurrentVelocity`
-   animation messages such as:
    -   `WE_ANIM_STEP_LEFT`
    -   `WE_ANIM_STEP_RIGHT`
    -   `WE_ANIM_SFX`

`select_fidget.skrit` uses:

``` text
owner.SetupStandardBoneAnimation(...)
```

`simple_loop.skrit` uses blender operations and responds to:

``` text
ANIMEVENT_FINISH
```

This strongly suggests:

> authored Skrit selects/controls animation behavior while the runtime
> provides the actual animation/blending/resource/bone services.

------------------------------------------------------------------------

# 23. Hero World Placement

The world map contains:

``` text
/world/maps/ds2_world/main.gas
/world/maps/ds2_world/info/start_positions.gas
```

and region actor placements.

A search across **142 extracted region `actor.gas` files** found no
direct:

``` text
hero_human_male
base_hero_human_male
```

placement.

Therefore the selectable hero is probably instantiated through a
player/party/creation path rather than being an ordinary map-placed
actor.

The exact construction path remains:

> **UNKNOWN**

Do not assume the player actor is created like an ordinary static world
actor.

------------------------------------------------------------------------

# 24. Milestone 1C --- Complete Hero Dependency Graph

The strongest current graph is:

``` text
hero_human_male
├── specializes → base_hero_human_male
│   ├── specializes → hero
│   │   └── specializes → actor_good → actor
│   ├── body.avg_move_velocity = 4.5
│   ├── body.initial_chore = chore_fidget
│   ├── chore_prefix = a_c_gah_fb_fs
│   ├── chore_walk → select_walk + key rl
│   ├── chore_fidget → select_fidget + dff/dff-02
│   └── bone translator
├── aspect.model → m_c_gah_amr_suit_ma_a1 ASP
├── aspect.textures → skin + armor DDS
├── inventory.custom_head → m_c_gah_amr_hlmt_hm_head-01
├── equipment.es_chest → amr_bdy_merc → base_armor_body
├── equipment.es_feet → amr_bot_merc → base_armor_boots
├── equipment.es_spellbook → book_glb_magic_01 → base_book_spell → spellbook
├── equipment.es_weapon_hand → dg_1h_tutorial
│   → base_dagger_template → weapon_melee → weapon
│   ├── aspect.model → m_w_dag_301-a ASP
│   └── aspect.texture → b_w_dag_301-a
├── initial spell → spell_ice_tutorial → base_spell_icebolt
├── initial spell → spell_fire_tutorial → base_spell_embers
└── initial other item → bw_sh_tutorial → base_bow_template

select_walk
├── reads inventory.animstance
├── receives walk key rl
└── stance + prefix + key → a_c_gah_fb_fsN_rl.prs
    └── exact N = UNKNOWN
```

------------------------------------------------------------------------

# 25. Animation Stance Investigation

A dedicated search was performed for where `inventory.animstance` is
assigned.

Results:

-   `select_walk.skrit` contains a local fallback:

    ``` text
    eAnimStance stance$ = AS_PLAIN;
    ```

-   later it explicitly reads:

    ``` text
    stance$ = m_Goid$.go.inventory.animstance;
    ```

-   the hero template comments suggest:

    -   stance 0 = unarmed
    -   stance 1 = melee/one-handed

-   no authored stance assignment was found for the dagger

-   no authored item→stance rule was found for the inspected
    dagger/bow/2H sword/staff templates

-   weapon classifications were found:

    -   dagger: melee, one-handed
    -   bow: ranged/projectile, two-handed
    -   2H sword: melee, two-handed
    -   staff: melee, two-handed

### Current conclusion

> **D. No authored rule sufficient to determine stance was found.**

It is plausible that the dagger results in stance 1, but this is only an
inference.

The most likely semantic boundary is:

``` text
equipment initialization/change
        ↓
native/runtime derived inventory state
        ↓
inventory.animstance
        ↓
select_walk
```

The exact native derivation is still unknown.

------------------------------------------------------------------------

# 26. Milestone 1D --- Runtime Observation Attempt

A runtime experiment was attempted.

It failed cleanly because the initial environment was WSL and Windows
interop was broken.

Observed environment issue:

``` text
UtilBindVsockAnyPort: socket failed 1
```

Consequences:

-   Windows game could not be launched through the WSL environment
-   no GUI capture available
-   no debugger was available
-   no runtime transaction was performed

Therefore:

> This was an environment failure, not evidence about DS2 semantics.

Do not interpret it as evidence that the game lacks a behavior.

------------------------------------------------------------------------

# 27. Actor Semantic Boundary Survey

A broader scan covered:

-   all 510 Skrit
-   363 component files
-   83 interactive GAS files
-   targeted actor/job/rule content

The resulting semantic matrix was:

  ----------------------------------------------------------------------------------------
  Area              Authored layer          Runtime/native layer         Evidence
  ----------------- ----------------------- ---------------------------- -----------------
  Initialization    actor/component inputs  construction/placement       strong

  Equipment         item/slot declarations  derived state/slot           strong
                                            transition                   

  Movement          movement intent/jobs    path/movement/collision      strong

  Animation         chores/selectors/keys   blender/pose/resources       strong

  Health            damage rules            life storage/state           strong
                                            transition                   

  Death             jobs/animation          lifecycle/scheduling         strong

  Interaction       use flow                inventory/movement/effects   strong

  AI                jobs/queries            scheduler/path/messages      strong
  ----------------------------------------------------------------------------------------

Important unresolved question:

> Is the native semantic layer relatively small and well-defined, or do
> ordinary actors depend on a large amount of opaque native feature
> logic?

Current evidence does not answer that conclusively.

------------------------------------------------------------------------

# 28. Movement

Hero movement data includes:

``` text
avg_move_velocity = 4.5
```

Jobs such as movement/listening use MCP requests including:

``` text
PL_APPROACH
```

The runtime appears responsible for:

-   path planning
-   navigation
-   collision
-   actual position integration
-   movement service
-   velocity

Animation then consumes velocity.

This gives a likely semantic chain:

``` text
authored movement intent
        ↓
MCP/path request
        ↓
runtime navigation/movement
        ↓
effective velocity
        ↓
animation selector
```

The exact physics/collision implementation remains unknown.

------------------------------------------------------------------------

# 29. Health / Damage / Death

The actor aspect contains life/health-related state.

`rules.skrit` contains substantial authored damage processing and calls:

``` text
Rules.ChangeLife
```

Observed events include:

``` text
WE_DAMAGED
WE_KILLED
WE_DESTRUCTED
```

Death behavior uses:

``` text
job_die
```

and includes:

-   animation selection

-   MCP request:

    ``` text
    PL_DIE
    ```

-   job cleanup

The likely boundary is:

``` text
authored damage rules
        ↓
runtime life state API
        ↓
life transition
        ↓
damage/death events
        ↓
authored death job
        ↓
runtime lifecycle
```

Again, the internal native implementation is not established.

------------------------------------------------------------------------

# 30. Interaction

`job_use.skrit` shows a meaningful interaction pipeline.

It can:

-   validate a target

-   use:

    ``` text
    Inventory.SBeginUse
    ```

-   request MCP approach

-   call:

    ``` text
    Inventory.SAutoUse
    ```

-   finish with:

    ``` text
    Inventory.SEndUse
    ```

This supports a model where:

``` text
authored interaction intent
        ↓
target validation
        ↓
movement/approach service
        ↓
inventory/use service
        ↓
target-specific effect
```

The exact implementation of the target effect remains unknown.

------------------------------------------------------------------------

# 31. AI / Job System

The hero brain uses jobs and world messages.

Observed systems include:

``` text
Mind.SDoJob
MCPManager.MakeRequest
MCPManager.Flush
```

`job_listen.skrit` uses:

``` text
k_job_c_mcp_path_utils
k_job_c_mcp_fidget_utils
MCPManager.MakeRequest(...)
```

This indicates:

-   jobs are authored behavior/state
-   a native scheduler/runtime manages them
-   MCP is a major coordination layer
-   pathing/fidget behavior is exposed through reusable authored
    utilities
-   message/job lifecycle is significant

The exact job scheduler implementation is unknown.

------------------------------------------------------------------------

# 32. Native Semantic Surface

A useful conceptual split is:

## Authored semantics

Likely represented in:

-   GAS
-   templates
-   component definitions
-   Skrit
-   maps
-   resource references
-   animation chore definitions
-   gameplay rules
-   jobs
-   quests

## Runtime semantics

Likely provided by:

-   object lifecycle
-   components
-   movement
-   physics/collision
-   animation
-   rendering
-   inventory state
-   life state
-   navigation
-   AI scheduler
-   messages
-   timers
-   world services
-   effects
-   networking
-   saves
-   input

This is a working model, not a finalized architecture.

------------------------------------------------------------------------

# 33. Save System Evidence

The executable contains strings referring to:

``` text
GameSave
save_skrit_engine
.ds2world
.ds2party
party.gas
info.gas
bookmark.ds2party
```

There are also strings relating to component-order persistence errors.

This establishes that save data is a substantial compatibility concern.

Exact save schemas and serialization semantics remain unresolved.

------------------------------------------------------------------------

# 34. Networking Evidence

The executable contains references to:

-   GameSpy
-   DirectPlay 8
-   NAT
-   sockets/networking
-   `UIGamespy`

Re-Sieged should not assume the original networking stack is directly
reusable.

Multiplayer compatibility, if retained, is a separate
research/architecture problem.

------------------------------------------------------------------------

# 35. World / Map Evidence

The main world resource:

``` text
World.ds2map
```

is a Tank.

The world content includes:

-   terrain
-   region resources
-   object placements
-   actor placements
-   start positions
-   map GAS
-   terrain node/index resources
-   logic resources

The exact binary world/map semantics remain to be established.

------------------------------------------------------------------------

# 36. Broken World

Broken World was legitimately owned/accessed but was not found as a
separate executable in the inspected DS2 installation.

Public evidence from the previous research identified resources
resembling:

``` text
xLogic.ds2res
xObjects.ds2res
xTerrain.ds2res
xDS2XWorld.ds2map
```

For architecture/research purposes:

> Treat DS2 and Broken World as separate compatibility profiles until
> their resource/runtime relationship is verified.

Do not assume Broken World is merely a trivial patch to the base-game
content model.

------------------------------------------------------------------------

# 37. Mod Compatibility

Mod compatibility is heterogeneous.

Potential categories:

### Tank overrides

Potentially compatible if:

-   Tank lookup semantics are reproduced
-   resource paths are preserved
-   precedence/override behavior is reproduced

### GAS

Potentially compatible if:

-   parsing
-   inheritance
-   defaults
-   lookup
-   component initialization
-   field semantics

are reproduced sufficiently.

### Skrit

Potentially compatible only if enough of:

-   VM behavior
-   language semantics
-   native API surface
-   object model
-   events/messages
-   timers
-   state behavior

are reproduced or translated.

### Maps

Require:

-   map parsing
-   object placement
-   terrain semantics
-   world services
-   triggers
-   region logic

### Visual assets

Potentially convertible:

-   textures
-   models
-   animations

but the actual resource formats and runtime semantics must be
understood.

### Binary/native mods

Likely problematic:

-   binary patches
-   fixed-address hooks
-   original ABI assumptions
-   D3D9 proxy assumptions
-   arbitrary native DLL plugins

unless a compatibility layer intentionally provides an equivalent
environment.

This is not yet a final mod compatibility promise.

------------------------------------------------------------------------

# 38. Security Threat Model

The eventual import/runtime pipeline should account for untrusted game
content and mods.

Threats identified:

-   malformed archives
-   path traversal
-   decompression bombs
-   malformed model/texture/audio files
-   malicious save files
-   malicious multiplayer inputs
-   malicious scripts if script capabilities are expanded
-   native plugins with arbitrary code execution
-   package/update substitution
-   dependency confusion
-   corrupted import data

Security should be considered from the beginning of the import/runtime
boundary, not added after the architecture is complete.

------------------------------------------------------------------------

# 39. Legal / Provenance Research Position

No original DS2 source code has been established as legitimately
available.

Do not copy or depend on:

-   leaked source
-   proprietary SDK material
-   proprietary game assets
-   extracted game data in the repository

Clean-room/reimplementation methodology should remain explicit.

The Dusklight-style import analogy is **not** a legal conclusion.

Legality depends on:

-   jurisdiction
-   reverse-engineering methods
-   what is shipped
-   how the user supplies original content
-   applicable licenses
-   distribution practices
-   whether third-party code/assets are incorporated

A future legal/provenance document should track the origin and license
of every external dependency/reference implementation.

------------------------------------------------------------------------

# 40. Current Evidence Classification

The research should be understood using confidence categories.

## Strong evidence

Examples:

-   DS2 executable is PE32/x86
-   DS2 executable imports Direct3D9
-   DS2 uses DSg2Tank resources
-   GAS is plain text structured data
-   Skrit is heavily used
-   hero uses `select_walk`
-   `select_walk` reads `inventory.animstance`
-   hero uses `a_c_gah_fb_fs` prefix
-   fs0/fs1 PRS resources exist
-   component schemas exist
-   authored damage rules call `Rules.ChangeLife`
-   jobs use MCP/Mind systems
-   actor behavior spans authored and runtime layers

## Plausible but not fully proven

Examples:

-   exact Tank internal format semantics beyond what tooling establishes
-   exact stance-selection algorithm
-   exact resource-name lookup implementation
-   exact player actor construction path
-   exact native component initialization sequence
-   exact save schema
-   exact movement/physics API
-   exact Skrit native binding mechanism
-   exact DS2/BW runtime relationship

## Explicitly unknown

Do not silently turn these into assumptions:

-   dagger → exact `animstance`
-   which exact PRS stance is selected at runtime
-   native implementation of `inventory.animstance`
-   native binding table
-   complete native API
-   player creation pipeline
-   collision/physics internals
-   save serialization
-   multiplayer internals
-   full world map semantics
-   Broken World executable/runtime architecture

------------------------------------------------------------------------

# 41. Runtime Observation Environment

The initial WSL environment was unsuitable for controlled runtime
observation because Windows interop failed.

Observed:

``` text
UtilBindVsockAnyPort: socket failed 1
```

A native Windows environment was then prepared.

Windows Codex was successfully launched in:

``` text
C:\Dev\Re-Sieged
```

Windows version observed by Codex:

``` text
Microsoft Windows 10.0.26200
```

Node and npm were installed on Windows and Codex was installed
successfully.

Therefore:

> Native Windows Codex is now a viable environment for future runtime
> observation work.

The correct division of labor discovered during setup is:

-   WSL: static archaeology, extraction, analysis, scripting
-   Windows: native runtime observation and Windows-specific experiments

However, runtime experiments should remain controlled and should not be
started merely because the environment now works.

------------------------------------------------------------------------

# 42. Runtime Observation Methodology

The intended runtime research is **black-box semantic observation**, not
reverse engineering the implementation.

Allowed/desired:

-   normal game launch
-   normal gameplay
-   screenshots/video
-   save inspection
-   passive OS process observation
-   optional passive debugger observation if already available
-   controlled input
-   observing state transitions

Not intended for the initial semantic milestone:

-   patching
-   injection
-   hooks
-   trainers
-   memory modification
-   native implementation reconstruction
-   modifying the original executable

The objective is to establish **observable semantic contracts** without
requiring knowledge of the original implementation.

------------------------------------------------------------------------

# 43. Proposed Controlled Runtime Transactions

## Transaction A --- Equipment → Animation State

Goal:

Determine what observable animation state changes when equipment
changes.

Questions:

-   What stance does the hero enter when equipped with the tutorial
    dagger?
-   What stance when unarmed?
-   What stance with bow?
-   Does changing equipment immediately alter walking animation?
-   Does animation change depend on weapon type, slot, or derived
    inventory state?
-   Can the effective animation state be observed without
    reverse-engineering memory?

## Transaction B --- Movement → Velocity → Animation

Goal:

Observe:

``` text
input
→ movement
→ effective velocity
→ animation selection
```

Questions:

-   Does animation blend based on actual velocity?
-   What happens at start/stop?
-   How are turning/strafe states represented?
-   Does movement speed affect animation rate?
-   What semantic information would a new runtime need?

## Transaction C --- Damage → Life → Death

Goal:

Observe:

``` text
damage
→ life state
→ death transition
→ job/animation
```

Questions:

-   What events are observable?
-   Does death happen immediately?
-   What happens to movement/jobs?
-   What is the persistence behavior?

## Optional Transaction D --- Interaction

Observe:

``` text
target
→ approach
→ use
→ effect
```

## Optional Transaction E --- AI/Job

Observe:

``` text
brain
→ job
→ MCP request
→ navigation/action
→ completion
```

------------------------------------------------------------------------

# 44. Important Runtime Research Rule

A failed observation is not evidence of absence.

For example:

-   inability to launch DS2 from WSL did not prove DS2 lacked runtime
    behavior
-   inability to find a static API table does not prove a native API
    does not exist
-   inability to find an authored stance assignment does not prove there
    is no stance system

Always classify failures as:

-   environment limitation
-   search limitation
-   evidence of absence
-   actual observed absence

These are not interchangeable.

------------------------------------------------------------------------

# 45. Architectural Questions Still Open

Claude should explicitly investigate these before committing the project
to an architecture.

## Runtime boundary

What exactly must Re-Sieged reimplement?

Possible candidates:

-   object/component model
-   GAS loader/inheritance
-   Skrit VM
-   Skrit API compatibility layer
-   world/map system
-   physics/collision
-   navigation/MCP
-   animation system
-   inventory
-   combat/rules
-   effects
-   save system
-   input
-   renderer
-   audio
-   multiplayer

Do not assume all of these need to be separate modules yet.

## Content boundary

Which original content can remain data-driven?

Which content requires conversion?

Which content requires semantic translation?

Which content requires a compatibility runtime?

## Script strategy

Potential approaches:

-   run original Skrit semantics through a compatible VM
-   translate Skrit to another runtime
-   create a clean-room compatible interpreter
-   mechanically convert some Skrit and preserve a compatibility layer
-   reauthor selected systems

This is a major architectural decision and should be evidence-driven.

## Native API strategy

Potential approaches:

-   reproduce a stable subset of native services
-   reproduce the full observable API
-   provide compatibility shims
-   translate calls at import time
-   compile scripts to a new runtime representation

Again, do not choose without sufficient evidence.

## Rendering boundary

The original renderer is D3D9-era.

Re-Sieged's renderer should probably be independent of the original
renderer, but the exact relationship between game semantics and render
resources needs to be understood.

## Input boundary

The new experience should be semantic/controller-first.

Avoid designing input as:

``` text
controller button → pretend keyboard key
```

Instead consider eventual semantics such as:

``` text
Move
Aim
Target
Interact
Attack
Ability
Inventory
Menu
Camera
```

but do not scaffold these as final architecture until the game semantics
are better understood.

------------------------------------------------------------------------

# 46. What Re-Sieged Should NOT Become

Avoid turning the project prematurely into:

-   a generic game engine
-   a Diablo clone
-   a DS2 texture pack
-   a D3D9 wrapper
-   a controller mapper
-   a mod launcher only
-   a Tank extractor only
-   a simple compatibility shim
-   a giant abstraction framework disconnected from actual DS2 behavior

The goal is a **modern native runtime/ecosystem for DS2/BW**, not a
generic engine project.

------------------------------------------------------------------------

# 47. Research / Development Principles

## Principle 1 --- Evidence before architecture

Do not create an abstraction because it "sounds right."

First establish:

-   what the original does
-   what data drives it
-   what runtime behavior is required
-   what must remain compatible
-   what can be replaced

## Principle 2 --- Preserve semantics, not implementation accidents

Re-Sieged does not need to reproduce internal DS2 implementation details
merely because the original had them.

It needs to reproduce the **observable semantics** required for
compatibility and the desired modern experience.

For example:

If DS2 exposes:

``` text
inventory.animstance
```

Re-Sieged may not need the same internal variable if scripts/mods
ultimately depend only on the observable behavior.

## Principle 3 --- Compatibility should be deliberate

Define compatibility levels rather than vaguely promising "mod support."

Potential future categories:

-   data compatibility
-   asset compatibility
-   script compatibility
-   save compatibility
-   behavioral compatibility
-   native plugin compatibility

These are suggestions for investigation, not final architecture.

## Principle 4 --- Provenance is architecture

Every borrowed idea/code/reference should have:

-   source
-   license
-   version/commit
-   modification status
-   compatibility implications

## Principle 5 --- Security belongs at import/runtime boundaries

Game data is not automatically trusted simply because it came from a
legitimate game installation.

## Principle 6 --- Platform independence

Do not let the Windows-specific legacy runtime dictate the modern
runtime architecture.

## Principle 7 --- Tests should express behavior

Once semantic contracts are understood, tests should describe:

``` text
given authored content X
when runtime state Y occurs
then observable behavior Z occurs
```

rather than only testing internal helper functions.

------------------------------------------------------------------------

# 48. Recommended Immediate Research Direction

The project should now proceed from the clean repository using the
information in this document.

A sensible order is:

1.  **Validate this research against primary evidence.**
2.  Establish a formal evidence/research log.
3.  Complete the Windows runtime observation environment.
4.  Perform controlled semantic transactions.
5.  Investigate DS2/BW resource differences.
6.  Determine the practical content/import boundary.
7.  Investigate Skrit semantics and native service requirements.
8.  Map the minimum runtime semantic surface.
9.  Only then begin architecture definition.
10. Only after architecture review should implementation scaffolding
    begin.

This is intentionally conservative.

------------------------------------------------------------------------

# 49. Suggested Research Deliverables

Claude may create durable project documentation such as:

``` text
docs/
  research/
    evidence/
    formats/
    runtime/
    scripting/
    actors/
    world/
    saves/
    mods/
    legal/
    provenance/
  architecture/
  compatibility/
  handoff/
```

These are suggestions only.

Do not create a large directory tree merely to look professional.

Create files when there is actual information to preserve.

------------------------------------------------------------------------

# 50. Suggested Evidence Record Format

For important findings, use a consistent structure:

``` text
Finding:
What was observed.

Source:
Exact file/resource/tool/version/location.

Method:
How it was established.

Confidence:
Confirmed / Strong / Plausible / Unknown.

Implication:
What this means for Re-Sieged.

Does NOT prove:
Important limitations.

Next verification:
What would establish the remaining uncertainty.
```

This will help prevent research drift and accidental conversion of
guesses into architecture.

------------------------------------------------------------------------

# 51. Claude Starting Instructions

Claude should treat this document as the initial project dossier.

Before implementing:

1.  Read the existing repository files.
2.  Read this handoff.
3.  Identify contradictions between the handoff and repository state.
4.  Separate:
    -   confirmed facts
    -   strong inferences
    -   hypotheses
    -   open questions
5.  Verify important claims where practical.
6.  Build a research plan.
7.  Preserve the clean repository unless a change is justified by the
    research.
8.  Do not import proprietary DS2 content into Git.
9.  Do not begin a large architecture scaffold merely because one is
    described conceptually here.
10. Ask/flag important ambiguities before making irreversible
    architecture decisions.

Claude should be especially careful about the following:

-   Do not treat `inventory.animstance` as fully understood.
-   Do not treat the Skrit lexical call list as a native API
    specification.
-   Do not treat Tank filenames as proof of runtime semantics.
-   Do not treat comments as authoritative runtime behavior.
-   Do not assume Broken World is architecturally identical to DS2.
-   Do not assume the original executable must be preserved as part of
    the final runtime.
-   Do not assume a single import/compatibility model before researching
    it.
-   Do not assume mod compatibility is binary yes/no.
-   Do not use leaked/proprietary source as a basis for implementation.
-   Do not make legal conclusions from the Dusklight analogy.

------------------------------------------------------------------------

# 52. Current Bottom Line

The research has established a useful picture:

Dungeon Siege II is not simply a collection of static assets rendered by
a D3D9 executable.

It appears to be a layered system in which:

``` text
Tank resources
      ↓
GAS/component/template data
      ↓
Skrit-authored behavior
      ↓
runtime/native services
      ↓
live actors/world/state
```

The authored layer is substantial.

The runtime layer is also substantial.

The most important discovery is not a particular file format. It is the
**boundary between authored semantics and native services**.

The hero investigation demonstrates this clearly:

``` text
hero template
    ↓
components / inventory / equipment
    ↓
authored chore selectors
    ↓
inventory.animstance
    ↓
animation resource selection
    ↓
native blender / movement / object services
```

The same pattern appears in:

-   movement
-   combat
-   damage
-   death
-   interaction
-   AI
-   effects
-   world messages
-   inventory
-   quests

Therefore, the central Re-Sieged architecture problem is:

> **Identify the smallest clean-room runtime semantic surface that can
> preserve the behavior of DS2/BW authored content while replacing the
> obsolete platform/rendering/input/runtime pieces with a modern native
> implementation.**

That should be the north star for the research.

Do not solve it by guessing.

Establish the boundary empirically, document it, then architect around
it.

------------------------------------------------------------------------

# 53. Historical Environment / Workflow Notes

These details are included so future agents understand how the research
was performed.

## WSL

Previously used for:

-   static extraction
-   Tank inspection
-   grep/search
-   corpus scanning
-   scripting
-   repository analysis

Repo:

``` text
/home/sunbrolynk/Re-Sieged
```

## Windows

Previously prepared for:

-   native Codex
-   runtime observation
-   Windows-specific testing

Repo:

``` text
C:\Dev\Re-Sieged
```

Native Windows Codex successfully reported:

``` text
C:\Dev\Re-Sieged
Microsoft Windows 10.0.26200
```

## Existing uncommitted archaeology artifacts

Earlier WSL/Windows work may have produced:

``` text
re-sieged-wsl-dump.txt
re-sieged-windows-dump.txt
NUL
```

along with `.gitignore` changes.

These are historical artifacts and should not be assumed to exist in the
clean handoff repository.

Do not blindly restore or commit them.

------------------------------------------------------------------------

# 54. Final Handoff Statement

This document is intended to replace the scattered prior conversation as
the durable starting point.

The repository can begin essentially empty.

The next agent should not need the previous chat transcript to
understand:

-   what Re-Sieged is
-   what the user wants
-   what was investigated
-   what was found
-   what remains unknown
-   why certain architecture questions matter
-   what not to assume
-   what the next research phase should accomplish

The project is **not yet at the implementation phase** merely because
substantial research has been done.

The correct next step is to turn the research into a verified model of
DS2/BW's semantic/runtime boundary.

Only then should Re-Sieged's production architecture be designed.
