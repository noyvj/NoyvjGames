"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id the script expects that
the HTML lacks. Catch both here, and keep the About page, sources and changelog honest."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem != "game"}      # the entry point is run last


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_0-9]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    listed = set(_module_list())
    assert listed == LOCAL, "app.js loads %s, engine modules are %s" % (sorted(listed), sorted(LOCAL))


def test_every_local_import_is_loaded_before_the_module_that_needs_it():
    modules = _module_list()
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_0-9]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in modules, "%s imports %s" % (path.name, imported)
                if path.stem != "game":
                    assert modules.index(imported) < modules.index(path.stem), "%s must load before %s" % (imported, path.stem)


def test_game_py_exposes_the_save_contract_the_widget_needs():
    text = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    for name in ("def handle(", "def get_state(", "def load_state("):
        assert name in text
    assert "window.pyodide = pyodide" in APP and 'globals.get("get_state")' in APP and 'globals.get("load_state")' in APP
    assert "slingshotRefresh" in text and "window.slingshotRefresh" in APP


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    assert used <= ids, "app.js uses ids the page lacks: %s" % sorted(used - ids)
    for name in ("missions", "atlas", "changelog", "settings", "info-page"):          # the Escape handler builds these ids
        assert name + "-panel" in ids and name + "-toggle-button" in ids


def test_ids_in_the_page_are_unique():
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_settings_js_finds_its_controls():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    text = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    used = set(re.findall(r'getElementById\("([^"]+)"\)', text)) | set(re.findall(r'on\("([^"]+)"', text))
    assert used and used <= ids, sorted(used - ids)
    assert "slingshot-" in text and "constellations" not in text.lower()
    for attr in ("data-reduced-motion", "data-effects", "data-high-contrast"):
        assert attr in text


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">')
    assert 'data-game-id="slingshot"' in head


def test_the_save_widget_is_wired_the_way_the_siblings_do_it():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/hub-auth.js", "shared/save-widget.js", "shared/confirm-dialog.js", 'src="app.js"']
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert '<script src="../../shared/save-widget.js" data-game-id="slingshot"></script>' in HTML


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_this_folder_edits_nothing_outside_itself():
    """The game is deliberately not registered with the hub yet: no script reaches outside its folder except to INCLUDE shared files."""
    for name in ("app.js", "settings.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "../" not in text.replace("../../shared/", ""), name


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-slingshot.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-slingshot.svg"' in HTML


def test_no_image_or_audio_files_are_used_every_planet_and_path_is_drawn_by_the_page():
    extra = [p.name for p in GAME_DIR.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav")]
    assert extra == []
    assert "<img" not in HTML and "new Image" not in APP and "Audio(" not in APP


def test_the_view_holds_no_rules_it_asks_the_engine_for_the_path_and_the_verdict():
    for needle in ("view.flight", "f.verdict", "f.outcome", "view.plan"):
        assert needle in APP, needle
    for banned in ("Math.random", "Date.now", "pass_through", "hohmann", "kepler", "Math.atan2"):
        assert banned.lower() not in APP.lower(), banned


def test_nothing_is_timed_by_the_game():
    for banned in ("setInterval(function () { send", "Date.now", "performance.now"):
        assert banned not in APP
    assert "stopPlay" in APP and "reducedMotion" in APP


def test_touch_and_motion_basics_are_present():
    assert 'data-reduced-motion="true"' in CSS and 'data-effects="off"' in CSS
    assert "../../shared/touch-targets.css" in HTML and "../../shared/a11y.css" in HTML
    assert 'role="img"' in HTML and 'aria-live="polite"' in HTML and "keydown" in APP


def test_state_is_never_told_by_colour_alone():
    """A burn is a diamond with its number, the goal body has a dashed ring and the word goal, the probe has a ring and its name, the future of the path is
    dashed, locked missions are dashed and say locked, done ones carry a tick, and the result title has its own symbol."""
    for needle in ("c-burn-n", "c-target", "(goal)", "c-probe-ring", "c-path-rest", "\u2713", "locked", "c-goalring"):
        assert needle in APP, needle
    for needle in (".c-path-rest { fill: none; stroke: var(--path-rest); stroke-width: 3; stroke-dasharray", ".c-target", ".a-mark.locked .a-ring { stroke-dasharray", "content: \"\\2713\""):
        assert needle in CSS, needle


def test_every_flight_has_a_text_version_in_the_page():
    assert 'id="chart-text"' in HTML and "Chart as text" in HTML and "f.words" in APP and 'id="atlas-text"' in HTML


def test_both_themes_and_high_contrast_define_the_colours():
    assert 'html[data-theme="light"]' in CSS and 'html[data-high-contrast="true"]' in CSS
    names = set(re.findall(r"(--[a-z-]+):", CSS.split('html[data-theme="light"] {')[0]))
    light = CSS.split('html[data-theme="light"] {')[1].split("}")[0]
    for var in ("--sky-b", "--path", "--path-rest", "--burn-fill", "--target", "--text", "--bg", "--central"):
        assert var in names and var in light, var


# ---- About, sources, changelog -------------------------------------------------------------------------------------------------
def test_the_about_page_has_a_pledge_how_it_works_a_model_and_dated_sourced_facts():
    import info
    v = info.view()
    assert v["pledge"] and v["how"] and v["model"] and len(v["facts"]) >= 4
    for fact in v["facts"]:
        assert fact["fact"] and fact["tie_in"] and fact["source"]["url"].startswith("https://") and fact["source"]["date_read"] == "2026-10-12"
    text = " ".join(v["pledge"])
    for word in ("timed", "luck", "sound"):
        assert word in text
    assert "circles" in " ".join(v["model"]) and "degrees" in " ".join(v["model"])


def test_sources_json_names_the_data_sources_and_the_notes_are_ours():
    data = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert data["game"] == "slingshot"
    for r in data["research"]:
        assert r["title"] and r["read"] == "2026-10-12" and r["note"]
    assert any("invented" in o["note"] for o in data["other"])


def test_the_changelog_is_a_list_of_dated_entries():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert entries and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and e["entry"] for e in entries)
    assert len(entries) <= 6


def test_the_claude_md_milestone_table_is_accurate_about_what_is_built():
    text = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (\d|R) \|.*\| (Done|Not started) \|$", text, flags=re.M)
    status = dict(rows)
    assert [status[k] for k in "123"] == ["Done"] * 3 and [status[k] for k in "4567R"] == ["Not started"] * 5
