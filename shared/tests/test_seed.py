"""shared/seed.py: the seeded-run module (planning/TODO.md Z-1) and the daily seed (Z-5).
Known values are pinned so an accidental change to the algorithm fails loudly; the JavaScript twin is
checked against the same numbers in test_seed_browser.py."""

import re
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import seed as sd  # noqa: E402

SEED_RE = re.compile(r"^[A-Z0-9]{2,12}-[%s]{5}$" % sd.ALPHABET)


def test_splitmix64_and_fnv_reference_values():
    r = sd.Rng("x")
    r.state = 0
    assert r.next() == 0xE220A8397B1DCDAF        # the published splitmix64 first output for state 0
    assert sd.fnv1a64("") == 0xCBF29CE484222325   # FNV-1a offset basis
    assert sd.fnv1a64("a") == 0xAF63DC4C8601EC8C  # FNV-1a 64 of "a"


def test_pinned_sequence_for_a_seed():
    r = sd.Rng("TIDE-K7F2Q")
    assert [r.next() for _ in range(3)] == [10252949485630092546, 9651280616414493402, 15263075260975997904]
    r = sd.Rng("TIDE-K7F2Q")
    assert r.random() == 0.555813505335214
    r = sd.Rng("TIDE-K7F2Q")
    assert [r.randint(1, 6), r.randint(1, 6), r.choice("abcdef")] == [1, 1, "a"]
    assert r.shuffled(list(range(8))) == [6, 2, 7, 3, 0, 1, 4, 5]
    assert r.sample(list(range(10)), 3) == [7, 8, 5]
    assert r.get_state() == "11866928699886969518"
    assert sd.Rng("TIDE-K7F2Q").fork("loot").next() == 4760238496513287047


def test_same_seed_same_run_and_other_seed_different():
    a = [sd.Rng("TIDE-AAAAA").random() for _ in range(1)]
    b = [sd.Rng("TIDE-AAAAA").random() for _ in range(1)]
    c = [sd.Rng("TIDE-AAAAB").random() for _ in range(1)]
    assert a == b and a != c


def test_draw_ranges():
    r = sd.Rng("TIDE-RANGE")
    for _ in range(2000):
        assert 0.0 <= r.random() < 1.0
        assert 3 <= r.randint(3, 9) <= 9
        assert 0 <= r.below(7) < 7
        assert 2.0 <= r.uniform(2.0, 5.0) < 5.0
    assert r.randint(4, 4) == 4
    assert r.below(1) == 0


def test_below_is_roughly_uniform():
    r = sd.Rng("TIDE-UNIFORM")
    counts = [0] * 6
    for _ in range(6000):
        counts[r.below(6)] += 1
    assert all(800 < c < 1200 for c in counts)


def test_shuffle_in_place_and_shuffled_copy():
    items = list(range(20))
    out = sd.Rng("TIDE-SHUF1").shuffle(items)
    assert out is items and sorted(items) == list(range(20)) and items != list(range(20))
    source = tuple(range(20))
    copy = sd.Rng("TIDE-SHUF1").shuffled(source)
    assert copy == items and source == tuple(range(20))


def test_sample_is_without_replacement_and_checked():
    r = sd.Rng("TIDE-SAMP1")
    picked = r.sample(list(range(10)), 10)
    assert sorted(picked) == list(range(10))
    with pytest.raises(ValueError):
        r.sample([1, 2], 3)


def test_weighted_choice_follows_weights():
    r = sd.Rng("TIDE-WEIGH")
    got = [r.weighted_choice(["a", "b", "c"], [0, 1, 9]) for _ in range(2000)]
    assert "a" not in got and got.count("c") > got.count("b") * 4
    with pytest.raises(ValueError):
        r.weighted_choice(["a"], [0])
    with pytest.raises(ValueError):
        r.weighted_choice(["a", "b"], [1])


def test_bad_arguments_raise():
    r = sd.Rng("TIDE-ERROR")
    for bad in (0, -1, 1.5, True, "3"):
        with pytest.raises(ValueError):
            r.below(bad)
    with pytest.raises(ValueError):
        r.randint(5, 1)
    with pytest.raises(IndexError):
        r.choice([])


def test_fork_depends_on_label_only():
    r = sd.Rng("TIDE-FORK1")
    first = r.fork("loot").next()
    r.next(); r.next()
    assert r.fork("loot").next() == first
    assert r.fork("weather").next() != first


def test_state_round_trip_resumes_the_stream():
    r = sd.Rng("TIDE-STATE")
    for _ in range(5):
        r.next()
    saved = r.get_state()
    expected = [r.random() for _ in range(4)]
    again = sd.Rng("TIDE-STATE")
    again.set_state(saved)
    assert [again.random() for _ in range(4)] == expected
    with pytest.raises(ValueError):
        again.set_state(str(1 << 64))


