import os
import re


def test_wide_screen_pane_layout_in_css():
    css_path = os.path.join(os.path.dirname(__file__), "..", "pc.css")
    with open(css_path, "r") as f:
        content = f.read()
    assert "@media (min-width: 1200px)" in content, "Wide-screen media query missing"
    assert re.search(r"#pc-stage \.planet-cols\s*\{[^}]*display:\s*flex", content, re.DOTALL), "Planet cols should use flex on wide screens"
    assert ".pc-divider" in content, "Divider class missing in CSS"
    assert "cursor: col-resize" in content, "Cursor style for divider missing"


def test_pane_dividers_wired_in_js():
    js_path = os.path.join(os.path.dirname(__file__), "..", "pc.js")
    with open(js_path, "r") as f:
        content = f.read()
    assert 'document.querySelector("#pc-stage .planet-cols")' in content, "JS does not target planet-cols"
    assert 'addEventListener("mousedown"' in content, "Drag handler not wired"
    assert ".pc-divider" in content, "JS does not reference divider class"
    assert "window.innerWidth >= 1200" in content, "Resize listener missing or threshold wrong"
