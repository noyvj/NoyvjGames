"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load, an id the
script expects that the HTML lacks, or a file the shell references that is missing. Catch them here."""

import json
import re
from pathlib import Path

import setdata

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    listed = set(re.findall(r'"([a-z_]+)\.py"', block))
    local = {p.stem for p in GAME_DIR.glob("*.py") if p.stem != "game"}
    assert listed == local, (sorted(listed), sorted(local))


def test_every_local_import_is_written_to_the_pyodide_file_system_first():
    local = {p.stem for p in GAME_DIR.glob("*.py")}
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    listed = set(re.findall(r'"([a-z_]+)\.py"', block))
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in local and imported != path.stem:
                assert imported in listed or imported == "game", (path.name, imported)


def test_the_set_files_the_page_fetches_are_exactly_the_format():
    assert re.findall(r'"([a-z]+)"', APP.split("SET_FILES = [")[1].split("]")[0]) == list(setdata.FILES)
    index = json.loads((GAME_DIR / "sets" / "index.json").read_text(encoding="utf-8"))
    for entry in index["sets"]:
        for name in setdata.FILES:
            assert (GAME_DIR / "sets" / entry["folder"] / ("%s.json" % name)).exists()


def test_pyodide_is_loaded_lazily_never_in_the_head():
    assert "pyodide.js" not in HTML
    assert "PYODIDE_URL" in APP and "loadScript(PYODIDE_URL)" in APP


def test_shell_includes_every_shared_piece_the_other_games_have():
    for needle in ("shared/theme.js", "shared/theme-light-games.css", "shared/site-settings.js", "shared/tutorial.js",
                   "shared/confirm-dialog.js", "shared/hub-auth.js", "shared/save-widget.js", "shared/opening-screen.js",
                   "shared/last-played.js", "shared/whats-new-banner.js", "shared/keyboard-shortcuts.js", "ad-bar.css",
                   "manifest.json", "settings.js", 'data-game-id="chronicle"'):
        assert needle in HTML, needle


def test_shared_scripts_load_in_the_order_the_opening_screen_needs():
    # opening-screen.js sets a flag the tutorial reads, and the save widget needs hub-auth first (see signal's audit note)
    assert HTML.index("hub-auth.js") < HTML.index("save-widget.js") < HTML.index("opening-screen.js") < HTML.index('src="app.js"')


def test_every_shared_file_the_page_references_exists():
    for src in re.findall(r'(?:src|href)="(\.\./\.\./[^"]+)"', HTML):
        assert (GAME_DIR / src).resolve().exists(), src
    for name in re.findall(r'(?:src|href)="([a-z][a-z0-9.\-]*\.(?:js|css|json))"', HTML):
        assert (GAME_DIR / name).exists(), name


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used and used <= ids, sorted(used - ids)


def test_ids_the_shared_scripts_expect_exist():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    for needed in ("tutorial-restart-button", "howto-toggle-button", "howto-panel", "achievements-toggle-button", "achievements-panel",
                   "changelog-toggle-button", "changelog-panel", "settings-toggle-button", "settings-panel", "info-page-toggle-button",
                   "info-page-panel", "archive-toggle-button", "archive-panel"):
        assert needed in ids, needed


def test_the_tutorial_points_at_elements_that_exist():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    for sel in re.findall(r'selector: "#([a-z\-]+)"', APP):
        assert sel in ids, sel


def test_nothing_in_the_page_posts_to_a_backend():
    assert "fastapicloud" not in APP and "fastapicloud" not in HTML
    assert not re.search(r'method:\s*["\']POST', APP)
    for url in re.findall(r'fetch\(([^)]*)\)', APP):
        assert "http" not in url, url          # every fetch is a relative file of this game


def test_the_report_button_never_sends_anything():
    assert "Reporting opens soon" in HTML or "Reporting opens soon" in APP
    assert "report-build-button" in HTML and "chronicle:report-drafts" in APP


def test_engine_has_no_dom_dependency():
    for name in ("game.py", "setdata.py", "puzzle.py", "achievements.py", "report.py"):
        source = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "document." not in source and "getElementById" not in source and "window." not in source.replace("js.window", ""), name
    assert len(re.findall(r"^\s+import js\b", (GAME_DIR / "game.py").read_text(encoding="utf-8"), re.M)) == 1


def test_settings_js_uses_its_own_keys_and_stays_out_of_the_save():
    text = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    for key in ("chronicle-text-scale", "chronicle-high-contrast", "chronicle-reduced-motion", "chronicle-effects"):
        assert key in text
    assert "pyodide.globals" not in text and "window.pyodide" not in text and "lexis" not in text.lower()


def test_changelog_shape_and_order():
    log = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert 1 <= len(log) <= 30
    assert [e["date"] for e in log] == sorted((e["date"] for e in log), reverse=True)
    for e in log:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and e["entry"].strip()
        assert "—" not in e["entry"] and "!" not in e["entry"]


def test_no_generated_images_or_binary_assets_ship():
    banned = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}
    assert [p.name for p in GAME_DIR.rglob("*") if p.suffix.lower() in banned] == []
    assert "<img" not in HTML and "<img" not in (GAME_DIR / "review.html").read_text(encoding="utf-8")


def test_the_page_has_no_hub_registration_or_desktop_boot_yet():
    assert not (GAME_DIR / "pc.html").exists() and not (GAME_DIR / "pc.js").exists()
    assert "layout-pref.js" not in HTML


def test_game_claude_md_has_a_milestone_table():
    text = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")
    assert "| # | Milestone" in text and "sample, draft until reviewed" in text.lower()
    for n in ("1", "2", "3"):
        assert re.search(r"^\| %s \|" % n, text, re.M)
