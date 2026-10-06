"""Milestone 7: the story spine, the contact report and the info page."""

import json
import re

import game
import info
import story
from bridge import MARKERS
from compound import COMPONENTS
from pulse import say_door, say_lamps


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def setup_function():
    call(action="reset")


def contact_one():
    call(action="speak", marks=say_door("open"))
    call(action="speak", marks=say_lamps(5))


def contact_two():
    contact_one()
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")


def contact_three():
    contact_two()
    call(action="speak", planet="bridge", message="tu p 0101")
    return call(action="speak", planet="bridge", message="tu q")


def beat_ids(view):
    return [b["id"] for b in view["story"]["beats"]]


# --- the story spine ---------------------------------------------------------------------------
def test_the_brief_is_always_there_and_no_beat_before_contact():
    view = call(action="open")
    assert view["story"]["brief"]["lines"] and view["story"]["beats"] == []
    speakers = {line["speaker"] for line in view["story"]["brief"]["lines"]}
    assert any("Captain" in s for s in speakers) and any("Engineer" in s for s in speakers)


def test_beats_unlock_exactly_with_contact_newest_first():
    assert beat_ids(call(action="open")) == []
    contact_one()
    assert beat_ids(call(action="open")) == ["planet1"]
    contact_two()
    assert beat_ids(call(action="open")) == ["planet2", "planet1"]
    contact_three()
    assert beat_ids(call(action="open")) == ["closing", "planet3", "planet2", "planet1"]


def test_every_view_carries_the_story_and_reset_clears_it():
    contact_two()
    for planet in ("pulse", "compound"):
        assert beat_ids(call(action="open", planet=planet)) == ["planet2", "planet1"]
    call(action="reset")
    assert beat_ids(call(action="open")) == []


def test_story_is_derived_and_never_saved():
    contact_two()
    saved = game.get_state()
    assert "story" not in json.dumps(saved) and not any("beat" in key for key in saved)
    call(action="reset")
    game.load_state(json.loads(json.dumps(saved)))
    assert beat_ids(call(action="open")) == ["planet2", "planet1"]


def test_story_is_deterministic():
    contact_three()
    assert call(action="open")["story"] == call(action="open")["story"]
    assert story.view({"pulse": True}) == story.view({"pulse": True})


def test_house_style_no_em_dashes_exclamations_or_en_dashes():
    for text in story.all_text() + [info.FRAMING] + [f["fact"] + f["tie_in"] for f in info.FACTS]:
        assert "—" not in text and "–" not in text and "!" not in text and " - " not in text, text


# The true glosses of every sign. The story may use ordinary words, but never these as translations, and
# never anything that says what a sign does (the plural, the ask and the negate roles).
FORBIDDEN = (r"water", r"grain", r"fire", r"small", r"big", r"plural\w*", r"negat\w*", r"ask\w*", r"lamps?", r"doors?",
             r"open\w*", r"shut", r"none", r"many", r"counts?", r"counted", r"binary", r"question\w*", r"how much")


def test_the_forbidden_list_covers_every_true_gloss():
    from pulse import PULSE
    glosses = {m for m, _slot in COMPONENTS.values()} | set(MARKERS.values()) | {w.meaning for w in PULSE.words}
    glosses.discard("end of message")
    for gloss in glosses:
        assert any(re.fullmatch(pattern, gloss) for pattern in FORBIDDEN), gloss


def test_no_beat_leaks_an_answer():
    pattern = re.compile(r"\b(" + "|".join(FORBIDDEN) + r")\b", re.IGNORECASE)
    for text in story.all_text():
        assert not pattern.search(text), (pattern.search(text).group(0), text)
    # and nothing spells a sign out: no token of marks, no glyph-looking letter pair in quotes
    for text in story.all_text():
        assert not re.search(r"\b[01]{4}\b", text)


# --- the contact report ------------------------------------------------------------------------
def test_no_report_before_contact_with_planet_three():
    assert call(action="open")["report"] is None
    contact_two()
    assert call(action="open", planet="compound")["report"] is None


