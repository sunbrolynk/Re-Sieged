#!/usr/bin/env python3
"""Compare two or three save snapshots (derived facts only).

Implements the comparison spec in docs/research/evidence/EV-004-save-diff.md
section 9. Inputs are two or three snapshot folders (or single files), for
example the EV-004 series A, A' and C.

Per file it reports: presence, size, SHA-256, whole-file Shannon entropy, a
per-4 KiB-block entropy summary (min/mean/max), and at most an 8-byte
signature at file start. Per comparison: if sizes are equal, the count of
differing bytes and the differing ranges as (offset, length), merging ranges
separated by fewer than --merge-gap equal bytes (default 16); if sizes differ,
the lengths of the common prefix and common suffix.

With three inputs (A, A', C) it runs A->A' (noise), A'->C (noise + change)
and A->C, and derives "change-only" ranges: the bytes that differ A'->C but
not A->A' (computed on unmerged runs, then merged for display).

Symlinks and Windows junctions inside snapshot folders are listed as skipped
and never followed. A file the game holds open (locked) is reported as
"file locked or unreadable"; close the game and retry.

Changed bytes are NEVER printed or written by default. --show-bytes writes a
separate, clearly named file into the output folder (never to stdout).

Inputs are opened read-only. Output: <name>.diff.json and <name>.diff.md in
the output folder (default <repo>/local/save_diff/).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_common import (  # noqa: E402
    TOOL_VERSION,
    UsageError,
    block_entropy_summary,
    check_input_path,
    check_output_dir,
    is_link_or_junction,
    md_escape,
    os_error_text,
    safe_console,
    shannon_entropy,
    signature,
    write_json,
    write_text,
)

SCRIPT = "save_diff"
CHUNK = 4096
SINGLE_FILE_KEY = "<file>"
SHOW_BYTES_WARNING = (
    "WARNING: --show-bytes writes raw save bytes to a local file. That file is for local "
    "investigation only: never commit it, paste it into docs/, or share it."
)

Range = tuple[int, int]  # (offset, length)


# -- core comparisons ----------------------------------------------------------
def diff_runs(a: bytes, b: bytes) -> tuple[int, list[Range]]:
    """Count differing bytes of equal-length inputs; return the unmerged runs.

    A run is a maximal stretch of consecutive differing bytes, so the runs
    cover exactly the differing bytes.
    """
    if len(a) != len(b):
        raise ValueError("diff_runs needs equal-length inputs")
    count = 0
    runs: list[list[int]] = []  # [start, end_exclusive]
    for base in range(0, len(a), CHUNK):
        ca, cb = a[base:base + CHUNK], b[base:base + CHUNK]
        if ca == cb:
            continue
        for i, (x, y) in enumerate(zip(ca, cb)):
            if x == y:
                continue
            count += 1
            off = base + i
            if runs and runs[-1][1] == off:
                runs[-1][1] = off + 1
            else:
                runs.append([off, off + 1])
    return count, [(s, e - s) for s, e in runs]


def merge_ranges(ranges: list[Range], merge_gap: int) -> list[Range]:
    """Merge sorted ranges separated by fewer than merge_gap bytes (adjacent ones always)."""
    merged: list[list[int]] = []
    for start, length in ranges:
        if merged and start - merged[-1][1] < max(merge_gap, 1):
            merged[-1][1] = max(merged[-1][1], start + length)
        else:
            merged.append([start, start + length])
    return [(s, e - s) for s, e in merged]


def diff_ranges(a: bytes, b: bytes, merge_gap: int = 16) -> tuple[int, list[Range]]:
    """Count differing bytes of equal-length inputs and return merged ranges.

    Two differing runs are merged when fewer than merge_gap equal bytes lie
    between them. Adjacent differing bytes always form one range.
    """
    count, runs = diff_runs(a, b)
    return count, merge_ranges(runs, merge_gap)


def common_prefix(a: bytes, b: bytes) -> int:
    n = min(len(a), len(b))
    pos = 0
    while pos < n:
        step = min(CHUNK, n - pos)
        if a[pos:pos + step] == b[pos:pos + step]:
            pos += step
            continue
        for i in range(step):
            if a[pos + i] != b[pos + i]:
                return pos + i
    return n


def common_suffix(a: bytes, b: bytes, limit: int) -> int:
    """Common suffix length, at most `limit` (so it never overlaps the prefix)."""
    n = 0
    while n < limit and a[len(a) - 1 - n] == b[len(b) - 1 - n]:
        n += 1
    return n


def subtract_ranges(keep: list[Range], remove: list[Range]) -> list[Range]:
    """Parts of `keep` ranges not covered by any `remove` range (sorted by offset).

    A single sweep over both sorted lists: O((n + m) log(n + m)) instead of
    comparing every pair.
    """
    rem: list[list[int]] = []
    for start, length in sorted(remove):
        if length <= 0:
            continue
        if rem and start <= rem[-1][1]:
            rem[-1][1] = max(rem[-1][1], start + length)
        else:
            rem.append([start, start + length])
    result: list[Range] = []
    j = 0
    for start, length in sorted(keep):
        pos, end = start, start + length
        while j < len(rem) and rem[j][1] <= pos:
            j += 1
        k = j
        while pos < end and k < len(rem) and rem[k][0] < end:
            r_start, r_end = rem[k]
            if r_start > pos:
                result.append((pos, r_start - pos))
            pos = max(pos, r_end)
            k += 1
        if pos < end:
            result.append((pos, end - pos))
    return result


def file_facts(data: bytes) -> dict[str, Any]:
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "entropy": shannon_entropy(data),
        "block_entropy": block_entropy_summary(data, CHUNK),
        "signature": signature(data),
    }


def compare(a: bytes | None, b: bytes | None, merge_gap: int, max_ranges: int) -> dict[str, Any]:
    if a is None and b is None:
        return {"presence": "neither"}  # 3-way: the file exists only in the other snapshot
    if a is None or b is None:
        return {"presence": "only_b" if a is None else "only_a"}
    out: dict[str, Any] = {
        "presence": "both",
        "size_a": len(a),
        "size_b": len(b),
        "sha256_equal": a == b,
        "same_size": len(a) == len(b),
    }
    if a == b:
        out.update({"differing_bytes": 0, "range_count": 0, "ranges": [], "ranges_truncated": False})
    elif len(a) == len(b):
        count, runs = diff_runs(a, b)
        ranges = merge_ranges(runs, merge_gap)
        out.update({
            "differing_bytes": count,
            "range_count": len(ranges),
            "ranges": [list(r) for r in ranges[:max_ranges]],
            "ranges_truncated": len(ranges) > max_ranges,
            "_all_ranges": ranges,  # internal; stripped before output
            "_runs": runs,  # internal (unmerged); stripped before output
        })
    else:
        prefix = common_prefix(a, b)
        out.update({
            "common_prefix": prefix,
            "common_suffix": common_suffix(a, b, min(len(a), len(b)) - prefix),
        })
    return out


# -- input collection ----------------------------------------------------------
class SnapshotReadError(Exception):
    """A snapshot file or folder could not be read (for example locked by the game)."""


def read_snapshot(path: Path) -> bytes:
    return path.read_bytes()


def collect(path: Path) -> tuple[dict[str, tuple[str, Path]], list[str]]:
    """Map casefolded relative path -> (relative path, absolute path).

    Also returns the relative paths of symlinks and Windows junctions, which
    are skipped (never followed).
    """
    if path.is_file():
        return {SINGLE_FILE_KEY: (path.name, path)}, []
    files: dict[str, tuple[str, Path]] = {}
    links: list[str] = []

    def on_error(exc: OSError) -> None:
        raise SnapshotReadError(f"a folder in snapshot {path.name} is unreadable ({os_error_text(exc)})")

    for dirpath, dirnames, filenames in os.walk(path, onerror=on_error, followlinks=False):
        base = Path(dirpath)
        descend = []
        for name in sorted(dirnames):
            if is_link_or_junction(base / name):
                links.append((base / name).relative_to(path).as_posix() + "/")
            else:
                descend.append(name)
        dirnames[:] = descend
        for name in filenames:
            full = base / name
            rel = full.relative_to(path).as_posix()
            if is_link_or_junction(full):
                links.append(rel)
            elif full.is_file():
                files[rel.casefold()] = (rel, full)
    return dict(sorted(files.items())), sorted(links, key=lambda r: (r.casefold(), r))


def pair_plan(labels: list[str]) -> list[tuple[int, int, str]]:
    if len(labels) == 2:
        return [(0, 1, f"{labels[0]}->{labels[1]}")]
    return [
        (0, 1, f"{labels[0]}->{labels[1]}"),
        (1, 2, f"{labels[1]}->{labels[2]}"),
        (0, 2, f"{labels[0]}->{labels[2]}"),
    ]


def run(inputs: list[Path], labels: list[str], merge_gap: int = 16, max_ranges: int = 1000,
        show_bytes_limit: int = 0) -> tuple[dict[str, Any], list[str]]:
    """Compare snapshots. Returns (report, raw byte lines for --show-bytes or [])."""
    kinds = {p.is_file() for p in inputs}
    if len(kinds) != 1:
        raise UsageError("inputs must be all files or all folders")
    collected = [collect(p) for p in inputs]
    maps = [m for m, _ in collected]
    if kinds == {True}:
        names = [m[SINGLE_FILE_KEY][0] for m in maps]
    else:
        names = None
    keys = sorted(set().union(*maps))
    plan = pair_plan(labels)
    report: dict[str, Any] = {
        "tool": SCRIPT,
        "tool_version": TOOL_VERSION,
        "labels": labels,
        "input_kind": "files" if names else "folders",
        "input_file_names": names,
        "merge_gap": merge_gap,
        "max_ranges_listed": max_ranges,
        "comparisons": [name for _, _, name in plan],
        "skipped_links": {lab: links for lab, (_, links) in zip(labels, collected)},
        "files": [],
        "note": "Derived facts only. Changed bytes are not included in this report.",
    }
    raw_lines: list[str] = []
    for key in keys:
        entries = [m.get(key) for m in maps]
        rel = next(e[0] for e in entries if e) if key != SINGLE_FILE_KEY else SINGLE_FILE_KEY
        blobs = []
        for e in entries:
            try:
                blobs.append(read_snapshot(e[1]) if e else None)
            except OSError as exc:
                raise SnapshotReadError(f"{e[0] if key == SINGLE_FILE_KEY else rel}: file locked or unreadable "
                                        f"({os_error_text(exc)}); close the game and retry") from None
        record: dict[str, Any] = {
            "path": rel,
            "snapshots": {lab: (file_facts(b) if b is not None else None) for lab, b in zip(labels, blobs)},
            "comparisons": {},
        }
        all_ranges: dict[str, list[Range]] = {}
        all_runs: dict[str, list[Range]] = {}
        for i, j, name in plan:
            result = compare(blobs[i], blobs[j], merge_gap, max_ranges)
            all_ranges[name] = result.pop("_all_ranges", [])
            all_runs[name] = result.pop("_runs", [])
            record["comparisons"][name] = result
            if show_bytes_limit and all_ranges[name]:
                raw_lines.append(f"== {rel} {name}")
                for off, length in all_ranges[name]:
                    shown = min(length, show_bytes_limit)
                    raw_lines.append(f"0x{off:08x} len {length}: "
                                     f"{labels[i]} {blobs[i][off:off + shown].hex()} | "
                                     f"{labels[j]} {blobs[j][off:off + shown].hex()}"
                                     + (" (truncated)" if shown < length else ""))
        if len(labels) == 3:
            record["change_only"] = change_only(plan, record, all_runs, merge_gap, max_ranges)
        report["files"].append(record)
    report["totals"] = totals(report, plan)
    return report, raw_lines


def change_only(plan, record, all_runs, merge_gap: int, max_ranges: int) -> dict[str, Any]:
    """Bytes that differ A'->C but did not differ A->A' (the noise pair).

    Works on the unmerged differing runs of both comparisons, so a real change
    that sits in the gap between two merged noise runs is kept; the result is
    re-merged with the same merge gap for display.
    """
    noise_name, change_name = plan[0][2], plan[1][2]
    noise, change = record["comparisons"][noise_name], record["comparisons"][change_name]
    if noise.get("presence") != "both" or change.get("presence") != "both":
        return {"available": False, "reason": "file missing from at least one snapshot"}
    if not (noise["same_size"] and change["same_size"]):
        return {"available": False, "reason": "sizes differ, so byte offsets are not comparable"}
    pieces = subtract_ranges(all_runs[change_name], all_runs[noise_name])
    ranges = merge_ranges(pieces, merge_gap)
    return {
        "available": True,
        "method": (f"differing bytes of {change_name} minus differing bytes of {noise_name} "
                   f"(unmerged runs), then merged with the merge gap"),
        "differing_bytes": sum(n for _, n in pieces),
        "range_count": len(ranges),
        "ranges": [list(r) for r in ranges[:max_ranges]],
        "ranges_truncated": len(ranges) > max_ranges,
    }


def totals(report: dict[str, Any], plan) -> dict[str, Any]:
    out = {}
    for _, _, name in plan:
        comps = [f["comparisons"][name] for f in report["files"]]
        out[name] = {
            "files": sum(1 for c in comps if c["presence"] != "neither"),
            "only_a": sum(1 for c in comps if c["presence"] == "only_a"),
            "only_b": sum(1 for c in comps if c["presence"] == "only_b"),
            "identical": sum(1 for c in comps if c.get("sha256_equal")),
            "changed_same_size": sum(1 for c in comps if c.get("presence") == "both"
                                     and not c["sha256_equal"] and c["same_size"]),
            "changed_size": sum(1 for c in comps if c.get("presence") == "both" and not c["same_size"]),
        }
    return out


# -- output --------------------------------------------------------------------
def render_summary(r: dict[str, Any], max_list: int = 10) -> list[str]:
    lines = [
        f"# Save diff: {' / '.join(md_escape(x) for x in r['labels'])}",
        "",
        f"Generated by `tools/research/{SCRIPT}.py` v{r['tool_version']}. Derived facts only: "
        f"sizes, hashes, counts, offsets, entropy, at most 8 signature bytes. Merge gap: {r['merge_gap']} bytes.",
        "",
        "## Totals",
        "",
        "| Comparison | Files | Only in first | Only in second | Identical | Changed (same size) | Changed (size) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, t in r["totals"].items():
        lines.append(f"| {md_escape(name)} | {t['files']} | {t['only_a']} | {t['only_b']} | {t['identical']} | "
                     f"{t['changed_same_size']} | {t['changed_size']} |")
    for lab, links in r.get("skipped_links", {}).items():
        if links:
            lines += ["", f"Skipped links/junctions in {md_escape(lab)} (not followed): "
                      + ", ".join(f"`{md_escape(x)}`" for x in links)]
    lines += ["", "## Per file", ""]
    for f in r["files"]:
        lines += [f"### `{md_escape(f['path'])}`", "",
                  "| Snapshot | Size | SHA-256 | Entropy | Block entropy min/mean/max | First 8 bytes |",
                  "| --- | ---: | --- | ---: | --- | --- |"]
        for lab, facts in f["snapshots"].items():
            if facts is None:
                lines.append(f"| {md_escape(lab)} | absent | | | | |")
                continue
            be, sig = facts["block_entropy"], facts["signature"]
            text = f" (`{md_escape(sig['ascii'])}`)" if sig["ascii"] else ""
            lines.append(f"| {md_escape(lab)} | {facts['size']:,} | {facts['sha256']} | {facts['entropy']} | "
                         f"{be['min']}/{be['mean']}/{be['max']} | `{sig['hex']}`{text} |")
        lines.append("")
        for name, c in f["comparisons"].items():
            lines.append("- " + md_escape(name) + ": " + describe(c, max_list))
        if "change_only" in f:
            co = f["change_only"]
            if co["available"]:
                lines.append(f"- change-only ({co['method']}): {co['differing_bytes']} differing bytes in "
                             f"{co['range_count']} ranges{fmt_ranges(co['ranges'], max_list)}")
            else:
                lines.append(f"- change-only: not available ({co['reason']})")
        lines.append("")
    return lines


def fmt_ranges(ranges: list[list[int]], max_list: int) -> str:
    if not ranges:
        return ""
    shown = ", ".join(f"(0x{o:x}, {n})" for o, n in ranges[:max_list])
    more = f", ... {len(ranges) - max_list} more in JSON" if len(ranges) > max_list else ""
    return f": {shown}{more}"


def describe(c: dict[str, Any], max_list: int) -> str:
    if c["presence"] == "neither":
        return "absent from both snapshots"
    if c["presence"] != "both":
        return "only in first snapshot" if c["presence"] == "only_a" else "only in second snapshot"
    if c["sha256_equal"]:
        return "identical"
    if c["same_size"]:
        return (f"{c['differing_bytes']} differing bytes in {c['range_count']} ranges"
                + fmt_ranges(c["ranges"], max_list))
    return (f"size {c['size_a']:,} -> {c['size_b']:,}; common prefix {c['common_prefix']:,}, "
            f"common suffix {c['common_suffix']:,}")


def sanitize(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._") or "snapshot"


def main(argv: list[str] | None = None) -> int:
    safe_console()
    parser = argparse.ArgumentParser(
        description="Compare 2 or 3 save snapshots (files or folders): sizes, SHA-256, changed-byte "
                    "counts and ranges, entropy, 8-byte signatures. Never outputs changed bytes by default.")
    parser.add_argument("snapshots", nargs="+", type=Path,
                        help="2 or 3 snapshot folders or files, in order (e.g. A A2 C); outside the repository")
    parser.add_argument("--labels", nargs="+", default=None, help="labels for the snapshots (default: folder/file names)")
    parser.add_argument("--out", type=Path, default=None, help=f"output folder (default: <repo>/local/{SCRIPT}/)")
    parser.add_argument("--name", default=None, help="output file prefix (default: labels joined with _vs_)")
    parser.add_argument("--merge-gap", type=int, default=16,
                        help="merge differing ranges separated by fewer than this many equal bytes (default 16)")
    parser.add_argument("--max-ranges", type=int, default=1000,
                        help="max ranges listed per comparison in the JSON (counts stay exact; default 1000)")
    parser.add_argument("--show-bytes", action="store_true",
                        help="ALSO write changed bytes (hex) to a separate local file. Off by default. Never commit it.")
    parser.add_argument("--show-bytes-limit", type=int, default=64,
                        help="max bytes shown per range with --show-bytes (default 64)")
    args = parser.parse_args(argv)

    if len(args.snapshots) not in (2, 3):
        parser.error("give 2 or 3 snapshots")
    if args.labels is not None and len(args.labels) != len(args.snapshots):
        parser.error("--labels needs one label per snapshot")
    if args.merge_gap < 0 or args.max_ranges < 0 or args.show_bytes_limit < 1:
        parser.error("--merge-gap/--max-ranges must be >= 0 and --show-bytes-limit >= 1")

    try:
        inputs = [check_input_path(p) for p in args.snapshots]
        out_dir = check_output_dir(args.out, SCRIPT, inputs)
        labels = [sanitize(x) for x in (args.labels or [p.name for p in inputs])]
        if len(set(labels)) != len(labels):
            raise UsageError("snapshot labels must be unique; pass --labels")
        if args.show_bytes:
            print(SHOW_BYTES_WARNING, file=sys.stderr)
        report, raw = run(inputs, labels, args.merge_gap, args.max_ranges,
                          args.show_bytes_limit if args.show_bytes else 0)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SnapshotReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    name = sanitize(args.name) if args.name else "_vs_".join(labels)
    json_path, md_path = out_dir / f"{name}.diff.json", out_dir / f"{name}.diff.md"
    try:
        write_json(json_path, report)
        write_text(md_path, render_summary(report))
    except OSError as exc:
        print(f"error: cannot write output ({os_error_text(exc)})", file=sys.stderr)
        return 1
    for comp, t in report["totals"].items():
        print(f"{comp}: {t['files']} files, {t['identical']} identical, {t['changed_same_size']} changed "
              f"(same size), {t['changed_size']} changed size, {t['only_a']} only-first, {t['only_b']} only-second")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    if args.show_bytes:
        raw_path = out_dir / f"{name}.RAW-BYTES-DO-NOT-COMMIT.txt"
        try:
            write_text(raw_path, ["# Raw changed bytes (hex). Local investigation only. Never commit or share.",
                                  *raw] if raw else ["# No differing ranges."])
        except OSError as exc:
            print(f"error: cannot write output ({os_error_text(exc)})", file=sys.stderr)
            return 1
        print(f"wrote {raw_path} (raw bytes; do not commit)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
