"""AU-2: the only sound is the optional generated palette from shared/sfx.js, reached from the view code (app.js)
and never from the Python engine, never through an audio element or a context of our own, and with the game's
own hum switch present in both pages."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def test_the_view_only_calls_the_shared_synth_with_known_cues():
    cues = set(re.findall(r'NoyvjSfx\.play\((.*?)\);', APP))
    assert cues == {'"bell"', 'night && humPref() ? "hum_start" : "hum_stop"'}
    assert "AudioContext" not in APP and "new Audio" not in APP


def test_the_engine_modules_know_nothing_about_sound():
    for path in GAME_DIR.glob("*.py"):
        assert not re.search(r"sfx|AudioContext|NoyvjSfx", path.read_text(encoding="utf-8")), path.name


def test_both_pages_load_the_shared_file_once_and_carry_the_settings_slot_and_hum_switch():
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        assert html.count('src="../../shared/sfx.js"') == 1, name
        assert 'id="sfx-setting-slot"' in html and 'id="sfx-hum-checkbox"' in html, name
        assert "<audio" not in html


def test_the_sources_page_says_the_sound_is_generated_in_code():
    import json
    other = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))["other"]
    assert any(o["title"] == "Generated sound (Web Audio)" and o["by"] == "this project" for o in other)
