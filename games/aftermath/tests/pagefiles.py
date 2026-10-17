"""Read what an Aftermath page ships, now that its stylesheet, inline scripts and game.py are split into several files.

index.html links style-1-base.css ... style-4-tools.css and then style.css (the order is the cascade), and its scripts
(boot.js, shortcuts.js, ...) are separate files; game.py is an entry point plus the aftermath_*.py modules. Tests that
check "the page has this rule / this wiring / the code says this" read the pieces together through these helpers, so
code can move between part files without breaking them.
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
    """game.py followed by every aftermath_*.py module, in the order game.py lists them."""
    entry = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    names = re.findall(r'^    "(aftermath_[a-z_]+)",$', entry, re.M)
    return entry + "\n" + "\n".join((GAME_DIR / f"{name}.py").read_text(encoding="utf-8") for name in names)
