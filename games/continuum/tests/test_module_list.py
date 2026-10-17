"""game.py is split into continuum_*.py modules, and sim.py / research.py are facades over continuum_sim_*.py /
continuum_research_*.py parts. Three lists have to agree: the .py files on disk, _PART_NAMES in game.py (the import order of
game.py's parts) and ENGINE_MODULES in boot.js (what the page writes into Pyodide's file system before it runs game.py). A
module may only import from the continuum_* modules listed before it."""
import ast
import sys
from pathlib import Path

from .pagefiles import engine_module_list

GAME_DIR = Path(__file__).resolve().parent.parent
FACADE_PARTS = ("continuum_sim_", "continuum_research_")


def _modules_on_disk():
    return sorted(path.stem for path in GAME_DIR.glob("continuum_*.py"))


def _part_names_in_game_py():
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_PART_NAMES" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise AssertionError("_PART_NAMES not found in game.py")


def test_every_module_on_disk_is_in_the_boot_list_and_game_py_lists_its_own_parts():
    on_disk = _modules_on_disk()
    boot = engine_module_list()
    assert sorted(name[:-3] for name in boot if name.startswith("continuum_")) == on_disk
    game_parts = _part_names_in_game_py()
    assert sorted(game_parts) == [name for name in on_disk if not name.startswith(FACADE_PARTS)]
    assert len(boot) == len(set(boot)), "a module is listed twice in ENGINE_MODULES"
    for name in boot:
        assert (GAME_DIR / name).exists(), f"ENGINE_MODULES lists {name}, which is not in the game folder"


def test_the_boot_list_and_game_py_use_the_same_order_for_the_game_parts():
    boot = [name[:-3] for name in engine_module_list() if name.startswith("continuum_") and not name.startswith(FACADE_PARTS)]
    assert boot == _part_names_in_game_py()


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
                if target.startswith("continuum_") and not target.startswith(FACADE_PARTS):
                    if name == "continuum_renderer" and node.col_offset == 0 and isinstance(node, ast.Import):
                        continue  # the late-bound wiring at the end of continuum_renderer imports the modules before it by name
                    assert target in order[:index], f"{name} imports {target}, which is not before it in _PART_NAMES"


def test_no_module_reads_a_live_variable_by_importing_it():
    """`from continuum_runstate import state` would copy the object once and go stale when the sandbox swaps the settlement."""
    for name in _modules_on_disk():
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "continuum_runstate":
                raise AssertionError(f"{name}.py does 'from continuum_runstate import ...'; use runstate.<name> instead")


def test_live_names_are_forwarded_by_the_game_module(game_env):
    module = game_env.module
    import continuum_runstate

    assert module.state is continuum_runstate.state
    replacement = type(module.state)()
    module.state = replacement
    assert continuum_runstate.state is replacement and game_env.state is replacement
    module.views_tab = "map"
    assert continuum_runstate.views_tab == "map"
    assert "state" in dir(module) and "views_tab" in dir(module)


def test_every_live_name_is_defined_in_the_state_module():
    import continuum_runstate  # noqa: F401 (imported fresh by game_env-free tests too)

    for name in continuum_runstate.LIVE_NAMES:
        assert hasattr(continuum_runstate, name), name


def test_render_is_wired_into_every_module_that_calls_it_before_it_exists(game_env):
    """Modules before continuum_renderer hold `render = None`; the renderer fills them in when it is imported."""
    renderer = sys.modules["continuum_renderer"]
    holders = [name for name in _part_names_in_game_py() if "render" in vars(sys.modules[name])]
    assert "continuum_setup" in holders and "continuum_renderer" in holders
    for name in holders:
        assert vars(sys.modules[name])["render"] is renderer.render, name
    assert game_env.module.render is renderer.render


def test_the_page_can_ask_for_the_clock_speed_without_a_stale_copy(game_env):
    module = game_env.module
    module.set_speed(2)
    assert module.current_sim_speed() == 2
    module.set_speed(0)
    assert module.current_sim_speed() == 0


def test_sim_and_research_facades_re_export_every_name_of_their_parts():
    import continuum_research_nodes_early
    import continuum_research_nodes_late
    import continuum_research_nodes_mid
    import continuum_research_tree
    import continuum_sim_city
    import continuum_sim_numbers
    import continuum_sim_tables
    import research
    import sim

    for facade, parts in ((sim, (continuum_sim_tables, continuum_sim_numbers, continuum_sim_city)),
                          (research, (continuum_research_tree, continuum_research_nodes_early,
                                      continuum_research_nodes_mid, continuum_research_nodes_late))):
        for part in parts:
            for name, value in vars(part).items():
                if not name.startswith("__"):
                    assert getattr(facade, name) is value, f"{facade.__name__}.{name}"
    assert sim.CityState is continuum_sim_city.CityState
    assert len(research.NODE_LIST) == 60 and research.NODES["fire_keeping"].node_id == "fire_keeping"
