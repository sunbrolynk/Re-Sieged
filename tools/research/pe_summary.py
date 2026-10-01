#!/usr/bin/env python3
"""Summarise a Windows PE32/PE32+ file (derived facts only, standard library).

Reports: machine, COFF timestamp, characteristics, image base, entry point,
subsystem, section table (with per-section entropy), data directories,
imports and delay-load imports (DLL + function names), exports (count +
names), resource types, version-resource values (FileVersion/ProductVersion
by default), SHA-256 and overlay size.

FuBi test (CLM-035, docs/research/scripting/gas-skrit-public-docs.md): counts
exports and heuristically classifies export names as MSVC-decorated C++
("?name@scope@@..."), C-decorated (_name@N / @name@N) or undecorated, with up
to N example names. An empty export table is reported as "no exports found",
which is NOT evidence that FuBi is absent: retail builds may strip the export
data or pack it into a resource.

Optional --count-string counts occurrences of a user-given text (ASCII and
UTF-16LE) and reports counts and offsets only.

Supports: CLM-001..006, CLM-035, CLM-070. Output: <label>.pe.json and
<label>.pe.md in the output folder (default <repo>/local/pe_summary/).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_common import (  # noqa: E402
    TOOL_VERSION,
    UsageError,
    check_input_path,
    check_output_dir,
    md_escape,
    os_error_text,
    safe_console,
    shannon_entropy,
    write_json,
    write_text,
)

SCRIPT = "pe_summary"

MACHINES = {
    0x014C: "i386", 0x8664: "AMD64", 0x01C0: "ARM", 0x01C4: "ARMNT",
    0xAA64: "ARM64", 0x0200: "IA64", 0x0000: "unknown",
}
SUBSYSTEMS = {
    0: "unknown", 1: "native", 2: "windows_gui", 3: "windows_cui", 5: "os2_cui",
    7: "posix_cui", 9: "windows_ce_gui", 10: "efi_application",
    11: "efi_boot_service_driver", 12: "efi_runtime_driver", 13: "efi_rom",
    14: "xbox", 16: "windows_boot_application",
}
FILE_CHARACTERISTICS = {
    0x0001: "RELOCS_STRIPPED", 0x0002: "EXECUTABLE_IMAGE", 0x0004: "LINE_NUMS_STRIPPED",
    0x0008: "LOCAL_SYMS_STRIPPED", 0x0020: "LARGE_ADDRESS_AWARE", 0x0100: "32BIT_MACHINE",
    0x0200: "DEBUG_STRIPPED", 0x0400: "REMOVABLE_RUN_FROM_SWAP", 0x0800: "NET_RUN_FROM_SWAP",
    0x1000: "SYSTEM", 0x2000: "DLL", 0x4000: "UP_SYSTEM_ONLY",
}
DLL_CHARACTERISTICS = {
    0x0020: "HIGH_ENTROPY_VA", 0x0040: "DYNAMIC_BASE", 0x0080: "FORCE_INTEGRITY",
    0x0100: "NX_COMPAT", 0x0200: "NO_ISOLATION", 0x0400: "NO_SEH", 0x0800: "NO_BIND",
    0x1000: "APPCONTAINER", 0x2000: "WDM_DRIVER", 0x4000: "GUARD_CF",
    0x8000: "TERMINAL_SERVER_AWARE",
}
SECTION_FLAGS = {
    0x00000020: "CODE", 0x00000040: "INITIALIZED_DATA", 0x00000080: "UNINITIALIZED_DATA",
    0x20000000: "EXECUTE", 0x40000000: "READ", 0x80000000: "WRITE",
}
DATA_DIRECTORY_NAMES = (
    "export", "import", "resource", "exception", "security", "basereloc", "debug",
    "architecture", "globalptr", "tls", "load_config", "bound_import", "iat",
    "delay_import", "clr_runtime", "reserved",
)
RESOURCE_TYPES = {
    1: "RT_CURSOR", 2: "RT_BITMAP", 3: "RT_ICON", 4: "RT_MENU", 5: "RT_DIALOG",
    6: "RT_STRING", 7: "RT_FONTDIR", 8: "RT_FONT", 9: "RT_ACCELERATOR", 10: "RT_RCDATA",
    11: "RT_MESSAGETABLE", 12: "RT_GROUP_CURSOR", 14: "RT_GROUP_ICON", 16: "RT_VERSION",
    17: "RT_DLGINCLUDE", 19: "RT_PLUGPLAY", 20: "RT_VXD", 21: "RT_ANICURSOR",
    22: "RT_ANIICON", 23: "RT_HTML", 24: "RT_MANIFEST",
}
RT_VERSION = 16
DEFAULT_VERSION_KEYS = ("FileVersion", "ProductVersion")
MAX_IMPORT_DESCRIPTORS = 4096
MAX_THUNKS = 65536            # per thunk table
MAX_TOTAL_THUNKS = 200_000    # per file, imports + delay imports (anti-amplification)
MAX_EXPORT_NAMES = 1_000_000
MAX_NAME_BYTES = 512          # longest import/export/DLL name read; longer is marked truncated
MAX_TOTAL_NAME_CHARS = 16_000_000  # all names returned per file (anti-amplification: overlapping names)
MAX_VALUE_CHARS = 128         # version values and resource type names
MAX_RESOURCE_ENTRIES = 100_000  # directory entries visited in the whole resource tree
MAX_RESOURCE_DEPTH = 4
MAX_VERSION_DEPTH = 8         # VS_VERSIONINFO nesting (real files use 4)
MAX_VERSION_LEAVES = 16       # RT_VERSION leaves parsed per file
TRUNCATED_MARK = "...(truncated)"
C_DECORATED = re.compile(r"^[_@][A-Za-z_][A-Za-z0-9_]*@[0-9]+\Z")
NO_EXPORTS_NOTE = (
    "no exports found. This is NOT evidence that FuBi is absent: retail builds may "
    "strip export data or pack it into a resource (classify as search limitation)."
)


class PEError(Exception):
    """The input is not a PE file, or a structure is out of bounds."""


class PEBudgetError(PEError):
    """A structure is implausibly large or self-referencing (possible crafted file).

    Unlike a plain PEError, per-entry tolerance never swallows this one: it
    stops the whole table.
    """


def cap_text(text: str, limit: int = MAX_VALUE_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + TRUNCATED_MARK


def flags(value: int, table: dict[int, str]) -> list[str]:
    return [name for bit, name in sorted(table.items()) if value & bit]


def version_string(ms: int, ls: int) -> str:
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


class PEFile:
    """Minimal read-only PE parser. All reads are bounds-checked."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        if len(data) < 0x40 or data[:2] != b"MZ":
            raise PEError("no MZ header")
        self.pe_offset = self.u32(0x3C)
        if self.data[self.pe_offset:self.pe_offset + 4] != b"PE\0\0":
            raise PEError("no PE signature at e_lfanew")
        coff = self.pe_offset + 4
        (self.machine, self.num_sections, self.timestamp, _sym_ptr, _sym_count,
         self.opt_size, self.characteristics) = self.unpack("<HHIIIHH", coff)
        self.opt_offset = coff + 20
        self.magic = self.u16(self.opt_offset)
        if self.magic == 0x10B:
            self.is_plus = False
        elif self.magic == 0x20B:
            self.is_plus = True
        else:
            raise PEError(f"unknown optional-header magic 0x{self.magic:04x}")
        self.ptr_size = 8 if self.is_plus else 4
        o = self.opt_offset
        self.linker_version = "{}.{}".format(*self.unpack("<BB", o + 2))
        self.entry_point = self.u32(o + 16)
        self.image_base = self.u64(o + 24) if self.is_plus else self.u32(o + 28)
        (self.section_alignment, self.file_alignment, os_major, os_minor, _img_major, _img_minor,
         sub_major, sub_minor, _win32, self.size_of_image, self.size_of_headers, self.checksum,
         self.subsystem, self.dll_characteristics) = self.unpack("<IIHHHHHHIIIIHH", o + 32)
        self.os_version = f"{os_major}.{os_minor}"
        self.subsystem_version = f"{sub_major}.{sub_minor}"
        dd_count_off = o + (108 if self.is_plus else 92)
        num_dirs = min(self.u32(dd_count_off), 16)
        self.data_dirs: list[tuple[int, int]] = []
        for i in range(num_dirs):
            self.data_dirs.append(self.unpack("<II", dd_count_off + 4 + 8 * i))
        self.sections = self._parse_sections(self.opt_offset + self.opt_size)
        self._thunk_budget = MAX_TOTAL_THUNKS
        self._name_cache: dict[int, str] = {}
        self._name_budget = MAX_TOTAL_NAME_CHARS
        self._res_tree: list[tuple[int | str, list[tuple[int, int]]]] | None = None

    # -- low-level reads -------------------------------------------------
    def unpack(self, fmt: str, offset: int) -> tuple:
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(self.data):
            raise PEError(f"read of {size} bytes at 0x{offset:x} is out of bounds")
        return struct.unpack_from(fmt, self.data, offset)

    def u16(self, offset: int) -> int:
        return self.unpack("<H", offset)[0]

    def u32(self, offset: int) -> int:
        return self.unpack("<I", offset)[0]

    def u64(self, offset: int) -> int:
        return self.unpack("<Q", offset)[0]

    def _parse_sections(self, offset: int) -> list[dict[str, Any]]:
        sections = []
        for i in range(self.num_sections):
            base = offset + 40 * i
            raw_name = self.data[base:base + 8]
            (vsize, va, raw_size, raw_ptr, _r, _l, _nr, _nl, chars) = self.unpack("<IIIIIIHHI", base + 8)
            sections.append({
                "name": raw_name.rstrip(b"\0").decode("ascii", errors="replace"),
                "virtual_address": va, "virtual_size": vsize,
                "raw_offset": raw_ptr, "raw_size": raw_size, "characteristics": chars,
            })
        return sections

    def rva_to_offset(self, rva: int) -> int | None:
        if rva < 0:
            return None  # e.g. an old-style VA below the image base
        for s in self.sections:
            span = max(s["virtual_size"], s["raw_size"])
            if s["virtual_address"] <= rva < s["virtual_address"] + span:
                delta = rva - s["virtual_address"]
                if delta >= s["raw_size"]:
                    return None  # in virtual-only (zero-fill) part
                off = s["raw_offset"] + delta
                return off if off < len(self.data) else None
        if rva < self.size_of_headers and rva < len(self.data):
            return rva
        return None

    def off(self, rva: int) -> int:
        offset = self.rva_to_offset(rva)
        if offset is None:
            raise PEError(f"RVA 0x{rva:x} does not map to file data")
        return offset

    def cstring(self, rva: int) -> str:
        """NUL-terminated name at `rva`; at most MAX_NAME_BYTES, else marked truncated.

        Cached by RVA, so many pointers to one name cost one read.
        """
        cached = self._name_cache.get(rva)
        if cached is not None:
            return self._charge_name(cached)
        start = self.off(rva)
        end = self.data.find(b"\0", start, start + MAX_NAME_BYTES)
        if end < 0:
            text = self.data[start:start + MAX_NAME_BYTES].decode("latin-1") + TRUNCATED_MARK
        else:
            text = self.data[start:end].decode("latin-1")
        self._name_cache[rva] = text
        return self._charge_name(text)

    def _charge_name(self, text: str) -> str:
        """Count every returned name against a per-file budget.

        The RVA cache does not help against names that overlap (pointers one
        byte apart into one long string), so the output size is capped here.
        """
        self._name_budget -= len(text)
        if self._name_budget < 0:
            raise PEBudgetError(f"more than {MAX_TOTAL_NAME_CHARS:,} characters of import/export names "
                                "in this file; stopped (possible crafted file)")
        return text

    def check_array(self, offset: int, count: int, item_size: int, what: str) -> None:
        if count * item_size > len(self.data) - offset:
            raise PEError(f"{what} ({count} entries) runs past the end of the file")

    def data_dir(self, index: int) -> tuple[int, int]:
        return self.data_dirs[index] if index < len(self.data_dirs) else (0, 0)

    # -- imports -----------------------------------------------------------
    def _thunk_names(self, thunk_rva: int, va_based: bool = False) -> list[str]:
        names = []
        ordinal_flag = 1 << (self.ptr_size * 8 - 1)
        pos = self.off(thunk_rva)
        for _ in range(MAX_THUNKS):
            value = self.u64(pos) if self.is_plus else self.u32(pos)
            if value == 0:
                break
            self._thunk_budget -= 1
            if self._thunk_budget < 0:
                raise PEBudgetError(f"more than {MAX_TOTAL_THUNKS} import thunks in this file; "
                                    "stopped (possible crafted file)")
            if value & ordinal_flag:
                names.append(f"#{value & 0xFFFF}")
            else:
                hint_rva = value & 0x7FFFFFFF
                if va_based:
                    hint_rva = value - self.image_base
                names.append(self.cstring(hint_rva + 2))
            pos += self.ptr_size
        return names

    def _descriptor(self, name_of, functions_of) -> dict[str, Any]:
        """One import descriptor; a bad name or thunk is recorded, not fatal."""
        entry: dict[str, Any] = {"dll": None, "functions": []}
        try:
            entry["dll"] = name_of()
            entry["functions"] = functions_of()
        except PEBudgetError:
            raise
        except PEError as exc:
            entry["error"] = str(exc)
        return entry

    def imports(self) -> list[dict[str, Any]]:
        rva, size = self.data_dir(1)
        if not rva or not size:
            return []
        result = []
        pos = self.off(rva)
        for _ in range(MAX_IMPORT_DESCRIPTORS):
            try:
                oft, _ts, _fwd, name_rva, ft = self.unpack("<IIIII", pos)
            except PEError as exc:
                result.append({"dll": None, "functions": [], "error": f"descriptor table: {exc}"})
                break
            if not (oft or name_rva or ft):
                break
            result.append(self._descriptor(lambda: self.cstring(name_rva),
                                           lambda: self._thunk_names(oft or ft)))
            pos += 20
        return result

    def delay_imports(self) -> list[dict[str, Any]]:
        rva, size = self.data_dir(13)
        if not rva or not size:
            return []
        result = []
        pos = self.off(rva)
        for _ in range(MAX_IMPORT_DESCRIPTORS):
            try:
                attrs, name_rva, _hmod, iat, int_rva, _biat, _uiat, _ts = self.unpack("<IIIIIIII", pos)
            except PEError as exc:
                result.append({"dll": None, "functions": [], "error": f"descriptor table: {exc}"})
                break
            if not (attrs or name_rva or iat or int_rva):
                break
            va_based = not (attrs & 1)  # old-style descriptors hold VAs, not RVAs
            base = self.image_base if va_based else 0
            result.append(self._descriptor(
                lambda: self.cstring(name_rva - base),
                lambda: self._thunk_names(int_rva - base, va_based) if int_rva else []))
            pos += 32
        return result

    # -- exports -----------------------------------------------------------
    def exports(self) -> dict[str, Any]:
        rva, size = self.data_dir(0)
        if not rva or not size:
            return empty_exports(present=False)
        (_c, _ts, _maj, _min, name_rva, base, n_funcs, n_names,
         funcs_rva, names_rva, ords_rva) = self.unpack("<IIHHIIIIIII", self.off(rva))
        if n_names > MAX_EXPORT_NAMES or n_funcs > MAX_EXPORT_NAMES:
            raise PEError("export table counts are implausibly large")
        names = []
        unreadable, first_error = 0, None
        if n_names:
            names_pos = self.off(names_rva)
            self.check_array(names_pos, n_names, 4, "export name pointer table")
            for i in range(n_names):
                try:
                    names.append(self.cstring(self.u32(names_pos + 4 * i)))
                except PEBudgetError:
                    raise
                except PEError as exc:  # one bad name must not hide the others
                    unreadable += 1
                    first_error = first_error or f"name {i}: {exc}"
        forwarders = 0
        if n_funcs:
            funcs_pos = self.off(funcs_rva)
            self.check_array(funcs_pos, n_funcs, 4, "export address table")
            for i in range(n_funcs):
                target = self.u32(funcs_pos + 4 * i)
                if rva <= target < rva + size:
                    forwarders += 1
        _ = ords_rva, base  # parsed for completeness; ordinals are not reported
        try:
            dll_name = self.cstring(name_rva) if name_rva else None
        except PEError:
            dll_name = None
        return {
            "present": True,
            "error": None,
            "dll_name": dll_name,
            "ordinal_base": base,
            "function_count": n_funcs,
            "named_count": n_names,
            "unreadable_name_count": unreadable,
            "first_name_error": first_error,
            "forwarder_count": forwarders,
            "names": names,
        }

    # -- resources ---------------------------------------------------------
    def _res_dir_entries(self, base: int, dir_off: int, res_size: int,
                         state: dict[str, Any]) -> list[tuple[int | str, int, bool]]:
        pos = base + dir_off
        n_named, n_ids = self.unpack("<HH", pos + 12)
        count = n_named + n_ids
        if dir_off + 16 + 8 * count > res_size:
            raise PEError(f"resource directory at +0x{dir_off:x} ({count} entries) overruns the "
                          "resource data directory")
        state["budget"] -= count
        if state["budget"] < 0:
            raise PEBudgetError(f"more than {MAX_RESOURCE_ENTRIES} resource directory entries; "
                                "stopped (possible crafted file)")
        entries = []
        for i in range(count):
            name_field, target = self.unpack("<II", pos + 16 + 8 * i)
            if name_field & 0x80000000:
                str_pos = base + (name_field & 0x7FFFFFFF)
                length = self.u16(str_pos)
                shown = min(length, MAX_VALUE_CHARS)
                key: int | str = self.data[str_pos + 2:str_pos + 2 + 2 * shown].decode("utf-16-le", errors="replace")
                if length > shown:
                    key += TRUNCATED_MARK
            else:
                key = name_field & 0xFFFF
            entries.append((key, target & 0x7FFFFFFF, bool(target & 0x80000000)))
        return entries

    def _res_leaves(self, base: int, dir_off: int, depth: int, res_size: int,
                    state: dict[str, Any]) -> list[tuple[int, int]]:
        """Return (data RVA, size) for all leaves under a directory.

        `state` is shared by the whole tree walk: a directory is visited at
        most once (even when several types point at it) and the total number
        of entries is capped, so a crafted tree cannot make the walk quadratic.
        """
        if depth > MAX_RESOURCE_DEPTH or dir_off in state["seen"]:
            return []
        state["seen"].add(dir_off)
        leaves = []
        for _key, target, is_dir in self._res_dir_entries(base, dir_off, res_size, state):
            if is_dir:
                leaves += self._res_leaves(base, target, depth + 1, res_size, state)
            else:
                data_rva, data_size, _cp, _res = self.unpack("<IIII", base + target)
                leaves.append((data_rva, data_size))
        return leaves

    def resource_tree(self) -> list[tuple[int | str, list[tuple[int, int]]]]:
        """(type key, leaves) per top-level resource type; walked once and cached."""
        if self._res_tree is not None:
            return self._res_tree
        rva, size = self.data_dir(2)
        if not rva or not size:
            self._res_tree = []
            return self._res_tree
        base = self.off(rva)
        state: dict[str, Any] = {"seen": {0}, "budget": MAX_RESOURCE_ENTRIES}
        tree = []
        # A subdirectory shared by several types is walked once: its leaves
        # count under the first type only (the others report 0 entries).
        for key, target, is_dir in self._res_dir_entries(base, 0, size, state):
            tree.append((key, self._res_leaves(base, target, 1, size, state) if is_dir else []))
        self._res_tree = tree
        return tree

    def resources(self) -> list[dict[str, Any]]:
        result = []
        for key, leaves in self.resource_tree():
            result.append({
                "type": key if isinstance(key, str) else RESOURCE_TYPES.get(key, f"#{key}"),
                "type_id": key if isinstance(key, int) else None,
                "entries": len(leaves),
                "total_bytes": sum(s for _r, s in leaves),
            })
        return result

    def version_resources(self, keys: tuple[str, ...], errors: list[str] | None = None) -> list[dict[str, Any]]:
        """Parse each RT_VERSION leaf; a bad leaf is recorded in `errors` and skipped."""
        out: list[dict[str, Any]] = []
        leaves = [leaf for key, type_leaves in self.resource_tree() if key == RT_VERSION for leaf in type_leaves]
        for index, (data_rva, data_size) in enumerate(leaves):
            if index >= MAX_VERSION_LEAVES:
                if errors is not None:
                    errors.append(f"version_info: {len(leaves)} RT_VERSION leaves; only the first "
                                  f"{MAX_VERSION_LEAVES} were parsed")
                break
            try:
                start = self.off(data_rva)
                out.append(parse_version_info(self.data[start:start + data_size], keys))
            except PEError as exc:
                if errors is not None:
                    errors.append(f"version_info: leaf {index}: {exc}")
        return out


