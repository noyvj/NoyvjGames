"""Pulls the tr("key", "English text", ...) calls out of the shared components' source so a test can
check them against shared/strings/en.json (Z-13). Only double-quoted English literals (joined with +)
are understood, which is the one form the components use."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ["save-widget.js", "confirm-dialog.js", "tutorial.js", "achievement-stats.js", "achievement-share.js"]
STRING = r'"(?:[^"\\\n]|\\.)*"'
CALL = re.compile(r'\btr\(\s*(' + STRING + r')\s*,\s*((?:' + STRING + r')(?:\s*\+\s*(?:' + STRING + r'))*)')


def extract(text):
    """{key: english} for every tr() call in the text (the same key must always carry the same text)."""
    found = {}
    for key_lit, english_expr in CALL.findall(text):
        key = json.loads(key_lit)
        english = "".join(json.loads(part) for part in re.findall(STRING, english_expr))
        if key in found and found[key] != english:
            raise AssertionError("key %r has two English texts: %r and %r" % (key, found[key], english))
        found[key] = english
    return found


def extract_all():
    out = {}
    for name in COMPONENTS:
        for key, english in extract((ROOT / "shared" / name).read_text(encoding="utf-8")).items():
            if key in out and out[key] != english:
                raise AssertionError("key %r differs between components" % key)
            out[key] = english
    return out
