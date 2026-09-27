"""Seeded generation: determinism, placement rules, solvability, frozen fixture."""

import datetime
import json
import time
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "daily_v1.json"


def test_same_seed_same_puzzle_across_calls(game):
    a = game.generate("hard", "signal:v1:2026-10-05:hard")
    b = game.generate("hard", "signal:v1:2026-10-05:hard")
    assert (a.transmitters, a.par, a.reference) == (b.transmitters, b.par, b.reference)


def test_different_dates_and_modes_differ(game):
    seen = {game.daily_puzzle("2026-10-%02d" % d, "easy").transmitters for d in range(1, 15)}
    assert len(seen) >= 12
    assert game.daily_puzzle("2026-10-01", "easy").transmitters != game.daily_puzzle("2026-10-01", "hard").transmitters


@pytest.mark.parametrize("mode", ["easy", "hard", "wide", "bigsky"])
def test_placement_rules_hold_for_every_preset(game, mode):
    board = game.board_for(mode)
    for i in range(4 if mode in ("wide", "bigsky") else 30):
        p = game.generate(mode, "test:rules:%s:%d" % (mode, i))
        assert len(set(p.transmitters)) == board.k
        assert list(p.transmitters) == sorted(p.transmitters)
        for t in p.transmitters:
            assert t in board.interior  # never on the outer ring
        for a in p.transmitters:
            for b in p.transmitters:
                if a != b:
                    assert board.dist[a][b] >= board.spacing


@pytest.mark.parametrize("mode", ["easy", "hard"])
def test_every_puzzle_is_uniquely_solvable_by_its_reference_pings(game, mode):
    board = game.board_for(mode)
    for i in range(25):
        p = game.generate(mode, "test:unique:%s:%d" % (mode, i))
        assert 1 <= p.par <= game.PRESETS[mode]["budget"] - game.PAR_MARGIN
        assert len(p.reference) == p.par
        pings = [(c, game.reading_at(board, p.transmitters, c)) for c in p.reference]
        sols, complete = game.solve(board, pings, limit=10 ** 6)
        assert complete and sols == [p.transmitters]
        # and one fewer reference ping is NOT enough (par is really the first unique step)
        fewer, _ = game.solve(board, pings[:-1], limit=2)
        assert len(fewer) == 2 if p.par > 1 else True


def test_big_board_puzzles_are_unique_too(game):
    for mode in ("wide", "bigsky"):
        board = game.board_for(mode)
        p = game.generate(mode, "test:big:" + mode)
        pings = [(c, game.reading_at(board, p.transmitters, c)) for c in p.reference]
        sols, complete = game.solve(board, pings, limit=2)
        assert complete and sols == [p.transmitters]


def test_par_is_within_budget_slack_for_a_year_of_dailies(game):
    for mode in game.DAILY_MODES:
        limit = game.PRESETS[mode]["budget"] - game.PAR_MARGIN
        start = datetime.date.fromisoformat(game.EPOCH)
        for i in range(0, 365, 5):
            date = (start + datetime.timedelta(days=i)).isoformat()
            assert game.daily_puzzle(date, mode).par <= limit


def test_frozen_fixture_of_a_year_of_daily_puzzles(game):
    data = json.loads(FIXTURE.read_text())
    assert data["seed_version"] == game.SEED_VERSION == "v1"
    assert data["epoch"] == game.EPOCH
    assert data["days"] == 365 and len(data["puzzles"]) == 365 * len(game.DAILY_MODES)
    for key, want in data["puzzles"].items():
        date, mode = key.split(":")
        p = game.generate(mode, game.daily_seed(date, mode))
        n = game.board_for(mode).n
        got = {"t": [[c // n, c % n] for c in p.transmitters], "par": p.par}
        assert got == want, key


def test_generation_time_ceilings_per_preset(game):
    """Generous CPython ceilings; the browser (Pyodide) is several times slower,
    see CLAUDE.md for the measured numbers. Wide/Big Sky stay practice-only."""
    ceilings = {"easy": 0.5, "hard": 1.5, "wide": 6.0, "bigsky": 20.0}
    for mode, ceiling in ceilings.items():
        worst = 0.0
        for i in range(3):
            t = time.time()
            game.generate(mode, "test:time:%s:%d" % (mode, i))
            worst = max(worst, time.time() - t)
        assert worst < ceiling, (mode, worst)


def test_puzzle_cache_is_bounded_and_pure(game):
    for i in range(60):
        game.puzzle_for_seed("easy", "test:cache:%d" % i)
    assert len(game._PUZZLE_CACHE) <= 48
    a = game.puzzle_for_seed("easy", "test:cache:59")
    assert a.transmitters == game.generate("easy", "test:cache:59").transmitters


def test_daily_modes_are_easy_and_hard_only(game):
    assert game.DAILY_MODES == ("easy", "hard")
    assert not game.PRESETS["wide"]["daily"] and not game.PRESETS["bigsky"]["daily"]
