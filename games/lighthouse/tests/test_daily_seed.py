"""Z-5c: "Today's run" sails a year from the UTC date's shared seed. The page derives the engine's number from the seed
text (NoyvjSeed.rng(text).randint(1, 2147483646)), so the same day gives everybody the same weather, ships and story
beats, and a run from an older day is simply an ordinary seed. Nothing new is saved: the seed text is the daily."""

import json
import sys
from pathlib import Path

import game
from state import clean_seed_text

SHARED = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
import seed as noyvj_seed  # noqa: E402


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


def number_for(text):
    """What the page sends as `seed` for a seed text."""
    return noyvj_seed.Rng(text).randint(1, 2147483646)


def sail(date):
    text = noyvj_seed.daily_seed("lighthouse", date)
    v = req(action="abandon", seed=number_for(text), seed_text=text, quiet=False)
    return text, v


def test_every_daily_seed_is_a_seed_the_engine_accepts():
    for day in range(1, 29):
        text = noyvj_seed.daily_seed("lighthouse", "2026-10-%02d" % day)
        assert clean_seed_text(text) == text
        assert text.startswith("LIGHTHOUSE-")


def test_the_same_day_gives_the_same_year_and_another_day_a_different_one():
    text_a, a = sail("2026-10-12")
    game.get_state()
    text_b, b = sail("2026-10-12")
    assert text_a == text_b and a["seed_text"] == text_a
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    sims = set()
    for day in range(10, 17):
        text, v = sail("2026-10-%02d" % day)
        sims.add(game.get_state()["run"]["seed"])
        assert v["seed_text"] == text
    assert len(sims) == 7


def test_abandoning_for_the_daily_keeps_the_lifetime_records():
    req(action="new_game", seed=5)
    game.keep.meta["ships_passed"] = 17
    game.keep.meta["achievements"] = list(game.keep.meta.get("achievements", []))
    sail("2026-10-12")
    assert game.get_state()["meta"]["ships_passed"] == 17


def test_a_saved_daily_year_reloads_with_its_text_and_an_old_save_is_unchanged():
    text, _ = sail("2026-10-12")
    saved = json.loads(json.dumps(game.get_state()))
    game.load_state(saved)
    assert req(action="open")["seed_text"] == text
    assert game.get_state()["run"]["seed"] == saved["run"]["seed"]
    old = json.loads(json.dumps(saved))
    old["run"].pop("seed_text", None)
    game.load_state(old)
    assert req(action="open")["seed_text"] == ""
