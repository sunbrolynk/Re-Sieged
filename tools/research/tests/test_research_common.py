"""Tests for research_common.py: path guards, Markdown escaping, error text."""

from __future__ import annotations

import json
import ntpath
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import research_common as rc  # noqa: E402
from support import assert_no_path  # noqa: E402


class FakeRepo(unittest.TestCase):
    """A throwaway "repository" plus an alias that names the same folder.

    resolve() is replaced by a plain abspath, which simulates Windows cases
    where resolve() returns a spelling that is not under the repository path
    (\\\\?\\ prefix, \\\\localhost\\c$ admin share, subst drive).
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        (self.repo / "docs").mkdir(parents=True)
        (self.repo / "local").mkdir()
        (self.repo / "docs" / "note.md").write_text("x", encoding="utf-8")
        self.alias = self.base / "alias"
        try:
            self.alias.symlink_to(self.repo, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.tmp.cleanup()
            self.skipTest("cannot create a directory symlink here (Windows without privilege)")
        self._saved = (rc.repo_root, rc._resolve)
        rc.repo_root = lambda: self.repo
        rc._resolve = lambda p: Path(os.path.abspath(p.expanduser()))

    def tearDown(self) -> None:
        rc.repo_root, rc._resolve = self._saved
        self.tmp.cleanup()

    def test_input_via_alias_is_refused(self) -> None:
        with self.assertRaises(rc.UsageError):
            rc.check_input_path(self.alias / "docs" / "note.md")

    def test_output_via_alias_outside_local_is_refused(self) -> None:
        with self.assertRaises(rc.UsageError):
            rc.check_output_dir(self.alias / "docs" / "out", "x")

    def test_output_via_alias_inside_local_is_accepted(self) -> None:
        target = self.alias / "local" / "sub"
        self.assertEqual(rc.check_output_dir(target, "x"), target)


class PathGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inp = self.root / "install"
        self.inp.mkdir()
        (self.inp / "a.bin").write_bytes(b"x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_windows_extended_and_unc_spellings_are_lexically_inside(self) -> None:
        within = rc._lexically_within
        self.assertTrue(within(r"\\?\C:\Dev\Re-Sieged\docs", r"c:\dev\re-sieged", ntpath))
        self.assertTrue(within(r"\\?\UNC\host\share\Re\docs", r"\\HOST\share\re", ntpath))
        self.assertTrue(within(r"C:\Dev\Re-Sieged", r"C:\Dev\Re-Sieged", ntpath))
        self.assertFalse(within(r"C:\Dev\Re-SiegedX", r"C:\Dev\Re-Sieged", ntpath))
        self.assertFalse(within(r"D:\Dev\Re-Sieged", r"C:\Dev\Re-Sieged", ntpath))

    def test_output_inside_input_folder_is_refused(self) -> None:
        with self.assertRaises(rc.UsageError):
            rc.check_output_dir(self.inp / "out", "x", [self.inp.resolve()])

    def test_output_next_to_input_file_is_refused(self) -> None:
        with self.assertRaises(rc.UsageError):
            rc.check_output_dir(self.inp, "x", [(self.inp / "a.bin").resolve()])

    def test_output_elsewhere_is_accepted(self) -> None:
        out = self.root / "out"
        self.assertEqual(rc.check_output_dir(out, "x", [self.inp.resolve()]), out.resolve())

    def test_explicit_local_subfolder_is_accepted(self) -> None:
        target = rc.repo_root() / "local" / "sub" / "deeper"
        self.assertEqual(rc.check_output_dir(target, "x"), target.resolve())
        self.assertFalse(target.exists())  # checking never creates it

    def test_output_that_is_a_file_is_refused(self) -> None:
        with self.assertRaises(rc.UsageError):
            rc.check_output_dir(self.inp / "a.bin", "x")


class TextTests(unittest.TestCase):
    def test_md_escape_control_characters(self) -> None:
        out = rc.md_escape("a\nb\r|c`d\x00e\u202ef\x85")
        for bad in ("\n", "\r", "\x00", "\u202e", "\x85"):
            self.assertNotIn(bad, out)
        self.assertEqual(out, "a\\x0ab\\x0d\\|c'd\\x00e\\u202ef\\x85")

    def test_os_error_text_is_locale_independent(self) -> None:
        exc = PermissionError(13, "Zugriff verweigert", "C:\\Users\\<you>\\x")
        self.assertEqual(rc.os_error_text(exc), "PermissionError errno 13")
        exc.winerror = 32  # what Windows sets for a sharing violation
        self.assertEqual(rc.os_error_text(exc), "PermissionError errno 13 winerror 32")

    def test_reparse_point_counts_as_link(self) -> None:
        junction = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o755,
                                         st_file_attributes=rc.FILE_ATTRIBUTE_REPARSE_POINT | 0x10)
        plain = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x10)
        posix = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o755)
        symlink = types.SimpleNamespace(st_mode=stat.S_IFLNK | 0o777)
        self.assertTrue(rc.is_link_stat(junction))
        self.assertFalse(rc.is_link_stat(plain))
        self.assertFalse(rc.is_link_stat(posix))
        self.assertTrue(rc.is_link_stat(symlink))

    def test_path_forms_catch_json_escaped_windows_path(self) -> None:
        # The old check `str(root) not in json_text` misses this leak.
        root = PureWindowsPath("C:\\Users\\<you>\\AppData\\Local\\Temp\\tmpq1w2e3")
        leaked = json.dumps({"p": str(root / "out")})
        self.assertNotIn(str(root), leaked)
        with self.assertRaises(AssertionError):
            assert_no_path(self, leaked, root)


if __name__ == "__main__":
    unittest.main()
