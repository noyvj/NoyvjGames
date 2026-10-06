"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load
or an id the script expects that the HTML lacks. Catch both here."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem != "game"}


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    listed = set(_module_list())
    assert listed == LOCAL, f"app.js loads {sorted(listed)}, engine modules are {sorted(LOCAL)}"
    for name in listed:
        assert (GAME_DIR / f"{name}.py").exists()


def test_every_local_import_is_loaded_before_game_py_runs():
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in _module_list(), f"{path.name} imports {imported}"


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    assert used <= ids, f"app.js uses ids the page lacks: {sorted(used - ids)}"


def test_marks_are_told_apart_by_shape_not_colour():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    zero = re.search(r"\.mark-0\s*\{([^}]*)\}", css).group(1)
    one = re.search(r"\.mark-1\s*\{([^}]*)\}", css).group(1)
    assert re.search(r"width:\s*([\d.]+)rem", zero).group(1) != re.search(r"width:\s*([\d.]+)rem", one).group(1)


def test_the_station_never_relies_on_colour_alone():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert ".lamp.lit" in css and "border: 2px solid" in css and "dashed" in css     # lit vs unlit differ by outline style
    assert ".door.open" in css and ".door.shut" in css
    assert "Door: " in APP and "lamps lit" in APP                                  # and by text
