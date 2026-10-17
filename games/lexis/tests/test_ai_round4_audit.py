"""Round 4 ideas R4-PX-19 (evidence board), R4-LEMO-1 (transmission cards), R4-LEMO-4 (sign keyboard), R4-LEPC-1 (hover
lights signs) and R4-LEPC-2 (three docked panes). The engine action is tested for real; the page parts are checked as
source-level wiring (ids that exist, data written before it is read, events on the right target, CSS in the right media
block), because there is no browser in this suite."""

import json
import re
from pathlib import Path

import game
from .pagefiles import app_text

GAME_DIR = Path(__file__).resolve().parent.parent
INDEX = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = app_text()
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
IDS = set(re.findall(r'\sid="([^"]+)"', INDEX))


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def fresh(scenes=0):
    req(action="reset")
    view = req(action="open")
    for _ in range(scenes):
        view = req(action="next_scene")
    return view


# ---- R4-PX-19: the evidence board ----------------------------------------------------------------------
def test_the_board_pins_exactly_the_transmissions_received():
    assert fresh(0)["evidence"] == {"fragments": [], "pins": {}}
    view = fresh(3)
    assert view["evidence"]["fragments"] == [scene["marks"] for scene in view["scenes"]]
    assert len(view["evidence"]["fragments"]) == 3


def test_naming_a_fragment_is_kept_and_clearing_it_removes_the_name():
    fresh(2)
    view = req(action="name_pin", pin=1, text="  a   beacon  ")
    assert view["evidence"]["pins"] == {"1": "a beacon"}
    assert game.get_state()["evidence_pins"] == {"1": "a beacon"}
    view = req(action="name_pin", pin=1, text="")
    assert view["evidence"]["pins"] == {}
    assert "evidence_pins" not in game.get_state()


def test_a_name_for_a_transmission_not_yet_received_or_a_bad_request_changes_nothing():
    fresh(1)
    for bad in ({"pin": 1, "text": "x"}, {"pin": -1, "text": "x"}, {"pin": True, "text": "x"},
                {"pin": "0", "text": "x"}, {"pin": 0, "text": 7}):
        view = req(action="name_pin", **bad)
        assert view["evidence"]["pins"] == {}, bad


def test_a_name_is_cut_to_sixty_characters():
    fresh(1)
    view = req(action="name_pin", pin=0, text="z" * 200)
    assert view["evidence"]["pins"]["0"] == "z" * game.MAX_PIN_TEXT


def test_the_names_survive_a_save_and_load_and_loading_twice_changes_nothing():
    fresh(3)
    req(action="name_pin", pin=0, text="the beacon")
    req(action="name_pin", pin=2, text="a lamp keeper")
    saved = json.loads(json.dumps(game.get_state()))
    req(action="reset")
    assert game.get_state().get("evidence_pins") is None
    game.load_state(saved)
    once = dict(game.state.evidence_pins)
    game.load_state(saved)
    assert game.state.evidence_pins == once == {"0": "the beacon", "2": "a lamp keeper"}


def test_a_saved_name_never_replaces_one_written_since_and_a_garbage_save_is_ignored():
    fresh(2)
    req(action="name_pin", pin=0, text="newer")
    game.load_state({"evidence_pins": {"0": "older", "1": "kept", "9999": "no such fragment", "x": "bad key", "1x": 5}})
    assert game.state.evidence_pins == {"0": "newer", "1": "kept"}
    for junk in (None, [], "text", {"evidence_pins": [1, 2]}, {"evidence_pins": {"0": ["list"]}}):
        game.load_state(junk)
    assert game.state.evidence_pins == {"0": "newer", "1": "kept"}


def test_an_old_save_without_the_key_loads_and_the_board_stays_empty():
    fresh(0)
    game.load_state({"station": [0, "shut"], "tray": [], "stock": []})
    assert req(action="open")["evidence"]["pins"] == {}


def test_the_board_panel_and_its_button_exist_and_are_registered_for_the_desktop_page():
    assert {"evidence-toggle-button", "evidence-board-panel", "evidence-pins"} <= IDS
    assert ["evidence-board-panel", "evidence-toggle-button", "Evidence board"] in CONFIG["windows"]
    menu_ids = [i for group in CONFIG["toolbar"]["menu"] for i in group["ids"]]
    assert "evidence-toggle-button" in menu_ids
    assert 'send({ action: "name_pin"' in APP
    assert APP.count("function renderEvidenceBoard") == 1


