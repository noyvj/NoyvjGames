"""index.html fetches every engine module into Pyodide by name; a module that game.py or another
engine module imports but the list omits would only fail in a real browser."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_engine_module_list_matches_the_local_imports():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    listed = set(re.findall(r'"([a-z_]+\.py)"', re.search(r"ENGINE_MODULES = \[(.*?)\]", html, re.S).group(1)))
    used = set()
    for path in GAME_DIR.glob("*.py"):
        for first, second in re.findall(r"^import (\w+)|^from (\w+) import", path.read_text(encoding="utf-8"), re.M):
            name = first or second
            if (GAME_DIR / f"{name}.py").exists():
                used.add(f"{name}.py")
    used.discard("game.py")
    assert used - listed == set(), f"imported but not fetched by index.html: {sorted(used - listed)}"
    assert listed - used == set(), f"fetched but never imported: {sorted(listed - used)}"
