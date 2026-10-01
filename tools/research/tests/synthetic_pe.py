"""Build tiny synthetic PE32/PE32+ images for tests (no game files, ADR-0002).

The layout is fixed and simple: headers (0x200 bytes), a ".text" section at
RVA 0x1000 and an ".rdata" section at RVA 0x2000 that holds the import,
delay-import, export and resource (version) directories.
"""

from __future__ import annotations

import struct
from typing import Callable

FILE_ALIGN = 0x200
SECT_ALIGN = 0x1000
TEXT_RVA = 0x1000
RDATA_RVA = 0x2000


def _align(value: int, to: int) -> int:
    return (value + to - 1) // to * to


class _Blob:
    """Append-only section body that hands out RVAs."""

    def __init__(self, base_rva: int) -> None:
        self.base = base_rva
        self.data = bytearray()

    def add(self, payload: bytes, align: int = 4) -> int:
        while len(self.data) % align:
            self.data.append(0)
        rva = self.base + len(self.data)
        self.data += payload
        return rva

    def cstr(self, text: str) -> int:
        return self.add(text.encode("ascii") + b"\0", align=2)

    def patch(self, rva: int, payload: bytes) -> None:
        start = rva - self.base
        self.data[start:start + len(payload)] = payload


Blob = _Blob
# A test hook: gets the .rdata blob and the image base, adds its own
# structures and returns data-directory overrides {index: (rva, size)}.
Custom = Callable[[_Blob, int], dict[int, tuple[int, int]]]


def version_node(key: str, value: bytes = b"", vtype: int = 0, children: tuple[bytes, ...] = (),
                 value_len: int | None = None) -> bytes:
    """One VS_VERSIONINFO-style node, padded to a 4-byte boundary."""
    body = bytearray(b"\0" * 6)
    body += key.encode("utf-16-le") + b"\0\0"
    while len(body) % 4:
        body.append(0)
    body += value
    if children:
        while len(body) % 4:
            body.append(0)
        for child in children:
            body += child
    length = len(body)
    if value_len is None:
        value_len = len(value) // 2 if vtype == 1 else len(value)
    struct.pack_into("<HHH", body, 0, length, value_len, vtype)
    while len(body) % 4:
        body.append(0)
    return bytes(body)


def version_blob(strings: dict[str, str], file_version: tuple[int, int, int, int]) -> bytes:
    ms = (file_version[0] << 16) | file_version[1]
    ls = (file_version[2] << 16) | file_version[3]
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x10000, ms, ls, ms, ls, 0x3F, 0, 4, 1, 0, 0, 0)
    string_nodes = tuple(
        version_node(k, (v + "\0").encode("utf-16-le"), vtype=1) for k, v in strings.items()
    )
    table = version_node("040904b0", vtype=1, children=string_nodes)
    sfi = version_node("StringFileInfo", vtype=1, children=(table,))
    var = version_node("VarFileInfo", vtype=1, children=(
        version_node("Translation", struct.pack("<HH", 0x0409, 1200)),))
    return version_node("VS_VERSION_INFO", fixed, vtype=0, children=(sfi, var))


