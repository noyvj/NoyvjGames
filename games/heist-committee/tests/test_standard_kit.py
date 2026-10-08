import json
import re
from pathlib import Path

import info

GAME = Path(__file__).resolve().parent.parent
HTML = (GAME / "index.html").read_text(encoding="utf-8")
APP = (GAME / "app.js").read_text(encoding="utf-8")


def test_changelog_is_valid_and_newest_first_readable():
    data = json.loads((GAME / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert entries and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and e["entry"].strip() for e in entries)


def test_the_shared_includes_a_finished_game_carries_are_all_there():
    for name in ("copy-result.js", "achievement-share.js", "mobile-dock.js", "mobile-hud.js", "save-widget.js", "opening-screen.js",
                 "story-toggle.js", "last-played.js", "whats-new-banner.js", "keyboard-shortcuts.js", "confirm-dialog.js",
                 "tutorial.js", "hub-auth.js", "info-page.css", "theme-light-games.css"):
        assert name in HTML, name
    assert HTML.index("save-widget.js") < HTML.index("opening-screen.js") < HTML.index('src="app.js"')
    assert HTML.index('src="app.js"') < HTML.index("last-played.js")


def test_keyboard_shortcut_panels_point_at_real_buttons_and_panels():
    block = HTML[HTML.index("KeyboardShortcuts.init"):]
    ids = set(re.findall(r'(?<![\w-])id="([^"]+)"', HTML))
    for toggle, panel in re.findall(r'toggle: "([\w-]+)", panel: "([\w-]+)"', block):
        assert toggle in ids and panel in ids


def test_tutorial_steps_only_point_at_ids_that_exist():
    ids = set(re.findall(r'(?<![\w-])id="([^"]+)"', HTML))
    steps = APP[APP.index("TUTORIAL_STEPS = ["):APP.index("HC.afterBoot")]
    for selector in re.findall(r'selector: "#([\w-]+)"', steps):
        assert selector in ids
    assert steps.count("title:") >= 8


def test_every_toolbar_button_is_a_toggle_for_a_real_panel():
    ids = set(re.findall(r'(?<![\w-])id="([^"]+)"', HTML))
    for button, panel in re.findall(r'<button id="([\w-]+)" type="button" aria-expanded="false" aria-controls="([\w-]+)"', HTML):
        assert panel in ids, button


def test_the_info_panel_is_fiction_only_and_explains_the_rules(g):
    reply = g(action="info")
    assert "no real-world" in reply["info"]["framing"]
    headings = [s["heading"] for s in reply["info"]["sections"]]
    assert len(headings) >= 5 and len(set(headings)) == len(headings)
    assert reply["view"]["phase"] == "board"


def test_info_text_matches_the_actual_rules(C):
    text = " ".join(s["body"] for s in info.SECTIONS)
    assert str(__import__("engine").CHAIN_CAP) not in text or "six" in text
    assert "Standby" in text and "Solid" in text


def test_the_game_never_talks_to_the_backend_itself():
    assert "noyvjgames.fastapicloud" not in APP
    for name in ("plan.js", "play.js"):
        assert "fetch(" not in (GAME / name).read_text(encoding="utf-8")


def test_no_audio_anywhere():
    for path in GAME.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert "new Audio" not in text and "AudioContext" not in text and "<audio" not in text
    assert "<audio" not in HTML
