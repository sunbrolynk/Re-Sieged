# Research scripts (Phase 1, WS-1)

Small, deterministic, standard-library-only Python scripts that turn a local
Dungeon Siege II install (or save snapshots) into **derived facts**: names,
sizes, hashes, counts, offsets, header field values and symbol names. They
are research tools, not production code (see the research plan, WS-1).

All scripts:

- need Python 3.10 or newer and nothing else (no `pip install`);
- read game files **only from a path you pass**, and refuse any input inside
  the repository (including the git-ignored `local\`). The check compares
  folder identity, so a junction, `subst` drive, `\\?\` path or
  `\\localhost\c$` share that points into the repository is refused too;
- open inputs read-only and never write next to them: an `--out` folder inside
  an input folder, or the folder holding an input file, is refused;
- write output to `--out` (default `<repo>\local\<script>\`, which is
  git-ignored). A folder inside the repository but outside `local\` is
  refused; a subfolder such as `local\ds2-steam\` is fine;
- write only the derived facts listed under "What is safe to share or
  commit" below into their reports, and never write absolute paths into
  their JSON/Markdown output (so your Windows user name does not end up in a
  report);
- do not follow symlinks or Windows junctions inside an input folder; they
  are listed as skipped;
- report a file they cannot read (for example one the game holds open) by
  name and error number, then carry on or stop with a non-zero exit code,
  without a traceback;
- are deterministic: the same input gives byte-identical JSON/Markdown
  (error texts use error numbers, not the translated Windows message).

`helpstats.py` and `prefixstats.py` follow the same input rule but print
counts to the console instead of writing files (see the last section).

Each has `--help`.

| Script | What it does | Claims it supports |
| --- | --- | --- |
| `install_inventory.py` | Walks an install folder. Per file: relative path, size, SHA-256, first 8 bytes (hex, plus text if printable ASCII), Tank signature (`DSg2Tank` / `DSigTank`). Adds edition hints (presence of known file names) | CLM-001, 003, 010, 011; edition detection |
| `pe_summary.py` | Parses a PE32/PE32+ file without third-party libraries: machine, timestamp, characteristics (for example `LARGE_ADDRESS_AWARE`), image base, subsystem, sections (with entropy), imports and delay-load imports, exports, resource types, version resource (`FileVersion`/`ProductVersion`), SHA-256. Runs the **FuBi export-table test**. Optional `--count-string` counts a text in ASCII and UTF-16LE (counts and offsets only) | CLM-001…006, CLM-035, CLM-070 |
| `save_diff.py` | Compares 2 or 3 save snapshots (folders or files) per EV-004 §9: sizes, SHA-256, differing-byte counts and merged `(offset, length)` ranges, common prefix/suffix when sizes differ, whole-file and per-4 KiB entropy, 8-byte signature. With 3 snapshots (A, A′, C) it also derives change-only ranges | EV-004 |
| `research_common.py` | Shared helpers: path guards, hashing, entropy, deterministic JSON | n/a |

## How to run (PowerShell, native Windows)

Open PowerShell in the repository. The commands use the `py` launcher that
the python.org installer adds; if you installed Python another way, use
`python` instead of `py -3`.

```powershell
cd C:\Dev\Re-Sieged
py -3 --version            # must be 3.10 or newer
$env:PYTHONDONTWRITEBYTECODE = 1   # optional: no __pycache__ folders in tools\research
$ds2 = 'C:\Program Files (x86)\Steam\steamapps\common\Dungeon Siege 2'
# GOG install instead (default GOG Galaxy path; yours may differ):
# $ds2 = 'C:\Program Files (x86)\GOG Galaxy\Games\Dungeon Siege 2'
```

Without `PYTHONDONTWRITEBYTECODE`, Python writes `__pycache__\` folders next
to the scripts. They are harmless and git-ignored in most setups; delete
them if `git status` shows them.

Long commands below are split with PowerShell's backtick (`` ` ``). The
backtick must be the **last character on the line**: a trailing space after
it breaks the command (PowerShell then runs the first line alone). If in
doubt, write the command on one line.

### 1. Install inventory

```powershell
py -3 tools\research\install_inventory.py $ds2
```

Writes `local\install_inventory\Dungeon_Siege_2.inventory.json` (every file)
and `Dungeon_Siege_2.inventory.md` (summary: Tank signatures, resource and
executable files with hashes, edition hints, extension counts). Hashing about
2.5 GB takes a few minutes; `--no-hash` skips it. Use `--label` to name the
output, for example `--label steam-ds2` or `--label retail-bw`.

### 2. PE summary and FuBi test

```powershell
py -3 tools\research\pe_summary.py "$ds2\DungeonSiege2.exe" `
  --count-string "Configured as Retail" `
  --count-string "GameSpy" `
  --count-string "xinput" --count-string "dinput8" `
  --count-string "save_skrit_engine" --ignore-case
```

`--ignore-case` applies to **every** `--count-string` in the command; to
mix case-sensitive and case-insensitive counts, run the script twice.