def build_pe(
    *,
    pe32plus: bool = False,
    imports: dict[str, list[str | int]] | None = None,
    delay_imports: dict[str, list[str]] | None = None,
    delay_va_based: bool = False,
    exports: list[str] | None = None,
    export_forwarders: dict[str, str] | None = None,
    export_dll_name: str = "synthetic.exe",
    version_strings: dict[str, str] | None = None,
    file_version: tuple[int, int, int, int] = (1, 2, 3, 4),
    timestamp: int = 0x4D2D0000,
    characteristics: int = 0x0102,
    text_payload: bytes = b"\xC3",
    version_raw: bytes | None = None,
    custom: Custom | None = None,
    security_dir: tuple[int, int] | None = None,
) -> bytes:
    """Build a PE image.

    delay_va_based: write old-style (pre-VC7, attributes 0) delay descriptors
    that hold VAs instead of RVAs. export_forwarders: {export name: "DLL.Func"}
    exports whose address points inside the export directory. version_raw: a
    raw RT_VERSION blob instead of the generated one (needs version_strings
    or is used alone). custom: see Custom.
    """
    ptr = 8 if pe32plus else 4
    ptr_fmt = "<Q" if pe32plus else "<I"
    ordinal_flag = 1 << (ptr * 8 - 1)
    image_base = 0x140000000 if pe32plus else 0x00400000
    rd = _Blob(RDATA_RVA)
    dirs = [(0, 0)] * 16

    # Imports -----------------------------------------------------------
    if imports:
        descriptors = []
        for dll, funcs in imports.items():
            name_rva = rd.cstr(dll)
            entries = []
            for f in funcs:
                if isinstance(f, int):
                    entries.append(ordinal_flag | f)
                else:
                    entries.append(rd.add(struct.pack("<H", 0) + f.encode("ascii") + b"\0", align=2))
            table = b"".join(struct.pack(ptr_fmt, e) for e in entries) + b"\0" * ptr
            int_rva = rd.add(table, align=ptr)
            iat_rva = rd.add(table, align=ptr)
            descriptors.append(struct.pack("<IIIII", int_rva, 0, 0, name_rva, iat_rva))
        blob = b"".join(descriptors) + b"\0" * 20
        dirs[1] = (rd.add(blob), len(blob))
        dirs[12] = (0, 0)

    # Delay imports (new-style RVA based, or old-style VA based) ----------
    if delay_imports:
        descriptors = []
        va = image_base if delay_va_based else 0
        for dll, funcs in delay_imports.items():
            name_rva = rd.cstr(dll)
            hints = [rd.add(struct.pack("<H", 0) + f.encode("ascii") + b"\0", align=2) for f in funcs]
            table = b"".join(struct.pack(ptr_fmt, va + h) for h in hints) + b"\0" * ptr
            int_rva = rd.add(table, align=ptr)
            iat_rva = rd.add(table, align=ptr)
            hmod_rva = rd.add(b"\0" * ptr, align=ptr)
            attrs = 0 if delay_va_based else 1
            descriptors.append(struct.pack("<IIIIIIII", attrs, va + name_rva, va + hmod_rva, va + iat_rva,
                                           va + int_rva, 0, 0, 0))
        blob = b"".join(descriptors) + b"\0" * 32
        dirs[13] = (rd.add(blob), len(blob))

    # Exports -------------------------------------------------------------
    if exports or export_forwarders:
        forwarders = export_forwarders or {}
        names = sorted([*(exports or []), *forwarders])
        dir_rva = rd.add(b"\0" * 40)  # the directory itself; forwarder strings follow it
        targets = {n: rd.cstr(forwarders[n]) for n in names if n in forwarders}
        dir_size = rd.base + len(rd.data) - dir_rva
        dll_rva = rd.cstr(export_dll_name)
        name_rvas = [rd.cstr(n) for n in names]
        funcs_rva = rd.add(b"".join(struct.pack("<I", targets.get(n, TEXT_RVA)) for n in names))
        names_rva = rd.add(b"".join(struct.pack("<I", r) for r in name_rvas))
        ords_rva = rd.add(b"".join(struct.pack("<H", i) for i in range(len(names))))
        rd.patch(dir_rva, struct.pack("<IIHHIIIIIII", 0, 0, 0, 0, dll_rva, 1, len(names), len(names),
                                      funcs_rva, names_rva, ords_rva))
        dirs[0] = (dir_rva, dir_size)

    # Resources: one RT_VERSION leaf -----------------------------------
    if version_strings is not None or version_raw is not None:
        res_rva = rd.add(b"", align=4)
        vblob = version_raw if version_raw is not None else version_blob(version_strings or {}, file_version)
        res = bytearray()
        res += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1) + struct.pack("<II", 16, 0x80000000 | 24)
        res += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1) + struct.pack("<II", 1, 0x80000000 | 48)
        res += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1) + struct.pack("<II", 0x0409, 72)
        res += struct.pack("<IIII", res_rva + 88, len(vblob), 0, 0)
        res += vblob
        rd.add(bytes(res), align=4)
        dirs[2] = (res_rva, len(res))

    if custom is not None:
        for index, value in custom(rd, image_base).items():
            dirs[index] = value
    if security_dir is not None:
        dirs[4] = security_dir

    rdata = bytes(rd.data) or b"\0"
    text = text_payload

    # Headers ---------------------------------------------------------------
    e_lfanew = 0x80
    opt_size = 240 if pe32plus else 224
    text_raw = FILE_ALIGN
    text_raw_size = _align(len(text), FILE_ALIGN)
    rdata_raw = text_raw + text_raw_size
    rdata_raw_size = _align(len(rdata), FILE_ALIGN)
    size_of_image = _align(RDATA_RVA + len(rdata), SECT_ALIGN)

    dos = bytearray(e_lfanew)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, e_lfanew)
    coff = b"PE\0\0" + struct.pack("<HHIIIHH", 0x8664 if pe32plus else 0x014C, 2, timestamp, 0, 0,
                                   opt_size, characteristics)
    if pe32plus:
        opt = struct.pack("<HBBIIIIIQ", 0x20B, 9, 0, text_raw_size, rdata_raw_size, 0, TEXT_RVA, TEXT_RVA,
                          image_base)
    else:
        opt = struct.pack("<HBBIIIIIII", 0x10B, 7, 10, text_raw_size, rdata_raw_size, 0, TEXT_RVA, TEXT_RVA,
                          RDATA_RVA, image_base)
    opt += struct.pack("<IIHHHHHHIIIIHH", SECT_ALIGN, FILE_ALIGN, 4, 0, 0, 0, 4, 0, 0, size_of_image,
                       FILE_ALIGN, 0, 2, 0x0000)
    opt += struct.pack("<QQQQ" if pe32plus else "<IIII", 0x100000, 0x1000, 0x100000, 0x1000)
    opt += struct.pack("<II", 0, 16)
    opt += b"".join(struct.pack("<II", r, s) for r, s in dirs)
    assert len(opt) == opt_size, len(opt)

    def section(name: bytes, vsize: int, va: int, raw_size: int, raw_ptr: int, chars: int) -> bytes:
        return name.ljust(8, b"\0") + struct.pack("<IIIIIIHHI", vsize, va, raw_size, raw_ptr, 0, 0, 0, 0, chars)

    headers = bytes(dos) + coff + opt
    headers += section(b".text", len(text), TEXT_RVA, text_raw_size, text_raw, 0x60000020)
    headers += section(b".rdata", len(rdata), RDATA_RVA, rdata_raw_size, rdata_raw, 0x40000040)
    assert len(headers) <= FILE_ALIGN
    image = headers.ljust(FILE_ALIGN, b"\0")
    image += text.ljust(text_raw_size, b"\0")
    image += rdata.ljust(rdata_raw_size, b"\0")
    return image
