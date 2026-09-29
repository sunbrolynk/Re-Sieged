# Claims register

Every factual claim about DS2/BW is listed here. Claims seeded on 2026-09-29
come from [the handoff](../handoff/2026-09-codex-research-handoff.md) (cited as
`H§n`). **All are _Reported_. None has been re-verified in this repository
yet.** When a claim is verified, add an evidence record and set Status to
`Verified (EV-###)`.

Confidence: **C**onfirmed · **S**trong · **P**lausible · **U**nknown.
See [README](README.md#confidence-levels).

## Executable and platform

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-001 | `DungeonSiege2.exe` is PE32, x86, Windows GUI, 8,212,480 bytes, image base `0x00400000` | S | H§7, H§8 | Reported |
| CLM-002 | Embedded version string reads `Gas Powered Games Dungeon Siege II v2.30.0.0 * Configured as Retail`; Steam app 39200, build 21154 | S | H§7 | Reported |
| CLM-003 | SHA-256 `0176da8839e7167cae59fa51200bf2c6c260e49a76cf9bf7c6c38c51052668ae` | S | H§7 | Reported |
| CLM-004 | Static imports include `d3d9.dll`, `d3dx9_29.dll`, `WSOCK32`, `WINHTTP`, `WINMM` and others; references Miles (`mss32.dll`) and Bink (`binkw32.dll`) | S | H§8 | Reported |
| CLM-005 | No static `XInput`/`dinput8` import found. Search limitation only: dynamic loading not ruled out | U | H§8 | Reported |
| CLM-006 | Executable strings reference GameSpy, DirectPlay 8, NAT, `UIGamespy` | S | H§34 | Reported |

## Resources (Tank)

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-010 | Base install has 9 resource files: `Logic`, `Movies1/2`, `Objects`, `Sound1/2`, `Terrain`, `Voices` (`.ds2res`) and `World.ds2map` | S | H§9 | Reported |
| CLM-011 | All sampled resource files start with the 8-byte signature `DSg2Tank` | S | H§9 | Reported |
| CLM-012 | Tank internal format (index, path reconstruction, compression) is understood only as far as Siege Control implements it. Not independently documented | P | H§16, H§40 | Reported |
| CLM-013 | `World.ds2map` is a Tank containing terrain, regions, placements, start positions and map GAS | S | H§35 | Reported |

## GAS and components

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-020 | GAS is plain-text structured data: nested blocks, key/value fields, comments | S | H§10 | Reported |
| CLM-021 | Templates use inheritance (`specializes`) | S | H§17 | Reported |
| CLM-022 | Some GAS fields are consumed by native systems, not only by Skrit (e.g. render profiles in `system_detail.gas`) | S | H§10 | Reported |
| CLM-023 | Actors are composed of components (aspect, attack, body, defend, physics, inventory, placement); `components.gas` documents the component system | S | H§14, H§15 | Reported |
| CLM-024 | `components.gas` does **not** enumerate the Skrit↔native binding surface | S | H§14 | Reported |

## Skrit

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-030 | `Logic.ds2res` contains 510 `.skrit` entries | S | H§12 | Reported |
| CLM-031 | These contain 3,856 unique dotted call expressions. **Lexical count, not a native API count** | S | H§12 | Reported |
| CLM-032 | Namespace method counts (lexical): Mind 91, WorldFXMgr 76, QuestManager 65, Inventory 57, Rules 32, GoDb 31, AIQuery 28, Server 12, WorldTerrain 10, MCPManager 9 | S | H§12 | Reported |
| CLM-033 | Event handler/message counts: OnGoHandleMessage 770, OnTimer 574, OnWorldMessage 538, PostWorldMessage 156, SendWorldMessage 138, AnimEventBitTest 117 | S | H§13 | Reported |
| CLM-034 | ~232 unique `WE_*`/`ANIMEVENT_*`/`PL_*`/`REQUEST_*` tokens | S | H§13 | Reported |
| CLM-035 | No binding table, extern convention, method ID table or API manual found in the install. Search limitation, not absence | U | H§14 | Reported |
| CLM-036 | `k_*.skrit` files are authored wrappers, not native binding declarations | S | H§14 | Reported |

## Hero actor (`hero_human_male`)

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-040 | Active declaration is in `templates/actors/good/heroes_ds2.gas`. The one in `heroes.gas` is inside a block comment | S | H§17 | Reported |
| CLM-041 | Inheritance: `hero_human_male → base_hero_human_male → hero → actor_good → actor` | S | H§17 | Reported |
| CLM-042 | `avg_move_velocity = 4.5`, `initial_chore = chore_fidget`, `chore_prefix = a_c_gah_fb_fs` | S | H§17 | Reported |
| CLM-043 | Walk chore uses `select_walk` with key `rl`; fidget uses `select_fidget`; default uses `simple_loop` | S | H§18 | Reported |
| CLM-044 | Starting equipment: `amr_bdy_merc`, `amr_bot_merc`, `book_glb_magic_01`, `dg_1h_tutorial`; inventory adds `spell_ice_tutorial`, `spell_fire_tutorial`, `bw_sh_tutorial` | S | H§19 | Reported |
| CLM-045 | Equipment inheritance chains as listed in H§20 (e.g. `dg_1h_tutorial → base_dagger_template → weapon_melee → weapon → equippable`) | S | H§20 | Reported |
| CLM-046 | Dagger model path is `/art/meshes/weapons/dagger/m_w_dag_301-a.asp`; texture Tank path not resolved | S/U | H§20 | Reported |
| CLM-047 | `select_walk.skrit` reads `owner.goid.go.inventory.animstance` to pick the animation | S | H§21, H§25 | Reported |
| CLM-048 | PRS files `…/farmboy/fs0/a_c_gah_fb_fs0_rl.prs` and `fs1/…fs1_rl.prs` exist, consistent with the pattern `prefix + stance + key` | S | H§21 | Reported |
| CLM-049 | The `prefix + stance + key` lookup is performed by the runtime. The pattern is observed; who implements it is not established | P | H§21 | Reported |
| CLM-050 | Hero template comments label stance 0 = unarmed, 1 = melee/one-handed. **Comments are not runtime proof** | P | H§18 | Reported |
| CLM-051 | No authored item→stance rule found in dagger/bow/2H sword/staff templates. Search limitation | U | H§25 | Reported |
| CLM-052 | `hero_human_male` is not placed in any of 142 scanned region `actor.gas` files, so it is probably built by a party/creation path | P | H§23 | Reported |

## Runtime-facing behavior (authored side)

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-060 | Animation Skrit calls runtime services: `owner.blender`, `UpdateBlender`, `SetupStandardBoneAnimation`, follower velocity, `ANIMEVENT_FINISH` | S | H§22 | Reported |
| CLM-061 | Movement intent goes through MCP requests (e.g. `PL_APPROACH`); path planning, collision and integration appear to be native | S/P | H§28 | Reported |
| CLM-062 | `rules.skrit` performs authored damage processing and calls `Rules.ChangeLife`; events `WE_DAMAGED`/`WE_KILLED`/`WE_DESTRUCTED` exist | S | H§29 | Reported |
| CLM-063 | Death uses `job_die`, which issues MCP `PL_DIE` | S | H§29 | Reported |
| CLM-064 | `job_use.skrit` flow: validate → `Inventory.SBeginUse` → MCP approach → `SAutoUse` → `SEndUse` | S | H§30 | Reported |
| CLM-065 | AI uses jobs (`Mind.SDoJob`) plus MCP (`MakeRequest`/`Flush`), with shared `k_job_c_mcp_*` utilities | S | H§31 | Reported |

## Saves

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-070 | Executable strings reference `GameSave`, `save_skrit_engine`, `.ds2world`, `.ds2party`, `party.gas`, `info.gas`, `bookmark.ds2party`, and component-order persistence errors | S | H§33 | Reported |

## Broken World

| ID | Claim | Conf. | Source | Status |
| --- | --- | --- | --- | --- |
| CLM-080 | No separate BW executable found in the inspected DS2 install | S | H§36 | Reported |
| CLM-081 | Public sources suggest BW resources named `xLogic`, `xObjects`, `xTerrain` (`.ds2res`) and `xDS2XWorld.ds2map`. **Not observed locally** | P | H§36 | Reported |

## Corrections log

When a claim changes, note it here: date, ID, old → new, and the evidence.

_None yet._
