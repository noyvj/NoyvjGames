"""Z-1c: the stall can be started from a shared seed text (POCKETBAZAAR-K7F2Q). Every older save and every new stall are
the standard stall, which shows POCKETBAZAAR-STAND and writes nothing new; another valid text changes only which customers
turn up, is saved only when it is not the standard one, and is validated on load."""

import json
import sys
from pathlib import Path

import pytest

import game
from .bot import call

SHARED = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
import seed as noyvj_seed  # noqa: E402


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def queue_of(view):
    return [(c["name"] if "name" in c else "", [(i["family"], i["tier"]) for i in c["items"]]) for c in view["customers"]]


def test_the_prefix_and_the_standard_text_match_the_shared_module():
    assert noyvj_seed.prefix_for("pocket-bazaar") == game.SEED_PREFIX
    assert noyvj_seed.is_valid(game.STANDARD_SEED_TEXT, "pocket-bazaar")
    for _ in range(20):
        text = noyvj_seed.new_seed("pocket-bazaar")
        assert noyvj_seed.is_valid(text, "pocket-bazaar") and game.clean_seed_text(text) in (text, "")


def test_a_new_stall_is_the_standard_one_and_writes_nothing_new():
    view = call(action="open")
    assert view["seed_text"] == game.STANDARD_SEED_TEXT
    assert "seed" not in game.get_state() and "seed_text" not in game.get_state()


def test_an_older_save_loads_as_the_standard_stall():
    game.load_state({"coins": 40, "next_day": 3, "days_played": 2})
    assert call(action="open")["seed_text"] == game.STANDARD_SEED_TEXT and game.stall.seed == game.DEFAULT_SEED


def test_a_stall_from_a_seed_text_shows_it_saves_it_and_reloads_it():
    call(action="reset", seed=123456, seed_text="POCKETBAZAAR-K7F2Q")
    assert call(action="open")["seed_text"] == "POCKETBAZAAR-K7F2Q"
    saved = json.loads(json.dumps(game.get_state()))
    assert saved["seed_text"] == "POCKETBAZAAR-K7F2Q" and saved["seed"] == 123456
    game.stall.__init__()
    game.load_state(saved)
    assert call(action="open")["seed_text"] == "POCKETBAZAAR-K7F2Q" and game.stall.seed == 123456


def test_the_seed_changes_only_the_customers_and_the_same_seed_repeats():
    standard = call(action="start_day")
    standard_queue = queue_of(standard)
    call(action="reset")
    assert queue_of(call(action="start_day")) == standard_queue                      # the standard stall repeats
    call(action="reset", seed=987654, seed_text="POCKETBAZAAR-K7F2Q")
    first = call(action="start_day")
    call(action="reset", seed=987654, seed_text="POCKETBAZAAR-K7F2Q")
    second = call(action="start_day")
    assert queue_of(first) == queue_of(second)
    assert first["festival"] == standard["festival"] and len(first["customers"]) == len(standard["customers"])
    assert queue_of(first) != standard_queue or first["board"] != standard["board"]


def test_the_standard_text_or_a_bad_text_gives_the_standard_stall():
    for text in (game.STANDARD_SEED_TEXT, "TIDE-K7F2Q", "pocketbazaar-k7f2q", "POCKETBAZAAR-K7F20", "", None, 4, "POCKETBAZAAR-K7F2"):
        call(action="reset", seed=555, seed_text=text)
        assert call(action="open")["seed_text"] == game.STANDARD_SEED_TEXT, text
        assert game.stall.seed == game.DEFAULT_SEED and "seed_text" not in game.get_state()


def test_a_seed_with_a_bad_number_falls_back_to_standard_and_a_bad_save_is_cleaned():
    call(action="reset", seed="12", seed_text="POCKETBAZAAR-K7F2Q")
    assert game.stall.seed_text == "" and game.stall.seed == game.DEFAULT_SEED
    game.load_state({"seed_text": "POCKETBAZAAR-K7F2Q", "seed": -3})
    assert game.stall.seed == game.DEFAULT_SEED and game.stall.seed_text == "POCKETBAZAAR-K7F2Q"
    game.load_state({"seed_text": "SIGNAL-K7F2Q", "seed": 99})
    assert game.stall.seed == game.DEFAULT_SEED and game.stall.seed_text == ""


def test_a_reset_back_to_standard_keeps_the_market_results_as_before():
    game.stall.market_days = {"2026-10-05": {"stars": 2, "served": 5, "total": 7, "coins": 10}}
    call(action="reset", seed=5, seed_text="POCKETBAZAAR-K7F2Q")
    assert game.stall.market_days