# ---- R4-LEMO-1: transmission cards -----------------------------------------------------------------------
def test_the_card_viewer_is_a_hidden_dialog_opened_by_a_hidden_toggle_and_all_its_ids_exist():
    viewer = re.search(r'<section id="scene-card-viewer"[^>]*>', INDEX).group(0)
    assert 'role="dialog"' in viewer and re.search(r"\shidden(\s|>)", viewer)
    assert re.search(r'<button id="scene-card-toggle-button"[^>]*\shidden', INDEX)
    for ident in ("scene-card", "scene-card-count", "scene-card-close", "scene-card-prev", "scene-card-next"):
        assert ident in IDS
        assert '"%s"' % ident in APP
    assert "scene-card-container" not in APP + INDEX + CSS      # the old stacked-cards container is gone


def test_the_card_viewer_swipes_up_for_next_and_down_for_previous_and_only_when_wired():
    assert "wireSceneCards();" in APP
    assert "dy < -50) stepSceneCard(1)" in APP and "dy > 50) stepSceneCard(-1)" in APP
    assert 'send({ action: "next_scene" })' in APP
    assert 'e.key === "Escape"' in APP


def test_the_cards_and_the_sign_keyboard_are_phone_only():
    assert re.search(r"#scene-card-toggle-button, \.scene-card-viewer, \.sign-keyboard \{ display: none; \}", CSS)
    phone = CSS[CSS.index("Phone-only extras"):]
    block = phone[:phone.index("/* Landscape on narrow screens")]
    assert "@media (max-width: 600px)" in block and "orientation" not in block
    assert ".scene-card-viewer:not([hidden])" in block and ".sign-keyboard:not([hidden])" in block


# ---- R4-LEMO-4: the sign keyboard -------------------------------------------------------------------------
def test_the_sign_keyboard_is_built_on_every_planet_before_the_early_returns_in_render():
    render = APP[APP.index("  function render() {"):]
    render = render[:render.index("saveResumeFrame();")]
    assert render.index("renderSignKeyboard();") < render.index('if (A.currentPlanet === "bridge")')


def test_sign_keyboard_buttons_are_named_by_ordinals_never_by_internal_letters():
    body = APP[APP.index("function signKeyboardButton"):APP.index("function renderSignKeyboard")]
    names = re.findall(r'setAttribute\("aria-label", ([^;]+)\);', body)
    assert len(names) == 3
    assert not any('"Add sign' in n or "+ item" in n.replace("ordinalIn(", "").replace(", item)", "") for n in names), names


def test_the_sign_keyboard_has_a_setting_that_is_read_applied_and_reset():
    assert "sign-keyboard-checkbox" in IDS
    assert 'KEYBOARD_KEY = "lexis-sign-keyboard"' in SETTINGS
    assert SETTINGS.count("applyKeyboard(") >= 4                 # defined, applied on load, on change, on reset
    assert "remove(KEYBOARD_KEY)" in SETTINGS
    assert 'html[data-sign-keyboard="off"] .sign-keyboard' in CSS
    save_fields = json.dumps(game.get_state())
    assert "sign" not in save_fields                            # per-device setting: never in the save


# ---- R4-LEPC-1: hover lights every copy of a sign ---------------------------------------------------------
def test_every_drawn_sign_carries_data_sign_for_pc_js_to_read():
    for drawer in ("function tokenNode", "function glyphNode", "function markerNode", "function partSvg"):
        body = APP[APP.index(drawer):]
        assert "dataset.sign =" in body[:body.index("\n  }\n")], drawer
    assert 'closest("[data-sign]")' in PC_JS and ".sign-match" in PC_CSS


def test_the_hover_code_uses_document_level_listeners_only():
    block = PC_JS[PC_JS.index("R4-LEPC-1"):PC_JS.index("Double-click a scene")]
    assert 'document.addEventListener("mouseover"' in block and 'document.addEventListener("mouseout"' in block
    assert "getElementById" not in block and "document.body" not in block


# ---- R4-LEPC-2: three docked panes -----------------------------------------------------------------------
def test_the_dividers_are_added_on_window_load_because_the_shell_builds_the_stage_later():
    block = PC_JS[PC_JS.index("R4-LEPC-2"):]
    assert block.index('window.addEventListener("load"') < block.index('getElementById("pc-stage")')
    assert 'role", "separator"' in block and "ArrowLeft" in block and "pointerdown" in block


def test_the_pane_layout_is_wide_screens_only_and_dividers_are_hidden_below():
    wide = PC_CSS[PC_CSS.index("R4-LEPC-2"):]
    assert "@media (min-width: 1200px)" in wide
    assert "display: contents" in wide and "--lexis-pane-a" in wide
    assert 'matchMedia("(min-width: 1200px)")' in PC_JS and "function teardown" in PC_JS     # no divider in the markup when narrow
    assert "--lexis-pane-a" in PC_JS and "--lexis-pane-c" in PC_JS
