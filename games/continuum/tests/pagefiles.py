"""Read what a Continuum page ships, now that game.py, the stylesheet, render3d.js and the inline scripts are split into several files.

index.html links style-1-base.css, style-2-console.css and then style.css (the order is the cascade); its scripts (render3d-scenes.js,
render3d.js, boot.js, shortcuts.js, ...) are separate files; game.py is the entry point for the continuum_*.py modules, and sim.py and
research.py are facades over continuum_sim_*.py and continuum_research_*.py. Tests that check "the page has this rule / this wiring / this
Python source" read the pieces together through these helpers, so a rule or function can move between part files without breaking them.
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
    """The page HTML followed by every local script it loads (boot.js, shortcuts.js, render3d.js, ...)."""
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    names = [s for s in re.findall(r'<script src="([^"]+)"', html) if _local(s)]
    seen = []
    for name in names:
        if name not in seen and (GAME_DIR / name).exists():
            seen.append(name)
    return html + "\n" + "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in seen)


def render3d_source():
    """render3d-scenes.js (building blocks and era scenes) followed by render3d.js (renderer, camera, controls), the old render3d.js."""
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in ("render3d-scenes.js", "render3d.js"))


def game_source():
    """game.py followed by every continuum_*.py module that holds code of the old single game.py (not the sim/research parts)."""
    names = ["game.py"] + sorted(p.name for p in GAME_DIR.glob("continuum_*.py")
                                 if not p.name.startswith(("continuum_sim_", "continuum_research_")))
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in names)


def engine_module_list():
    """The .py file names in boot.js's ENGINE_MODULES, in order."""
    text = (GAME_DIR / "boot.js").read_text(encoding="utf-8")
    block = re.search(r"const ENGINE_MODULES = \[(.*?)\];", text, re.S).group(1)
    return re.findall(r'"([A-Za-z_]+\.py)"', block)
