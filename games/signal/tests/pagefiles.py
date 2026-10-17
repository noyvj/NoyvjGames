"""Read what Signal ships, now that game.py is split into signal_*.py modules.

game.py is the entry point; the rules live in the modules listed in its _PART_NAMES (see "File map" in CLAUDE.md).
Tests that check "the engine source has this text" read all of them together through engine_text(), so a function can
move between modules without breaking them.
"""
import ast
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def part_names():
    """The module names in _PART_NAMES, in import (dependency) order."""
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_PART_NAMES" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise AssertionError("_PART_NAMES not found in game.py")


def engine_files():
    """game.py followed by every part module, as file names."""
    return ["game.py"] + [name + ".py" for name in part_names()]


def engine_text():
    """The whole engine source: game.py and every signal_*.py module concatenated."""
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in engine_files())


# ---- the page script (app.js and, when it is cut into parts, app-1-... before it) -------------------------------------
import re  # noqa: E402

APP_PART = re.compile(r"^app(?:-\d+-[a-z-]+)?\.js$")


def app_files(page="index.html"):
    """The game's own app scripts in the order the page loads them."""
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    return [n for n in re.findall(r'<script src="([^"]+)"', html) if APP_PART.match(n)]


def app_text(page="index.html"):
    """Every app script concatenated in load order."""
    return "\n".join((GAME_DIR / name).read_text(encoding="utf-8") for name in app_files(page))
