"""Round 4 (phone and Desktop view ideas) added JavaScript only, so these tests guard the wiring that earlier local-AI
batches got wrong: requests the engine does not know, ids that do not exist, hooks that look things up before the page
has built them, and a day that does not come back whole after a reload."""

import json
import re
from pathlib import Path

import pytest

import game

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def test_every_request_the_view_sends_is_an_action_the_engine_knows():
    source = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    handler = source.split("def handle")[1].split("def get_state")[0]
    known = set(re.findall(r'"([a-z_]+)"', handler))
    market = (GAME_DIR / "market.js").read_text(encoding="utf-8")
    sent = set(re.findall(r'action: "([a-z_]+)"', APP + market))
    assert sent, "expected requests in app.js"
    assert sent <= known, f"sent but not handled: {sorted(sent - known)}"


def test_the_ids_the_new_phone_features_use_exist_in_the_page():
    for ident in ("mobile-dock", "mirror-checkbox", "haptics-checkbox", "message", "selection-info"):
        assert f'id="{ident}"' in HTML, ident
    assert "mobile-dock" in APP and "haptics-checkbox" in SETTINGS and "mirror-checkbox" in SETTINGS


def test_the_dock_and_the_peek_panel_are_hidden_until_a_phone_asks_for_them():
    assert re.search(r"^\.mobile-dock \{ display: none; \}", STYLE, re.M)
    assert re.search(r"^\.peek-panel \{ display: none; \}", STYLE, re.M)
    assert re.search(r"^\.patience-dots \{ display: none; \}", STYLE, re.M)
    # the dock only shows while a day is open
    assert '#game[data-phase="open"] .mobile-dock' in STYLE


def test_haptics_follow_the_reduced_motion_setting_and_have_an_off_switch():
    assert 'getAttribute("data-reduced-motion") === "true"' in APP
    assert "hasAttribute(\"data-reduced-motion\")" not in APP
    assert "Math.random" not in APP
    assert "HAPTICS_KEY" in SETTINGS and "pocket-bazaar-haptics" in APP


def test_desktop_hooks_use_things_the_page_really_has():
    # the first local-AI pass read data-good / data-patience attributes and a hotkeys map that nothing ever set
    for dead in ("data-good", "data-patience", "NOYVJ_PC_HOTKEYS"):
        assert dead not in PC_JS, dead
    assert "pocketBazaarApi" in APP and "pocketBazaarApi" in PC_JS
    assert "pocketBazaarAfterRender" in APP and "pbPcAfterRender" in PC_JS


def test_the_shift_d_hint_is_on_the_desktop_hint_bar():
    assert ["Shift+D", "Hand over chosen goods"] in PC_CONFIG["hints"]


def test_rebound_keys_never_replace_the_number_keys():
    # an unset crate key used to read as "1", so 2 to 5 stopped opening crates
    assert 'getCustom("crates", "")' in APP
    assert '/^[1-9]$/.test(key)' in APP


def test_a_day_comes_back_whole_after_a_save_and_load():
    """R4-PBMO-6: the engine keeps the whole open day in the save, so a short break never loses a merge."""
    call(action="start_day")
    for family in [c["family"] for c in call(action="open")["crates"]][:2]:
        call(action="crate", family=family)
    call(action="crate", family=call(action="open")["crates"][0]["family"])
    before = call(action="open")
    saved = json.loads(json.dumps(game.get_state()))
    game.stall.__init__()
    game.load_state(saved)
    after = call(action="open")
    assert after["phase"] == "open"
    assert after["board"] == before["board"]
    assert [(c["name"], c["patience"], c["items"]) for c in after["customers"]] == [(c["name"], c["patience"], c["items"]) for c in before["customers"]]
    assert after["day"] == before["day"]
