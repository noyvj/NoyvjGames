"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id
the script expects that the HTML lacks. Catch both here."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
LOCAL = {p.stem for p in GAME_DIR.glob("*.py") if p.stem != "game"}      # the entry point is run last


def _module_list():
    block = APP.split("ENGINE_MODULES = [")[1].split("]")[0]
    return re.findall(r'"([a-z_]+)\.py"', block)


def test_the_page_loads_every_engine_module_and_no_stray_ones():
    listed = set(_module_list())
    assert listed == LOCAL, f"app.js loads {sorted(listed)}, engine modules are {sorted(LOCAL)}"


def test_every_local_import_is_loaded_before_game_py_runs():
    modules = _module_list()
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in modules, f"{path.name} imports {imported}"
                if path.stem != "game":
                    assert modules.index(imported) < modules.index(path.stem), f"{imported} must load before {path.stem}"


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
    assert 'data-game-id="rule-finder"' in head


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_the_changelog_is_valid_and_dated():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert data and all(re.match(r"\d{4}-\d{2}-\d{2}$", e["date"]) and e["entry"] for e in data)


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-rule-finder.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-rule-finder.svg"' in HTML


def test_shared_includes_are_in_the_standard_order_after_the_page_scripts():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/tutorial.js", "shared/hub-auth.js", "shared/save-widget.js", "shared/opening-screen.js", "shared/story-toggle.js",
             "shared/confirm-dialog.js", 'src="app.js"', "shared/last-played.js", "shared/whats-new-banner.js", "shared/keyboard-shortcuts.js"]
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)


def test_the_page_has_one_item_builder_per_kind_of_item():
    for needle in ('id="builder-num"', 'id="builder-shape"', 'id="builder-grid"', 'id="num-input"', 'id="shape-palette"', 'id="grid-cells"', 'id="send-button"'):
        assert needle in HTML
    for needle in ('"test"', '"preview"', '"name"', '"restart"'):
        assert needle in APP


def test_the_view_never_decides_what_goes_through():
    """app.js draws answers from the engine; it holds no rule of its own."""
    assert "accepts" not in APP and "rule_accepts" not in APP and "% 2" not in APP and "isPrime" not in APP


def test_the_tutorial_only_points_at_things_the_page_has():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    steps = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "#([\w-]+)"', steps)
    assert len(selectors) >= 5 and set(selectors) <= ids
    assert 'id="tutorial-restart-button"' in HTML and "ruleFinderTutorialSteps" in HTML and "tutorial.js" in HTML


def test_the_opening_screen_and_story_toggle_are_wired_for_this_game():
    assert 'opening-screen.js" data-game-id="rule-finder" data-game-name="Rule Finder"' in HTML
    assert 'story-toggle.js" data-game-id="rule-finder" data-story-selectors=".story-text"' in HTML
    assert 'class="verdict-line story-text note"' in HTML and "line story-text" in APP


def test_every_panel_the_shortcuts_close_exists_and_has_a_toggle():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    block = HTML.split("KeyboardShortcuts.init(")[1].split("});")[0]
    pairs = re.findall(r'toggle: "([\w-]+)", panel: "([\w-]+)"', block)
    assert len(pairs) >= 5
    for toggle, panel in pairs:
        assert toggle in ids and panel in ids
    assert "Backspace takes a tile back" in block


def test_the_sources_file_follows_the_schema_and_lists_only_what_the_plan_records():
    data = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert data["game"] == "rule-finder" and re.match(r"\d{4}-\d{2}-\d{2}$", data["updated"]) and data["research"] == []
    assert {i["title"] for i in data["inspiration"]} == {"Wason's 2-4-6 task", "Eleusis"}
    for entry in data["inspiration"]:
        assert entry["kind"] in ("game", "show", "book", "film", "other") and entry["note"]
    for entry in data["other"]:
        assert entry["title"] and entry["by"] and entry["note"] and entry.get("url", "https://").startswith("https://")
    assert "../../sources.html?game=rule-finder" in HTML


def test_the_about_page_says_fiction_and_the_pledge():
    import info
    v = info.view()
    text = " ".join(v["pledge"]) + v["framing"]
    for needle in ("no timer", "No audio", "no leaderboards", "invented", "no real-world facts"):
        assert needle.lower() in (text + v["notice"]).lower()
    assert len(v["pledge"]) >= 5 and v["how"] and "Fiction" in v["notice"]
