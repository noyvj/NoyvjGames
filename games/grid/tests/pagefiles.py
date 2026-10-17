"""Read what a Grid page ships, now that game.py, the stylesheet and the inline scripts are split into several files.

index.html links style-1-base.css ... style-5-extras.css and then style.css (the order is the cascade), its scripts
(boot.js, tutorial-steps.js, feedback.js, ...) are separate files, and game.py is the entry point for the grid_*.py
modules. Tests that check "the page has this rule / this wiring / this Python source" read the pieces together through
these helpers, so a rule or function can move between part files without breaking them.
"""
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _local(href):
    return "://" not in href and not href.startswith(("../", "/", "#", "data:"))


def game_css():
    """Every local stylesheet index.html links, concatenated in link order."""
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    names = [h for h in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html) if _local(h)]
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in names)


def page_text(page="index.html"):
    """The page HTML followed by every local script it loads (boot.js, shortcuts.js, feedback.js, ...)."""
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    names = [s for s in re.findall(r'<script src="([^"]+)"', html) if _local(s)]
    seen = []
    for name in names:
        if name not in seen and (GAME_DIR / name).exists():
            seen.append(name)
    return html + "\n" + "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in seen)


def game_source():
    """game.py followed by every grid_*.py module, the Python the old single game.py held."""
    names = ["game.py"] + sorted(p.name for p in GAME_DIR.glob("grid_*.py"))
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in names)
