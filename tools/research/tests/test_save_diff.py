"""Tests for save_diff.py using small synthetic save files."""

from __future__ import annotations

import io
import json
import random
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import save_diff  # noqa: E402
from research_common import repo_root, shannon_entropy  # noqa: E402
from support import assert_no_path  # noqa: E402

SECRET = b"SECRETXY"  # distinctive "changed bytes" that must never reach the report


def patched(data: bytes, patches: dict[int, bytes]) -> bytes:
    buf = bytearray(data)
    for off, value in patches.items():
        buf[off:off + len(value)] = value
    return bytes(buf)


class UnitTests(unittest.TestCase):
    def test_diff_ranges_merge(self) -> None:
        a = bytes(200)
        b = patched(a, {10: b"\x01", 12: b"\x01", 100: b"\x01"})
        self.assertEqual(save_diff.diff_ranges(a, b), (3, [(10, 3), (100, 1)]))
        self.assertEqual(save_diff.diff_ranges(a, b, merge_gap=0)[1], [(10, 1), (12, 1), (100, 1)])

    def test_merge_gap_boundary(self) -> None:
        a = bytes(100)
        # 15 equal bytes between 10 and 26: merged. 16 equal bytes between 10 and 27: separate.
        self.assertEqual(save_diff.diff_ranges(a, patched(a, {10: b"\x01", 26: b"\x01"}))[1], [(10, 17)])
        self.assertEqual(save_diff.diff_ranges(a, patched(a, {10: b"\x01", 27: b"\x01"}))[1], [(10, 1), (27, 1)])

    def test_diff_across_chunks(self) -> None:
        a = bytes(10000)
        b = patched(a, {4095: b"\x01\x01"})
        self.assertEqual(save_diff.diff_ranges(a, b), (2, [(4095, 2)]))

    def test_prefix_suffix(self) -> None:
        a = b"HEADER" + b"ab" + b"TAIL"
        b = b"HEADER" + b"xyz!" + b"TAIL"
        r = save_diff.compare(a, b, 16, 100)
        self.assertEqual((r["common_prefix"], r["common_suffix"]), (6, 4))
        self.assertFalse(r["same_size"])
        # The suffix never overlaps the prefix.
        r = save_diff.compare(b"AAAA", b"AAAAAA", 16, 100)
        self.assertEqual((r["common_prefix"], r["common_suffix"]), (4, 0))

    def test_subtract_ranges(self) -> None:
        self.assertEqual(save_diff.subtract_ranges([(0, 10), (50, 5)], [(3, 2)]), [(0, 3), (5, 5), (50, 5)])
        self.assertEqual(save_diff.subtract_ranges([(0, 10)], [(0, 10)]), [])

    def test_subtract_ranges_matches_bytewise_reference(self) -> None:
        rnd = random.Random(7)
        for _ in range(300):
            keep = sorted((rnd.randrange(200), rnd.randrange(1, 20)) for _ in range(rnd.randrange(8)))
            keep = save_diff.merge_ranges(keep, 1)  # disjoint, like real diff output
            remove = [(rnd.randrange(200), rnd.randrange(0, 20)) for _ in range(rnd.randrange(8))]
            covered = {k for s_, n in remove for k in range(s_, s_ + n)}
            expected = sorted(k for s_, n in keep for k in range(s_, s_ + n) if k not in covered)
            got = [k for s_, n in save_diff.subtract_ranges(keep, remove) for k in range(s_, s_ + n)]
            self.assertEqual(got, expected)

    def test_subtract_ranges_is_not_quadratic(self) -> None:
        keep = [(i * 10, 5) for i in range(20000)]
        remove = [(i * 10 + 2, 1) for i in range(20000)]
        start = time.perf_counter()
        result = save_diff.subtract_ranges(keep, remove)
        self.assertLess(time.perf_counter() - start, 2.0)
        self.assertEqual(len(result), 40000)
        self.assertEqual(result[:2], [(0, 2), (3, 2)])

    def test_merge_gap_larger_than_a_skipped_chunk(self) -> None:
        a = bytes(3 * save_diff.CHUNK)
        b = patched(a, {100: b"\x01", 2 * save_diff.CHUNK + 50: b"\x01"})  # chunk 1 is identical
        count, ranges = save_diff.diff_ranges(a, b, merge_gap=10000)
        self.assertEqual(count, 2)
        self.assertEqual(ranges, [(100, 2 * save_diff.CHUNK + 50 - 100 + 1)])
        self.assertEqual(len(save_diff.diff_ranges(a, b, merge_gap=16)[1]), 2)

    def test_entropy(self) -> None:
        self.assertEqual(shannon_entropy(bytes(4096)), 0.0)
        self.assertEqual(shannon_entropy(bytes(range(256))), 8.0)
        self.assertEqual(shannon_entropy(b""), 0.0)


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        base = b"RSSAVE01" + bytes(range(256)) * 4 + bytes(500)
        self.a, self.a2, self.c = (self.root / n for n in ("EQ-1-A", "EQ-2-A2", "EQ-3-C"))
        for d in (self.a, self.a2, self.c):
            (d / "Save").mkdir(parents=True)
            (d / "Save" / "same.bin").write_bytes(b"unchanged")
        (self.a / "Save" / "slot.ds2party").write_bytes(base)
        (self.a2 / "Save" / "slot.ds2party").write_bytes(patched(base, {50: b"\xee"}))            # noise
        (self.c / "Save" / "slot.ds2party").write_bytes(patched(base, {50: b"\xdd", 600: SECRET}))  # noise + change
        (self.c / "Save" / "new.gas").write_bytes(b"new file")
        self.out = self.root / "out"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = save_diff.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_three_way(self) -> None:
        report, raw = save_diff.run([self.a, self.a2, self.c], ["A", "A2", "C"])
        self.assertEqual(raw, [])
        self.assertEqual(report["comparisons"], ["A->A2", "A2->C", "A->C"])
        files = {f["path"]: f for f in report["files"]}
        self.assertEqual(sorted(files), ["Save/new.gas", "Save/same.bin", "Save/slot.ds2party"])
        slot = files["Save/slot.ds2party"]
        self.assertEqual(slot["comparisons"]["A->A2"]["ranges"], [[50, 1]])
        self.assertEqual(slot["comparisons"]["A2->C"]["differing_bytes"], 1 + len(SECRET))
        self.assertEqual(slot["comparisons"]["A2->C"]["ranges"], [[50, 1], [600, 8]])
        co = slot["change_only"]
        self.assertTrue(co["available"])
        self.assertEqual(co["ranges"], [[600, 8]])
        self.assertEqual(co["differing_bytes"], 8)
        self.assertEqual(files["Save/new.gas"]["comparisons"]["A->C"]["presence"], "only_b")
        self.assertIsNone(files["Save/new.gas"]["snapshots"]["A"])
        self.assertTrue(files["Save/same.bin"]["comparisons"]["A->C"]["sha256_equal"])
        sig = slot["snapshots"]["A"]["signature"]
        self.assertEqual(sig, {"hex": b"RSSAVE01".hex(), "ascii": "RSSAVE01", "length": 8})
        t = report["totals"]["A->C"]
        self.assertEqual((t["files"], t["identical"], t["changed_same_size"], t["only_b"]), (3, 1, 1, 1))

    def test_change_in_gap_between_merged_noise_is_kept(self) -> None:
        # Noise at 10 and 25 merges to (10, 16) with the default gap; the real
        # change at 18 sits in that gap and must survive.
        a = bytes(100)
        a2 = patched(a, {10: b"\x01", 25: b"\x01"})
        c = patched(a, {10: b"\x02", 18: b"\x05", 25: b"\x02"})
        paths = []
        for name, data in (("A", a), ("A2", a2), ("C", c)):
            path = self.root / "gap" / f"{name}.sav"
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
            paths.append(path)
        report, _ = save_diff.run(paths, ["A", "A2", "C"])
        rec = report["files"][0]
        self.assertEqual(rec["comparisons"]["A->A2"]["ranges"], [[10, 16]])
        co = rec["change_only"]
        self.assertEqual(co["ranges"], [[18, 1]])
        self.assertEqual(co["differing_bytes"], 1)

    def test_three_way_with_different_sizes(self) -> None:
        (self.c / "Save" / "slot.ds2party").write_bytes(b"RSSAVE01" + b"\xff" * 300)
        report, _ = save_diff.run([self.a, self.a2, self.c], ["A", "A2", "C"])
        slot = {f["path"]: f for f in report["files"]}["Save/slot.ds2party"]
        self.assertFalse(slot["comparisons"]["A2->C"]["same_size"])
        self.assertEqual(slot["comparisons"]["A2->C"]["common_prefix"], 8)
        self.assertEqual(slot["change_only"], {"available": False,
                                               "reason": "sizes differ, so byte offsets are not comparable"})
        self.assertEqual(report["totals"]["A->C"]["changed_size"], 1)

    def test_file_only_in_first_snapshot(self) -> None:
        (self.a / "Save" / "gone.gas").write_bytes(b"old")
        report, _ = save_diff.run([self.a, self.a2, self.c], ["A", "A2", "C"])
        gone = {f["path"]: f for f in report["files"]}["Save/gone.gas"]
        self.assertEqual(gone["comparisons"]["A->A2"], {"presence": "only_a"})
        self.assertEqual(gone["comparisons"]["A2->C"], {"presence": "neither"})  # was "only_b"
        self.assertEqual(report["totals"]["A2->C"]["only_b"], 1)  # new.gas only; gone.gas is in neither
        self.assertFalse(gone["change_only"]["available"])
        self.assertEqual(report["totals"]["A->A2"]["only_a"], 1)
        md = "\n".join(save_diff.render_summary(report))
        self.assertIn("only in first snapshot", md)

    def test_locked_file_is_reported(self) -> None:
        saved = save_diff.read_snapshot

        def locked(path):
            raise PermissionError(13, "The process cannot access the file", str(path))

        save_diff.read_snapshot = locked
        try:
            code, _, err = self.run_main(str(self.a), str(self.c), "--out", str(self.out))
        finally:
            save_diff.read_snapshot = saved
        self.assertEqual(code, 1)
        self.assertIn("file locked or unreadable (PermissionError errno 13)", err)
        self.assertIn("close the game", err)
        self.assertNotIn("Traceback", err)
        assert_no_path(self, err, self.root)

    def test_symlinked_dir_is_skipped_and_listed(self) -> None:
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "x.bin").write_bytes(b"x")
        try:
            (self.a / "linked").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("cannot create a directory symlink here (Windows without privilege)")
        report, _ = save_diff.run([self.a, self.c], ["A", "C"])
        self.assertEqual(report["skipped_links"], {"A": ["linked/"], "C": []})
        self.assertNotIn("linked/x.bin", [f["path"] for f in report["files"]])

    def test_junction_is_skipped(self) -> None:
        saved = save_diff.is_link_or_junction
        save_diff.is_link_or_junction = lambda p: p.name == "Save" or saved(p)
        try:
            report, _ = save_diff.run([self.a, self.c], ["A", "C"])
        finally:
            save_diff.is_link_or_junction = saved
        self.assertEqual(report["files"], [])
        self.assertEqual(report["skipped_links"], {"A": ["Save/"], "C": ["Save/"]})

    def test_refuses_output_inside_a_snapshot(self) -> None:
        code, _, err = self.run_main(str(self.a), str(self.c), "--out", str(self.a / "out"))
        self.assertEqual(code, 2)
        self.assertIn("inside an input", err)

    def test_two_single_files(self) -> None:
        report, _ = save_diff.run([self.a / "Save" / "slot.ds2party", self.c / "Save" / "slot.ds2party"], ["A", "C"])
        self.assertEqual(report["input_kind"], "files")
        self.assertEqual(len(report["files"]), 1)
        self.assertEqual(report["files"][0]["comparisons"]["A->C"]["range_count"], 2)
        self.assertNotIn("change_only", report["files"][0])

    def test_default_output_has_no_changed_bytes(self) -> None:
        code, stdout, err = self.run_main(str(self.a), str(self.a2), str(self.c), "--labels", "A", "A2", "C",
                                          "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        written = list(self.out.iterdir())
        self.assertEqual(sorted(p.name for p in written), ["A_vs_A2_vs_C.diff.json", "A_vs_A2_vs_C.diff.md"])
        texts = [p.read_text(encoding="utf-8") for p in written]
        for text in texts + [stdout]:
            self.assertNotIn(SECRET.decode(), text)
            self.assertNotIn(SECRET.hex(), text)
        for text in texts:
            assert_no_path(self, text, self.root)
        self.assertEqual(json.loads((self.out / "A_vs_A2_vs_C.diff.json").read_text(encoding="utf-8"))["labels"],
                         ["A", "A2", "C"])

    def test_show_bytes_writes_separate_file_with_warning(self) -> None:
        code, stdout, err = self.run_main(str(self.a2), str(self.c), "--labels", "A2", "C",
                                          "--out", str(self.out), "--show-bytes")
        self.assertEqual(code, 0)
        self.assertIn("WARNING", err)
        raw = self.out / "A2_vs_C.RAW-BYTES-DO-NOT-COMMIT.txt"
        self.assertIn(SECRET.hex(), raw.read_text(encoding="utf-8"))
        for p in (self.out / "A2_vs_C.diff.json", self.out / "A2_vs_C.diff.md"):
            self.assertNotIn(SECRET.hex(), p.read_text(encoding="utf-8"))
        self.assertNotIn(SECRET.hex(), stdout)

    def test_deterministic(self) -> None:
        self.run_main(str(self.a), str(self.c), "--out", str(self.out / "x"))
        self.run_main(str(self.a), str(self.c), "--out", str(self.out / "y"))
        name = "EQ-1-A_vs_EQ-3-C.diff.json"
        self.assertEqual((self.out / "x" / name).read_bytes(), (self.out / "y" / name).read_bytes())

    def test_argument_errors(self) -> None:
        with self.assertRaises(SystemExit):
            self.run_main(str(self.a))
        code, _, err = self.run_main(str(self.a), str(self.c / "Save" / "same.bin"), "--out", str(self.out))
        self.assertEqual(code, 2)
        self.assertIn("all files or all folders", err)
        code, _, err = self.run_main(str(repo_root() / "tools"), str(self.c), "--out", str(self.out))
        self.assertEqual(code, 2)
        code, _, err = self.run_main(str(self.a), str(self.c), "--out", str(repo_root() / "docs" / "x"))
        self.assertEqual(code, 2)

    def test_inputs_unchanged(self) -> None:
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.run_main(str(self.a), str(self.a2), str(self.c), "--out", str(self.out), "--show-bytes")
        for p, data in before.items():
            self.assertEqual(p.read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
