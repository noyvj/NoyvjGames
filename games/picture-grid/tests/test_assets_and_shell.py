"""The page is plain files with no build step, so the easy mistakes are a module the page forgets to load or an id the script
expects that the HTML lacks. Catch both here."""

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
    assert "picture-grid-" in text and "rule-finder" not in text.lower()


def test_shared_head_includes_keep_the_site_wide_order():
    head = HTML[: HTML.index("</head>")]
    order = ["shared/theme.js", "shared/lite-mode.js", "shared/error-boundary.js", "shared/perf-mark.js", "shared/site-settings.js"]
    positions = [head.index(name) for name in order]
    assert positions == sorted(positions)
    assert head.rstrip().endswith('lite-mode.css">')
    assert 'data-game-id="picture-grid"' in head


def test_the_save_widget_is_wired_the_way_the_siblings_do_it():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/hub-auth.js", "shared/save-widget.js", "shared/confirm-dialog.js", 'src="app.js"']
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert '<script src="../../shared/save-widget.js" data-game-id="picture-grid"></script>' in HTML


def test_every_file_the_page_links_exists():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', HTML):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref


def test_this_folder_edits_nothing_outside_itself_and_links_nothing_that_is_missing():
    """The game is deliberately not registered with the hub yet: no engine module or script reaches outside its folder except
    to INCLUDE shared files."""
    for name in ("app.js", "settings.js"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        assert "../" not in text.replace("../../shared/", ""), name


def test_the_favicon_is_a_code_drawn_svg_in_this_folder_and_the_page_uses_it():
    svg = (GAME_DIR / "icons" / "favicon-picture-grid.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "<image" not in svg and "data:" not in svg
    assert 'href="icons/favicon-picture-grid.svg"' in HTML


def test_no_image_files_are_used_for_pictures():
    """Every picture is hand-authored pixel data: there are no bitmap files in the game folder."""
    extra = [p.name for p in GAME_DIR.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".ogg", ".wav")]
    assert extra == []
    assert "<img" not in HTML and "new Image" not in APP and "Audio(" not in APP


def test_the_view_never_decides_a_line_is_finished_or_a_mark_wrong():
    """app.js draws the engine's `satisfied` and `wrong`; it holds no clue logic and no solution of its own."""
    assert "view.satisfied" in APP and "view.wrong" in APP
    for banned in ("lineClue", "row_clues.map", "solution", "isComplete", "Math.random", "Date.now", "setInterval"):
        assert banned not in APP, banned


def test_every_tint_the_engine_can_name_has_a_colour_ramp_in_both_themes():
    import pictures
    for tint in pictures.TINTS:
        assert ":root .tint-%s" % tint in CSS and 'html[data-theme="light"] .tint-%s' % tint in CSS


def test_touch_and_motion_basics_are_present():
    assert "touch-action" in CSS and 'data-reduced-motion="true"' in CSS and 'data-effects="off"' in CSS
    assert "../../shared/touch-targets.css" in HTML and "../../shared/a11y.css" in HTML
    assert 'role="application"' in HTML and 'aria-live="polite"' in HTML


def test_state_is_never_told_by_colour_alone():
    """A filled cell has a facet and a hatch, a dot is its own shape, a mistake has a slash, a finished clue has a tick."""
    for needle in ("b-facet", "b-hatch", "b-dot", "b-wrong-slash", "b-check", "\u2713"):
        assert needle in APP