Writes `local\pe_summary\DungeonSiege2.exe.pe.json` and `.pe.md`. You can
pass several files at once (for example every `.exe` and `.dll` in `$ds2`).
`--examples N` changes how many example decorated export names are listed
(default 20). `--version-key KEY` (repeatable) reports another version-resource
string instead of the defaults.

How to read the FuBi test: the script counts export-table names and sorts
them into MSVC-decorated C++ (`?name@Class@@...`), C-decorated (`_name@8`) and
undecorated names, and groups decorated names by their (heuristic) class or
namespace. **"No exports found" is a search limitation, not evidence that
FuBi is absent**: GPG's own 2001 talk suggests retail builds may strip export
data or pack it into a resource, so look at the resource-type list too.
"Export table present but unparsed" is also a search limitation: the table
exists but the script could not read it (the reason is in `parse_errors`).
Decorated exports are consistent with a FuBi-style binding, but do not prove
one.

On damaged or unusual files the script records what it could not read in
`parse_errors` and keeps the rest. Names longer than 512 characters, and
resource-type names and version values longer than 128, are cut and marked
`...(truncated)`. The overlay size includes an Authenticode signature when
the file is signed (the report says so).

### 3. Save diff (EV-004)

Use the snapshot folders made with the EV-004 §6 snapshot block:

```powershell
$sess = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Re-Sieged-captures\EV-004\session-YYYYMMDD'
py -3 tools\research\save_diff.py "$sess\EQ-1-A" "$sess\EQ-2-A2" "$sess\EQ-3-C" --labels A A2 C
```

Close the game before you run it: a save the game still holds open is
reported as "file locked or unreadable" and the script stops with exit
code 1.

Writes `local\save_diff\A_vs_A2_vs_C.diff.json` and `.diff.md`. Comparisons:
A→A2 (noise), A2→C (noise + change), A→C, plus "change-only" ranges: the
bytes that differ A2→C but did not differ A→A2, computed byte-exactly before
any merging and then merged for display (only when all three files have the
same size). `--merge-gap` (default 16) merges ranges separated by fewer equal
bytes.

`--show-bytes` (off by default) **also** writes
`<name>.RAW-BYTES-DO-NOT-COMMIT.txt` with the changed bytes in hex, for local
investigation only. It prints a warning. Nothing from that file goes into an
evidence record.

### Tests

The tests use synthetic fixtures built in code (a hand-made PE, fake
`DSg2Tank` files, tiny fake saves); they never touch game files.

```powershell
$env:PYTHONDONTWRITEBYTECODE = 1
py -3 -m unittest discover -s tools\research\tests -v
```

A few tests need to create symlinks or junctions; they skip themselves on
Windows when that is not allowed (Developer Mode off, no admin rights).

## What is safe to share or commit

The raw JSON/Markdown output stays in `local\` (git-ignored). What goes into
an evidence record (`docs\research\evidence\EV-###-*.md`) is a **selection of
derived facts** from it:

- file names and relative paths, sizes, SHA-256 hashes, counts;
- PE header values, section names, import DLL and function names, export
  counts and a handful of example export names;
- version numbers from the version resource;
- offsets and lengths of changed ranges, entropy figures;
- a signature of at most 8 bytes (for example `DSg2Tank`).

Replace any absolute path you copy from the console with a placeholder such
as `C:\Users\<you>`; console lines like `wrote C:\...` can contain your user
name.

**Never commit or share:** game files of any kind (`.exe`, `.dll`, `.ds2res`,
`.ds2map`, saves), anything extracted from them, hex dumps, the
`*.RAW-BYTES-DO-NOT-COMMIT.txt` file, or whole import/export lists pasted in
bulk (summarise and quote a few names instead). Tank decompression or
extraction is deliberately **not** provided here; it waits for a provenance
decision.

## Reading the results honestly

- An edition hint is a file-name presence check. A file name is not proof
  of an edition, version or behaviour.
- A missing import is not proof a DLL is never used: the game may load it at
  runtime (`LoadLibrary`). Classify it as a *search limitation*.
- A string count says the bytes occur in the file, not that the code uses
  them.

---

## DS1 help-log counters (added 2026-09-30, gas-skrit review fix)

<!-- Section appended by the Researcher; the content above is owned by the
     Phase 1 scripts author. -->

`helpstats.py` and `prefixstats.py` count the structure of GPG's public DS1
v1.11 Skrit help dump (`help.log` from `help-1.1.zip`) and FEX listing
(`fex-1.1.txt` from `fex-1.1.zip`); see
`docs/research/scripting/gas-skrit-public-docs.md` (sources S2, S3). They
differ from the scripts above in one way: they print **counts only** to the
console (no class, function or enum names) instead of writing to `--out`.
Like the other scripts they refuse inputs inside the repository, including
`local\`, so keep the downloads in a folder outside it:

```powershell
$gs = Join-Path $HOME 'Re-Sieged-inputs\gasskrit'
py -3 tools\research\helpstats.py "$gs\help.log" --fex "$gs\fex-1.1.txt" --enum-values eAnimStance
py -3 tools\research\prefixstats.py "$gs\help.log"
```

Tests: `tools\research\tests\test_helpstats.py` (synthetic log, no GPG text).
