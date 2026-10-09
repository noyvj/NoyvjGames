"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id the script expects
that the HTML lacks. Catch both here."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem != "game"}


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_0-9]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    assert set(_module_list()) == LOCAL, f"app.js loads {sorted(_module_list())}, engine modules are {sorted(LOCAL)}"


def test_every_local_import_is_loaded_before_game_py_runs():
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_0-9]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in _module_list(), f"{path.name} imports {imported}"


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    assert used <= ids, f"app.js uses ids the page lacks: {sorted(used - ids)}"


def test_the_page_has_the_standard_shared_includes_in_the_usual_order():
    order = ["layout-pref.js", "theme-light-games.css", "style.css", "info-page.css", "theme.js", "lite-mode.js", "error-boundary.js",
             "perf-mark.js", "debug-overlay.js", "info-footer.js", "site-settings.js", "settings.js", "ad-bar.css", "achievement-share.js",
             "a11y.css", "touch-targets.css", "lite-mode.css", "pyodide.js", "tutorial.js", "hub-auth.js", "save-widget.js", "opening-screen.js",
             "src=\"app.js\"", "last-played.js", "whats-new-banner.js"]
    at = [HTML.index(name) for name in order]
    assert at == sorted(at), "shared includes are out of the usual order"
    assert set(re.findall(r'data-game-id="([^"]+)"', HTML)) == {"logic-gates"}


def test_the_favicon_is_inside_the_game_folder_and_is_code_drawn_svg():
    assert 'href="../../icons/favicon-logic-gates.svg"' in HTML
    svg = (GAME_DIR / "icons" / "favicon-logic-gates.svg").read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<svg") and "<image" not in svg


def test_the_stylesheet_has_the_blanket_hidden_rule():
    assert "[hidden] { display: none !important; }" in (GAME_DIR / "style.css").read_text(encoding="utf-8")


def test_the_view_has_no_timers_or_clock_for_play():
    for banned in ("setInterval", "Date.now", "new Date", "performance.now", "Math.random", "requestAnimationFrame"):
        assert banned not in APP, banned
    assert APP.count("setTimeout") == 2        # the toast's fade and the live-region refresh: nothing about play
