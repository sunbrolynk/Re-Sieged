"""Shared helpers for the Re-Sieged Phase 1 research scripts.

Research-grade code (see docs/research/plan.md, WS-1): standard library only,
runs on Windows, no architectural commitment.

The helpers here enforce the two safety boundaries every script shares:

* Input boundary: game files are read only from a path the user passes, and
  never from inside the repository (so nothing proprietary is ever expected
  to live in the working tree).
* Output boundary: raw output goes to a user-given folder that defaults to
  <repo>/local/<script>/ (git-ignored). A folder inside the repository but
  outside local/ is refused, so raw output cannot land in docs/ or tools/.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

TOOL_VERSION = "0.2.0"  # 0.2.0: review fixes (new JSON keys, change-only method)
SIGNATURE_LEN = 8  # bytes; the longest file-start signature we ever report
HASH_CHUNK = 1024 * 1024


class UsageError(Exception):
    """Raised for a refused input/output path or other user-facing error."""


def repo_root() -> Path:
    """The repository root: this file lives in <repo>/tools/research/."""
    return Path(__file__).resolve().parents[2]


def _resolve(path: Path) -> Path:
    r"""Canonicalise a user path. The single place paths are resolved.

    On Windows, resolve() leaves some spellings of the same folder unequal to
    the repository path (a UNC admin share such as \\localhost\c$\..., an
    extended-length \\?\ prefix, a subst drive). is_inside() therefore also
    compares file identity. Tests replace this function to simulate such a
    non-canonical result on other platforms.
    """
    return path.expanduser().resolve()


def _strip_extended_prefix(text: str) -> str:
    r"""Remove a Windows extended-length prefix (\\?\C:\... or \\?\UNC\host\...)."""
    for prefix, replacement in (("\\\\?\\UNC\\", "\\\\"), ("\\\\?\\", ""),
                                ("//?/UNC/", "//"), ("//?/", "")):
        if text[:len(prefix)].upper() == prefix.upper():
            return replacement + text[len(prefix):]
    return text


def _lexically_within(path: Any, parent: Any, pathmod: Any = os.path) -> bool:
    """Lexical containment; `pathmod` is os.path (tests pass ntpath to check Windows rules)."""
    a = pathmod.normcase(_strip_extended_prefix(str(path)))
    b = pathmod.normcase(_strip_extended_prefix(str(parent)))
    try:
        return pathmod.commonpath([a, b]) == pathmod.commonpath([b])
    except ValueError:  # different drives, or mixed absolute/relative
        return False


def _same_dir(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except (OSError, ValueError):
        return False


def is_inside(path: Path, parent: Path) -> bool:
    r"""True if `path` is `parent` or lies below it.

    Decided two ways, so that no spelling of a path slips through: a lexical
    comparison (case-insensitive on Windows, extended-length prefix removed),
    and a file-identity comparison (os.path.samefile) of every existing
    ancestor of `path` with `parent`. The identity check covers junctions,
    subst drives, UNC admin shares and \\?\ paths that name the same folder.
    """
    if _lexically_within(path, parent):
        return True
    if not parent.exists():
        return False
    for ancestor in (path, *path.parents):
        if ancestor.exists() and _same_dir(ancestor, parent):
            return True
    return False


def check_input_path(path: Path) -> Path:
    """Resolve an input path and refuse it if it does not exist or is in the repo."""
    resolved = _resolve(path)
    if not resolved.exists():
        raise UsageError(f"input not found: {path}")
    if is_inside(resolved, repo_root()):
        raise UsageError(
            f"refusing to read {path}: inputs must be outside the repository "
            "(game files and saves never live in the working tree)"
        )
    return resolved


def default_out_dir(script_name: str) -> Path:
    return repo_root() / "local" / script_name


def check_output_dir(out: Path | None, script_name: str, inputs: Iterable[Path] = ()) -> Path:
    """Return the output folder.

    Refused: a repository folder other than local/; a folder inside any input
    folder, or the folder that directly holds an input file (the scripts never
    write next to their inputs); an existing path that is not a folder.
    """
    target = _resolve(out if out is not None else default_out_dir(script_name))
    root = repo_root()
    if is_inside(target, root) and not is_inside(target, root / "local"):
        raise UsageError(
            f"refusing to write to {target}: inside the repository, raw output may "
            "only go under local/ (git-ignored)"
        )
    for source in inputs:
        if source.is_dir():
            inside = is_inside(target, source)
        else:
            holder = source.parent
            inside = (_lexically_within(target, holder) and _lexically_within(holder, target)) \
                or _same_dir(target, holder)
        if inside:
            raise UsageError(
                f"refusing to write to {target}: the output folder must not be inside an input "
                "folder or next to an input file (inputs are never written to)"
            )
    if target.exists() and not target.is_dir():
        raise UsageError(f"refusing to write to {target}: it exists and is not a folder")
    return target


FILE_ATTRIBUTE_REPARSE_POINT = 0x400  # Windows: symlinks, junctions, mount points


def is_link_stat(st: os.stat_result) -> bool:
    """True for a symlink, or (Windows) any reparse point such as a junction."""
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def is_link_or_junction(path: Path) -> bool:
    """True if `path` is a symlink or a Windows junction/reparse point (not followed).

    os.walk(followlinks=False) and Path.is_symlink() do not treat a junction
    as a link on the Python versions this project supports, so walking a
    folder must check the reparse-point attribute itself.
    """
    try:
        return is_link_stat(os.lstat(path))
    except OSError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def is_printable_ascii(data: bytes) -> bool:
    return len(data) > 0 and all(0x20 <= b <= 0x7E for b in data)


def signature(data: bytes) -> dict[str, Any]:
    """Describe at most the first SIGNATURE_LEN bytes: hex always, text only if printable."""
    head = data[:SIGNATURE_LEN]
    return {
        "hex": head.hex(),
        "ascii": head.decode("ascii") if is_printable_ascii(head) else None,
        "length": len(head),
    }


def read_head(path: Path, count: int = SIGNATURE_LEN) -> bytes:
    with path.open("rb") as handle:
        return handle.read(count)


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits per byte (0.0 for empty input)."""
    if not data:
        return 0.0
    total = len(data)
    entropy = 0.0
    for c in Counter(data).values():
        p = c / total
        entropy -= p * math.log2(p)
    return round(abs(entropy), 4)


