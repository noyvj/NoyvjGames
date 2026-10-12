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
    assert "teachTheMachineRefresh" in text and "window.teachTheMachineRefresh" in APP


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    assert used <= ids, "app.js uses ids the page lacks: %s" % sorted(used - ids)
    for name in ("lessons", "notebook", "changelog", "settings", "info-page"):          # the Escape handler builds these ids
        assert name + "-panel" in ids and name + "-toggle-button" in ids


def test_ids_in_the_page_are_unique():
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_settings_js_finds_its_controls():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    text = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    used = set(re.findall(r'getElementById\("([^"]+)"\)', text)) | set(re.findall(r'on\("([^"]+)"', text))
    assert used and used <= ids, sorted(used - ids)
    assert "teach-the-machine-" in text and "constellations" not in text.lower()
    for attr in ("data-reduced-motion", "data-effects", "data-high-contrast"):
        assert attr in text


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">')
    assert 'data-game-id="teach-the-machine"' in head


def test_the_save_widget_is_wired_the_way_the_siblings_do_it():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/hub-auth.js", "shared/save-widget.js", "shared/confirm-dialog.js", 'src="app.js"']
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert '<script src="../../shared/save-widget.js" data-game-id="teach-the-machine"></script>' in HTML


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_this_folder_edits_nothing_outside_itself():
    """The game is deliberately not registered with the hub yet: no script reaches outside its folder except to INCLUDE shared files."""
    for name in ("app.js", "settings.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "../" not in text.replace("../../shared/", ""), name


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-teach-the-machine.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-teach-the-machine.svg"' in HTML


def test_no_image_or_audio_files_are_used_pip_is_drawn_by_the_page():
    extra = [p.name for p in GAME_DIR.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav")]
    assert extra == []
    assert "<img" not in HTML and "new Image" not in APP and "Audio(" not in APP and "<svg" in HTML


def test_the_view_holds_no_rules_and_no_clock():
    """app.js draws what the engine says; it grows no tree, scores nothing and decides no category."""
    for banned in ("Math.random", "Date.now", "setInterval", "entropy", "Math.log", "view.lesson.need <", ".right >="):
        assert banned not in APP, banned
    assert "view.lesson.result" in APP and "w.category_name" in APP and "r.passed" in APP


def test_touch_and_motion_basics_are_present():
    assert 'data-reduced-motion="true"' in CSS and 'data-effects="off"' in CSS
    assert "../../shared/touch-targets.css" in HTML and "../../shared/a11y.css" in HTML
    assert 'aria-live="polite"' in HTML and "keydown" in APP and 'role", "switch"' in APP


def test_state_is_never_told_by_colour_alone():
    """A switch says ON or OFF in words and has a ticked or empty box; right and wrong are words with a tick and a cross; an off feature is a
    dashed chip; a cleared lesson has a double border and the word; Pip's lamp has a different glyph per state and a sentence under it."""
    for needle in ('"ON" : "OFF"', "Cleared, best features", '"Right" : "Wrong"', '"Found" : "Not found yet"', "lamp.words"):
        assert needle in APP, needle
    for needle in ('.switch[aria-checked="false"] { border-style: dashed', ".chip.off { border-style: dashed", ".verdict.right { border-style: double",
                   ".verdict.wrong::before", ".lesson-btn.cleared { border-style: double", ".pip-glyph-pleased", ".pip-glyph-puzzled", ".pip-glyph-trained", "\\2611"):
        assert needle in CSS, needle


def test_every_case_is_text_the_player_can_read():
    for needle in ('"train-list"', '"result-list"', '"why-steps"', '"tree-list"'):
        assert needle in APP, needle
    assert 'id="pip-title"' in HTML and 'role="img"' in HTML and 'role="switch"' not in HTML


def _hex(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _lum(rgb):
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    la, lb = sorted((_lum(_hex(a)), _lum(_hex(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _theme(block_start):
    block = CSS.split(block_start)[1].split("}")[0]
    return dict(re.findall(r"(--[a-z-]+):\s*(#[0-9a-fA-F]{6})", block))


def test_text_colours_have_enough_contrast_in_both_themes():
    dark, light = _theme(":root {"), _theme('html[data-theme="light"] {')
    for name, theme in (("dark", dark), ("light", light)):
        for fg, bgs in (("--text", ("--bg", "--panel", "--surface", "--chip-bg")), ("--muted", ("--bg", "--panel", "--surface", "--chip-bg")),
                        ("--accent", ("--bg", "--panel", "--surface")), ("--on-primary", ("--btn-primary",)), ("--ok", ("--surface", "--panel")),
                        ("--focus", ("--bg", "--panel"))):
            for bg in bgs:
                assert _contrast(theme[fg], theme[bg]) >= 4.5, (name, fg, bg, round(_contrast(theme[fg], theme[bg]), 2))
    for var in ("--bg", "--text", "--panel", "--surface", "--btn", "--btn-primary", "--edge", "--line", "--accent", "--focus", "--lamp", "--chip-bg"):
        assert var in dark and var in light, var


def test_both_themes_and_high_contrast_define_the_colours():
    assert 'html[data-theme="light"]' in CSS and 'html[data-high-contrast="true"]' in CSS


# ---- About, sources, changelog -----------------------------------------------------------------------------------------
def test_the_about_page_has_a_pledge_how_it_works_and_dated_sourced_facts():
    import info
    v = info.view()
    assert v["pledge"] and v["how"] and len(v["facts"]) >= 3
    for fact in v["facts"]:
        assert fact["fact"] and fact["tie_in"] and fact["source"]["url"].startswith("https://") and fact["source"]["date_read"] == "2026-10-12"
    assert "invented" in v["framing"] and "does not claim" in v["framing"]            # honest about being a toy, not a claim about real systems
    assert v["live"]["api"].startswith("https://en.wikipedia.org/api/rest_v1/page/summary/")


def test_the_about_page_source_urls_are_all_listed_in_sources_json():
    import info
    sources = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    listed = {item["url"] for item in sources["research"] + sources["other"] if "url" in item}
    for fact in info.view()["facts"]:
        assert fact["source"]["url"] in listed, fact["source"]["url"]
    for item in sources["research"]:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["read"]) and item["url"].startswith("https://") and item["note"]
    assert sources["game"] == "teach-the-machine"


def test_the_changelog_is_valid_and_newest_first_friendly():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    assert data["changelog"]
    for entry in data["changelog"]:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]) and len(entry["entry"]) > 40
