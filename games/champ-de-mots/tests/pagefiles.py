"""Read what a Le Champ de Mots page ships, now that game.py, minigames.py, style.css and the inline scripts are split
into several files.

index.html links style-1-base.css, style-2-panels.css and style.css (that order is the cascade), its scripts (boot.js,
tutorial-steps.js, page-hooks.js, ...) are separate files, game.py is the entry point for the champ_*.py modules and
minigames.py is the entry point for the champ_minigames_*.py modules. Tests that check "the page has this rule / this
wiring / this Python source" read the pieces together through these helpers, so a rule or function can move between part
files without breaking them.
"""
import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
STYLE_PART = re.compile(r"^style(-\d+-[a-z]+)?\.css$")


def _local(href):
    return "://" not in href and not href.startswith(("../", "/", "#", "data:"))


def style_css():
    """What the old single style.css held: style-1-base.css, style-2-panels.css and style.css, in link order."""
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    names = [h for h in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html) if _local(h) and STYLE_PART.match(h)]
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in names)


def page_text(page="index.html"):
    """The page HTML followed by every local script it loads (boot.js, shortcuts.js, page-hooks.js, ...)."""
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    names = [s for s in re.findall(r'<script src="([^"]+)"', html) if _local(s)]
    seen = []
    for name in names:
        if name not in seen and (GAME_DIR / name).exists():
            seen.append(name)
    return html + "\n" + "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in seen)


def _part_names(entry):
    tree = ast.parse((GAME_DIR / entry).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_PART_NAMES" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise AssertionError(f"_PART_NAMES not found in {entry}")


def game_source():
    """game.py followed by every champ_*.py module it imports (not the minigames' modules): the Python the old single
    game.py held, in module-list order."""
    names = ["game.py"] + [f"{name}.py" for name in _part_names("game.py")]
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in names)


def minigames_source():
    """minigames.py followed by every champ_minigames_*.py module: the Python the old single minigames.py held."""
    names = ["minigames.py"] + [f"{name}.py" for name in _part_names("minigames.py")]
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in names)