def empty_exports(present: bool, error: str | None = None) -> dict[str, Any]:
    return {"present": present, "error": error, "dll_name": None, "function_count": 0,
            "named_count": 0, "unreadable_name_count": 0, "first_name_error": None,
            "forwarder_count": 0, "names": []}


# -- VS_VERSIONINFO --------------------------------------------------------
def _align4(value: int) -> int:
    return (value + 3) & ~3


def _read_node(blob: bytes, pos: int, end: int, depth: int = 0) -> tuple[dict[str, Any], int]:
    """Parse one version-info node; return (node, next position)."""
    if depth > MAX_VERSION_DEPTH:
        raise PEError(f"version info nested deeper than {MAX_VERSION_DEPTH} levels")
    if pos + 6 > end:
        raise PEError("version node header out of bounds")
    length, value_len, vtype = struct.unpack_from("<HHH", blob, pos)
    if length < 6:
        raise PEError("version node too short")
    node_end = min(pos + length, end)
    key_start = pos + 6
    key_end = key_start
    while key_end + 1 < node_end and blob[key_end:key_end + 2] != b"\0\0":
        key_end += 2
    key = cap_text(blob[key_start:key_end].decode("utf-16-le", errors="replace"))
    cursor = _align4(key_end + 2)
    value: bytes = b""
    if value_len:
        span = value_len * 2 if vtype == 1 else value_len
        value = blob[cursor:min(cursor + span, node_end)]
        cursor = _align4(cursor + span)
    children = []
    while cursor + 6 <= node_end:
        try:
            child, nxt = _read_node(blob, cursor, node_end, depth + 1)
        except PEError:
            break  # tolerate padding or a mis-sized value; keep what parsed so far
        children.append(child)
        if nxt <= cursor:
            break
        cursor = nxt
    return {"key": key, "type": vtype, "value": value, "children": children}, _align4(pos + length)


