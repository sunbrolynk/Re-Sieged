"""Tests for helpstats.py and prefixstats.py on a synthetic help log.

The fixture is invented text that only mimics the layout of the DS1 help dump
(timestamp prefix, '** Section **' headers, indentation). It contains no GPG
content. Run: python -m unittest discover -s tools/research/tests
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import helpstats  # noqa: E402
import prefixstats  # noqa: E402

SYNTHETIC_LOG = "\r\n".join(
    [
        "+00:00:00.001 - header line",
        "+00:00:00.002 - ** Classes **",
        "+00:00:00.003 - Class: Alpha [SINGLETON]",
        "+00:00:00.004 -     void SDoThing( int ) [RPC]",
        "+00:00:00.005 -     void RCDoOther( ) [RPC] [CHECK_SERVER]",
        "+00:00:00.006 -     int Value",
        "+00:00:00.007 - Class: Beta",
        "+00:00:00.008 -     void RSSync( ) [RPC] [!SKRIT]",
        "+00:00:00.009 -     bool plain( float ) [COMPLEX]",
        "+00:00:00.010 - ** Global functions **",
        "+00:00:00.011 - bool GlobalOne( int )",
        "+00:00:00.012 - void GlobalTwo( )",
        "+00:00:00.013 - ** Enumerations **",
        "+00:00:00.014 - eFirst [CONTINUOUS]",
        "+00:00:00.015 - eSecond [IRREGULAR]",
        "+00:00:00.016 - Enumerations:",
        "+00:00:00.017 -     eFirst",
        "+00:00:00.018 -         a_one = 0",
        "+00:00:00.019 -         a_two = 1",
        "+00:00:00.020 -     eSecond",
        "+00:00:00.021 - ",
    ]
)


class HelpStatsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "help.log"
        # write_bytes, not write_text: in text mode Windows would turn each "\r\n"
        # into "\r\r\n", adding a blank line after every line of the fixture.
        self.path.write_bytes(SYNTHETIC_LOG.encode("latin-1"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_counts(self) -> None:
        counts = helpstats.help_counts(helpstats.read_lines(self.path))
        self.assertEqual(counts["classes"], 2)
        self.assertEqual(counts["singleton classes"], 1)
        self.assertEqual(counts["member lines (Classes section, with '(')"], 4)
        self.assertEqual(counts["global function lines"], 2)
        self.assertEqual(counts["enumerations (tagged names)"], 2)
        self.assertEqual(counts["enum value block: entries"], 2)
        self.assertEqual(counts["enum value block: entries with values"], 1)
        self.assertEqual(counts["enum value block: value lines"], 2)
        self.assertEqual(counts["member tags"]["RPC"], 3)

    def test_enum_value_count(self) -> None:
        lines = helpstats.read_lines(self.path)
        self.assertEqual(helpstats.enum_value_count(lines, "eFirst"), 2)
        self.assertEqual(helpstats.enum_value_count(lines, "eSecond"), 0)
        self.assertIsNone(helpstats.enum_value_count(lines, "eMissing"))

    def test_output_has_no_names(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            helpstats.main([str(self.path)])
            prefixstats.main([str(self.path)])
        out = buf.getvalue()
        for name in ("Alpha", "Beta", "SDoThing", "GlobalOne", "eFirst", "a_one"):
            self.assertNotIn(name, out)

    def test_refuses_input_inside_repo(self) -> None:
        inside = Path(__file__).resolve()  # any existing file in the repository
        for script, args in ((helpstats, [str(inside)]), (prefixstats, [str(inside)]),
                             (helpstats, [str(self.path), "--fex", str(inside)])):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = script.main(args)
            self.assertEqual(code, 2, script.__name__)
            self.assertIn("outside the repository", err.getvalue())
            self.assertEqual(out.getvalue(), "")

    def test_missing_input_is_a_usage_error(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(helpstats.main([str(self.path) + ".missing"]), 2)
            self.assertEqual(prefixstats.main([str(self.path) + ".missing"]), 2)
        self.assertIn("input not found", err.getvalue())

    def test_unreadable_input_is_reported_without_traceback(self) -> None:
        secret = str(self.path)

        def locked(*_args, **_kwargs):
            raise PermissionError(13, "The process cannot access the file", secret)

        for module, attr in ((helpstats, "read_lines"), (prefixstats, "class_member_lines")):
            saved = getattr(module, attr)
            setattr(module, attr, locked)
            err = io.StringIO()
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    code = module.main([str(self.path)])
            finally:
                setattr(module, attr, saved)
            self.assertEqual(code, 1, module.__name__)
            self.assertIn("help.log: file locked or unreadable (PermissionError errno 13)", err.getvalue())
            self.assertNotIn(str(Path(self.tmp.name)), err.getvalue())
            self.assertNotIn(Path(self.tmp.name).name, err.getvalue())

    def test_prefix_buckets(self) -> None:
        members = prefixstats.class_member_lines(self.path)
        self.assertEqual(len(members), 4)
        buckets = sorted(
            prefixstats.bucket(prefixstats.CALL_NAME.search(l).group(1))
            for l in members
        )
        self.assertEqual(buckets, ["RC", "RS", "S", "other"])


if __name__ == "__main__":
    unittest.main()
