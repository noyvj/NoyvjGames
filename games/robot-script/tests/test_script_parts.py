"""app.js was one big function; it is now several classic scripts that share ONE object, window.RobotScriptApp.
These tests check the page loads them in the right order, that each part only uses what an earlier part exported, and
that the split added no new global name."""

import re
from pathlib import Path

from .pagefiles import APP_PART, app_files

GAME_DIR = Path(__file__).resolve().parent.parent
NAMESPACE = "RobotScriptApp"
# Every window.X the page script set before the split, plus nothing new.
EXPECTED_WINDOW_NAMES = {"RobotScriptApp", "CHANGELOG_JSON", "pyodide", "robotScriptRefresh"}


def _read(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def _disk_parts():
    numbered = sorted((p.name for p in GAME_DIR.glob("app-*.js")), key=lambda n: int(n.split("-")[1]))
    return numbered + ["app.js"]


def test_index_lists_the_app_scripts_in_numbered_order_with_app_js_last():
    listed = app_files()
    assert listed == _disk_parts(), listed
    assert all(APP_PART.match(n) for n in listed)
    html = _read("index.html")
    positions = [html.index(f'<script src="{n}"></script>') for n in listed]
    assert positions == sorted(positions)
    between = html[positions[0]:positions[-1] + len(f'<script src="{listed[-1]}"></script>')]
    assert between.count("<script") == len(listed), "the parts must sit next to each other"
    for shared in ("hub-auth.js", "save-widget.js", "opening-screen.js"):
        assert html.index(shared) < positions[0], shared


def _header_aliases(text):
    """(local, exported) pairs of the `var x = A.x, ...` lines at the top of a part."""
    top = text.split('var A = window.%s' % NAMESPACE, 1)[1].split("\n\n", 1)[0]
    return re.findall(r"([\w$]+) = A\.([\w$]+)", top)


def _assigned(text):
    """Names a part puts on the object: the setup lines at its top and the export block at its end."""
    top = text.split('var A = window.%s' % NAMESPACE, 1)[1].split("\n\n", 1)[0]
    tail = text.split("// what the other parts use", 1)[1] if "// what the other parts use" in text else ""
    return set(re.findall(r"\bA\.([\w$]+) = ", top + "\n" + tail))


def test_each_part_only_aliases_what_an_earlier_part_exported():
    seen = set()
    for name in app_files():
        text = _read(name)
        for local, exported in _header_aliases(text) if name != "app-1-core.js" else []:
            assert local == exported, (name, local, exported)
            assert exported in seen, f"{name} uses A.{exported} before an earlier part sets it"
        mine = _assigned(text)
        assert not (mine & seen), f"{name} sets names an earlier part already set: {sorted(mine & seen)}"
        seen |= mine


def test_every_namespace_read_is_set_somewhere():
    assigned = set()
    reads = set()
    for name in app_files():
        text = _read(name)
        assigned |= _assigned(text)
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)       # comments may say "A.name"
        reads |= set(re.findall(r"\bA\.([\w$]+)", code))
    assert reads <= assigned, sorted(reads - assigned)


def test_the_first_part_creates_the_namespace_and_the_others_reuse_it():
    files = app_files()
    assert f"var A = window.{NAMESPACE} = {{}};" in _read(files[0])
    for name in files[1:]:
        assert f"var A = window.{NAMESPACE};" in _read(name), name


def test_nothing_new_is_global_and_every_part_is_one_function():
    window_names = set()
    for name in app_files():
        text = _read(name)
        window_names |= set(re.findall(r"\bwindow\.([A-Za-z_$][\w$]*) = ", text))
        loose = [
            line for line in text.split("\n")
            if line and not line[0].isspace() and not line.startswith(("/*", " *", "*/", "(function () {", "})();"))
        ]
        assert not loose, (name, loose[:3])
        body = re.sub(r"^(?:/\*.*?\*/\s*)", "", text, flags=re.S)
        assert body.startswith('(function () {\n  "use strict";'), name
        assert body.rstrip().endswith("})();"), name
        assert text.count("\n(function () {") + (1 if text.startswith("(function () {") else 0) == 1, name
    assert window_names == EXPECTED_WINDOW_NAMES, sorted(window_names ^ EXPECTED_WINDOW_NAMES)


def test_no_other_script_on_the_page_uses_the_namespace_name():
    html = _read("index.html")
    mine = set(app_files())
    for src in re.findall(r'<script src="([^"]+)"', html):
        if "://" in src or src in mine:
            continue
        path = (GAME_DIR / src).resolve()
        assert NAMESPACE not in path.read_text(encoding="utf-8"), src
