import pytest

import goods
from rng import Rng, mix, MAX_DRAWS


def test_every_family_has_five_named_tiers_a_letter_and_a_distinct_shape():
    letters, shapes = set(), set()
    for fam in goods.FAMILIES:
        info = goods.FAMILY_INFO[fam]
        assert len(info["tiers"]) == goods.MAX_TIER and len(set(info["tiers"])) == goods.MAX_TIER
        letters.add(info["letter"])
        shapes.add(info["shape"])
    assert len(letters) == len(shapes) == len(goods.FAMILIES)


def test_codes_round_trip_and_reject_junk():
    for fam in goods.FAMILIES:
        for t in range(1, 6):
            assert goods.parse_code(goods.good_code((fam, t))) == (fam, t)
    assert goods.parse_code("..") is None
    assert goods.parse_code("**") == (goods.WILD, 1)
    for bad in ("X9", "P6", "P0", "p1", "", "P"):
        with pytest.raises(ValueError):
            goods.parse_code(bad)


def test_valid_good_is_strict():
    assert goods.valid_good(("produce", 3))
    assert goods.valid_good((goods.WILD, 1))
    assert not goods.valid_good((goods.WILD, 2))
    for bad in (("produce", 0), ("produce", 6), ("nope", 1), ("produce", True), ("produce", "3"), None, 5, ("produce",)):
        assert not goods.valid_good(bad)


def test_prices_rise_by_tier_and_selling_is_never_zero_or_better_than_a_customer():
    assert all(goods.VALUE[t] < goods.VALUE[t + 1] for t in range(1, 5))
    for fam in goods.FAMILIES:
        for t in range(1, 6):
            assert 1 <= goods.sell_value((fam, t)) < goods.good_value((fam, t))
    assert goods.sell_value((goods.WILD, 1)) == 1


def test_build_costs_match_the_merge_arithmetic():
    assert [goods.crate_beats(t) for t in range(1, 6)] == [1, 3, 7, 15, 31]
    assert [goods.cells_needed(t) for t in range(1, 6)] == [1, 2, 3, 4, 5]


def test_next_tier_name():
    assert goods.next_tier_name(("textiles", 1)) == "Ribbon"
    assert goods.next_tier_name(("textiles", 5)) is None
    assert goods.next_tier_name(None) is None


def test_rng_is_exactly_reproducible_and_resumes_from_a_count():
    a = Rng(12345)
    first = [a.next_u32() for _ in range(5)]
    assert first == [Rng(12345).next_u32()] + first[1:]
    assert first == [4207900869, 1317490944, 2079646450, 3513001552, 2187978186]   # pinned: saves depend on it
    b = Rng(12345, draws=3)
    assert [b.next_u32(), b.next_u32()] == first[3:5]
    assert b.draws == 5
    c = Rng.from_dict(a.to_dict())
    assert c.next_u32() == a.next_u32()


def test_rng_helpers_stay_in_range():
    r = Rng(7)
    for _ in range(300):
        assert 0 <= r.below(5) < 5
        assert 3 <= r.between(3, 6) <= 6
        assert r.choice("abc") in "abc"
    assert r.weighted([("x", 0), ("y", 5)]) == "y"
    assert all(Rng(s).chance(1, 1) for s in range(20))
    assert not any(Rng(s).chance(0, 4) for s in range(20))
    seen = {Rng(s).below(4) for s in range(60)}
    assert seen == {0, 1, 2, 3}


def test_rng_rejects_bad_saves():
    for bad in ({"seed": -1, "draws": 0}, {"seed": 2 ** 32, "draws": 0}, {"seed": 1, "draws": -1},
                {"seed": 1, "draws": MAX_DRAWS + 1}, {"seed": True, "draws": 0}, {"seed": 1, "draws": 1.5}):
        with pytest.raises(ValueError):
            Rng.from_dict(bad)
    with pytest.raises(ValueError):
        Rng(1).below(0)


def test_mix_is_stable_and_depends_on_every_part():
    assert mix(1, 2) == mix(1, 2) and mix(1, 2) != mix(2, 1) and mix(1, 2) != mix(1, 3)
    assert 0 <= mix(99, 5, 7) < 2 ** 32
