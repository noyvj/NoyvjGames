"""Read what a Loop page ships, now that its stylesheet and inline scripts are split into several files.

index.html links style-1-base.css ... style-6-features.css and then style.css (the order is the cascade), and its
scripts (boot.js, shortcuts.js, ...) are separate files. Tests that check "the page has this rule / this wiring"
read the pieces together through these two helpers, so a rule can move between part files without breaking them.
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
