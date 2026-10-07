"""Milestone 8: accessibility, light theme, display settings, What's New and the Desktop boot.

The page is plain files, so these are source-level checks: contrast is computed from the real colour variables,
every state is checked for a non-colour cue, and the markup is checked for the labels and live regions the
script depends on. The live behaviour (keyboard, focus kept across redraws, announcements) was driven in a
browser; see CLAUDE.md."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")


# ---- colour maths (WCAG 2.x) --------------------------------------------------------------------
def _variables(selector):
    block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS).group(1)
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})\b", block))


def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


DARK = _variables(":root")
LIGHT = {**DARK, **_variables('html[data-theme="light"]')}

# (foreground, background, minimum): text pairs need 4.5, outlines and icons that carry meaning need 3.
TEXT_PAIRS = [("--text", "--bg"), ("--text", "--panel"), ("--text", "--surface"), ("--text", "--btn"),
              ("--muted", "--panel"), ("--muted", "--bg"), ("--accent", "--panel"), ("--accent", "--bg"),
              ("--on-primary", "--btn-primary")]
UI_PAIRS = [("--edge", "--panel"), ("--edge", "--surface"), ("--muted", "--off"), ("--focus", "--panel"),
            ("--focus", "--bg"), ("--hover-edge", "--panel")]


def test_both_themes_define_every_colour_variable():
    assert set(DARK) == set(_variables('html[data-theme="light"]')), "the light theme must override every variable"


def test_text_contrast_is_at_least_aa_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in TEXT_PAIRS:
            ratio = contrast(theme[fg], theme[bg])
            assert ratio >= 4.5, f"{name}: {fg} on {bg} is {ratio:.2f}"


def test_outlines_and_focus_ring_contrast_is_at_least_three_to_one_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in UI_PAIRS:
            ratio = contrast(theme[fg], theme[bg])
            assert ratio >= 3.0, f"{name}: {fg} on {bg} is {ratio:.2f}"


def test_a_lit_lamp_stands_out_from_its_panel_by_fill_or_outline_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        best = max(contrast(theme["--on"], theme["--panel"]), contrast(theme["--on-edge"], theme["--panel"]))
        assert best >= 3.0, f"{name}: {best:.2f}"


def test_the_stylesheet_has_no_hard_coded_dark_surfaces_left():
    body = CSS.split("* { box-sizing")[1]
    assert not re.search(r"#0e1526|#1b2744|#234a7a|#121a2b", body), "use the colour variables so the light theme applies"


def test_the_light_theme_follows_the_site_theme():
    assert 'shared/theme.js" data-floating-toggle' in HTML and "theme-light-games.css" in HTML
    assert 'html[data-theme="light"]' in CSS
    assert 'data-game-id="lexis"' in HTML and "site-settings.js" in HTML     # a signed-in player's theme follows them
    assert "NoyvjTheme" in SETTINGS and 'id="theme-setting-button"' in HTML


# ---- states carry a non-colour cue ----------------------------------------------------------------
def _rule(selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert match, selector
    return match.group(1)


def test_every_state_has_a_shape_or_text_cue_as_well_as_a_colour():
    assert "dashed" in _rule(".lamp") and "solid" in _rule(".lamp.lit")           # lit lamp: solid outline vs dashed
    assert "lit" in APP and "lamp-count" in APP and 'id="lamp-count"' in HTML      # and a written count
    assert "double" in _rule(".door.shut") and "solid" in _rule(".door.open")      # door: outline style plus a word
    tab = _rule('.planet-tabs button[aria-pressed="true"]')
    assert "underline" in tab and "font-weight" in tab and "border-width" in tab   # chosen planet: not fill alone
    assert "dashed" in _rule(".ach-list li:not(.earned)") and "Earned" in APP and "Not yet" in APP
    assert "dashed" in _rule('button[aria-disabled="true"]'.replace('button[aria-disabled="true"]', 'button[disabled], button[aria-disabled="true"]'))
    assert "dashed" in _rule(".glyph.marker")                                      # a small sign is dashed, a noun solid
    assert "stock-count" in APP                                                    # counter chips carry a number


def test_notebook_check_result_is_text_and_never_marks_an_entry():
    assert "ticked entries are right" in APP
    assert "classList" not in APP.split("function wireCheck")[1].split("function wireCompound")[0], "Check never styles an entry"


# ---- keyboard and focus -----------------------------------------------------------------------------
def test_focus_ring_covers_every_focusable_kind_in_both_themes():
    ring = re.search(r"([^{}]*:focus-visible[^{}]*)\{([^}]*)\}", CSS)
    selectors = ring.group(1)
    for kind in ("button", "input", "a:", "select", "textarea"):
        assert kind in selectors, kind
    assert "outline: 3px" in ring.group(2) and "var(--focus)" in ring.group(2)


def test_a_button_that_turns_itself_off_keeps_focus():
    """Builder, send, check and next buttons use aria-disabled (still focusable); only the pre-boot busy state
    uses the disabled attribute, so pressing Send never throws focus to the top of the page."""
    assert "aria-disabled" in APP and "function guard(" in APP
    disabled_assignments = re.findall(r"\.disabled\s*=", APP)
    assert len(disabled_assignments) <= 3, disabled_assignments    # setBusy and the planet tabs only


def test_redraws_do_not_rebuild_a_focused_notebook_or_button_row():
    assert "function fillOnce(" in APP and "dataset.signature" in APP
    assert APP.count("fillOnce(") >= 9                              # three notebooks and six button holders
    assert "syncNotebookValues" in APP
    assert "list.textContent = \"\";\n    seenTokens().forEach" not in APP


def test_the_sentence_builder_has_keyboard_shortcuts_scoped_to_its_panel():
    for needle in ("data-builder", "Backspace", "Delete", "ArrowLeft", "ArrowRight", "Home", "End"):
        assert needle in APP, needle
    assert 'data-builder="pulse"' in HTML and 'data-builder="compound"' in HTML and 'data-builder="bridge"' in HTML
    assert re.search(r"INPUT\|TEXTAREA\|SELECT", APP), "shortcuts must pause while typing in a field"
    assert "e.ctrlKey" in APP and "e.metaKey" in APP, "browser shortcuts must pass through"
    assert "S adds a short tick" in HTML and "Backspace removes the last mark" in HTML     # listed in the ? help


def test_there_is_a_skip_link_and_a_main_landmark():
    assert 'class="skip-link" href="#planet-tabs"' in HTML
    assert '<main id="game">' in HTML and 'id="planet-tabs"' in HTML
    assert ".skip-link:focus" in CSS


# ---- screen readers ---------------------------------------------------------------------------------
class _Tree(HTMLParser):
    VOID = {"meta", "link", "br", "img", "input", "hr", "ins"}

    def __init__(self):
        super().__init__()
        self.stack, self.errors, self.tags = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}> after {self.stack[-3:]}")
            return
        self.stack.pop()


def _tree():
    parser = _Tree()
    parser.feed(HTML)
    return parser


def test_the_markup_is_balanced():
    parser = _tree()
    assert not parser.errors, parser.errors
    assert parser.stack == []


def test_every_labelled_group_has_a_role_and_ids_are_unique():
    parser = _tree()
    for tag, attrs in parser.tags:
        if tag == "div" and "aria-label" in attrs:
            assert attrs.get("role") in ("group", "img", "status"), attrs
    ids = [a["id"] for _t, a in parser.tags if "id" in a]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_live_regions_exist_for_every_thing_a_player_must_notice():
    for element in ("goal-line", "scene-status", "reaction", "check-result", "toast", "announce", "engine-status",
                    "door", "c-reaction", "b-reaction", "contact-line"):
        assert re.search(rf'id="{element}"[^>]*(aria-live|role="status")', HTML), element
    assert 'id="announce" class="sr-only"' in HTML and ".sr-only" in CSS
    assert "function noteScenes(" in APP and "announce(" in APP
    assert "function setText(" in APP, "live text is only reassigned when it changes"


def test_toggle_buttons_say_whether_their_panel_is_open():
    for button, panel in (("achievements-toggle-button", "achievements-panel"), ("crew-log-toggle-button", "crew-log-panel"),
                          ("info-page-toggle-button", "info-page-panel"), ("changelog-toggle-button", "changelog-panel"),
                          ("settings-toggle-button", "settings-panel")):
        assert re.search(rf'id="{button}"[^>]*aria-expanded="false"[^>]*aria-controls="{panel}"', HTML), button


def test_notebook_and_builder_controls_have_distinct_accessible_names():
    assert "Include group \" + (index + 1)" in APP and "Your guess for part \" + (index + 1)" in APP
    assert "Add thing \" + (index + 1)" in APP and "Add small sign \" + (index + 1)" in APP


def test_accessible_names_never_give_an_answer_away():
    """A part is called 'part 2', never by its internal letter; a small sign 'small sign 1', never p, n or q
    (the letters are the first letters of plural, negate and question); a number button never states its value."""
    for banned in ('"part " + code', '"small sign " + letter', "Add the number \" + value", "+ code +", "+ letter +"):
        assert banned not in APP.replace('"Add small sign " + (index + 1)', ""), banned
    assert "Add the number group \" + describeMarks(token)" in APP


# ---- reduced motion and effects ---------------------------------------------------------------------
def test_reduced_motion_and_effects_switches_exist_and_are_honoured_by_the_css():
    for element in ("reduced-motion-checkbox", "effects-checkbox", "high-contrast-checkbox", "text-size-increase-button",
                    "text-size-decrease-button", "text-size-reset-button", "display-reset-button"):
        assert f'id="{element}"' in HTML, element
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS
    assert "animation: none !important" in CSS and "transition: none !important" in CSS
    assert "box-shadow: none" in _rule('html[data-effects="off"] .lamp.lit')


def test_reduced_motion_follows_the_system_until_the_player_chooses():
    assert "prefers-reduced-motion: reduce" in SETTINGS
    assert 'motionChoice() === null ? systemPrefersReducedMotion()' in SETTINGS
    for key in ("lexis-text-scale", "lexis-reduced-motion", "lexis-effects", "lexis-high-contrast"):
        assert key in SETTINGS
    assert "pyodide" not in SETTINGS and "handle(" not in SETTINGS, "display settings stay out of the save"


def test_text_scale_is_applied_through_the_root_font_size():
    assert "font-size: calc(100% * var(--text-scale, 1))" in CSS
    assert "1rem/1.5" in CSS


# ---- What's New -------------------------------------------------------------------------------------
def test_changelog_is_well_formed_and_in_the_house_style():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert 2 <= len(entries) <= 10
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates, reverse=True)
    for entry in entries:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
        assert len(entry["entry"]) > 40
        assert "—" not in entry["entry"] and "!" not in entry["entry"]


def test_the_whats_new_panel_and_banner_are_wired_like_the_other_games():
    assert 'id="changelog-panel"' in HTML and 'id="changelog-toggle-button"' in HTML
    assert "window.CHANGELOG_JSON = text" in APP and 'fetch("changelog.json")' in APP
    banner = HTML.index('shared/whats-new-banner.js" data-game-id="lexis"')
    assert banner > HTML.index('<script src="app.js">'), "the banner polls for the global app.js sets"
    assert 'shared/last-played.js" data-game-id="lexis"' in HTML
    assert '{ toggle: "changelog-toggle-button", panel: "changelog-panel" }' in HTML     # Esc closes it


# ---- Desktop boot ------------------------------------------------------------------------------------
def test_every_id_app_js_uses_exists_in_the_desktop_page_too():
    ids = set(re.findall(r'\bid="([^"]+)"', PC_HTML))
    used = set(re.findall(r'\$\("([^"]+)"\)', APP))
    assert used <= ids, sorted(used - ids)


def test_the_desktop_page_has_its_own_files_and_tutorial_steps():
    assert 'href="pc.css"' in PC_HTML and 'src="pc.js"' in PC_HTML and 'data-layout="pc"' in PC_HTML
    assert "window.LEXIS_PC_TUTORIAL_STEPS = [" in PC_JS
    assert "window.lexisTutorialSteps" in HTML and "LEXIS_PC_TUTORIAL_STEPS" in HTML
    assert "lexisTutorialSteps(TUTORIAL_STEPS)" in APP
    assert 'shared/layout-pref.js" data-game-id="lexis" data-pc-page="pc.html"' in HTML
    steps = re.findall(r'selector:\s*"([^"]+)"', PC_JS)
    assert len(steps) >= 8


def test_the_desktop_layout_keeps_both_columns_and_scrolls_inside_panels_not_the_page():
    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)" in PC_CSS
    assert "overflow-y: auto" in PC_CSS
    assert 'html[data-theme="light"]' in PC_CSS, "the Desktop windows are checked in both themes"
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert [w[0] for w in config["windows"]] == ["crew-log-panel", "report-panel", "achievements-panel",
                                                 "changelog-panel", "settings-panel", "info-page-panel"]


def test_the_planet_columns_wrap_the_four_panels_of_every_planet():
    parser = _tree()
    columns = [a.get("class") for t, a in parser.tags if t == "div" and a.get("class") in ("planet-cols", "planet-col")]
    assert columns.count("planet-cols") == 3 and columns.count("planet-col") == 6
