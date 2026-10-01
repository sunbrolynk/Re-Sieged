"""Tests for install_inventory.py using a synthetic install folder."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import install_inventory  # noqa: E402
from research_common import check_output_dir, default_out_dir, repo_root, UsageError  # noqa: E402
from support import assert_no_path  # noqa: E402

CONTENT_MARKER = b"RS-CONTENT-MARKER-DO-NOT-LEAK"


def make_install(root: Path) -> Path:
    inst = root / "Dungeon Siege 2"
    res = inst / "Resources"
    res.mkdir(parents=True)
    (inst / "DungeonSiege2.exe").write_bytes(b"MZ\x90\x00" + b"\0" * 60 + CONTENT_MARKER)
    (res / "Logic.ds2res").write_bytes(b"DSg2Tank" + CONTENT_MARKER)
    (res / "World.ds2map").write_bytes(b"DSg2Tank" + b"\x01\x02")
    (res / "xLogic.ds2res").write_bytes(b"DSg2Tank" + b"\0" * 32)
    (res / "Old.dsres").write_bytes(b"DSigTank" + b"\0" * 8)
    (res / "Broken.ds2res").write_bytes(b"NOTATANK" + CONTENT_MARKER)
    (inst / "goggame-1837106902.info").write_bytes(b"{}")
    (inst / "empty.bin").write_bytes(b"")
    (inst / "binary.dat").write_bytes(b"\x00\xff\x10\x80abcd" + CONTENT_MARKER)
    deep = inst / "sub" / "deep"
    deep.mkdir(parents=True)
    (deep / "readme.txt").write_bytes(b"Hi" + CONTENT_MARKER)
    return inst


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inst = make_install(self.root)
        self.inv = install_inventory.build_inventory(self.inst)
        self.by_path = {f["path"]: f for f in self.inv["files"]}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_totals_and_ordering(self) -> None:
        self.assertEqual(self.inv["totals"]["files"], 10)
        paths = [f["path"] for f in self.inv["files"]]
        self.assertEqual(paths, sorted(paths, key=lambda p: (p.casefold(), p)))
        self.assertIn("sub/deep/readme.txt", paths)
        self.assertIn("Resources/Logic.ds2res", paths)

    def test_hash_size_and_head(self) -> None:
        logic = self.by_path["Resources/Logic.ds2res"]
        data = (self.inst / "Resources" / "Logic.ds2res").read_bytes()
        self.assertEqual(logic["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(logic["size"], len(data))
        self.assertEqual(logic["head"], {"hex": b"DSg2Tank".hex(), "ascii": "DSg2Tank", "length": 8})
        self.assertIsNone(self.by_path["binary.dat"]["head"]["ascii"])
        self.assertEqual(self.by_path["empty.bin"]["head"], {"hex": "", "ascii": None, "length": 0})

    def test_tank_magic(self) -> None:
        self.assertEqual(self.inv["tank_magic_counts"], {"DSg2Tank": 3, "DSigTank": 1})
        self.assertEqual(self.inv["resource_extension_without_tank_magic"], ["Resources/Broken.ds2res"])
        self.assertEqual(self.by_path["Resources/Old.dsres"]["tank_magic"], "DSigTank")

    def test_edition_hints(self) -> None:
        hints = {h["id"]: h for h in self.inv["edition_hints"]}
        self.assertTrue(hints["ds2-exe"]["present"])
        self.assertFalse(hints["bw-exe-candidate"]["present"])
        self.assertEqual(hints["bw-x-resource-files"]["matches"], ["Resources/xLogic.ds2res"])
        self.assertTrue(hints["gog-marker-files"]["present"])
        self.assertFalse(hints["steam-marker-files"]["present"])
        base = hints["base-resource-files"]
        self.assertIn("Movies1.ds2res", base["missing"])
        self.assertNotIn("Logic.ds2res", base["missing"])
        self.assertNotIn("World.ds2map", base["missing"])

    def test_hint_matching_is_case_insensitive(self) -> None:
        (self.inst / "STEAM_API.DLL").write_bytes(b"MZ")
        inv = install_inventory.build_inventory(self.inst)
        hints = {h["id"]: h for h in inv["edition_hints"]}
        self.assertEqual(hints["steam-marker-files"]["matches"], ["STEAM_API.DLL"])

    def test_read_error_is_locale_independent(self) -> None:
        def denied(_path, count=8):
            raise PermissionError(13, "Zugriff verweigert (localized text)", "C:\\Users\\<you>\\x")
        saved = install_inventory.read_head
        install_inventory.read_head = denied
        try:
            inv = install_inventory.build_inventory(self.inst)
        finally:
            install_inventory.read_head = saved
        entry = inv["files"][0]
        self.assertEqual(entry["error"], "PermissionError errno 13")
        self.assertNotIn("Zugriff", json.dumps(inv))
        self.assertEqual(inv["totals"]["errors"], 10)

    def test_symlinked_dir_is_recorded_not_followed(self) -> None:
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "hidden.ds2res").write_bytes(b"DSg2Tank")
        try:
            (self.inst / "linked").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("cannot create a directory symlink here (Windows without privilege)")
        inv = install_inventory.build_inventory(self.inst)
        paths = {f["path"]: f for f in inv["files"]}
        self.assertTrue(paths["linked/"]["symlink"])
        self.assertNotIn("linked/hidden.ds2res", paths)
        self.assertEqual(inv["totals"]["symlinks"], 1)

    def test_junction_is_recorded_not_followed(self) -> None:
        # Simulates a Windows junction: a real folder that the reparse-point
        # check reports as a link. os.walk(followlinks=False) alone would
        # descend into it.
        saved = install_inventory.is_link_or_junction
        install_inventory.is_link_or_junction = lambda p: p.name == "deep" or saved(p)
        try:
            inv = install_inventory.build_inventory(self.inst)
        finally:
            install_inventory.is_link_or_junction = saved
        paths = {f["path"]: f for f in inv["files"]}
        self.assertTrue(paths["sub/deep/"]["symlink"])
        self.assertNotIn("sub/deep/readme.txt", paths)

    @unittest.skipUnless(os.name == "nt", "Windows junctions only")
    def test_real_windows_junction_is_not_followed(self) -> None:
        try:
            import _winapi
            outside = self.root / "elsewhere"
            outside.mkdir()
            (outside / "hidden.ds2res").write_bytes(b"DSg2Tank")
            _winapi.CreateJunction(str(outside), str(self.inst / "junction"))
        except (ImportError, AttributeError, OSError):
            self.skipTest("cannot create a junction here")
        inv = install_inventory.build_inventory(self.inst)
        paths = {f["path"]: f for f in inv["files"]}
        self.assertTrue(paths["junction/"]["symlink"])
        self.assertNotIn("junction/hidden.ds2res", paths)

    def test_no_hash(self) -> None:
        inv = install_inventory.build_inventory(self.inst, do_hash=False)
        self.assertTrue(all(f["sha256"] is None for f in inv["files"]))
        self.assertEqual(inv["tank_magic_counts"]["DSg2Tank"], 3)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inst = make_install(self.root)
        self.out = self.root / "out"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = install_inventory.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_outputs_have_no_content_and_no_absolute_paths(self) -> None:
        code, stdout, _ = self.run_main(str(self.inst), "--out", str(self.out))
        self.assertEqual(code, 0)
        js = (self.out / "Dungeon_Siege_2.inventory.json").read_text(encoding="utf-8")
        md = (self.out / "Dungeon_Siege_2.inventory.md").read_text(encoding="utf-8")
        for text in (js, md, stdout):
            self.assertNotIn(CONTENT_MARKER.decode(), text)
        for text in (js, md, stdout.replace(str(self.out), "<out>")):
            assert_no_path(self, text, self.root)
        self.assertEqual(json.loads(js)["totals"]["files"], 10)
        self.assertIn("DSg2Tank", md)

    def test_deterministic(self) -> None:
        self.run_main(str(self.inst), "--out", str(self.out / "a"), "--label", "run")
        self.run_main(str(self.inst), "--out", str(self.out / "b"), "--label", "run")
        for suffix in (".inventory.json", ".inventory.md"):
            self.assertEqual((self.out / "a" / ("run" + suffix)).read_bytes(),
                             (self.out / "b" / ("run" + suffix)).read_bytes())

    def test_refuses_input_inside_repo(self) -> None:
        code, _, err = self.run_main(str(repo_root() / "tools"), "--out", str(self.out))
        self.assertEqual(code, 2)
        self.assertIn("outside the repository", err)

    def test_refuses_file_input(self) -> None:
        code, _, err = self.run_main(str(self.inst / "empty.bin"), "--out", str(self.out))
        self.assertEqual(code, 2)
        self.assertIn("not a folder", err)

    def test_refuses_output_inside_install(self) -> None:
        code, _, err = self.run_main(str(self.inst), "--out", str(self.inst / "report"))
        self.assertEqual(code, 2)
        self.assertIn("inside an input", err)
        self.assertFalse((self.inst / "report").exists())

    def test_output_dir_rules(self) -> None:
        self.assertEqual(default_out_dir("install_inventory"), repo_root() / "local" / "install_inventory")
        self.assertEqual(check_output_dir(None, "install_inventory"),
                         (repo_root() / "local" / "install_inventory").resolve())
        self.assertEqual(check_output_dir(self.out, "x"), self.out.resolve())
        with self.assertRaises(UsageError):
            check_output_dir(repo_root() / "docs" / "research", "x")
        with self.assertRaises(UsageError):
            check_output_dir(repo_root() / "tools" / "research", "x")


if __name__ == "__main__":
    unittest.main()
