"""Shared test helpers (no game content)."""

from __future__ import annotations

import json
from pathlib import Path, PurePath


def path_forms(root: PurePath) -> list[str]:
    """Every spelling under which an absolute temp path could leak into a report.

    Checking only str(root) is not enough on Windows: JSON escapes each
    backslash ("C:\\\\Users\\\\..."), and the temp folder may be spelled with
    an 8.3 short name ("RUNNER~1"). The temp folder's unique basename
    ("tmpab12cd") survives every spelling, so it is checked too.
    """
    candidates = {str(root)}
    if isinstance(root, Path):
        candidates.add(str(root.resolve()))
    forms = {root.name}
    for text in candidates:
        forms.add(text)
        forms.add(json.dumps(text)[1:-1])
    return sorted(forms)


def assert_no_path(test, text: str, root: PurePath) -> None:
    for form in path_forms(root):
        test.assertNotIn(form, text, f"absolute path form {form!r} leaked into output")
