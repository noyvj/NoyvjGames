"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id the script
expects that the HTML lacks. Catch both here."""

import json
import re
from pathlib import Path

import info
import reactions

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
    assert len(_module_list()) == len(listed)


def test_every_local_import_is_loaded_before_the_module_that_needs_it():
    modules = _module_list()
    for path in GAME_DIR.glob("*.py"):
        for imported in re.findall(r"^(?:from|import)\s+([a-z_0-9]+)", path.read_text(encoding="utf-8"), flags=re.M):
            if imported in LOCAL:
                assert imported in modules, "%s imports %s" % (path.name, imported)
                if path.stem != "game":
                    assert modules.index(imported) < modules.index(path.stem), "%s must load before %s" % (imported, path.stem)


def test_no_engine_module_uses_syntax_newer_than_python_3_9():
    import ast
    for path in GAME_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
        assert not [n for n in ast.walk(tree) if type(n).__name__ == "Match"], path.name


def test_game_py_exposes_the_save_contract_the_widget_needs():
    text = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    for name in ("def handle(", "def get_state(", "def load_state("):
        assert name in text
    assert "window.pyodide = pyodide" in APP and 'globals.get("get_state")' in APP and 'globals.get("load_state")' in APP
    assert "reactionBenchRefresh" in APP and "reactionBenchRefresh" in text


def test_every_id_app_js_uses_exists_in_the_page():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used, "expected $('id') lookups"
    assert used <= ids, "app.js uses ids the page lacks: %s" % sorted(used - ids)


def test_ids_in_the_page_are_unique():
    ids = re.findall(r'(?<![-\w])id="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))


def test_settings_js_finds_its_controls():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    text = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    used = set(re.findall(r'getElementById\("([^"]+)"\)', text)) | set(re.findall(r'on\("([^"]+)"', text))
    assert used and used <= ids, sorted(used - ids)
    assert "reaction-bench-" in text and "picture-grid" not in text.lower() and "big" not in text.lower()


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">')
    assert 'data-game-id="reaction-bench"' in head


def test_the_save_widget_is_wired_the_way_the_siblings_do_it():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/hub-auth.js", "shared/save-widget.js", "shared/confirm-dialog.js", 'src="app.js"', "shared/last-played.js", "shared/keyboard-shortcuts.js"]
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert '<script src="../../shared/save-widget.js" data-game-id="reaction-bench"></script>' in HTML


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_this_folder_links_nothing_outside_itself_except_shared_includes():
    for name in ("app.js", "settings.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "../" not in text.replace("../../shared/", ""), name
    for path in GAME_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(?<![\w.])open\(", text) and "../" not in text, path.name


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-reaction-bench.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-reaction-bench.svg"' in HTML


def test_no_image_or_audio_files_are_used():
    extra = [p.name for p in GAME_DIR.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav")]
    assert extra == []
    assert "<img" not in HTML and "new Image" not in APP and "Audio(" not in APP


def test_the_view_never_decides_whether_an_equation_balances():
    """app.js draws the engine's ledger, balanced flag and product verdicts; it holds no chemistry of its own."""
    assert "rx.balanced" in APP and "rx.can_run" in APP and "row.ok" in APP and "c.tried" in APP
    for banned in ("countAtoms", "nullspace", "gcd(", "Math.random", "setInterval", "reaction.answer", ".right ==="):
        assert banned not in APP, banned


def test_state_is_never_told_by_colour_alone():
    """Flasks differ in shape, ledger rows have a glyph and a word, tried lists are struck through with a reason, atom chips have a shape and a letter."""
    for needle in ("chip-letter", "\u2713", "\u2717", "too many on the right", "too few on the right", "Tried: not this one", "Goes in", "Comes out", "not found yet", "not on this bench"):
        assert needle in APP, needle
    for needle in ("line-through", "border-style: double", "border-style: dashed", "flask-hatch"):
        assert needle in CSS + APP, needle
    assert re.search(r"CONE", APP) and re.search(r"ROUND", APP)


def test_every_dial_is_a_keyboard_operable_spinbutton_with_a_label_and_range():
    for needle in ('"spinbutton"', "aria-valuemin", "aria-valuemax", "aria-valuenow", "aria-valuetext", "ArrowUp", "ArrowDown", "Home", "End", "PageUp"):
        assert needle in APP, needle
    assert "dialLabel" in APP and "Coefficient for" in APP


def test_touch_and_motion_basics_are_present():
    assert 'data-reduced-motion="true"' in CSS and 'data-effects="off"' in CSS
    assert "../../shared/touch-targets.css" in HTML and "../../shared/a11y.css" in HTML
    assert 'aria-live="polite"' in HTML and 'id="ledger"' in HTML and "<th scope" in HTML


def test_both_themes_define_the_same_variables():
    dark = re.search(r":root \{(.*?)\}", CSS, flags=re.S).group(1)
    light = re.search(r'html\[data-theme="light"\] \{(.*?)\}', CSS, flags=re.S).group(1)
    assert set(re.findall(r"(--[\w-]+):", dark)) == set(re.findall(r"(--[\w-]+):", light))


def test_sources_json_names_every_source_the_about_page_uses():
    sources = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert sources["game"] == "reaction-bench"
    urls = {item["url"] for item in sources["research"]}
    for fact in info.FACTS:
        assert fact["source"]["url"] in urls, fact["id"]
    assert info.LIVE_SOURCE["url"] in urls and any("pubchem" in u for u in urls)
    for item in sources["research"]:
        assert item["read"] == info.DATE_READ and item["note"]


def test_the_about_page_has_a_pledge_how_it_works_and_dated_facts():
    v = info.view()
    assert len(v["pledge"]) >= 4 and len(v["how"]) >= 4 and len(v["facts"]) >= 3
    for f in v["facts"]:
        assert f["source"]["date_read"] == info.DATE_READ and f["source"]["url"].startswith("https://")
    assert "1615" in " ".join(f["fact"] for f in v["facts"]) and "1869" in " ".join(f["fact"] for f in v["facts"])


def test_the_changelog_is_valid_and_dated():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert len(data) >= 2 and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and e["entry"] for e in data)


def test_the_claude_md_table_matches_what_exists():
    text = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")
    rows = {m.group(1): m.group(2).strip() for m in re.finditer(r"^\| (\d|R) \|.*\| (Done|Not started) \|$", text, flags=re.M)}
    assert rows == {"1": "Done", "2": "Done", "3": "Done", "4": "Done", "5": "Done", "6": "Not started", "7": "Not started", "R": "Not started"}
    assert str(len(reactions.ALL)) in text
