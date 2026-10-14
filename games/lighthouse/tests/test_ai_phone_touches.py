"""The phone touches (Round 4 mobile ideas R4-LHMO-*): source-level wiring checks. Each phone extra is optional (off until
Settings > On a phone switches it on), phone width only, never in the Desktop layout, and sends only engine actions the
engine accepts. There is no browser here, so these tests check the contract between index.html, app.js, the mobile-*.js
files and style.css, plus the engine actions the extras send."""

import json
import re
from pathlib import Path

import game

GAME_DIR = Path(__file__).resolve().parent.parent
INDEX = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
PREFS = (GAME_DIR / "mobile-prefs.js").read_text(encoding="utf-8")
IDS = set(re.findall(r'\sid="([^"]+)"', INDEX))
MINE = ["mobile-prefs.js", "mobile-lamp.js", "mobile-crank.js", "mobile-letters.js", "swipe-letters.js", "mobile-lamp-rail.js"]


def src(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def ids_used(js):
    return set(re.findall(r'getElementById\("([^"]+)"\)', js))


def night():
    req(action="new_game", seed=4)
    req(action="start_night")
    return req(action="open")


# ---- shared plumbing -----------------------------------------------------------------------------------------
def test_every_mobile_script_is_loaded_once_after_app_js_in_both_pages():
    pc = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    for page in (INDEX, pc):
        scripts = re.findall(r'<script src="([^"]+)"', page)
        for name in MINE:
            assert scripts.count(name) == 1, name
            assert scripts.index(name) > scripts.index("app.js")
            assert (GAME_DIR / name).exists(), name
        assert scripts.index("mobile-prefs.js") < min(scripts.index(n) for n in MINE[1:])
    # files that nothing loads were removed, not left behind
    assert not (GAME_DIR / "battery-saver.js").exists() and not (GAME_DIR / "mobile-hud-glow.js").exists()


def test_app_js_tells_the_phone_scripts_about_every_view_on_document():
    assert 'document.dispatchEvent(new CustomEvent("lighthouse-view"' in APP
    assert "window.lighthouseApi = {" in APP
    for name in ("mobile-lamp.js", "mobile-crank.js", "mobile-lamp-rail.js"):
        js = src(name)
        assert 'document.addEventListener("lighthouse-view"' in js, name
        assert 'window.addEventListener("lighthouse-view"' not in js
    # every custom event the phone files listen for is dispatched on document by someone
    listened = set()
    for name in MINE[1:]:
        listened |= set(re.findall(r'document\.addEventListener\("(lighthouse-[a-z-]+)"', src(name)))
    assert listened == {"lighthouse-view", "lighthouse-phone-pref"}
    assert 'new CustomEvent("lighthouse-phone-pref"' in PREFS


def test_every_phone_preference_has_a_control_a_default_and_a_reset():
    controls = re.findall(r'control: "([^"]+)"', PREFS)
    assert len(controls) == 5
    for control in controls:
        assert control in IDS, control
    assert "display-reset-button" in PREFS and "display-reset-button" in IDS
    assert "lsRemove(DEFS[name].key)" in PREFS
    # per-device only: stored in localStorage under lighthouse-* keys, never in the save
    assert all(k.startswith("lighthouse-") for k in re.findall(r'key: "([^"]+)"', PREFS))
    assert "lighthouse-phone" not in json.dumps(req(action="open")).lower()
    assert "lighthouse-phone" not in json.dumps(game.get_state()).lower()


def test_the_phone_extras_never_reach_the_desktop_layout():
    assert ".phone-settings { display: none; }" in CSS
    assert 'html:not([data-layout="pc"]) .phone-settings' in CSS
    for rule in re.findall(r'(html\[data-(?:phone|battery)[^{]+)\{', CSS):
        assert 'data-layout="pc"' in rule, rule


# ---- R4-LHMO-1: the lamp slider ------------------------------------------------------------------------------
def test_lhmo1_slider_ids_exist_and_the_option_to_show_it_is_in_settings():
    for i in ids_used(src("mobile-lamp.js")):
        assert i in IDS, i
    assert 'id="phone-lamp-select"' in INDEX and 'value="slider"' in INDEX
    assert 'type="range" min="0" max="3" step="1"' in INDEX
    assert INDEX.count('class="lamp-notches"') == 1
    for word in ("Dim", "Standard", "Bright", "Storm"):
        assert "<li>%s</li>" % word in INDEX


def test_lhmo1_slider_is_hidden_until_chosen_and_only_on_a_phone():
    assert ".lamp-slider-wrap { display: none; }" in CSS
    assert 'html[data-phone-lamp="slider"]:not([data-layout="pc"]) .lamp-slider-wrap' in CSS
    assert ".lamp-slider-wrap[hidden] { display: none !important; }" in CSS
    assert 'class="lamp-slider-wrap" role="group" aria-label="Lamp level" hidden' in INDEX


def test_lhmo1_slider_levels_are_the_engines_own_level_ids():
    js = src("mobile-lamp.js")
    ids = re.search(r'var IDS = \[([^\]]+)\]', js).group(1)
    assert re.findall(r'"(\w+)"', ids) == ["dim", "standard", "bright", "storm"]
    view = night()
    assert [o["id"] for o in view["level_options"]] == ["dim", "standard", "bright", "storm"]
    for level in ("storm", "dim", "bright", "standard"):
        again = req(action="level", level=level)
        assert again["beam"]["level"] == level
    assert 'send({ action: "level", level: IDS[i] })' in js


# ---- R4-LHMO-2: the wind crank ---------------------------------------------------------------------------------
def test_lhmo2_crank_ids_exist_and_a_plain_button_does_the_same_without_drawing():
    js = src("mobile-crank.js")
    for i in ids_used(js):
        assert i in IDS, i
    assert 'id="phone-crank-checkbox"' in INDEX
    assert re.search(r'<button id="crank-button" type="button"[^>]*>Wind it</button>', INDEX)
    assert 'button.addEventListener("click"' in js and "wind()" in js
    # the handle turns by the change since the last pointer event (the old maths double counted the start angle)
    assert "lastPointerAngle" in js and "startAngle" not in js


def test_lhmo2_crank_sends_only_actions_the_engine_accepts():
    js = src("mobile-crank.js")
    assert re.findall(r"send\((\{[^}]*\})\)", js) == ['{ action: "wind" }']
    night()
    game.keep.clock_left = 3.0
    wound = req(action="wind")
    assert "error" not in wound and wound["clockwork"]["left"] > 3.0
    again = req(action="wind")   # already wound: the engine says so and changes nothing
    assert again["clockwork"]["left"] == wound["clockwork"]["left"]


def test_lhmo2_crank_is_hidden_until_chosen_and_reduced_motion_players_keep_it():
    assert ".crank-wrap { display: none; }" in CSS
    assert 'html[data-phone-crank="on"]:not([data-layout="pc"]) .crank-wrap' in CSS
    assert 'data-reduced-motion="true"] .crank-wrap' not in CSS
    assert "data-reduced-motion" not in src("mobile-crank.js").split("function reduced")[0]


# ---- R4-LHMO-4: paper cards ------------------------------------------------------------------------------------
def test_lhmo4_cards_wiring():
    js = src("mobile-letters.js")
    for i in ids_used(js):
        assert i in IDS, i
    assert 'id="phone-cards-checkbox"' in INDEX and 'id="letters-filed-toggle"' in INDEX
    # the card is found by an attribute app.js really sets on every letter
    assert "li.dataset.letterId = l.id" in APP and "dataset.letterId" in js
    # nothing is ever removed from the DOM or lost: filing only sets an attribute
    assert ".remove()" not in js and "removeChild" not in js
    assert "MutationObserver(enhance).observe(list, { childList: true })" in js


def test_lhmo4_every_letter_the_engine_offers_has_an_id_and_nothing_filed_is_saved():
    req(action="new_game", seed=9)
    view = req(action="open")
    assert "inbox" in view["story"]
    for letter in view["story"]["inbox"]:
        assert letter["id"] and "read" in letter
    assert "filed" not in json.dumps(game.get_state()).lower()


def test_lhmo4_cards_only_exist_when_chosen_at_phone_width():
    assert ".letters-filed-toggle, .card-actions { display: none; }" in CSS
    for rule in re.findall(r'(html\[data-phone-cards="on"\][^{]*)\{', CSS):
        assert 'data-layout="pc"' in rule, rule
    assert "paper-flip" in CSS and ':not([data-reduced-motion="true"]):not([data-effects="off"])' in CSS


# ---- R4-LHMO-6: the letters drawer -------------------------------------------------------------------------------
def test_lhmo6_drawer_wiring():
    js = src("swipe-letters.js")
    for i in ids_used(js):
        assert i in IDS, i
    assert 'id="phone-edge-checkbox"' in INDEX and 'id="letters-close-button"' in INDEX
    # it opens the panel the same way the toolbar button does, instead of setting an attribute that nothing reads
    assert "toggle.click()" in js and "data-open" not in js and "#letters-panel[data-open" not in CSS
    assert "[role='dialog']:not([hidden])" in js
    assert "composedPath" in js and "Escape" in js


def test_lhmo6_the_drawer_css_applies_to_the_open_panel_only():
    assert 'html[data-phone-edge="on"]:not([data-layout="pc"]) #letters-panel:not([hidden])' in CSS
    assert ".edge-strip[hidden] { display: none !important; }" in CSS
    # the letters panel is not turned into an off-screen sheet when it is merely present
    assert not re.search(r"#letters-panel\s*\{[^}]*translateX\(-100%\)", CSS)


# ---- R4-LHMO-8: battery saver ----------------------------------------------------------------------------------
def test_lhmo8_battery_saver_is_a_setting_and_only_the_beam_keeps_moving():
    assert 'id="battery-saver-checkbox"' in INDEX
    assert 'attr: "data-battery-saver"' in PREFS and 'key: "lighthouse-battery-saver"' in PREFS
    text = " ".join(re.findall(r'html\[data-battery-saver="on"\][^{]*\{[^}]*\}', CSS))
    assert "animation: none !important; transition: none !important;" in text
    assert "#beam.sweeping { animation: sweep 7s ease-in-out infinite !important; }" in text
    assert 'id="beam"' in INDEX and 'beam.classList.toggle("sweeping"' in APP


# ---- R4-LHMO-9: the lamp rail ----------------------------------------------------------------------------------
def test_lhmo9_rail_buttons_carry_the_engines_level_ids_and_are_labelled():
    for i in ids_used(src("mobile-lamp-rail.js")):
        assert i in IDS, i
    rail = re.search(r'<div id="lamp-rail".*?</div>', INDEX, flags=re.S).group(0)
    levels = re.findall(r'data-level="(\w+)"[^>]*>(\w+)</button>', rail)
    assert [lv for lv, _ in levels] == ["dim", "standard", "bright", "storm"]
    assert [t.lower() for _, t in levels] == [lv for lv, _ in levels]
    assert 'value="rail"' in INDEX and "setLampLevel" not in src("mobile-lamp-rail.js")
    assert [o["id"] for o in night()["level_options"]] == [lv for lv, _ in levels]


def test_lhmo9_rail_and_slider_are_one_setting_so_they_never_stack():
    assert 'attr: "data-phone-lamp"' in PREFS and 'values: ["off", "slider", "rail"]' in PREFS
    assert 'html[data-phone-lamp="rail"]:not([data-layout="pc"]) .lamp-rail' in CSS
    assert 'html[data-phone-lamp="slider"]:not([data-layout="pc"]) .lamp-slider-wrap' in CSS


# ---- R4-LHMO-10: the oil and repair chips ------------------------------------------------------------------------
def test_lhmo10_chips_exist_and_app_js_fills_them():
    for i in ("hud-oil-chip", "hud-repair-chip", "hud-repair", "hud-repair-state"):
        assert i in IDS, i
        assert '$("%s")' % i in APP, i
    assert 'data-stat="oil"' in INDEX and 'data-stat="repair"' in INDEX
    assert '{ selector: "#hud-repair", label: "Repair" }' in APP


def test_lhmo10_low_glow_is_calm_and_respects_motion_and_effects():
    assert '.chip[data-stat][data-state="low"] { border: 2px solid' in CSS
    anim = re.search(r':not\(\[data-reduced-motion="true"\]\):not\(\[data-effects="off"\]\)[^{]*chip\[data-stat\]\[data-state="low"\] \{ animation: chip-glow ([\d.]+)s', CSS)
    assert anim and float(anim.group(1)) >= 3
    assert ".chip-repair { display: none; }" in CSS


def test_lhmo10_the_view_carries_the_numbers_the_chips_show():
    view = night()
    assert view["structure"] and all(0 <= p["value"] <= 100 for p in view["structure"])
    assert view["oil"] > 0 and view["oil_cap"] > 0
    game.keep.structure["lantern"] = 10
    assert min(p["value"] for p in req(action="open")["structure"]) == 10


# ---- found live in the browser pass (Playwright, 360x740) -----------------------------------------------------
def test_the_click_that_ends_the_opening_swipe_does_not_close_the_drawer_again():
    js = src("swipe-letters.js")
    assert "openedAt = Date.now()" in js and "Date.now() - openedAt < 600" in js


def test_an_unread_card_is_painted_open_again_after_the_engine_redraws_the_list():
    js = src("mobile-letters.js")
    assert 'querySelectorAll("li.paper-card"), paint' in js
    assert "opened[card.dataset.letterId] = true" in js


def test_floating_phone_extras_start_to_the_right_of_the_story_and_theme_pills():
    assert "left: 3.6rem; right: 0.4rem; bottom: calc(var(--dock-h, 0px) + 3.8rem)" in CSS
    assert "position: fixed; left: 3.6rem; bottom: calc(var(--dock-h, 0px) + 3.8rem)" in CSS
