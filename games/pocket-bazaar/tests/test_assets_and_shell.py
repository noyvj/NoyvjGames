"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id
the script expects that the HTML lacks. Catch both here."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
DEV_ONLY = {"game", "textplay"}                       # the entry point is run last; textplay is the test harness
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem not in DEV_ONLY}


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    listed = set(_module_list())
    assert listed == LOCAL, f"app.js loads {sorted(listed)}, engine modules are {sorted(LOCAL)}"


def test_every_local_import_is_loaded_before_game_py_runs():
    for path in GAME_DIR.glob("*.py"):
        if path.stem == "textplay":
            continue
        for imported in re.findall(r"^(?:from|import)\s+([a-z_]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in _module_list(), f"{path.name} imports {imported}"


def test_engine_modules_never_touch_the_dom_or_a_clock():
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.stem == "game":
            text = text.replace("import js\n", "")           # the one allowed import: the redraw hook
        assert not re.search(r"^\s*(import|from)\s+(js|time|datetime|random)\b", text, flags=re.M), path.name


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    assert used <= ids, f"app.js uses ids the page lacks: {sorted(used - ids)}"


def test_ids_in_the_page_are_unique():
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">')
    assert 'data-game-id="pocket-bazaar"' in head


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref).resolve().exists(), ref
