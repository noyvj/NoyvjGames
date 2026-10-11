"""Z-1c: a career can carry the shared seed text (HEISTCOMMITT-K7F2Q). The engine keeps it only when it is valid,
saves it only when present, and swaps a seed in only for a career nothing has happened in."""

import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
import seed as noyvj_seed  # noqa: E402


def test_the_prefix_matches_the_shared_module(g):
    assert noyvj_seed.prefix_for("heist-committee") == g.module.SEED_PREFIX
    for _ in range(20):
        text = noyvj_seed.new_seed("heist-committee")
        assert g.module._clean_seed_text(text) == text and noyvj_seed.is_valid(text, "heist-committee")


def test_a_new_career_with_a_seed_text_shows_and_saves_it(g):
    r = g(action="new_career", seed=1234, seed_text="HEISTCOMMITT-K7F2Q")
    assert r["view"]["career_seed_text"] == "HEISTCOMMITT-K7F2Q"
    assert g.module.get_state() == {"schema": 1, "career_seed": 1234, "career_seed_text": "HEISTCOMMITT-K7F2Q"}
    g.module.load_state(json.loads(json.dumps(g.module.get_state())))
    assert g(action="open")["view"]["career_seed_text"] == "HEISTCOMMITT-K7F2Q"


def test_the_text_is_not_written_when_the_career_has_none(g):
    assert g(action="open")["view"]["career_seed_text"] == ""
    assert "career_seed_text" not in g.module.get_state()


def test_a_wrong_or_malformed_text_is_dropped(g):
    for bad in ("TIDE-K7F2Q", "heistcommitt-k7f2q", "HEISTCOMMITT-K7F20", "HEISTCOMMITT-K7F2", "", None, 7, ["HEISTCOMMITT-K7F2Q"]):
        assert g(action="new_career", seed=5, seed_text=bad)["view"]["career_seed_text"] == "", bad
    g.module.load_state({"career_seed": 5, "career_seed_text": "SIGNAL-K7F2Q"})
    assert g(action="open")["view"]["career_seed_text"] == ""


def test_an_untouched_career_can_be_given_its_seed_once(g):
    assert g(action="open")["view"]["career_untouched"] is True
    r = g(action="seed_career", seed=4321, seed_text="HEISTCOMMITT-ABCDE")
    assert r["view"]["career_seed_text"] == "HEISTCOMMITT-ABCDE" and g.module.get_state()["career_seed"] == 4321
    g(action="seed_career", seed=999, seed_text="HEISTCOMMITT-ZZZZZ")      # already has one: refused
    assert g.module.get_state()["career_seed"] == 4321 and g(action="open")["view"]["career_seed_text"] == "HEISTCOMMITT-ABCDE"


def test_a_career_with_history_keeps_its_seed(g):
    g.module.load_state({"career_seed": 6, "cash": 450})
    assert g(action="open")["view"]["career_untouched"] is False
    g(action="seed_career", seed=1, seed_text="HEISTCOMMITT-ABCDE")
    assert g.module.get_state()["career_seed"] == 6 and g(action="open")["view"]["career_seed_text"] == ""
    # a job taken also counts
    g.module.load_state({"career_seed": 6})
    board = g(action="open")["view"]["board"]
    g(action="take_job", target=board[0]["id"])
    assert g(action="open")["view"]["career_untouched"] is False


def test_the_same_seed_gives_the_same_board(g):
    boards = []
    for _ in range(2):
        g(action="new_career", seed=2468, seed_text="HEISTCOMMITT-K7F2Q")
        boards.append([t["id"] for t in g(action="open")["view"]["board"]])
    assert boards[0] == boards[1]


def test_an_older_save_without_the_key_loads_unchanged(g):
    g.module.load_state({"schema": 1, "career_seed": 9, "cash": 410, "jobs_started": 2})
    assert g.module.get_state()["career_seed"] == 9 and "career_seed_text" not in g.module.get_state()
