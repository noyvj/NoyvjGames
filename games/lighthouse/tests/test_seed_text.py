"""Z-1c: a run can carry the shared seed text (LIGHTHOUSE-K7F2Q). The engine keeps it only when it is valid, writes it
only when present, and an older save without it loads unchanged."""

import json
import sys
from pathlib import Path

import game
import sim
from state import Keep, clean_seed_text

SHARED = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
import seed as noyvj_seed  # noqa: E402


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def test_a_new_game_with_a_seed_text_shows_it_in_the_view_and_keeps_it_in_the_save():
    text = noyvj_seed.new_seed("lighthouse")
    v = req(action="new_game", seed=123, seed_text=text)
    assert v["seed_text"] == text
    assert game.get_state()["run"]["seed_text"] == text
    game.load_state(json.loads(json.dumps(game.get_state())))
    assert req(action="open")["seed_text"] == text


def test_the_text_is_absent_from_the_save_when_the_run_has_none():
    req(action="new_game", seed=9)
    assert req(action="open")["seed_text"] == ""
    assert "seed_text" not in game.get_state()["run"]


def test_an_older_save_without_the_key_loads_unchanged():
    k = Keep(5)
    sim.to_evening(k)
    d = k.to_dict()
    assert "seed_text" not in d["run"]
    assert Keep.from_dict(d).to_dict() == d


def test_bad_texts_are_dropped_one_at_a_time():
    good = "LIGHTHOUSE-K7F2Q"
    assert clean_seed_text(good) == good
    for bad in ("", None, 5, "lighthouse-k7f2q", "TIDE-K7F2Q", "LIGHTHOUSE-K7F20", "LIGHTHOUSE-K7F2", "LIGHTHOUSE-K7F2QQ",
                "LIGHTHOUSEK7F2Q", "LIGHTHOUSE-K7F2I", ["LIGHTHOUSE-K7F2Q"], "LIGHTHOUSE-K7F2Q\n"):
        assert clean_seed_text(bad) == "", bad
    k = Keep(5)
    sim.to_evening(k)
    d = k.to_dict()
    d["run"]["seed_text"] = "TIDE-K7F2Q"
    assert Keep.from_dict(d).seed_text == ""


def test_the_engine_agrees_with_the_shared_module_on_what_a_good_text_is():
    for _ in range(20):
        text = noyvj_seed.new_seed("lighthouse")
        assert noyvj_seed.is_valid(text, "lighthouse") and clean_seed_text(text) == text
    assert noyvj_seed.prefix_for("lighthouse") == "LIGHTHOUSE"


def test_an_abandoned_year_takes_the_new_text_and_a_plain_abandon_clears_it():
    req(action="new_game", seed=1, seed_text="LIGHTHOUSE-K7F2Q")
    assert req(action="abandon", seed=2, seed_text="LIGHTHOUSE-ABCDE")["seed_text"] == "LIGHTHOUSE-ABCDE"
    assert req(action="abandon", seed=3)["seed_text"] == ""
    assert req(action="reset", seed=3, seed_text="nonsense")["seed_text"] == ""
