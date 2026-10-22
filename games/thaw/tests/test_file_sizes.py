"""Thaw is split into small files so a small local AI (it holds about 24k tokens and must read a whole file to edit
it) can edit them. These tests keep it that way: no editable file passes about 14,000 estimated tokens (bytes / 4),
and the Python module list the page loads matches the thaw_*.py files on disk. See "File map" in CLAUDE.md."""

import ast
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
MAX_TOKENS = 14_000

# Not edited by hand by the AI: the Desktop page is generated (scripts/generate-pc-pages.py), the JSON files are
# data, CLAUDE.md and NOTES.md are documentation (NOTES.md is the long history, read one section at a time).
EXEMPT = {"pc.html", "CLAUDE.md", "NOTES.md", "achievements.json", "changelog.json", "sources.json", "pc-config.json"}
# index.html is the page's markup (about 57 KB once every script and stylesheet is a separate file). It is the one file
# allowed above the usual limit, with a hard cap so it cannot keep growing.
CAPS = {"index.html": 15_000}
SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".txt"}


def _tokens(path):
    return len(path.read_bytes().replace(b"\r\n", b"\n")) // 4


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
    block = re.search(r"const THAW_PY_MODULES = \[(.*?)\];", boot, re.S).group(1)
    return re.findall(r'"([^"]+\.py)"', block)


def _game_part_names():
    tree = ast.parse((GAME_DIR / "game.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "_PART_NAMES" for t in node.targets):
            return [f"{ast.literal_eval(e)}.py" for e in node.value.elts]
    raise AssertionError("game.py has no _PART_NAMES")


def test_the_page_module_list_matches_the_python_files_on_disk():
    on_disk = sorted(path.name for path in GAME_DIR.glob("thaw_*.py"))
    assert sorted(_boot_modules()) == on_disk
    assert len(set(_boot_modules())) == len(_boot_modules())


def test_game_py_and_the_page_list_the_modules_in_the_same_order():
    assert _boot_modules() == _game_part_names()


def test_each_module_imports_only_from_modules_listed_before_it():
    order = [name[:-3] for name in _boot_modules()]
    for position, module in enumerate(order):
        tree = ast.parse((GAME_DIR / f"{module}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("thaw_"):
                imported = [node.module]
            elif isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names if alias.name.startswith("thaw_")]
            else:
                continue
            for name in imported:
                assert name in order and order.index(name) < position, f"{module} imports {name}"


def test_the_pages_load_the_split_stylesheets_in_order():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        links = re.findall(r'<link rel="stylesheet" href="(style[^"]*\.css)"', html)
        assert links == [
            "style-1-base.css", "style-2-visuals.css", "style-3-panels.css", "style-4-features.css", "style.css",
        ], page
