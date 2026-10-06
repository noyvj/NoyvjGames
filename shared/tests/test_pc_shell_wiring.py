"""pc-shell.js is plain JS with no build step, so a function that init() calls but that was
deleted in an edit only fails in a browser. Catch that here."""

import re
from pathlib import Path

JS = (Path(__file__).resolve().parents[2] / "shared" / "pc-shell.js").read_text(encoding="utf-8")


def test_every_function_init_calls_is_defined():
    start = JS.index("  function init() {")
    body = JS[start:JS.index("\n  }\n", start)]
    called = set(re.findall(r"^\s{4}(\w+)\(", body, flags=re.M))
    defined = set(re.findall(r"function (\w+)\(", JS))
    assert called, "expected init() to call setup functions"
    assert called <= defined, f"init() calls undefined functions: {sorted(called - defined)}"


def test_the_shell_script_is_balanced():
    for open_char, close_char in ("{}", "()", "[]"):
        assert JS.count(open_char) == JS.count(close_char), (open_char, close_char)


def test_dragged_windows_have_the_css_they_need():
    css = (Path(__file__).resolve().parents[2] / "shared" / "pc-shell.css").read_text(encoding="utf-8")
    assert ".pc-window-frame.pc-window-moved" in css and "transform: none" in css
    assert "touch-action: none" in css
    assert "placeFrame(frame)" in JS and "dblclick" in JS
