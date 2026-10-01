#!/usr/bin/env python3
"""Cross-tabulate exported member-name prefixes against FuBi tags (counts only).

Input: `help.log` from GPG's public `help-1.1.zip` (DS1 v1.11 Skrit help
dump; source S3 in docs/research/scripting/gas-skrit-public-docs.md). This is
a DS1 documentation download, not a DS2 game file. Like every research
script, it refuses inputs inside the repository (including the git-ignored
`local/`): keep it in a folder outside it, for example
`%USERPROFILE%\\Re-Sieged-inputs\\gasskrit\\`.

For every member line of the "** Classes **" section, the function name is
put in one prefix bucket: `S` (S + upper + lower, e.g. SFoo), `RS`, `RC`, or
`other`. For each bucket the script prints the total and how many lines carry
the [RPC], [CHECK_SERVER] and [!SKRIT] tags. No names are printed.

Supports: gas-skrit-public-docs.md "Name-prefix convention" (an Inference
about DS1 only). Standard library only; runs on Windows.

Usage:
    python tools/research/prefixstats.py <path/to/help.log>
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
CALL_NAME = re.compile(r"(\w+)\s*\(")
TAGS = ("RPC", "CHECK_SERVER", "!SKRIT")
BUCKETS = ("S", "RS", "RC", "other")


def bucket(name: str) -> str:
    if re.match(r"RS[A-Z]", name):
        return "RS"
    if re.match(r"RC[A-Z]", name):
        return "RC"
    if re.match(r"S[A-Z][a-z]", name):
        return "S"
    return "other"


def class_member_lines(path: Path) -> list[str]:
    lines = [
        TIMESTAMP_PREFIX.sub("", l)
        for l in path.read_text(encoding="latin-1").splitlines()
    ]
    out: list[str] = []
    in_classes = False
    for l in lines:
        if l.startswith("** ") and l.rstrip().endswith("**"):
            in_classes = l.strip("* ").strip() == "Classes"
            continue
        if in_classes and l.startswith("    ") and "(" in l:
            out.append(l)
    return out


def report(help_log: Path) -> None:
    totals: Counter[str] = Counter()
    tagged: Counter[tuple[str, str]] = Counter()
    for line in class_member_lines(help_log):
        m = CALL_NAME.search(line)
        if not m:
            continue
        b = bucket(m.group(1))
        totals[b] += 1
        for t in TAGS:
            if f"[{t}]" in line:
                tagged[(b, t)] += 1

    digest = hashlib.sha256(help_log.read_bytes()).hexdigest()
    print(f"help.log sha256: {digest}")
    print("prefix\ttotal\t" + "\t".join(TAGS))
    for b in BUCKETS:
        print(f"{b}\t{totals[b]}\t" + "\t".join(str(tagged[(b, t)]) for t in TAGS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("help_log", type=Path, help="path to DS1 help.log (S3)")
    args = parser.parse_args(argv)
    safe_console()
    try:
        help_log = check_input_path(args.help_log)
        if not help_log.is_file():
            raise UsageError(f"not a file: {args.help_log}")
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        report(help_log)
    except OSError as exc:
        name = Path(exc.filename).name if exc.filename else "input"
        print(f"error: {name}: file locked or unreadable ({os_error_text(exc)})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
