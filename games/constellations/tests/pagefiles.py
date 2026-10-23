"""Read what Constellations' page script ships, now that app.js is cut into several files.

index.html loads app-1-core.js ... app-3-panels.js and then app.js (the order matters: see the File map in CLAUDE.md).
Tests that check "the page script has this wiring or text" read the parts together through app_text(), so a function
can move between parts without breaking them.
"""
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
APP_PART = re.compile(r"^app(?:-\d+-[a-z-]+)?\.js$")


def _page(name="index.html"):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def app_files(page="index.html"):
    """The game's own app scripts in the order index.html loads them (app-1-core.js ... app.js)."""
    names = re.findall(r'<script src="([^"]+)"', _page(page))
    return [n for n in names if APP_PART.match(n)]


def app_text(page="index.html"):
    """Every app script concatenated in load order."""
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in app_files(page))
