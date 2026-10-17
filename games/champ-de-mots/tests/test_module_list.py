"""game.py and minigames.py are split into champ_*.py modules. Three lists have to agree: the .py files on disk, the
_PART_NAMES tuples (game.py for the game's modules, minigames.py for champ_minigames_*) and CHAMP_PY_MODULES in boot.js
(what the page writes into Pyodide's file system before it runs game.py; it also lists minigames.py and formats.py). A
module may only import from the ones listed before it."""
import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _parts(entry):
    tree = ast.parse((GAME_DIR / entry).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_PART_NAMES" for t in node.targets):
            return [elt.value for elt in node.value.elts]
    raise AssertionError(f"_PART_NAMES not found in {entry}")


def _on_disk(prefix):
    return sorted(path.stem for path in GAME_DIR.glob(f"{prefix}*.py"))


def _boot_js_modules():
    text = (GAME_DIR / "boot.js").read_text(encoding="utf-8")
    block = re.search(r"const CHAMP_PY_MODULES = \[(.*?)\];", text, re.S).group(1)
    return re.findall(r'"([^"]+)"', block)


def test_every_module_on_disk_is_in_its_entry_file_and_in_the_page_boot_list():
    game_parts, minigame_parts = _parts("game.py"), _parts("minigames.py")
    assert all(name.startswith("champ_") and not name.startswith("champ_minigames_") for name in game_parts)
    assert all(name.startswith("champ_minigames_") for name in minigame_parts)
    assert sorted(game_parts + minigame_parts) == _on_disk("champ_")
    assert sorted(_boot_js_modules()) == sorted([f"{n}.py" for n in game_parts + minigame_parts] + ["minigames.py", "formats.py"])


def test_the_boot_list_keeps_the_entry_files_order():
    boot = [name[:-3] for name in _boot_js_modules()]
    game_parts, minigame_parts = _parts("game.py"), _parts("minigames.py")
    assert [n for n in boot if n in game_parts] == game_parts
    assert [n for n in boot if n in minigame_parts] == minigame_parts


def test_a_module_only_imports_from_the_modules_before_it():
    for entry, prefix in (("game.py", "champ_"), ("minigames.py", "champ_minigames_")):
        order = _parts(entry)
        for index, name in enumerate(order):
            tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    targets = [node.module]
                elif isinstance(node, ast.Import):
                    targets = [alias.name for alias in node.names]
                for target in targets:
                    if target.startswith(prefix) and not (prefix == "champ_" and target.startswith("champ_minigames_")):
                        assert target in order[:index], f"{name} imports {target}, which is not before it in {entry}'s _PART_NAMES"


def test_no_module_reads_a_live_variable_by_importing_it():
    """`from champ_runstate import current_question` would copy the value once and go stale when it is replaced."""
    for name in _on_disk("champ_"):
        tree = ast.parse((GAME_DIR / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in ("champ_runstate", "champ_minigames_runstate"):
                raise AssertionError(f"{name}.py does 'from {node.module} import ...'; use runstate.<name> instead")


def test_live_names_are_forwarded_by_the_game_module(game_env):
    module = game_env.module
    import champ_runstate

    assert module.practice_open is champ_runstate.practice_open
    module.practice_open = True
    assert champ_runstate.practice_open is True
    module.combo_count = 5
    assert champ_runstate.combo_count == 5 and "combo_count" in dir(module)
    assert "practice_open" not in vars(module)


def test_live_names_are_forwarded_by_the_minigames_module(game_env):
    mg = game_env.module.minigames
    import champ_minigames_runstate

    assert mg.blitz_open is champ_minigames_runstate.blitz_open
    mg.blitz_score = 40
    assert champ_minigames_runstate.blitz_score == 40 and "blitz_score" in dir(mg)


def test_a_patched_function_reaches_every_module_that_holds_it(game_env):
    """tests monkeypatch game.<name>; the write is copied into every module that holds the name."""
    module = game_env.module
    import champ_examformats
    import champ_questions

    marker = lambda plot: True  # noqa: E731
    module.generate_question = marker
    assert champ_questions.generate_question is marker
    assert champ_examformats.__dict__.get("generate_question", marker) is marker


def test_every_live_name_is_defined_in_its_state_module(game_env):
    import champ_minigames_runstate
    import champ_runstate

    for module in (champ_runstate, champ_minigames_runstate):
        for name in module.LIVE_NAMES:
            assert hasattr(module, name), name