def test_prefix_for():
    assert sd.prefix_for("tide") == "TIDE"
    assert sd.prefix_for("trade-empire") == "TRADEEMPIRE"
    assert sd.prefix_for("champ-de-mots") == "CHAMPDEMOTS"
    assert len(sd.prefix_for("a-very-long-game-slug-indeed")) == sd.PREFIX_MAX
    with pytest.raises(ValueError):
        sd.prefix_for("x")


def test_alphabet_has_no_lookalikes():
    assert len(sd.ALPHABET) == 31 and len(set(sd.ALPHABET)) == 31
    assert not set("01ILO") & set(sd.ALPHABET)


def test_new_seed_shape_and_entropy_hook():
    for _ in range(50):
        assert SEED_RE.match(sd.new_seed("trade-empire"))
    fixed = sd.new_seed("tide", entropy=lambda n: 0)
    assert fixed == "TIDE-22222"
    assert sd.new_seed("tide", entropy=sd.Rng("fixed")) == sd.new_seed("tide", entropy=sd.Rng("fixed"))
    assert len({sd.new_seed("tide") for _ in range(50)}) > 40


def test_daily_seed_is_deterministic_per_date_and_game():
    assert sd.daily_seed("tide", "2026-10-08") == "TIDE-X54PB"            # pinned
    assert sd.daily_seed("signal", "2026-10-08") == "SIGNAL-7JWUM"
    assert sd.daily_seed("trade-empire", "2026-10-09") == "TRADEEMPIRE-FU6FG"
    assert sd.daily_seed("tide", date(2026, 10, 8)) == sd.daily_seed("tide", "2026-10-08")
    days = {sd.daily_seed("tide", "2026-10-%02d" % d) for d in range(1, 29)}
    assert len(days) == 28                                                 # no repeats in a month
    assert sd.daily_seed("tide", "2026-10-08") != sd.daily_seed("thaw", "2026-10-08")
    assert SEED_RE.match(sd.daily_seed("tide", "2026-10-08"))


@pytest.mark.parametrize("bad", ["2026-13-01", "2026-02-30", "26-10-08", "2026/10/08", "", None, 20261008])
def test_daily_seed_rejects_bad_dates(bad):
    with pytest.raises(ValueError):
        sd.daily_seed("tide", bad)


@pytest.mark.parametrize("typed,game,expected", [
    ("TIDE-K7F2Q", "tide", "TIDE-K7F2Q"),
    ("  tide-k7f2q ", "tide", "TIDE-K7F2Q"),
    ("tide k7f2q", "tide", "TIDE-K7F2Q"),
    ("tidek7f2q", "tide", "TIDE-K7F2Q"),
    ("k7f2q", "tide", "TIDE-K7F2Q"),
    ("TIDE–K7F2Q", "tide", "TIDE-K7F2Q"),
    ("TIDE_K7F2Q", None, "TIDE-K7F2Q"),
    ("trade-empire-k7f2q", "trade-empire", "TRADEEMPIRE-K7F2Q"),
    ("tidek7f2q", None, "TIDE-K7F2Q"),
    ("k7f2q", None, ""),
    ("TIDE-K7F2", "tide", ""),
    ("TIDE-K7F2QQ", "tide", ""),
    ("TIDE-K0F2Q", "tide", ""),
    ("TIDE-KIF2Q", "tide", ""),
    ("T-K7F2Q", None, ""),
    ("", "tide", ""),
    (None, "tide", ""),
    (12345, "tide", ""),
])
def test_normalize(typed, game, expected):
    assert sd.normalize(typed, game) == expected


def test_validate_results():
    ok = sd.validate("tide-k7f2q", "tide")
    assert ok == {"ok": True, "seed": "TIDE-K7F2Q", "error": "", "message": ""}
    empty = sd.validate("   ", "tide")
    assert not empty["ok"] and empty["error"] == "empty" and "TIDE-K7F2Q" in empty["message"]
    bad = sd.validate("TIDE-K0F2Q", "tide")
    assert bad["error"] == "format" and "0, 1, I, L or O" in bad["message"]
    wrong = sd.validate("SIGNAL-K7F2Q", "tide")
    assert wrong["error"] == "wrong-game" and "SIGNAL" in wrong["message"]
    assert sd.validate("SIGNAL-K7F2Q")["ok"]
    assert sd.is_valid("tide-k7f2q", "tide") and not sd.is_valid("nope", "tide")


def test_generated_seeds_always_validate():
    for g in ("tide", "trade-empire", "champ-de-mots", "sol"):
        for _ in range(20):
            s = sd.new_seed(g)
            assert sd.validate(s, g)["seed"] == s
