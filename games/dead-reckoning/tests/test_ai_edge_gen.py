"""Edge-case tests for gen.py: limits, boundaries, and rejection of invalid inputs."""


import gen


def test_to_base36_handles_zero_and_boundaries():
    assert gen.to_base36(0) == "0"
    assert gen.to_base36(1) == "1"
    assert gen.to_base36(35) == "z"
    assert gen.to_base36(36) == "10"
    assert gen.to_base36(gen.SEED_LIMIT - 1) == "zzzzzz"


def test_chart_id_and_code_of_respect_difficulty_and_seed_limits():
    assert gen.chart_id(1, 0) == "practice-1-0"
    assert gen.chart_id(5, gen.SEED_LIMIT - 1) == "practice-5-zzzzzz"
    assert gen.chart_id(3, 0, two=True) == "practice-3t-0"

    assert gen.code_of(1, 0) == "DR1-0"
    assert gen.code_of(5, gen.SEED_LIMIT - 1) == "DR5-ZZZZZZ"
    assert gen.code_of(3, 0, two=True) == "DR3T-0"


def test_parse_ex_accepts_valid_codes_and_rejects_junk():
    assert gen.parse_ex("DR1-0") == (1, 0, False)
    assert gen.parse_ex("DR5-ZZZZZZ") == (5, gen.SEED_LIMIT - 1, False)
    assert gen.parse_ex("DR3T-0") == (3, 0, True)

    for bad in ("", None, "DR6-1", "DR0-1", "DR3-ZZZZZZZ", "XX3-AB"):
        assert gen.parse_ex(bad) is None, f"parse_ex({bad!r}) should be None"


def test_parse_rejects_two_ship_codes_and_junk():
    assert gen.parse("DR1-0") == (1, 0)
    assert gen.parse("DR3T-0") is None
    assert gen.parse("") is None


def test_is_practice_id_matches_only_chart_ids():
    assert gen.is_practice_id("practice-1-0") is True
    assert gen.is_practice_id("practice-5-zzzzzz") is True
    assert gen.is_practice_id("DR1-0") is False
    assert gen.is_practice_id("") is False


def test_next_seed_stays_within_bounds():
    for n in range(10):
        for d in gen.DIFFICULTIES:
            val = gen.next_seed(n, d)
            assert 0 <= val < gen.SEED_LIMIT, f"next_seed({n}, {d}) out of bounds"


def test_make_chart_returns_none_for_out_of_range_inputs():
    for d, s in ((0, 1), (6, 1), (3, -1), (3, gen.SEED_LIMIT), (3, "x"), (3, True)):
        assert gen.make_chart(d, s) is None, f"make_chart({d}, {s!r}) should be None"
