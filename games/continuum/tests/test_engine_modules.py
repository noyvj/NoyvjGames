"""boot.js (ENGINE_MODULES) fetches every engine module into Pyodide by name; a module that game.py or another
engine module imports but the list omits would only fail in a real browser."""

import ast
import re
from pathlib import Path

from .pagefiles import engine_module_list

GAME_DIR = Path(__file__).resolve().parent.parent


def test_engine_module_list_matches_the_local_imports():
    listed = set(engine_module_list())
    used = set()
    for path in GAME_DIR.glob("*.py"):
        for first, second in re.findall(r"^import (\w+)|^from (\w+) import", path.read_text(encoding="utf-8"), re.M):
            name = first or second
            if (GAME_DIR / f"{name}.py").exists():
                used.add(f"{name}.py")
    # game.py loads its continuum_* parts by name (importlib), not with import statements
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "_PART_NAMES" for t in node.targets):
            used |= {f"{ast.literal_eval(e)}.py" for e in node.value.elts}
    used.discard("game.py")
    assert used - listed == set(), f"imported but not fetched by index.html: {sorted(used - listed)}"
    assert listed - used == set(), f"fetched but never imported: {sorted(listed - used)}"
