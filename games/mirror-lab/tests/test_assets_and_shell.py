"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id the script expects
that the HTML lacks. Catch both here."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem != "game"}      # the entry point is run last


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_0-9]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    assert set(_module_list()) == LOCAL


def test_every_local_import_is_loaded_before_the_module_that_needs_it():
    modules = _module_list()
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_0-9]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in modules, "%s imports %s" % (path.name, imported)
                if path.stem != "game":
                    assert modules.index(imported) < modules.index(path.stem), "%s must load before %s" % (imported, path.stem)


def test_the_dev_tools_are_not_loaded_by_the_page_and_the_engine_does_not_import_them():
    assert "tools" not in APP and "solve" not in _module_list()
    for path in GAME_DIR.glob("*.py"):
        assert not re.search(r"^(?:from|import)\s+(solve|specs|build_benches)\b", path.read_text(encoding="utf-8"), flags=re.M), path.name


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used and used <= ids, sorted(used - ids)


def test_ids_in_the_page_are_unique():
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">') and 'data-game-id="mirror-lab"' in head


def test_every_file_the_page_links_exists_in_this_folder_or_shared():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_the_save_widget_is_wired_the_way_the_sibling_games_do_it():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/hub-auth.js", "shared/save-widget.js", "shared/story-toggle.js", "shared/confirm-dialog.js", 'src="app.js"']
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert 'src="../../shared/save-widget.js" data-game-id="mirror-lab"' in HTML
    assert "window.pyodide = pyodide" in APP and 'globals.get("get_state")' in APP and 'globals.get("load_state")' in APP
    assert "mirrorLabRefresh" in APP and "mirrorLabRefresh" in (GAME_DIR / "game.py").read_text(encoding="utf-8")


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-mirror-lab.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-mirror-lab.svg"' in HTML


def test_the_view_never_decides_where_a_beam_goes():
    """app.js draws what the engine returns; it holds no optics of its own."""
    for word in ("reflect", "trace(", "mirror_out", "% 2", "lit.push", "DR[", "DC["):
        assert word not in APP, word


def test_the_page_has_the_controls_the_engine_actions_need():
    for needle in ('id="tray"', 'id="bench-holder"', 'id="clear-button"', 'id="next-button"', 'id="pickup-tool-button"', 'id="sensor-list"', 'id="announce"'):
        assert needle in HTML
    for needle in ('"place"', '"flip"', '"pickup"', '"move"', '"clear_bench"', '"pick"', '"next"', '"reset"'):
        assert needle in APP


def test_targets_are_44_pixels_and_the_bench_has_a_visible_keyboard_ring():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert re.search(r"button, select \{[^}]*min-height: 44px", css)
    assert ".ml-cursor" in css and "stroke: var(--focus)" in css and "ml-cursor" in APP
    assert 'tabindex="0"' in HTML and "bench-holder" in HTML
