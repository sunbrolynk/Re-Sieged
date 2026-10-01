"""Tests for pe_summary.py using synthetic PE images only."""

from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pe_summary  # noqa: E402
from research_common import repo_root  # noqa: E402
from support import assert_no_path  # noqa: E402
from synthetic_pe import RDATA_RVA, build_pe  # noqa: E402

EXPORTS = ["?Foo@Bar@@QAEXXZ", "?Baz@Bar@@QAEHH@Z", "_PlainStd@8", "PlainC"]
CONTENT_MARKER = b"RS-CONTENT-MARKER-DO-NOT-LEAK"


def full_pe32() -> bytes:
    return build_pe(
        imports={"KERNEL32.dll": ["GetTickCount"], "WSOCK32.dll": [5]},
        delay_imports={"XINPUT1_3.dll": ["XInputGetState"]},
        exports=EXPORTS,
        version_strings={"CompanyName": "Synthetic Co", "FileVersion": "2.30.0.0", "ProductVersion": "2.30"},
        file_version=(2, 30, 0, 0),
        characteristics=0x0122,
        text_payload=b"\xC3" + CONTENT_MARKER + b"RS-NEEDLE" + "RS-NEEDLE".encode("utf-16-le"),
    )


class ParseTests(unittest.TestCase):
    def test_pe32_headers(self) -> None:
        data = full_pe32()
        r = pe_summary.summarize(data, "synthetic.exe")
        self.assertEqual(r["format"], "PE32")
        self.assertEqual(r["machine"]["name"], "i386")
        self.assertEqual(r["image_base"], "0x00400000")
        self.assertEqual(r["subsystem"]["name"], "windows_gui")
        self.assertEqual(r["timestamp"]["value"], 0x4D2D0000)
        self.assertIn("LARGE_ADDRESS_AWARE", r["characteristics"]["flags"])
        self.assertEqual([s["name"] for s in r["sections"]], [".text", ".rdata"])
        self.assertEqual(r["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(r["file_size"], len(data))
        self.assertEqual(r["overlay_size"], 0)
        self.assertEqual(r["parse_errors"], [])

    def test_imports_and_delay_imports(self) -> None:
        r = pe_summary.summarize(full_pe32(), "synthetic.exe")
        self.assertEqual(r["imports"], [
            {"dll": "KERNEL32.dll", "functions": ["GetTickCount"]},
            {"dll": "WSOCK32.dll", "functions": ["#5"]},
        ])
        self.assertEqual(r["import_totals"], {"dlls": 2, "functions": 2})
        self.assertEqual(r["delay_imports"], [{"dll": "XINPUT1_3.dll", "functions": ["XInputGetState"]}])

    def test_exports_and_fubi_classification(self) -> None:
        r = pe_summary.summarize(full_pe32(), "synthetic.exe", examples=20)
        self.assertTrue(r["exports"]["present"])
        self.assertEqual(r["exports"]["function_count"], 4)
        self.assertEqual(r["exports"]["names"], sorted(EXPORTS))
        f = r["fubi_test"]
        self.assertEqual(f["classification_counts"], {"msvc_decorated": 2, "c_decorated": 1, "undecorated": 1})
        self.assertEqual(f["heuristic_scope_count"], 1)
        self.assertEqual(f["heuristic_scope_examples"], [{"scope": "Bar", "exports": 2}])
        self.assertIn("do not prove", f["verdict"])

    def test_examples_limit(self) -> None:
        r = pe_summary.summarize(full_pe32(), "synthetic.exe", examples=1)
        self.assertEqual(len(r["fubi_test"]["msvc_decorated_examples"]), 1)

    def test_no_exports_is_not_absence(self) -> None:
        r = pe_summary.summarize(build_pe(imports={"KERNEL32.dll": ["ExitProcess"]}), "noexp.exe")
        self.assertFalse(r["exports"]["present"])
        self.assertIn("no exports found", r["fubi_test"]["verdict"])
        self.assertIn("NOT evidence", r["fubi_test"]["verdict"])
        self.assertEqual(r["fubi_test"]["negative_result_class"], "search limitation")

    def test_version_resource(self) -> None:
        r = pe_summary.summarize(full_pe32(), "synthetic.exe")
        self.assertEqual(len(r["version_info"]), 1)
        v = r["version_info"][0]
        self.assertEqual(v["fixed"]["file_version"], "2.30.0.0")
        table = v["string_tables"][0]
        self.assertEqual(table["lang_codepage"], "040904b0")
        self.assertEqual(table["values"], {"FileVersion": "2.30.0.0", "ProductVersion": "2.30"})
        # Other keys are listed by name only; their values are not reported.
        self.assertIn("CompanyName", table["keys_present"])
        self.assertNotIn("Synthetic Co", json.dumps(r))
        self.assertEqual([x["type"] for x in r["resources"]], ["RT_VERSION"])

    def test_version_key_option(self) -> None:
        r = pe_summary.summarize(full_pe32(), "synthetic.exe", version_keys=("CompanyName",))
        self.assertEqual(r["version_info"][0]["string_tables"][0]["values"], {"CompanyName": "Synthetic Co"})

    def test_pe32_plus(self) -> None:
        data = build_pe(pe32plus=True, imports={"KERNEL32.dll": ["GetTickCount", 7]}, exports=["Exported"])
        r = pe_summary.summarize(data, "synthetic64.exe")
        self.assertEqual(r["format"], "PE32+")
        self.assertEqual(r["machine"]["name"], "AMD64")
        self.assertEqual(r["image_base"], "0x140000000")
        self.assertEqual(r["imports"], [{"dll": "KERNEL32.dll", "functions": ["GetTickCount", "#7"]}])
        self.assertEqual(r["exports"]["names"], ["Exported"])

    def test_string_counts(self) -> None:
        r = pe_summary.summarize(full_pe32(), "synthetic.exe", needles=["RS-NEEDLE", "absent-text"])
        needle, absent = r["string_counts"]
        self.assertEqual(needle["ascii"]["count"], 1)
        self.assertEqual(needle["utf16le"]["count"], 1)
        self.assertEqual(absent["ascii"]["count"], 0)
        r = pe_summary.summarize(full_pe32(), "synthetic.exe", needles=["rs-needle"], ignore_case=True)
        self.assertEqual(r["string_counts"][0]["ascii"]["count"], 1)

    def test_not_a_pe(self) -> None:
        with self.assertRaises(pe_summary.PEError):
            pe_summary.summarize(b"DSg2Tank" + b"\0" * 200, "x.bin")

    def test_truncated_pe(self) -> None:
        with self.assertRaises(pe_summary.PEError):
            pe_summary.summarize(full_pe32()[:0x100], "cut.exe")

    def test_msvc_scope_heuristic(self) -> None:
        scope = pe_summary.msvc_scope
        self.assertEqual(scope("?Foo@Bar@@QAEXXZ"), "Bar")
        self.assertEqual(scope("?Foo@Bar@NS@@QAEXXZ"), "NS::Bar")
        self.assertEqual(scope("??0Bar@@QAE@XZ"), "Bar")
        self.assertEqual(scope("??_GBar@@UAEPAXI@Z"), "Bar")
        self.assertIsNone(scope("?Global@@YAXXZ"))
        self.assertIsNone(scope("?Foo@?AVec@@QAEXXZ"))
        self.assertIsNone(scope("PlainC"))


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.exe = self.root / "in" / "synthetic.exe"
        self.exe.parent.mkdir()
        self.exe.write_bytes(full_pe32())
        self.out = self.root / "out"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pe_summary.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_writes_outputs_without_content(self) -> None:
        code, stdout, _ = self.run_main(str(self.exe), "--out", str(self.out), "--count-string", "RS-NEEDLE")
        self.assertEqual(code, 0)
        js = (self.out / "synthetic.exe.pe.json").read_text(encoding="utf-8")
        md = (self.out / "synthetic.exe.pe.md").read_text(encoding="utf-8")
        for text in (js, md, stdout):
            self.assertNotIn(CONTENT_MARKER.decode(), text)
        for text in (js, md):
            assert_no_path(self, text, self.root)
        self.assertIn("?Foo@Bar@@QAEXXZ", md)

    def test_deterministic(self) -> None:
        self.run_main(str(self.exe), "--out", str(self.out / "a"))
        self.run_main(str(self.exe), "--out", str(self.out / "b"))
        self.assertEqual((self.out / "a" / "synthetic.exe.pe.json").read_bytes(),
                         (self.out / "b" / "synthetic.exe.pe.json").read_bytes())

    def test_non_pe_input_fails_cleanly(self) -> None:
        bogus = self.root / "in" / "Logic.ds2res"
        bogus.write_bytes(b"DSg2Tank" + b"\0" * 64)
        code, _, err = self.run_main(str(bogus), "--out", str(self.out))
        self.assertEqual(code, 1)
        self.assertIn("not a PE file", err)

    def test_refuses_input_inside_repo(self) -> None:
        code, _, err = self.run_main(str(repo_root() / "README.md"), "--out", str(self.out))
        self.assertEqual(code, 2)
        self.assertIn("outside the repository", err)

    def test_refuses_output_in_repo_outside_local(self) -> None:
        code, _, err = self.run_main(str(self.exe), "--out", str(repo_root() / "docs" / "pe-out"))
        self.assertEqual(code, 2)
        self.assertIn("local/", err)
        self.assertFalse((repo_root() / "docs" / "pe-out").exists())


def file_offset(data: bytes, rva: int) -> int:
    return pe_summary.PEFile(data).off(rva)


def patch(data: bytes, offset: int, payload: bytes) -> bytes:
    return data[:offset] + payload + data[offset + len(payload):]


def resource_dir(entries: list[tuple[int, int]]) -> bytes:
    """IMAGE_RESOURCE_DIRECTORY with ID entries [(name_field, target_field)]."""
    out = struct.pack("<IIHHHH", 0, 0, 0, 0, 0, len(entries))
    return out + b"".join(struct.pack("<II", n, t) for n, t in entries)


class RobustnessTests(unittest.TestCase):
    """Crafted and damaged inputs: every case returns or raises PEError, within budget."""

    def sweep(self, data: bytes) -> None:
        bad = []
        for n in range(len(data) + 1):
            try:
                pe_summary.summarize(data[:n], "cut.exe")
            except pe_summary.PEError:
                pass
            except Exception as exc:  # noqa: BLE001 - that is what the test looks for
                bad.append((n, type(exc).__name__))
        self.assertEqual(bad[:5], [])

    def test_prefix_truncation_sweep_pe32(self) -> None:
        self.sweep(full_pe32())

    def test_prefix_truncation_sweep_pe32_plus(self) -> None:
        self.sweep(build_pe(pe32plus=True, imports={"KERNEL32.dll": ["GetTickCount", 7]},
                            delay_imports={"XINPUT1_3.dll": ["XInputGetState"]}, exports=["Exported"],
                            version_strings={"FileVersion": "1.0"}))

    def test_linker_version_read_is_bounds_checked(self) -> None:
        # Optional-header magic ends at byte 154; the linker version bytes follow.
        with self.assertRaises(pe_summary.PEError):
            pe_summary.PEFile(full_pe32()[:154])

    def test_resource_fan_out_is_linear(self) -> None:
        n = 4000

        def custom(rd, _image_base):
            base = rd.add(b"", align=4)
            sub_off = 16 + 8 * n
            leaf_off = sub_off + 16 + 8 * n
            root = resource_dir([(i + 1, 0x80000000 | sub_off) for i in range(n)])
            sub = resource_dir([(i + 1, leaf_off) for i in range(n)])
            leaf = struct.pack("<IIII", RDATA_RVA, 4, 0, 0)
            blob = root + sub + leaf
            rd.add(blob)
            return {2: (base, len(blob))}

        data = build_pe(custom=custom)
        start = time.perf_counter()
        r = pe_summary.summarize(data, "fan.exe")
        self.assertLess(time.perf_counter() - start, 5.0)
        self.assertEqual(len(r["resources"]), n)
        self.assertEqual(sum(x["entries"] for x in r["resources"]), n)  # the shared folder counts once
        self.assertIn("counts once", r["resources_note"])
        self.assertIn("counts once, under the first", "\n".join(pe_summary.render_summary(r, 20)))

    def test_resource_entry_budget(self) -> None:
        def custom(rd, _image_base):
            base = rd.add(b"", align=4)
            # 400 types, each its own sub-folder of 300 leaves: 120,400 entries > budget.
            types_, subs = 400, 300
            sub_size = 16 + 8 * subs
            first_sub = 16 + 8 * types_
            leaf_off = first_sub + types_ * sub_size
            root = resource_dir([(i + 1, 0x80000000 | (first_sub + i * sub_size)) for i in range(types_)])
            sub = resource_dir([(j + 1, leaf_off) for j in range(subs)])
            blob = root + sub * types_ + struct.pack("<IIII", RDATA_RVA, 4, 0, 0)
            rd.add(blob)
            return {2: (base, len(blob))}

        r = pe_summary.summarize(build_pe(custom=custom), "budget.exe")
        self.assertEqual(r["resources"], [])
        self.assertTrue(any("resource directory entries" in e for e in r["parse_errors"]))

    def test_resource_directory_overrunning_its_size_is_an_error(self) -> None:
        def custom(rd, _image_base):
            base = rd.add(b"", align=4)
            blob = struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 5000) + bytes(64)
            rd.add(blob)
            return {2: (base, len(blob))}

        r = pe_summary.summarize(build_pe(custom=custom), "overrun.exe")
        self.assertEqual(r["resources"], [])
        self.assertTrue(any("overruns" in e for e in r["parse_errors"]))

    def test_resource_cycle_terminates(self) -> None:
        def custom(rd, _image_base):
            base = rd.add(b"", align=4)
            sub_off = 16 + 8
            root = resource_dir([(3, 0x80000000 | sub_off)])
            sub = resource_dir([(1, 0x80000000 | 0), (2, 0x80000000 | sub_off)])  # back to root and self
            blob = root + sub
            rd.add(blob)
            return {2: (base, len(blob))}

        r = pe_summary.summarize(build_pe(custom=custom), "cycle.exe")
        self.assertEqual(r["resources"], [{"type": "RT_ICON", "type_id": 3, "entries": 0, "total_bytes": 0}])

    def test_named_resource_types(self) -> None:
        long_name = "N" * 300
        ctrl_name = "BAD\nNAME|X"

        def custom(rd, _image_base):
            base = rd.add(b"", align=4)
            names = [ctrl_name, long_name, "SYNTHTYPE"]
            header = 16 + 8 * len(names)
            strings, offsets = b"", []
            for name in names:
                offsets.append(header + len(strings))
                strings += struct.pack("<H", len(name)) + name.encode("utf-16-le")
                if len(strings) % 4:
                    strings += b"\0" * (4 - len(strings) % 4)
            leaf_off = header + len(strings)
            root = struct.pack("<IIHHHH", 0, 0, 0, 0, len(names), 0)
            root += b"".join(struct.pack("<II", 0x80000000 | o, leaf_off) for o in offsets)
            blob = root + strings + struct.pack("<IIII", RDATA_RVA, 4, 0, 0)
            rd.add(blob)
            return {2: (base, len(blob))}

        r = pe_summary.summarize(build_pe(custom=custom), "named.exe")
        types_ = [x["type"] for x in r["resources"]]
        self.assertEqual(types_[2], "SYNTHTYPE")
        self.assertEqual(types_[1], "N" * pe_summary.MAX_VALUE_CHARS + pe_summary.TRUNCATED_MARK)
        self.assertIsNone(r["resources"][2]["type_id"])
        md = "\n".join(pe_summary.render_summary(r, 20))
        self.assertIn("BAD\\x0aNAME\\|X", md)
        self.assertNotIn("BAD\nNAME", md)

    def test_deep_version_nesting(self) -> None:
        blob = struct.pack("<HHH", 8, 0, 0) + b"\0\0"
        for _ in range(5000):
            blob = struct.pack("<HHH", 8 + len(blob), 0, 0) + b"\0\0" + blob
        start = time.perf_counter()
        info = pe_summary.parse_version_info(blob, ("FileVersion",))  # no RecursionError
        self.assertEqual(info["string_tables"], [])
        r = pe_summary.summarize(build_pe(version_raw=blob), "deep.exe")
        self.assertEqual(len(r["version_info"]), 1)
        self.assertLess(time.perf_counter() - start, 5.0)

    def test_import_thunk_amplification(self) -> None:
        thunks, descriptors = 65535, 8  # 524,280 thunks via one shared table

        def custom(rd, _image_base):
            hint = rd.add(struct.pack("<H", 0) + b"Amplified\0", align=2)
            table = rd.add(struct.pack("<I", hint) * thunks + b"\0" * 4)
            name = rd.cstr("AMP.dll")
            desc = struct.pack("<IIIII", table, 0, 0, name, table) * descriptors + bytes(20)
            return {1: (rd.add(desc), len(desc))}

        start = time.perf_counter()
        r = pe_summary.summarize(build_pe(custom=custom), "amp.exe")
        self.assertLess(time.perf_counter() - start, 5.0)
        self.assertTrue(any("import thunks" in e for e in r["parse_errors"]))
        self.assertLess(len(json.dumps(r)), 5_000_000)

    def test_export_name_amplification(self) -> None:
        count = 60000  # overlapping names one byte apart into one long string

        def custom(rd, _image_base):
            text = rd.add(b"A" * 600 + b"\0")
            names = rd.add(b"".join(struct.pack("<I", text + (i % 500)) for i in range(count)))
            funcs = rd.add(struct.pack("<I", 0x1000) * count)
            ords = rd.add(bytes(2 * count))
            export_dir = struct.pack("<IIHHIIIIIII", 0, 0, 0, 0, 0, 1, count, count, funcs, names, ords)
            return {0: (rd.add(export_dir), len(export_dir))}

        start = time.perf_counter()
        r = pe_summary.summarize(build_pe(custom=custom), "expamp.dll")
        self.assertLess(time.perf_counter() - start, 5.0)
        self.assertTrue(any("characters of import/export names" in e for e in r["parse_errors"]))
        self.assertIn("export table present but unparsed", r["fubi_test"]["verdict"])
        self.assertLess(len(json.dumps(r)), 20_000_000)

    def version_leaves_pe(self, leaf_rvas: list[int]) -> bytes:
        def custom(rd, _image_base):
            from synthetic_pe import version_blob
            vblob = version_blob({"FileVersion": "9.8.7.6"}, (9, 8, 7, 6))
            vrva = rd.add(vblob)
            base = rd.add(b"", align=4)
            n = len(leaf_rvas)
            sub_off = 16 + 8
            entries_off = sub_off + 16 + 8 * n
            root = resource_dir([(16, 0x80000000 | sub_off)])
            sub = resource_dir([(i + 1, entries_off + 16 * i) for i in range(n)])
            leaves = b"".join(struct.pack("<IIII", vrva if r is None else r, len(vblob), 0, 0) for r in leaf_rvas)
            blob = root + sub + leaves
            rd.add(blob)
            return {2: (base, len(blob))}

        return build_pe(custom=custom)

    def test_one_bad_version_leaf_keeps_the_others(self) -> None:
        r = pe_summary.summarize(self.version_leaves_pe([0x7FFFFF00, None]), "vbad.exe")
        self.assertEqual(len(r["version_info"]), 1)
        self.assertEqual(r["version_info"][0]["fixed"]["file_version"], "9.8.7.6")
        self.assertTrue(any("version_info: leaf 0" in e for e in r["parse_errors"]))

    def test_too_many_version_leaves_keeps_the_first(self) -> None:
        n = pe_summary.MAX_VERSION_LEAVES + 3
        r = pe_summary.summarize(self.version_leaves_pe([None] * n), "vmany.exe")
        self.assertEqual(len(r["version_info"]), pe_summary.MAX_VERSION_LEAVES)
        self.assertIn(f"version_info: {n} RT_VERSION leaves; only the first "
                      f"{pe_summary.MAX_VERSION_LEAVES} were parsed", r["parse_errors"])

    def test_long_import_name_is_truncated(self) -> None:
        expected = "Q" * pe_summary.MAX_NAME_BYTES + pe_summary.TRUNCATED_MARK
        r = pe_summary.summarize(build_pe(imports={"KERNEL32.dll": ["Q" * 1000, "R" * 5000]}), "long.exe")
        self.assertEqual(r["imports"][0]["functions"][0], expected)
        self.assertEqual(r["imports"][0]["functions"][1], expected.replace("Q", "R"))
        self.assertEqual(r["parse_errors"], [])

    def test_va_based_delay_imports_pe32(self) -> None:
        data = build_pe(delay_imports={"XINPUT1_3.dll": ["XInputGetState", "XInputEnable"]}, delay_va_based=True)
        r = pe_summary.summarize(data, "old.exe")
        self.assertEqual(r["delay_imports"],
                         [{"dll": "XINPUT1_3.dll", "functions": ["XInputGetState", "XInputEnable"]}])
        self.assertEqual(r["parse_errors"], [])

    def test_delay_imports_pe32_plus(self) -> None:
        data = build_pe(pe32plus=True, delay_imports={"XINPUT1_3.dll": ["XInputGetState"]})
        r = pe_summary.summarize(data, "new64.exe")
        self.assertEqual(r["delay_imports"], [{"dll": "XINPUT1_3.dll", "functions": ["XInputGetState"]}])

    def test_va_below_image_base_does_not_wrap_to_file_end(self) -> None:
        data = build_pe(delay_imports={"XINPUT1_3.dll": ["XInputGetState"]}, delay_va_based=True)
        pe = pe_summary.PEFile(data)
        desc = pe.off(pe.data_dir(13)[0])
        data = patch(data, desc + 4, struct.pack("<I", 0x2000))  # an RVA where a VA belongs
        r = pe_summary.summarize(data, "neg.exe")
        entry = r["delay_imports"][0]
        self.assertIsNone(entry["dll"])  # previously "MZ", read from the file start via a negative offset
        self.assertIn("does not map", entry["error"])
        self.assertIsNone(pe.rva_to_offset(-4))

    def test_export_forwarders(self) -> None:
        data = build_pe(exports=["Local"], export_forwarders={"Fwd": "NTDLL.RtlSomething"})
        r = pe_summary.summarize(data, "fwd.dll")
        self.assertEqual(r["exports"]["function_count"], 2)
        self.assertEqual(r["exports"]["forwarder_count"], 1)
        self.assertEqual(r["exports"]["names"], ["Fwd", "Local"])

    def test_one_bad_export_name_keeps_the_rest(self) -> None:
        data = full_pe32()
        pe = pe_summary.PEFile(data)
        names_rva = struct.unpack_from("<I", data, pe.off(pe.data_dir(0)[0]) + 32)[0]
        data = patch(data, pe.off(names_rva), struct.pack("<I", 0x7FFFFF00))
        r = pe_summary.summarize(data, "badname.exe")
        self.assertTrue(r["exports"]["present"])
        self.assertEqual(len(r["exports"]["names"]), len(EXPORTS) - 1)
        self.assertEqual(r["exports"]["unreadable_name_count"], 1)
        self.assertNotIn("no exports found", r["fubi_test"]["verdict"])

    def test_unparsed_export_table_is_not_no_exports(self) -> None:
        data = full_pe32()
        pe = pe_summary.PEFile(data)
        data = patch(data, pe.off(pe.data_dir(0)[0]) + 32, struct.pack("<I", 0x7FFFFF00))  # names table RVA
        r = pe_summary.summarize(data, "badexp.exe")
        verdict = r["fubi_test"]["verdict"]
        self.assertIn("export table present but unparsed", verdict)
        self.assertNotIn("no exports found", verdict)
        self.assertEqual(r["fubi_test"]["negative_result_class"], "search limitation")
        self.assertTrue(r["exports"]["present"])

    def test_bad_import_descriptor_keeps_the_others(self) -> None:
        data = full_pe32()
        pe = pe_summary.PEFile(data)
        first = pe.off(pe.data_dir(1)[0])
        data = patch(data, first + 12, struct.pack("<I", 0x7FFFFF00))  # first DLL name RVA
        r = pe_summary.summarize(data, "badimp.exe")
        self.assertEqual(len(r["imports"]), 2)
        self.assertIsNone(r["imports"][0]["dll"])
        self.assertIn("error", r["imports"][0])
        self.assertEqual(r["imports"][1], {"dll": "WSOCK32.dll", "functions": ["#5"]})

    def test_overlay_note_mentions_authenticode(self) -> None:
        unsigned_size = len(build_pe())
        signed = build_pe(security_dir=(unsigned_size, 64)) + bytes(64)  # certificate table appended
        r = pe_summary.summarize(signed, "signed.exe")
        self.assertEqual(r["overlay_size"], 64)
        self.assertIn("Authenticode", r["overlay_note"])
        self.assertIsNone(pe_summary.summarize(full_pe32(), "plain.exe")["overlay_note"])


class CliErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inp = self.root / "in"
        self.inp.mkdir()
        (self.inp / "one.exe").write_bytes(full_pe32())
        (self.inp / "two.exe").write_bytes(full_pe32())
        self.out = self.root / "out"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = pe_summary.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_unexpected_exception_is_reported_by_type_only(self) -> None:
        saved = pe_summary.summarize
        secret = str(self.root / "in" / "one.exe")

        def flaky(data, name, *rest):
            if name == "one.exe":
                raise IndexError(f"index out of range near {secret}")
            return saved(data, name, *rest)

        pe_summary.summarize = flaky
        try:
            code, _, err = self.run_main(str(self.inp / "one.exe"), str(self.inp / "two.exe"), "--out", str(self.out))
        finally:
            pe_summary.summarize = saved
        self.assertEqual(code, 1)
        self.assertIn("one.exe: IndexError", err)
        self.assertNotIn("Traceback", err)
        assert_no_path(self, err, self.root)
        self.assertTrue((self.out / "two.exe.pe.json").exists())  # the next file still ran

    def test_locked_file_is_reported_without_traceback(self) -> None:
        saved = pe_summary.read_input

        def locked(path):
            exc = PermissionError(13, "The process cannot access the file", str(path))
            raise exc

        pe_summary.read_input = locked
        try:
            code, _, err = self.run_main(str(self.inp / "one.exe"), "--out", str(self.out))
        finally:
            pe_summary.read_input = saved
        self.assertEqual(code, 1)
        self.assertIn("one.exe: file locked or unreadable (PermissionError errno 13)", err)
        assert_no_path(self, err, self.root)

    def test_refuses_output_next_to_input(self) -> None:
        code, _, err = self.run_main(str(self.inp / "one.exe"), "--out", str(self.inp))
        self.assertEqual(code, 2)
        self.assertIn("next to an input file", err)


if __name__ == "__main__":
    unittest.main()
