#!/usr/bin/env python3
"""Count the structure of GPG's official DS1 v1.11 Skrit help log (counts only).

Input: `help.log` from GPG's public `help-1.1.zip` (Siege University, hosted
on download.microsoft.com; see docs/research/scripting/gas-skrit-public-docs.md,
source S3). Optionally also `fex-1.1.txt` from `fex-1.1.zip` (source S2).
These are DS1 documentation downloads, not DS2 game files. Like every
research script, it refuses inputs inside the repository (including the
git-ignored `local/`): keep the downloads in a folder outside it, for example
`%USERPROFILE%\\Re-Sieged-inputs\\gasskrit\\`.

Output: counts only, printed to stdout. The script never prints class,
function or enum names, so its output can be quoted in research notes
without reproducing the listing (AGENTS.md hard rule 1).

Supports: gas-skrit-public-docs.md "Published native surface" (Q-001, Q-004,
CLM-035). Standard library only; runs on Windows.

Usage:
    python tools/research/helpstats.py <path/to/help.log> [--fex <path/to/fex-1.1.txt>]
        [--enum-values <EnumName>]   (count the value lines listed for one enum)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_common import UsageError, check_input_path, os_error_text, safe_console  # noqa: E402

TIMESTAMP_PREFIX = re.compile(r"^\+\d\d:\d\d:\d\d\.\d+ - ")
TAG = re.compile(r"\[([!A-Z_]+)\]")
CALL_NAME = re.compile(r"(\w+)\s*\(")
ENUM_KIND = re.compile(r"\[(CONTINUOUS|IRREGULAR)\]\s*$")


def checked_file(path: Path) -> Path:
    """Refuse inputs inside the repository (shared rule) and non-files."""
    resolved = check_input_path(path)
    if not resolved.is_file():
        raise UsageError(f"not a file: {path}")
    return resolved


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_lines(path: Path) -> list[str]:
    raw = path.read_text(encoding="latin-1").splitlines()
    return [TIMESTAMP_PREFIX.sub("", line) for line in raw]


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    """Group lines under the '** Name **' headers the help dump uses."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("** ") and line.rstrip().endswith("**"):
            current = line.strip("* ").strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def help_counts(lines: list[str]) -> dict[str, object]:
    sections = split_sections(lines)
    classes_part = sections.get("Classes", [])
    globals_part = sections.get("Global functions", [])
    enums_part = sections.get("Enumerations", [])

    class_headers = [l for l in classes_part if l.startswith("Class: ")]
    singletons = [l for l in class_headers if "[SINGLETON]" in l]
    members = [l for l in classes_part if l.startswith("    ") and "(" in l]
    tags = Counter(t for l in members for t in TAG.findall(l))
    global_funcs = [
        l for l in globals_part if l and not l.startswith(" ") and "(" in l
    ]

    # The "** Enumerations **" section first lists enum names with a
    # [CONTINUOUS]/[IRREGULAR] tag. A later "Enumerations:" block (output of
    # the help.enums command) lists enums at 4-space indent and, for some of
    # them, their values at 8-space indent.
    enum_names = [l for l in enums_part if ENUM_KIND.search(l)]
    enum_kinds = Counter(ENUM_KIND.search(l).group(1) for l in enum_names)
    enum_block_entries = 0
    enum_block_with_values = 0
    enum_value_lines = 0
    in_block = False
    last_entry_has_values = False
    for l in enums_part:
        if l.strip() == "Enumerations:":
            in_block = True
            continue
        if not in_block:
            continue
        if l.startswith("        ") and l.strip():
            enum_value_lines += 1
            if not last_entry_has_values:
                enum_block_with_values += 1
                last_entry_has_values = True
        elif l.startswith("    ") and l.strip():
            enum_block_entries += 1
            last_entry_has_values = False

    return {
        "sections": len(sections),
        "classes": len(class_headers),
        "singleton classes": len(singletons),
        "member lines (Classes section, with '(')": len(members),
        "global function lines": len(global_funcs),
        "enumerations (tagged names)": len(enum_names),
        "enumerations by tag": dict(sorted(enum_kinds.items())),
        "enum value block: entries": enum_block_entries,
        "enum value block: entries with values": enum_block_with_values,
        "enum value block: value lines": enum_value_lines,
        "member tags": dict(tags.most_common()),
    }


def enum_value_count(lines: list[str], enum_name: str) -> int | None:
    """Number of value lines listed under one enum in the value block, or None."""
    count: int | None = None
    for l in lines:
        if count is None:
            if l.startswith("    ") and not l.startswith("        ") and l.strip() == enum_name:
                count = 0
            continue
        if l.startswith("        ") and l.strip():
            count += 1
        else:
            break
    return count


def fex_counts(lines: list[str]) -> dict[str, int]:
    names = set()
    for l in lines:
        m = CALL_NAME.search(l)
        if m:
            names.add(m.group(1))
    return {"fex lines": len(lines), "fex distinct function names": len(names)}


def exc_file_name(exc: OSError) -> str:
    """Base name of the file an OSError is about (never the absolute path)."""
    return Path(exc.filename).name if exc.filename else "input"


def report(help_log: Path, fex: Path | None, enum_name: str | None) -> None:
    print(f"help.log sha256: {sha256_of(help_log)}")
    help_lines = read_lines(help_log)
    for key, value in help_counts(help_lines).items():
        print(f"{key}: {value}")
    if enum_name:
        n = enum_value_count(help_lines, enum_name)
        shown = "not listed" if n is None else n
        print(f"value lines for {enum_name}: {shown}")
    if fex is not None:
        print(f"fex sha256: {sha256_of(fex)}")
        for key, value in fex_counts(read_lines(fex)).items():
            print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("help_log", type=Path, help="path to DS1 help.log (S3)")
    parser.add_argument("--fex", type=Path, help="path to fex-1.1.txt (S2)")
    parser.add_argument(
        "--enum-values", metavar="NAME", help="count value lines for this enum"
    )
    args = parser.parse_args(argv)
    safe_console()

    try:
        help_log = checked_file(args.help_log)
        fex = checked_file(args.fex) if args.fex is not None else None
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        report(help_log, fex, args.enum_values)
    except OSError as exc:
        print(f"error: {exc_file_name(exc)}: file locked or unreadable ({os_error_text(exc)})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
