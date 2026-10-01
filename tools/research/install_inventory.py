#!/usr/bin/env python3
"""Inventory a Dungeon Siege II install folder (derived facts only).

For every file under the install folder this records the relative path, size,
SHA-256 and the first 8 bytes (hex, plus text if printable ASCII). It flags
Tank signatures (DSg2Tank for DS2, DSigTank for DS1) and lists edition hints:
known file names whose presence *suggests* an edition or overlay.

Supports: CLM-010, CLM-011 (Tank files), CLM-001/003 (executable size/hash),
and edition detection ideas in docs/research/editions-and-broken-world.md.

It never opens a Tank beyond its first 8 bytes and never copies content.
Output: <label>.inventory.json (full list) and <label>.inventory.md (summary)
in the output folder (default <repo>/local/install_inventory/).
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_common import (  # noqa: E402
    TOOL_VERSION,
    UsageError,
    check_input_path,
    check_output_dir,
    is_link_or_junction,
    md_escape,
    os_error_text,
    read_head,
    safe_console,
    sha256_file,
    signature,
    write_json,
    write_text,
)

SCRIPT = "install_inventory"

TANK_MAGICS = {
    b"DSg2Tank": "DSg2Tank",  # DS2 resource container (CLM-011)
    b"DSigTank": "DSigTank",  # DS1-style resource container
}

# Base-install resource files named in CLM-010.
BASE_RESOURCE_FILES = (
    "Logic.ds2res", "Movies1.ds2res", "Movies2.ds2res", "Objects.ds2res",
    "Sound1.ds2res", "Sound2.ds2res", "Terrain.ds2res", "Voices.ds2res",
    "World.ds2map",
)

# Edition hints. Each pattern is matched case-insensitively against file
# *base names* anywhere in the tree. Presence is a hint, never proof.
EDITION_MARKERS: tuple[dict[str, Any], ...] = (
    {
        "id": "ds2-exe",
        "patterns": ["DungeonSiege2.exe"],
        "meaning": "Main DS2 executable name",
        "source": "CLM-001",
    },
    {
        "id": "bw-exe-candidate",
        "patterns": ["DungeonSiege2BrokenWorld.exe"],
        "meaning": "Candidate BW executable name; NOT confirmed by any source read",
        "source": "editions-and-broken-world.md",
    },
    {
        "id": "base-resource-files",
        "patterns": list(BASE_RESOURCE_FILES),
        "meaning": "The nine base-install resource files of CLM-010",
        "source": "CLM-010",
    },
    {
        "id": "bw-x-resource-files",
        "patterns": ["x*.ds2res", "x*.ds2map"],
        "meaning": "x-prefixed resource files reported for the Broken World overlay",
        "source": "CLM-081; editions-and-broken-world.md [E10]",
    },
    {
        "id": "gog-marker-files",
        "patterns": ["goggame-*.info", "goggame-*.hashdb"],
        "meaning": "GOG store marker files (GOG DS2 product id is 1837106902)",
        "source": "editions-and-broken-world.md [E7][E22]",
    },
    {
        "id": "steam-marker-files",
        "patterns": ["steam_api.dll", "steam_api64.dll", "steam_appid.txt"],
        "meaning": "Steam-related files (a hint only; the appmanifest lives outside the game folder)",
        "source": "editions-and-broken-world.md",
    },
    {
        "id": "language-files",
        "patterns": ["language.dll", "Language.ds2res"],
        "meaning": "Localisation files reported in the store language depots",
        "source": "editions-and-broken-world.md [E7]",
    },
    {
        "id": "community-proxy-dll",
        "patterns": ["version.dll", "dinput8.dll", "d3d9.dll"],
        "meaning": "DLL names used by community fixes/proxies when found in the game folder (modified install hint)",
        "source": "editions-and-broken-world.md [E10][E11]",
    },
)

HINT_NOTE = (
    "Edition hints are file-name presence checks. A file name is not proof of an "
    "edition, version or behavior (AGENTS.md evidence discipline)."
)


def sanitize_label(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._")
    return cleaned or "install"


def walk_files(root: Path, unreadable: list[dict[str, str]] | None = None) -> list[tuple[str, Path, bool]]:
    """Return (relative posix path, absolute path, is_link) for every file.

    Symlinked directories and Windows junctions/reparse points are not
    followed: they are recorded as link entries ("name/") without descending.
    Folders that cannot be listed are appended to `unreadable` (relative
    path + locale-independent error). Order is deterministic.
    """
    found: list[tuple[str, Path, bool]] = []

    def on_error(exc: OSError) -> None:
        if unreadable is not None:
            where = Path(exc.filename) if exc.filename else root
            try:
                rel = where.relative_to(root).as_posix()
            except ValueError:
                rel = "?"
            unreadable.append({"path": rel + "/", "error": os_error_text(exc)})

    for dirpath, dirnames, filenames in os.walk(root, onerror=on_error, followlinks=False):
        base = Path(dirpath)
        descend = []
        for name in sorted(dirnames):
            full = base / name
            if is_link_or_junction(full):
                found.append((full.relative_to(root).as_posix() + "/", full, True))
            else:
                descend.append(name)
        dirnames[:] = descend  # os.walk only descends into what is left here
        for name in filenames:
            full = base / name
            rel = full.relative_to(root).as_posix()
            found.append((rel, full, is_link_or_junction(full)))
    found.sort(key=lambda item: (item[0].casefold(), item[0]))
    return found


def describe_file(rel: str, full: Path, is_link: bool, do_hash: bool) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "path": rel,
        "extension": Path(rel.rstrip("/")).suffix.lower(),
    }
    if is_link:
        entry.update({"symlink": True, "size": None, "sha256": None, "head": None, "tank_magic": None})
        return entry
    try:
        entry["size"] = full.stat().st_size
        head = read_head(full)
        entry["head"] = signature(head)
        entry["tank_magic"] = TANK_MAGICS.get(head[:8])
        entry["sha256"] = sha256_file(full) if do_hash else None
    except OSError as exc:
        entry.update({"size": entry.get("size"), "sha256": None, "head": None, "tank_magic": None,
                      "error": os_error_text(exc)})
    return entry


def edition_hints(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hints = []
    for marker in EDITION_MARKERS:
        matches: list[str] = []
        per_pattern: dict[str, list[str]] = {}
        for pattern in marker["patterns"]:
            hits = [
                f["path"] for f in files
                if fnmatch.fnmatchcase(Path(f["path"].rstrip("/")).name.casefold(), pattern.casefold())
            ]
            per_pattern[pattern] = hits
            matches.extend(hits)
        hint = {
            "id": marker["id"],
            "meaning": marker["meaning"],
            "source": marker["source"],
            "patterns": marker["patterns"],
            "present": bool(matches),
            "matches": sorted(set(matches), key=lambda p: (p.casefold(), p)),
        }
        if marker["id"] == "base-resource-files":
            hint["missing"] = [p for p in marker["patterns"] if not per_pattern[p]]
        hints.append(hint)
    return hints


def build_inventory(install_dir: Path, do_hash: bool = True) -> dict[str, Any]:
    unreadable: list[dict[str, str]] = []
    files = [describe_file(rel, full, link, do_hash) for rel, full, link in walk_files(install_dir, unreadable)]
    unreadable.sort(key=lambda d: (d["path"].casefold(), d["path"]))
    regular = [f for f in files if not f.get("symlink")]
    tank_counts = Counter(f["tank_magic"] for f in regular if f.get("tank_magic"))
    ext_counts = Counter(f["extension"] or "(none)" for f in regular)
    resource_ext = {".ds2res", ".ds2map", ".dsres", ".dsmap", ".tank"}
    resource_without_magic = [
        f["path"] for f in regular if f["extension"] in resource_ext and not f.get("tank_magic")
    ]
    return {
        "tool": SCRIPT,
        "tool_version": TOOL_VERSION,
        "hashing": "sha256" if do_hash else "skipped (--no-hash)",
        "totals": {
            "files": len(regular),
            "symlinks": len(files) - len(regular),
            "bytes": sum(f["size"] or 0 for f in regular),
            "errors": sum(1 for f in files if "error" in f) + len(unreadable),
        },
        "unreadable_folders": unreadable,
        "extension_counts": dict(sorted(ext_counts.items())),
        "tank_magic_counts": dict(sorted(tank_counts.items())),
        "resource_extension_without_tank_magic": resource_without_magic,
        "edition_hints": edition_hints(files),
        "edition_hints_note": HINT_NOTE,
        "files": files,
    }


def render_summary(inv: dict[str, Any], label: str) -> list[str]:
    t = inv["totals"]
    lines = [
        f"# Install inventory: {label}",
        "",
        f"Generated by `tools/research/{SCRIPT}.py` v{inv['tool_version']}. Derived facts only "
        "(names, sizes, hashes, 8-byte signatures). Full list: the matching `.inventory.json`.",
        "",
        f"- Files: {t['files']:,} ({t['bytes']:,} bytes); symlinks/junctions skipped: {t['symlinks']}; read errors: {t['errors']}",
        f"- Hashing: {inv['hashing']}",
    ]
    if inv["unreadable_folders"]:
        lines.append("- Folders that could not be listed (search limitation, not absence): "
                     + ", ".join(f"`{md_escape(d['path'])}` ({d['error']})" for d in inv["unreadable_folders"]))
    lines += [
        "",
        "## Tank signatures (first 8 bytes)",
        "",
    ]
    if inv["tank_magic_counts"]:
        for magic, count in inv["tank_magic_counts"].items():
            lines.append(f"- `{magic}`: {count} file(s)")
    else:
        lines.append("- No file starts with a known Tank signature (observed absence in this folder).")
    if inv["resource_extension_without_tank_magic"]:
        lines.append("- Resource-extension files WITHOUT a Tank signature: "
                     + ", ".join(f"`{md_escape(p)}`" for p in inv["resource_extension_without_tank_magic"]))
    lines += ["", "## Resource and executable files", "",
              "| Path | Size (bytes) | First 8 bytes (hex) | Text | SHA-256 |",
              "| --- | ---: | --- | --- | --- |"]
    keep = {".ds2res", ".ds2map", ".dsres", ".dsmap", ".tank", ".exe", ".dll"}
    for f in inv["files"]:
        if f.get("symlink") or (f["extension"] not in keep and not f.get("tank_magic")):
            continue
        head = f.get("head") or {}
        lines.append(
            f"| `{md_escape(f['path'])}` | {f['size'] if f['size'] is not None else '?'} | "
            f"`{head.get('hex', '')}` | {('`' + md_escape(head['ascii']) + '`') if head.get('ascii') else ''} | "
            f"{f.get('sha256') or ''} |"
        )
    lines += ["", "## Edition hints", "", f"> {HINT_NOTE}", "",
              "| Hint | Present | Matches | Source |", "| --- | --- | --- | --- |"]
    for h in inv["edition_hints"]:
        matches = ", ".join(f"`{md_escape(m)}`" for m in h["matches"]) or "none"
        if h.get("missing"):
            matches += "; missing: " + ", ".join(f"`{m}`" for m in h["missing"])
        lines.append(f"| {h['id']}: {md_escape(h['meaning'])} | {'yes' if h['present'] else 'no'} | "
                     f"{matches} | {md_escape(h['source'])} |")
    lines += ["", "## Extension counts", ""]
    for ext, count in inv["extension_counts"].items():
        lines.append(f"- `{md_escape(ext)}`: {count}")
    lines += ["", "A \"no\" above is an *observed absence in this folder only*; it says nothing "
              "about other editions or about files loaded from elsewhere."]
    return lines


def main(argv: list[str] | None = None) -> int:
    safe_console()
    parser = argparse.ArgumentParser(
        description="Inventory a DS2 install folder: paths, sizes, SHA-256, 8-byte signatures, "
                    "Tank magic and edition hints. Derived facts only.")
    parser.add_argument("install_dir", type=Path, help="game install folder (outside the repository)")
    parser.add_argument("--out", type=Path, default=None,
                        help=f"output folder (default: <repo>/local/{SCRIPT}/)")
    parser.add_argument("--label", default=None,
                        help="output file prefix (default: the install folder name)")
    parser.add_argument("--no-hash", action="store_true", help="skip SHA-256 (faster; hashes reported as null)")
    args = parser.parse_args(argv)

    try:
        install_dir = check_input_path(args.install_dir)
        if not install_dir.is_dir():
            raise UsageError(f"not a folder: {args.install_dir}")
        out_dir = check_output_dir(args.out, SCRIPT, [install_dir])
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    label = sanitize_label(args.label or install_dir.name)
    inventory = build_inventory(install_dir, do_hash=not args.no_hash)
    json_path = out_dir / f"{label}.inventory.json"
    md_path = out_dir / f"{label}.inventory.md"
    try:
        write_json(json_path, inventory)
        write_text(md_path, render_summary(inventory, label))
    except OSError as exc:
        print(f"error: cannot write output ({os_error_text(exc)})", file=sys.stderr)
        return 1

    t = inventory["totals"]
    print(f"{t['files']} files, {t['bytes']:,} bytes, tank magic: {inventory['tank_magic_counts'] or 'none'}")
    for h in inventory["edition_hints"]:
        print(f"  hint {h['id']}: {'present' if h['present'] else 'absent'}")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
