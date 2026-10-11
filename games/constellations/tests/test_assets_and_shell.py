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
    assert "constellationsRefresh" in text and "window.constellationsRefresh" in APP


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    made = set(re.findall(r'svgEl\("[a-z]+", \{ id: "([^"]+)"', APP))              # ids the script creates itself
    assert used <= ids | made, "app.js uses ids the page lacks: %s" % sorted(used - ids - made)
    for name in ("charts", "atlas", "changelog", "settings", "info-page"):          # the Escape handler builds these ids
        assert name + "-panel" in ids and name + "-toggle-button" in ids


def test_ids_in_the_page_are_unique():
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_settings_js_finds_its_controls():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    text = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    used = set(re.findall(r'getElementById\("([^"]+)"\)', text)) | set(re.findall(r'on\("([^"]+)"', text))
    assert used and used <= ids, sorted(used - ids)
    assert "constellations-" in text and "picture-grid" not in text.lower()
    for attr in ("data-letters", "data-names", "data-reduced-motion", "data-effects", "data-high-contrast"):
        assert attr in text


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">')
    assert 'data-game-id="constellations"' in head


def test_the_save_widget_is_wired_the_way_the_siblings_do_it():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/hub-auth.js", "shared/save-widget.js", "shared/confirm-dialog.js", 'src="app.js"']
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert '<script src="../../shared/save-widget.js" data-game-id="constellations"></script>' in HTML


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_this_folder_edits_nothing_outside_itself():
    """The game is deliberately not registered with the hub yet: no script reaches outside its folder except to INCLUDE shared files."""
    for name in ("app.js", "settings.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "../" not in text.replace("../../shared/", ""), name


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-constellations.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-constellations.svg"' in HTML


def test_no_image_or_audio_files_are_used_every_star_and_line_is_drawn_by_the_page():
    extra = [p.name for p in GAME_DIR.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav")]
    assert extra == []
    assert "<img" not in HTML and "new Image" not in APP and "Audio(" not in APP


def test_the_view_never_decides_a_figure_is_finished_or_a_number_met():
    """app.js draws the engine's `state`, `valid` and `problems`; it holds no rules and no figure of its own."""
    assert "view.valid" in APP and ".state" in APP and "view.problems" in APP
    for banned in ("figure", "solutions", "analyse", "Math.random", "Date.now", "setInterval", "setTimeout(function () { send"):
        assert banned not in APP, banned


def test_touch_and_motion_basics_are_present():
    assert "touch-action" in CSS and 'data-reduced-motion="true"' in CSS and 'data-effects="off"' in CSS
    assert "../../shared/touch-targets.css" in HTML and "../../shared/a11y.css" in HTML
    assert 'role="application"' in HTML and 'aria-live="polite"' in HTML
    assert "pointerdown" in APP and "keydown" in APP and "setPointerCapture" in APP


def test_state_is_never_told_by_colour_alone():
    """A numbered star is a badge with its number, a met number has a double ring and a tick, too many has a dashed ring and a !, a given line is a
    double rail, a crossed-out pair has an x, crossing lines are dashed and marked, a held star has a halo."""
    for needle in ("b-badge", "b-badge-outer", "\u2713", '"!"', "b-never-x", "b-cross-mark", "b-held2", "b-near", "b-letter"):
        assert needle in APP, needle
    for needle in (".b-line.cross { stroke: var(--stroke-cross); stroke-dasharray", ".b-line.given", ".b-badge.over", "stroke-dasharray"):
        assert needle in CSS, needle


def test_every_chart_has_a_text_version_in_the_page():
    assert 'id="chart-text"' in HTML and "Chart as text" in HTML and "view.words" in APP


def test_both_themes_and_high_contrast_define_the_colours():
    assert 'html[data-theme="light"]' in CSS and 'html[data-high-contrast="true"]' in CSS
    names = set(re.findall(r"(--[a-z-]+):", CSS.split('html[data-theme="light"] {')[0]))
    light = CSS.split('html[data-theme="light"] {')[1].split("}")[0]
    for var in ("--sky-b", "--star", "--stroke", "--stroke-cross", "--badge-bg", "--text", "--bg"):
        assert var in names and var in light, var


# ---- About, sources, changelog -----------------------------------------------------------------------------------------
def test_the_about_page_has_a_pledge_how_it_works_and_dated_sourced_facts():
    import info
    v = info.view()
    assert v["pledge"] and v["how"] and len(v["facts"]) >= 3
    for fact in v["facts"]:
        assert fact["fact"] and fact["tie_in"] and fact["source"]["url"].startswith("https://") and fact["source"]["date_read"] == "2026-10-12"
    assert v["live"]["api"].startswith("https://en.wikipedia.org/api/rest_v1/page/summary/")
    text = " ".join(v["pledge"])
    for word in ("timed", "luck", "sound"):
        assert word in text


def test_sources_json_names_the_two_data_sources_and_the_notes_are_ours():
    data = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert data["game"] == "constellations"
    urls = " ".join(r.get("url", "") for r in data["research"])
    assert "astronexus/HYG-Database" in urls and "stellarium.org" in urls
    for r in data["research"]:
        assert r["title"] and r["read"] == "2026-10-12" and r["note"]
    assert any("written for this game" in o["note"] for o in data["other"])


def test_the_changelog_is_a_list_of_dated_entries():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert entries and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and e["entry"] for e in entries)
    assert len(entries) <= 6
