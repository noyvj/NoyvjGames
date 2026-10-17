"""game.py is split into grid_*.py modules. Three lists have to agree: the .py files on disk, _PART_NAMES in game.py
(the import order) and GRID_PY_MODULES in boot.js (what the page writes into Pyodide's file system before it runs
game.py). A module may only import from the ones listed before it."""
import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _modules_on_disk():
    return sorted(path.stem for path in GAME_DIR.glob("grid_*.py"))


def _part_names_in_game_py():
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_PART_NAMES" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise AssertionError("_PART_NAMES not found in game.py")


def _boot_js_modules():
    text = (GAME_DIR / "boot.js").read_text(encoding="utf-8")
    block = re.search(r"const GRID_PY_MODULES = \[(.*?)\];", text, re.S).group(1)
    return re.findall(r'"([^"]+)"', block)


def test_every_module_on_disk_is_in_game_py_and_in_the_page_boot_list():
    on_disk = _modules_on_disk()
    assert sorted(_part_names_in_game_py()) == on_disk
    assert sorted(name[:-3] for name in _boot_js_modules()) == on_disk
    assert all(name.endswith(".py") for name in _boot_js_modules())


def test_the_boot_list_and_game_py_use_the_same_order():
    assert [name[:-3] for name in _boot_js_modules()] == _part_names_in_game_py()


def test_a_module_only_imports_from_the_modules_before_it():
    order = _part_names_in_game_py()
    for index, name in enumerate(order):
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.ImportFrom) and node.module:
                targets = [node.module]
            elif isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            for target in targets:
                if target.startswith("grid_"):
                    assert target in order[:index], f"{name} imports {target}, which is not before it in _PART_NAMES"


def test_no_module_reads_a_live_variable_by_importing_it():
    """`from grid_runstate import state` would copy the grid once and go stale when the grid is replaced."""
    for name in _modules_on_disk():
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "grid_runstate":
                raise AssertionError(f"{name}.py does 'from grid_runstate import ...'; use runstate.<name> instead")


def test_live_names_are_forwarded_by_the_game_module(game_env):
    module = game_env.module
    import grid_runstate

    assert module.state is grid_runstate.state
    replacement = module.GridState()
    module.state = replacement
    assert grid_runstate.state is replacement
    assert game_env.state is replacement
    module.career_open = True
    assert grid_runstate.career_open is True
    assert "state" in dir(module) and "career_open" in dir(module)


def test_every_live_name_is_defined_in_the_state_module(game_env):
    import grid_runstate

    for name in grid_runstate.LIVE_NAMES:
        assert hasattr(grid_runstate, name), name