def block_entropy_summary(data: bytes, block: int = 4096) -> dict[str, Any]:
    """Min / mean / max entropy over fixed-size blocks (last partial block included)."""
    values = [shannon_entropy(data[i:i + block]) for i in range(0, len(data), block)]
    if not values:
        return {"block_size": block, "blocks": 0, "min": None, "mean": None, "max": None}
    return {
        "block_size": block,
        "blocks": len(values),
        "min": min(values),
        "mean": round(sum(values) / len(values), 4),
        "max": max(values),
    }


def write_json(path: Path, payload: Any) -> None:
    """Deterministic JSON: sorted keys, fixed indent, LF line endings, UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_text(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip("\n") + "\n")


def safe_console() -> None:
    """Avoid UnicodeEncodeError on legacy Windows consoles (cp1252 etc.)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


# C0/C1 control characters, line/paragraph separators and bidirectional
# overrides: they can break a Markdown table row or disguise text.
_UNSAFE_CHARS = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029\u202a-\u202e\u2066-\u2069]")


def md_escape(text: str) -> str:
    """Escape characters that would break a Markdown table cell or code span.

    Control and bidi characters become visible \\xNN / \\uNNNN escapes.
    """
    text = _UNSAFE_CHARS.sub(
        lambda m: f"\\x{ord(m.group()):02x}" if ord(m.group()) < 0x100 else f"\\u{ord(m.group()):04x}", text)
    return text.replace("|", "\\|").replace("`", "'")


def os_error_text(exc: OSError) -> str:
    """Locale-independent description of an OSError: type, errno, winerror.

    exc.strerror is translated by the OS (for example German Windows), so it
    would make output differ between machines; the numbers do not.
    """
    parts = [type(exc).__name__]
    if exc.errno is not None:
        parts.append(f"errno {exc.errno}")
    winerror = getattr(exc, "winerror", None)
    if winerror is not None:
        parts.append(f"winerror {winerror}")
    return " ".join(parts)
