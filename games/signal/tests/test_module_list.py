"""game.py is split into signal_*.py modules. Three lists have to agree: the .py files on disk, _PART_NAMES in game.py
(the import order) and SIGNAL_PY_MODULES in the page script (what the page writes into Pyodide's file system before it
runs game.py). A module may only import from the ones listed before it."""
import ast
import re
from pathlib import Path

from .pagefiles import app_text, part_names

GAME_DIR = Path(__file__).resolve().parent.parent


def _modules_on_disk():
    return sorted(path.stem for path in GAME_DIR.glob("signal_*.py"))


def _page_modules():
    block = re.search(r"var SIGNAL_PY_MODULES = \[(.*?)\];", app_text(), re.S).group(1)
    return re.findall(r'"([^"]+)"', block)


def test_every_module_on_disk_is_in_game_py_and_in_the_page_list():
    on_disk = _modules_on_disk()
    assert sorted(part_names()) == on_disk
    assert sorted(name[:-3] for name in _page_modules()) == on_disk
    assert all(name.endswith(".py") for name in _page_modules())


def test_the_page_list_and_game_py_use_the_same_order():
    assert [name[:-3] for name in _page_modules()] == part_names()


def test_a_module_only_imports_from_the_modules_before_it():
    order = part_names()
    for index, name in enumerate(order):
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.ImportFrom) and node.module:
                targets = [node.module]
            elif isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            for target in targets:
                if target.startswith("signal_"):
                    assert target in order[:index], f"{name} imports {target}, which is not before it in _PART_NAMES"


def test_no_module_reads_a_live_variable_by_importing_it():
    """`from signal_runstate import S` would copy the object once and go stale at the next reset."""
    for name in _modules_on_disk():
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "signal_runstate":
                raise AssertionError(f"{name}.py does 'from signal_runstate import ...'; use runstate.<name> instead")


def test_live_names_are_forwarded_by_the_game_module(game):
    import signal_runstate

    assert set(signal_runstate.LIVE_NAMES) == {"_clock", "_rand", "S", "_cur", "_last_today"}
    for name in signal_runstate.LIVE_NAMES:
        assert hasattr(signal_runstate, name), name
        assert name in dir(game), name
    game.reset_engine()
    assert game.S is signal_runstate.S
    assert game._cur is signal_runstate._cur is None
    game._last_today = "2026-10-01"
    assert signal_runstate._last_today == "2026-10-01"
    game.reset_engine()
    assert signal_runstate._last_today is None


def test_a_write_to_a_function_name_reaches_the_module_that_uses_it(game, monkeypatch):
    """Tests monkeypatch game.<name>; the modules that call the function must see the replacement."""
    import signal_session

    monkeypatch.setattr(game, "utc_today", lambda: "2030-01-01")
    assert signal_session.utc_today() == "2030-01-01"
    assert game.utc_today() == "2030-01-01"


def test_the_page_loads_the_engine_list_before_game_py():
    text = app_text()
    assert text.index("SIGNAL_PY_MODULES.map") < text.index('fetch("game.py")')
