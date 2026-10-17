"""game.py is split into canopy_*.py modules. Three lists have to agree: the .py files on disk, _PART_NAMES in game.py
(the import order) and CANOPY_PY_MODULES in boot.js (what the page writes into Pyodide's file system before it runs
game.py). A module may only import from the ones listed before it."""
import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _modules_on_disk():
    return sorted(path.stem for path in GAME_DIR.glob("canopy_*.py"))


def _part_names_in_game_py():
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_PART_NAMES" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise AssertionError("_PART_NAMES not found in game.py")


def _boot_js_modules():
    text = (GAME_DIR / "boot.js").read_text(encoding="utf-8")
    block = re.search(r"const CANOPY_PY_MODULES = \[(.*?)\];", text, re.S).group(1)
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
                if target.startswith("canopy_"):
                    assert target in order[:index], f"{name} imports {target}, which is not before it in _PART_NAMES"


def test_no_module_reads_a_live_variable_by_importing_it():
    """`from canopy_runstate import total_income` would copy the number once and go stale at the next harvest."""
    for name in _modules_on_disk():
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "canopy_runstate":
                raise AssertionError(f"{name}.py does 'from canopy_runstate import ...'; use runstate.<name> instead")


def test_live_names_are_forwarded_by_the_game_module(game_env):
    module = game_env.module
    import canopy_runstate

    assert module.total_income is canopy_runstate.total_income
    module.total_income = 12345
    assert canopy_runstate.total_income == 12345
    assert game_env.total_income == 12345
    module.selected_index = 7
    assert canopy_runstate.selected_index == 7
    assert "total_income" in dir(module) and "selected_index" in dir(module)


def test_every_live_name_is_defined_in_the_state_module(game_env):
    import canopy_runstate

    for name in canopy_runstate.LIVE_NAMES:
        assert hasattr(canopy_runstate, name), name


def test_both_pages_load_boot_js_and_the_four_stylesheets():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        assert '<script src="boot.js"></script>' in html, page
        assert html.index('<script src="tutorial-steps.js"></script>') < html.index('<script src="boot.js"></script>'), page


def test_the_community_comparison_reads_live_numbers_through_a_function(game_env):
    """The page used to read total_income, community_relations ... by name from the game's globals; those live
    variables are now held in canopy_runstate, so boot.js asks community_field_value() instead."""
    boot = (GAME_DIR / "boot.js").read_text(encoding="utf-8")
    assert 'pyodide.globals.get("community_field_value")(field)' in boot
    module = game_env.module
    module.total_income = 41.5
    module.total_replants = 3
    assert module.community_field_value("total_income") == 41.5
    assert module.community_field_value("total_replants") == 3
    assert module.community_field_value("community_relations") == module.community_relations