def _text(value: bytes) -> str:
    text = value.decode("utf-16-le", errors="replace").split("\0", 1)[0]
    return text[:MAX_VALUE_CHARS]


def parse_version_info(blob: bytes, keys: tuple[str, ...]) -> dict[str, Any]:
    root, _ = _read_node(blob, 0, len(blob))
    result: dict[str, Any] = {"root_key": root["key"], "fixed": None, "string_tables": []}
    fixed = root["value"]
    if len(fixed) >= 52 and struct.unpack_from("<I", fixed, 0)[0] == 0xFEEF04BD:
        f = struct.unpack_from("<13I", fixed, 0)
        result["fixed"] = {
            "file_version": version_string(f[2], f[3]),
            "product_version": version_string(f[4], f[5]),
            "file_flags": f[7], "file_os": f[8], "file_type": f[9],
        }
    for child in root["children"]:
        if child["key"] != "StringFileInfo":
            continue
        for table in child["children"]:
            entry: dict[str, Any] = {"lang_codepage": table["key"], "keys_present": [], "values": {}}
            for string in table["children"]:
                entry["keys_present"].append(string["key"])
                if string["key"] in keys:
                    entry["values"][string["key"]] = _text(string["value"])
            result["string_tables"].append(entry)
    return result


# -- FuBi heuristics ---------------------------------------------------------
def classify_export(name: str) -> str:
    if name.startswith("?"):
        return "msvc_decorated"
    if C_DECORATED.match(name):
        return "c_decorated"
    return "undecorated"


