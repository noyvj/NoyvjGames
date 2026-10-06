import json

import game
from achievements import ACHIEVEMENTS
from pulse import say_door, say_lamps


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def setup_function():
    call(action="reset")


def earned():
    return {a["id"] for a in call(action="open")["achievements"] if a["earned"]}


def test_manifest_matches_the_engine():
    manifest = json.load(open(game.__file__.replace("game.py", "achievements.json")))["achievements"]
    assert [m["id"] for m in manifest] == [a[0] for a in ACHIEVEMENTS]
    assert all(m["label"] and m["description"] for m in manifest)


def test_nothing_is_earned_at_the_start():
    assert earned() == set()
    assert game.get_state()["achievements_earned"] == []


def test_planet_one_achievements():
    call(action="speak", marks="1000" + "1010" + "1111")                # not understood
    assert "learning_from_static" in earned() and "first_signal" not in earned()
    call(action="speak", marks=say_lamps(7))
    assert {"first_signal", "lamp_keeper"} <= earned()
    call(action="speak", marks=say_lamps(0))
    assert "lamp_keeper" in earned()                                    # stays earned after the lamps go out
    call(action="write", form="1000", gloss="lamp")
    assert "first_words" in earned()


def test_sharp_ear_needs_three_entries_all_right():
    for f, g in (("1000", "lamp"), ("1001", "door"), ("1010", "open")):
        call(action="write", form=f, gloss=g)
    call(action="confirm", forms=["1000", "1001"])
    assert "sharp_ear" not in earned()
    call(action="confirm", forms=["1000", "1001", "1010"])
    assert "sharp_ear" in earned()


def test_planet_two_achievements_and_the_save_projection():
    call(action="speak", marks=say_door("open"))
    call(action="speak", marks=say_lamps(5))
    assert "first_contact" in earned()
    for _ in range(4):
        call(action="next_scene", planet="compound")
    for _ in range(6):
        call(action="next_scene")
    for code, meaning in (("k", "water"), ("m", "grain"), ("t", "fire"), ("o", "small"), ("u", "big")):
        call(action="write", planet="compound", form=code, gloss=meaning)
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")
    got = earned()
    assert {"unseen_sign", "second_contact", "full_glossary", "patient_listener"} <= got
    assert set(game.get_state()["achievements_earned"]) == got
    saved = json.loads(json.dumps(game.get_state()))
    call(action="reset")
    game.load_state(saved)
    assert earned() >= {"first_contact", "second_contact"}


def test_every_achievement_is_reachable():
    # Easy to 100%: the whole set is earned by a straightforward playthrough.
    call(action="speak", marks="1000" + "1010" + "1111")
    call(action="speak", marks=say_lamps(7))
    call(action="speak", marks=say_door("open"))
    call(action="speak", marks=say_lamps(5))
    for _ in range(6):
        call(action="next_scene")
    for _ in range(4):
        call(action="next_scene", planet="compound")
    for code, meaning in (("k", "water"), ("m", "grain"), ("t", "fire"), ("o", "small"), ("u", "big")):
        call(action="write", planet="compound", form=code, gloss=meaning)
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")
    for f, g in (("1000", "lamp"), ("1001", "door"), ("1010", "open")):
        call(action="write", form=f, gloss=g)
    call(action="confirm", forms=["1000", "1001", "1010"])
    assert earned() == {a[0] for a in ACHIEVEMENTS} - {"third_contact", "markers_known"}
    # planet 3 (unlocked by contact with planet 2): learn the three small signs, then meet the crew's request
    for _ in range(5):
        call(action="next_scene", planet="bridge")
    for letter, role in (("p", "plural"), ("n", "negate"), ("q", "ask")):
        call(action="write", planet="bridge", form=letter, gloss=role)
    call(action="speak", planet="bridge", message="tu p 0101")
    call(action="speak", planet="bridge", message="tu q")
    assert earned() == {a[0] for a in ACHIEVEMENTS}
    assert len(ACHIEVEMENTS) == 12


def test_planet_three_achievements_and_the_save_projection():
    call(action="speak", marks=say_door("open"))
    call(action="speak", marks=say_lamps(5))
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")
    assert not {"third_contact", "markers_known"} & earned()
    for letter, gloss in (("p", "plural"), ("n", "negate"), ("q", "more")):
        call(action="write", planet="bridge", form=letter, gloss=gloss)
    assert "markers_known" not in earned()                          # one is wrong: not earned
    call(action="write", planet="bridge", form="q", gloss="ask")
    assert "markers_known" in earned()
    call(action="speak", planet="bridge", message="tu q")
    assert "third_contact" not in earned()
    call(action="speak", planet="bridge", message="tu p 0101")
    got = earned()
    assert {"third_contact", "markers_known"} <= got and set(game.get_state()["achievements_earned"]) == got
    saved = json.loads(json.dumps(game.get_state()))
    call(action="reset")
    game.load_state(saved)
    assert {"third_contact", "markers_known"} <= earned()