def test_the_report_states_the_truth_after_the_fact():
    contact_one()
    for form, gloss in (("1000", "lamp"), ("1001", "wrong")):
        call(action="write", form=form, gloss=gloss)
    for letter, gloss in (("k", "water"), ("m", "grain"), ("o", "tiny")):
        call(action="write", planet="compound", form=letter, gloss=gloss)
    call(action="next_scene")
    call(action="next_scene", planet="compound")
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")
    for letter, gloss in (("p", "plural"), ("n", "negate"), ("q", "ask")):
        call(action="write", planet="bridge", form=letter, gloss=gloss)
    call(action="speak", planet="bridge", message="tu p 0101")
    view = call(action="speak", planet="bridge", message="tu q")
    report = view["report"]
    pulse, compound, bridge = report["planets"]
    assert (pulse["written"], pulse["right"]) == (2, 1)
    assert (compound["written"], compound["right"]) == (3, 2)
    assert (bridge["written"], bridge["right"]) == (3, 3)
    assert pulse["transmissions"] == 1 and pulse["transmissions_total"] == 6
    assert compound["transmissions"] == 1 and bridge["transmissions"] == 0
    assert pulse["sent"] == 2 and compound["sent"] == 2 and bridge["sent"] == 2
    assert report["totals"] == {"transmissions": 2, "sent": 6, "written": 8, "right": 6}
    text = " ".join(line for p in report["planets"] for line in p["learned"])
    for gloss in ("water", "grain", "fire", "small", "big", "plural", "negate", "ask", "lamp", "door", "open", "shut"):
        assert gloss in text, gloss
    assert {a["label"] for a in report["achievements"]} >= {"First Contact", "Second Contact", "Third Contact"}
    assert report["achievements_total"] == 12
    assert call(action="open")["report"] == report                 # viewable again at any time


# --- the info page -----------------------------------------------------------------------------
def test_facts_have_a_named_source_and_a_date_read():
    assert 4 <= len(info.FACTS) <= 6
    for fact in info.FACTS:
        source = fact["source"]
        assert source["title"] and source["publisher"] and source["url"].startswith("https://")
        assert len(fact["fact"]) < 600 and fact["tie_in"]
    assert info.DATE_READ == "2026-10-07"
    shown = info.view({"pulse": True, "compound": True, "bridge": True})["facts"]
    assert all(not f["locked"] and f["source"]["date_read"] == "2026-10-07" for f in shown)


def test_facts_about_a_planet_unlock_with_its_contact_and_never_leak_early():
    facts = call(action="open")["info"]["facts"]
    locked = {f["id"] for f in facts if f["locked"]}
    assert locked == {"binary", "characters", "plural", "negation"}
    assert all(set(f) == {"id", "locked", "unlock"} for f in facts if f["locked"])    # nothing but the id
    open_ids = {f["id"] for f in facts if not f["locked"]}
    assert open_ids == {"linear_b", "arecibo"}
    contact_one()
    unlocked = {f["id"] for f in call(action="open")["info"]["facts"] if not f["locked"]}
    assert unlocked == {"binary", "linear_b", "arecibo"}
    contact_three()
    assert not any(f["locked"] for f in call(action="open")["info"]["facts"])


def test_the_page_wires_story_info_and_report():
    from pathlib import Path
    html = (Path(game.__file__).parent / "index.html").read_text(encoding="utf-8")
    for needle in ('id="crew-log-panel"', 'id="crew-log-toggle-button"', 'id="report-panel"', 'id="report-toggle-button"',
                   'id="info-page-panel"', 'id="info-page-toggle-button"', "story-toggle.js", "info-page.css"):
        assert needle in html, needle
    selectors = re.search(r'data-story-selectors="([^"]+)"', html).group(1)
    assert "#crew-log-panel" in selectors and "#crew-log-toggle-button" in selectors