def msvc_scope(name: str) -> str | None:
    """Heuristic enclosing scope ("A::B") of an MSVC-decorated name, or None.

    "?Func@Class@NS@@..." gives "NS::Class"; "??0Class@@..." (special members)
    gives "Class". Template fragments ("?$...") and back-references make the
    naive split unreliable; such names return None.
    """
    if not name.startswith("?"):
        return None
    if name.startswith("??"):
        rest = name[4:] if name[2:3] == "_" else name[3:]
        parts = rest.split("@@", 1)[0].split("@")
    else:
        parts = name[1:].split("@@", 1)[0].split("@")[1:]
    parts = [p for p in parts if p]
    if not parts or any(p.startswith("?") or p.isdigit() for p in parts):
        return None
    return "::".join(reversed(parts))


def fubi_test(export_info: dict[str, Any], examples: int) -> dict[str, Any]:
    names = export_info["names"]
    kinds = Counter(classify_export(n) for n in names)
    decorated = [n for n in names if classify_export(n) == "msvc_decorated"]
    scopes = Counter(s for s in (msvc_scope(n) for n in decorated) if s)
    result = {
        "export_function_count": export_info["function_count"],
        "export_named_count": export_info["named_count"],
        "classification_counts": {k: kinds.get(k, 0) for k in ("msvc_decorated", "c_decorated", "undecorated")},
        "msvc_decorated_examples": decorated[:examples],
        "heuristic_scope_count": len(scopes),
        "heuristic_scope_examples": [
            {"scope": s, "exports": c} for s, c in sorted(scopes.items(), key=lambda kv: (-kv[1], kv[0]))[:examples]
        ],
        "method": "Name-pattern heuristic on the PE export table only (no demangling, no DbgHelp).",
    }
    if export_info.get("error"):
        result["verdict"] = (f"export table present but unparsed ({export_info['error']}); "
                             "search limitation, not evidence about FuBi.")
        result["negative_result_class"] = "search limitation"
    elif not export_info["present"] or not names:
        result["verdict"] = NO_EXPORTS_NOTE
        result["negative_result_class"] = "search limitation"
    else:
        result["verdict"] = (f"{kinds.get('msvc_decorated', 0)} of {len(names)} named exports look "
                             "MSVC-decorated. Decorated exports are consistent with, but do not prove, "
                             "a FuBi-style binding.")
    return result


