"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id
the script expects that the HTML lacks. Catch both here."""

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
    drawn = set(re.findall(r'\bid="(dr-[a-z-]+)(?:%s)?"', (GAME_DIR / "render.py").read_text(encoding="utf-8")))   # ids inside the engine's own SVG
    assert used <= ids | drawn, f"app.js uses ids the page lacks: {sorted(used - ids - drawn)}"


def test_the_page_has_the_standard_shared_includes_in_the_usual_order():
    order = ["layout-pref.js", "theme-light-games.css", "style.css", "info-page.css", "theme.js", "lite-mode.js", "error-boundary.js",
             "perf-mark.js", "debug-overlay.js", "info-footer.js", "site-settings.js", "settings.js", "ad-bar.css", "copy-result.js",
             "achievement-share.js", "a11y.css", "touch-targets.css", "lite-mode.css", "pyodide.js", "tutorial.js", "hub-auth.js",
             "save-widget.js", "opening-screen.js", "src=\"app.js\"", "last-played.js", "whats-new-banner.js"]
    at = [HTML.index(name) for name in order]
    assert at == sorted(at), "shared includes are out of the usual order"
    assert 'data-game-id="dead-reckoning"' in HTML


def test_the_favicon_is_inside_the_game_folder_and_is_code_drawn_svg():
    assert 'href="../../icons/favicon-dead-reckoning.svg"' in HTML
    svg = (GAME_DIR / "icons" / "favicon-dead-reckoning.svg").read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<svg") and "<image" not in svg


def test_the_desktop_boot_files_exist_and_pc_html_is_the_generated_page():
    import importlib.util
    import json
    root = GAME_DIR.parent.parent
    spec = importlib.util.spec_from_file_location("generate_pc_pages", root / "scripts" / "generate-pc-pages.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert (GAME_DIR / "pc.html").read_text(encoding="utf-8") == generator.build("dead-reckoning", cfg)
    for name in ("pc.css", "pc.js"):
        assert (GAME_DIR / name).exists()
    assert "DEAD_RECKONING_PC_TUTORIAL_STEPS" in HTML and "DEAD_RECKONING_PC_TUTORIAL_STEPS" in (GAME_DIR / "pc.js").read_text(encoding="utf-8")
