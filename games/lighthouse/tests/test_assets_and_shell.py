"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load, an id
the script expects that the HTML lacks, or a shared include in the wrong order. Catch them here."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
NOT_ENGINE = {"game", "harness"}
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem not in NOT_ENGINE}


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    listed = set(_module_list())
    assert listed == LOCAL, f"app.js loads {sorted(listed)}, engine modules are {sorted(LOCAL)}"


def test_every_local_import_is_loaded_before_game_py_runs():
    order = _module_list()
    for path in GAME_DIR.glob("*.py"):
        if path.stem in NOT_ENGINE:
            continue
        for imported in re.findall(r"^(?:from|import)\s+([a-z_]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in order, f"{path.name} imports {imported}"


def test_game_py_imports_only_things_the_page_loads():
    for imported in re.findall(r"^(?:from|import)\s+([a-z_]+)", (GAME_DIR / "game.py").read_text(encoding="utf-8"), flags=re.M):
        assert imported in LOCAL or imported in {"json", "js"}, imported


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP)) | set(re.findall(r'guard\("([^"]+)"', APP))
    used |= set(re.findall(r'setEnabled\("([^"]+)"', APP))
    used |= set(re.findall(r'wirePanelToggle\("([^"]+)", "([^"]+)"\)', APP) and [i for pair in re.findall(r'wirePanelToggle\("([^"]+)", "([^"]+)"\)', APP) for i in pair])
    assert used, "expected $('id') lookups"
    # ids built at run time by the script itself are not in the static page
    dynamic = {i for i in used if i.startswith(("room-chair", "repair-meter-", "task-rest", "task-tidy", "task-beachcomb", "task-garden"))}
    assert used - dynamic <= ids, f"app.js uses ids the page lacks: {sorted(used - dynamic - ids)}"


def test_ids_are_unique_in_the_page():
    ids = re.findall(r'\sid="([^"]+)"', HTML)
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_the_shared_includes_come_in_the_site_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/layout-pref.js", "shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js",
             "shared/debug-overlay.js", "shared/info-footer.js", "shared/site-settings.js", "shared/a11y.css", "shared/touch-targets.css",
             "shared/lite-mode.css"]
    at = [head.index(x) for x in order]
    assert at == sorted(at)
    assert head.rstrip().endswith('lite-mode.css">')
    for file in ("error-boundary.js", "perf-mark.js", "info-footer.js", "site-settings.js"):
        assert re.search(rf'shared/{file}"[^>]*data-game-id="lighthouse"', head)


def test_the_page_wires_the_save_widget_opening_screen_and_time_controls():
    for needle in ('shared/save-widget.js" data-game-id="lighthouse"', 'shared/opening-screen.js" data-game-id="lighthouse"',
                   'shared/time-controls.js" data-game-id="lighthouse"', 'shared/pause-hidden.js" data-game-id="lighthouse"',
                   'id="pause-hidden-checkbox"', 'id="settings-toggle-button"', 'id="info-page-toggle-button"',
                   'data-pc-page="pc.html"', 'rel="icon" type="image/svg+xml" href="icons/favicon-lighthouse.svg"'):
        assert needle in HTML, needle
    assert (GAME_DIR / "icons" / "favicon-lighthouse.svg").exists()


def test_every_player_facing_hidden_panel_uses_the_hidden_attribute_not_a_style():
    assert not re.search(r'style="[^"]*display\s*:\s*none', HTML)


def test_scene_colours_are_set_in_style_attributes_not_var_presentation_attributes():
    assert not re.search(r'\b(?:fill|stroke)="var\(', HTML)
    assert "fill=\"var(" not in APP


def test_the_changelog_is_well_formed_and_newest_first_in_the_file():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert entries and all(set(e) == {"date", "entry"} for e in entries)
    assert [e["date"] for e in entries] == sorted((e["date"] for e in entries), reverse=True)


def test_the_favicon_is_code_drawn_svg():
    svg = (GAME_DIR / "icons" / "favicon-lighthouse.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and 'viewBox="0 0 64 64"' in svg and "<image" not in svg and "data:" not in svg


def test_no_audio_anywhere():
    for name in ("app.js", "index.html", "style.css"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert not re.search(r"new Audio\(|<audio|AudioContext|\.mp3\b|\.ogg\b|\.wav\b", text), name


def test_the_story_toggle_hides_the_whole_story_layer_and_nothing_else():
    match = re.search(r'story-toggle.js" data-game-id="lighthouse" data-story-selectors="([^"]+)"', HTML)
    assert match
    selectors = [s.strip() for s in match.group(1).split(",")]
    for needed in ("#letters-panel", "#letters-toggle-button", "#room-panel", ".odd-detail", ".sailor-note"):
        assert needed in selectors
    for never in ("#hud", "#scene-panel", "#evening-panel", "#night-panel", "#day-panel", "#log-panel"):
        assert never not in selectors


def test_story_ids_the_script_uses_exist():
    for needle in ('id="letters-list"', 'id="sailors-list"', 'id="gifts-list"', 'id="room-svg"', 'id="report-letters"', 'id="letters-toggle-button"'):
        assert needle in HTML, needle