# -- string counting ----------------------------------------------------------
def count_needle(data: bytes, lowered: bytes | None, text: str, ignore_case: bool,
                 max_offsets: int = 5) -> dict[str, Any]:
    haystack = lowered if ignore_case and lowered is not None else data
    needle_text = text.lower() if ignore_case else text
    out: dict[str, Any] = {"text": text, "ignore_case": ignore_case}
    for enc_name, enc in (("ascii", "latin-1"), ("utf16le", "utf-16-le")):
        try:
            needle = needle_text.encode(enc)
        except UnicodeEncodeError:
            out[enc_name] = {"count": None, "note": "not encodable"}
            continue
        count, offsets, pos = 0, [], haystack.find(needle)
        while pos >= 0 and needle:
            count += 1
            if len(offsets) < max_offsets:
                offsets.append(pos)
            pos = haystack.find(needle, pos + 1)
        out[enc_name] = {"count": count, "first_offsets": offsets}
    return out


# -- top level ---------------------------------------------------------------
def summarize(data: bytes, file_name: str, examples: int = 20,
              version_keys: tuple[str, ...] = DEFAULT_VERSION_KEYS,
              needles: list[str] | None = None, ignore_case: bool = False) -> dict[str, Any]:
    pe = PEFile(data)
    sections = []
    for s in pe.sections:
        raw = data[s["raw_offset"]:s["raw_offset"] + s["raw_size"]]
        sections.append({**s, "characteristics": f"0x{s['characteristics']:08x}",
                         "flags": flags(s["characteristics"], SECTION_FLAGS),
                         "raw_entropy": shannon_entropy(raw)})
    raw_end = max([s["raw_offset"] + s["raw_size"] for s in pe.sections if s["raw_size"]] or [0])
    errors: list[str] = []

    def guarded(label: str, fn, default):
        try:
            return fn()
        except PEError as exc:
            errors.append(f"{label}: {exc}")
            return default

    imports = guarded("imports", pe.imports, [])
    delay = guarded("delay_imports", pe.delay_imports, [])
    try:
        exports = pe.exports()
    except PEError as exc:  # the directory exists (else no error), but could not be read
        errors.append(f"exports: {exc}")
        exports = empty_exports(present=True, error=str(exc))
    for imp in imports + delay:
        if imp.get("error"):
            errors.append(f"import {imp['dll'] or '?'}: {imp['error']}")
    if exports.get("first_name_error"):
        errors.append(f"exports: {exports['unreadable_name_count']} unreadable name(s), first: "
                      f"{exports['first_name_error']}")
    security_size = pe.data_dir(4)[1]
    lowered = data.lower() if ignore_case and needles else None
    result = {
        "tool": SCRIPT,
        "tool_version": TOOL_VERSION,
        "file_name": file_name,
        "file_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "format": "PE32+" if pe.is_plus else "PE32",
        "machine": {"value": f"0x{pe.machine:04x}", "name": MACHINES.get(pe.machine, "other")},
        "timestamp": {
            "value": pe.timestamp,
            "utc": datetime.fromtimestamp(pe.timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "COFF TimeDateStamp; linkers may write a hash instead of a time (reproducible builds)",
        },
        "characteristics": {"value": f"0x{pe.characteristics:04x}",
                            "flags": flags(pe.characteristics, FILE_CHARACTERISTICS)},
        "linker_version": pe.linker_version,
        "os_version": pe.os_version,
        "subsystem": {"value": pe.subsystem, "name": SUBSYSTEMS.get(pe.subsystem, "other"),
                      "version": pe.subsystem_version},
        "dll_characteristics": {"value": f"0x{pe.dll_characteristics:04x}",
                                "flags": flags(pe.dll_characteristics, DLL_CHARACTERISTICS)},
        "image_base": f"0x{pe.image_base:08x}",
        "entry_point_rva": f"0x{pe.entry_point:08x}",
        "size_of_image": pe.size_of_image,
        "size_of_headers": pe.size_of_headers,
        "checksum": f"0x{pe.checksum:08x}",
        "data_directories": [
            {"name": DATA_DIRECTORY_NAMES[i], "rva": f"0x{r:08x}", "size": s}
            for i, (r, s) in enumerate(pe.data_dirs) if r or s
        ],
        "sections": sections,
        "overlay_size": max(0, len(data) - raw_end) if raw_end else 0,
        "overlay_note": ("includes the Authenticode signature (security directory, "
                         f"{security_size:,} bytes)" if security_size else None),
        "imports": imports,
        "import_totals": {"dlls": len(imports), "functions": sum(len(i["functions"]) for i in imports)},
        "delay_imports": delay,
        "exports": exports,
        "fubi_test": fubi_test(exports, examples),
        "resources": guarded("resources", pe.resources, []),
        "resources_note": "a subdirectory shared by several types counts once, under the first type",
        "version_info": guarded("version_info", lambda: pe.version_resources(version_keys, errors), []),
        "version_keys_reported": list(version_keys),
        "string_counts": [count_needle(data, lowered, n, ignore_case) for n in (needles or [])],
        "parse_errors": errors,
    }
    return result


def render_summary(r: dict[str, Any], examples: int) -> list[str]:
    lines = [
        f"# PE summary: {md_escape(r['file_name'])}",
        "",
        f"Generated by `tools/research/{SCRIPT}.py` v{r['tool_version']}. Derived facts only.",
        "",
        f"- Format: {r['format']}, machine {r['machine']['name']} ({r['machine']['value']})",
        f"- Size: {r['file_size']:,} bytes; SHA-256 `{r['sha256']}`",
        f"- COFF timestamp: {r['timestamp']['value']} ({r['timestamp']['utc']})",
        f"- Characteristics: {r['characteristics']['value']} {', '.join(r['characteristics']['flags'])}",
        f"- Image base: {r['image_base']}; entry point RVA {r['entry_point_rva']}; linker {r['linker_version']}",
        f"- Subsystem: {r['subsystem']['name']} ({r['subsystem']['value']}), version {r['subsystem']['version']}",
        f"- DLL characteristics: {r['dll_characteristics']['value']} {', '.join(r['dll_characteristics']['flags'])}",
        f"- Overlay after last section: {r['overlay_size']:,} bytes"
        + (f" ({r['overlay_note']})" if r.get("overlay_note") else ""),
        "",
        "## Sections",
        "",
        "| Name | VA | Virtual size | Raw offset | Raw size | Flags | Entropy |",
        "| --- | --- | ---: | --- | ---: | --- | ---: |",
    ]
    for s in r["sections"]:
        lines.append(f"| `{md_escape(s['name'])}` | 0x{s['virtual_address']:08x} | {s['virtual_size']:,} | "
                     f"0x{s['raw_offset']:08x} | {s['raw_size']:,} | {', '.join(s['flags'])} | {s['raw_entropy']} |")
    lines += ["", "## Imports", "",
              f"{r['import_totals']['dlls']} DLLs, {r['import_totals']['functions']} functions "
              "(full names in the JSON).", ""]
    for imp in r["imports"]:
        lines.append(import_line(imp))
    if r["delay_imports"]:
        lines += ["", "Delay-load imports:", ""]
        for imp in r["delay_imports"]:
            lines.append(import_line(imp))
    else:
        lines += ["", "No delay-load import directory."]
    e, f = r["exports"], r["fubi_test"]
    lines += ["", "## Exports and FuBi test", ""]
    if e.get("error"):
        lines.append(f"- Export table present but unparsed: {md_escape(e['error'])}")
    elif e["present"]:
        lines.append(f"- Export table: {e['function_count']} functions, {e['named_count']} named, "
                     f"{e['forwarder_count']} forwarders; DLL name `{md_escape(e['dll_name'] or '')}`")
    c = f["classification_counts"]
    lines += [f"- Name classes: MSVC-decorated {c['msvc_decorated']}, C-decorated {c['c_decorated']}, "
              f"undecorated {c['undecorated']}",
              f"- Heuristic scopes (classes/namespaces) among decorated names: {f['heuristic_scope_count']}",
              f"- Verdict: {f['verdict']}"]
    if f["msvc_decorated_examples"]:
        lines += ["", f"Up to {examples} decorated export names:", ""]
        lines += [f"- `{md_escape(n)}`" for n in f["msvc_decorated_examples"]]
    if f["heuristic_scope_examples"]:
        lines += ["", "Most frequent heuristic scopes:", ""]
        lines += [f"- `{md_escape(s['scope'])}`: {s['exports']}" for s in f["heuristic_scope_examples"]]
    lines += ["", "## Resources", "",
              "Entry counts per type; a subdirectory shared by several types counts once, under the first.", ""]
    if r["resources"]:
        for res in r["resources"]:
            lines.append(f"- {md_escape(str(res['type']))}: {res['entries']} entries, {res['total_bytes']:,} bytes")
    else:
        lines.append("- No resource directory.")
    lines += ["", "## Version resource", ""]
    if not r["version_info"]:
        lines.append("- No RT_VERSION resource found.")
    for v in r["version_info"]:
        if v["fixed"]:
            lines.append(f"- Fixed info: file {v['fixed']['file_version']}, product {v['fixed']['product_version']}")
        for t in v["string_tables"]:
            vals = "; ".join(f"{k} = `{md_escape(val)}`" for k, val in sorted(t["values"].items())) or "none of the requested keys"
            lines.append(f"- String table {t['lang_codepage']}: {vals} (keys present: {', '.join(t['keys_present'])})")
    if r["string_counts"]:
        lines += ["", "## String counts", ""]
        for sc in r["string_counts"]:
            lines.append(f"- `{md_escape(sc['text'])}`: ASCII {sc['ascii'].get('count')}, "
                         f"UTF-16LE {sc['utf16le'].get('count')}")
    if r["parse_errors"]:
        lines += ["", "## Parse errors", ""] + [f"- {md_escape(x)}" for x in r["parse_errors"]]
    return lines


def import_line(imp: dict[str, Any]) -> str:
    line = f"- `{md_escape(imp['dll'] or '?')}`: {len(imp['functions'])} functions"
    if imp.get("error"):
        line += f" (partly unreadable: {md_escape(imp['error'])})"
    return line


def unique_label(name: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", name) or "file"
    label, n = base, 2
    while label.casefold() in used:
        label, n = f"{base}-{n}", n + 1
    used.add(label.casefold())
    return label


def read_input(path: Path) -> bytes | None:
    """The whole file, or None if it does not start with "MZ" (checked first, so a
    large non-PE file such as a Tank is not read into memory)."""
    with path.open("rb") as handle:
        if handle.read(2) != b"MZ":
            return None
        handle.seek(0)
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    safe_console()
    parser = argparse.ArgumentParser(
        description="Summarise PE32/PE32+ files (headers, sections, imports, exports, version "
                    "resource, FuBi export-name test). Derived facts only.")
    parser.add_argument("files", nargs="+", type=Path, help="PE files (outside the repository)")
    parser.add_argument("--out", type=Path, default=None, help=f"output folder (default: <repo>/local/{SCRIPT}/)")
    parser.add_argument("--examples", type=int, default=20, metavar="N",
                        help="max example decorated export names / scopes to report (default 20)")
    parser.add_argument("--version-key", action="append", default=None, metavar="KEY",
                        help="version-resource string key to report (repeatable; default FileVersion and ProductVersion)")
    parser.add_argument("--count-string", action="append", default=None, metavar="TEXT",
                        help="count ASCII and UTF-16LE occurrences of TEXT (repeatable; counts and offsets only)")
    parser.add_argument("--ignore-case", action="store_true",
                        help="make every --count-string case-insensitive (applies to all of them)")
    args = parser.parse_args(argv)
    if args.examples < 0:
        parser.error("--examples must be >= 0")

    try:
        inputs = [check_input_path(p) for p in args.files]
        out_dir = check_output_dir(args.out, SCRIPT, inputs)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    keys = tuple(args.version_key) if args.version_key else DEFAULT_VERSION_KEYS
    used: set[str] = set()
    status = 0
    for path in inputs:
        if not path.is_file():
            print(f"error: not a file: {path.name}", file=sys.stderr)
            status = 1
            continue
        # Per-file isolation: one bad or locked file never stops the others,
        # and no traceback (which would print absolute paths) reaches the user.
        try:
            data = read_input(path)
        except OSError as exc:
            print(f"error: {path.name}: file locked or unreadable ({os_error_text(exc)})", file=sys.stderr)
            status = 1
            continue
        if data is None:
            print(f"error: {path.name}: not a PE file (no MZ header)", file=sys.stderr)
            status = 1
            continue
        try:
            result = summarize(data, path.name, args.examples, keys, args.count_string, args.ignore_case)
        except PEError as exc:
            print(f"error: {path.name}: {exc}", file=sys.stderr)
            status = 1
            continue
        except Exception as exc:  # noqa: BLE001 - parser bug on odd input; report the type only
            print(f"error: {path.name}: {type(exc).__name__} while parsing (please report)", file=sys.stderr)
            status = 1
            continue
        label = unique_label(path.name, used)
        try:
            write_json(out_dir / f"{label}.pe.json", result)
            write_text(out_dir / f"{label}.pe.md", render_summary(result, args.examples))
        except OSError as exc:
            print(f"error: cannot write output for {path.name} ({os_error_text(exc)})", file=sys.stderr)
            return 1
        f = result["fubi_test"]
        print(f"{path.name}: {result['format']} {result['machine']['name']}, {result['file_size']:,} bytes, "
              f"sha256 {result['sha256']}")
        print(f"  imports: {result['import_totals']['dlls']} DLLs / {result['import_totals']['functions']} functions; "
              f"exports: {result['exports']['function_count']}; MSVC-decorated: "
              f"{f['classification_counts']['msvc_decorated']}")
        if not result["exports"]["names"]:
            print(f"  {f['verdict']}")
        print(f"  wrote {out_dir / (label + '.pe.json')}")
    return status


if __name__ == "__main__":
    sys.exit(main())
