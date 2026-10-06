"""Owner-only pages must load shared/owner-gate.js before any other script."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = {
    "admin.html": "shared/owner-gate.js",
    "ideas.html": "shared/owner-gate.js",
    "warframe_build_tracker/index.html": "../shared/owner-gate.js",
}


def test_every_owner_page_loads_the_gate_first():
    for page, src in PAGES.items():
        html = (ROOT / page).read_text(encoding="utf-8")
        scripts = re.findall(r'<script[^>]*\bsrc="([^"]+)"', html)
        assert scripts and scripts[0] == src, f"{page}: gate must be the first script, got {scripts[:1]}"


def test_gate_names_the_owner_and_the_backend_lookup():
    js = (ROOT / "shared" / "owner-gate.js").read_text(encoding="utf-8")
    assert 'const OWNER = "noyvj"' in js
    assert "/users/me" in js
