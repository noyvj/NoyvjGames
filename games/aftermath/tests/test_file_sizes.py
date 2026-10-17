"""Aftermath is split into small files so a small local AI (it holds about 24k tokens and must read a whole file to edit
it) can edit them. These tests keep it that way: no editable file passes about 14,000 estimated tokens (bytes / 4),
and the Python module list the page loads matches the aftermath_*.py files on disk. See "File map" in CLAUDE.md."""

import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
MAX_TOKENS = 14_000

# Not edited by hand by the AI: the Desktop page is generated (scripts/generate-pc-pages.py), the JSON files are
# data, CLAUDE.md is documentation for the main session.
EXEMPT = {"pc.html", "CLAUDE.md", "achievements.json", "changelog.json", "sources.json", "pc-config.json"}
# index.html is the page's markup (about 57 KB once every script and stylesheet is a separate file: roughly 740 lines
# of panels and controls, much of it explanatory comments). It is the one file allowed above the usual limit, with a
# hard cap so it cannot keep growing.
CAPS = {"index.html": 15_000}
SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".txt"}


def _tokens(path):
    return len(path.read_bytes()) // 4


def _editable_files():
    for path in sorted(GAME_DIR.rglob("*")):
        rel = path.relative_to(GAME_DIR)
        if not path.is_file() or "__pycache__" in rel.parts or ".pytest_cache" in rel.parts:
            continue
        if path.suffix not in SUFFIXES or path.name in EXEMPT:
            continue
        yield rel, path


def test_no_editable_file_is_over_the_token_limit():
    too_big = {
        str(rel): _tokens(path)
        for rel, path in _editable_files()
        if _tokens(path) > CAPS.get(rel.as_posix(), MAX_TOKENS)
    }
    assert not too_big, f"split these files (limit {MAX_TOKENS} tokens, about {MAX_TOKENS * 4} bytes): {too_big}"


def _boot_modules():
    boot = (GAME_DIR / "boot.js").read_text(encoding="utf-8")
    block = re.search(r"const AFTERMATH_PY_MODULES = \[(.*?)\];", boot, re.S).group(1)
    return re.findall(r'"([^"]+\.py)"', block)


def _game_part_names():
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "_PART_NAMES" for t in node.targets):
            return [f"{ast.literal_eval(e)}.py" for e in node.value.elts]
    raise AssertionError("game.py has no _PART_NAMES")


def test_the_page_module_list_matches_the_python_files_on_disk():
    on_disk = sorted(path.name for path in GAME_DIR.glob("aftermath_*.py"))
    assert sorted(_boot_modules()) == on_disk
    assert len(set(_boot_modules())) == len(_boot_modules())


def test_game_py_and_the_page_list_the_modules_in_the_same_order():
    assert _boot_modules() == _game_part_names()


def test_each_module_imports_only_from_modules_listed_before_it():
    order = [name[:-3] for name in _boot_modules()]
    for position, module in enumerate(order):
        tree = ast.parse((GAME_DIR / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("aftermath_"):
                imported = [node.module]
            elif isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names if alias.name.startswith("aftermath_")]
            else:
                continue
            for name in imported:
                assert name in order and order.index(name) < position, f"{module} imports {name}"


def test_no_module_reads_a_live_variable_by_importing_it():
    """`from aftermath_runstate import run` would copy the run once and go stale when the run is replaced."""
    for path in GAME_DIR.glob("aftermath_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "aftermath_runstate":
                raise AssertionError(f"{path.name} does 'from aftermath_runstate import ...'; use runstate.<name> instead")


def test_the_pages_load_the_split_stylesheets_in_order():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        links = re.findall(r'<link rel="stylesheet" href="(style[^"]*\.css)"', html)
        assert links == ["style-1-base.css", "style-2-console.css", "style-3-panels.css", "style-4-tools.css", "style.css"], page


def test_live_names_are_forwarded_by_the_game_module(game_env):
    module = game_env.module
    import aftermath_runstate

    assert module.run is aftermath_runstate.run
    replacement = module.RunState(run_number=9)
    module.run = replacement
    assert aftermath_runstate.run is replacement
    assert "run" in dir(module) and "skill_tree" in dir(module)
    for name in aftermath_runstate.LIVE_NAMES:
        assert hasattr(aftermath_runstate, name), name


def test_the_late_bound_render_is_filled_in_when_the_renderer_loads(game_env):
    # Three modules call render() but come before aftermath_renderer in the list: each holds a `render = None`
    # placeholder that aftermath_renderer fills in at the end of its own file. This keeps that wiring from being forgotten.
    import sys

    renderer = sys.modules["aftermath_renderer"]
    for name in ("aftermath_tools", "aftermath_challenges", "aftermath_skillmap"):
        assert sys.modules[name].render is renderer.render, name
    assert game_env.module.render is renderer.render
