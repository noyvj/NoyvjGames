"""Edge-case tests for gen.py public functions."""

import gen


def test_parse_valid_and_invalid_inputs():
    # Valid share code
    diff, seed = gen.parse("EH3-1K9X2")
    assert diff == 3 and isinstance(seed, int)
    # Valid case id (lowercase)
    diff, seed = gen.parse("practice-3-1k9x2")
    assert diff == 3 and isinstance(seed, int)
    # Invalid formats return None
    for bad in (None, "", "EH0-1", "EH6-1", "EVIDENCEHUNT-K7F2Q", "12345"):
        assert gen.parse(bad) is None, bad


def test_is_daily_text_valid_and_invalid():
    # Valid daily text
    assert gen.is_daily_text("EVIDENCEHUNT-K7F2Q") is True
    # Invalid prefix or length
    for bad in ("TIDE-K7F2Q", "EVIDENCEHUNT-K7F2", "EVIDENCEHUNT-K7F2Q1"):
        assert gen.is_daily_text(bad) is False, bad
    # Lowercase is rejected by the regex
    assert gen.is_daily_text("evidencehunt-k7f2q") is False


def test_daily_house_returns_valid_pair():
    valid = "EVIDENCEHUNT-K7F2Q"
    result = gen.daily_house(valid)
    assert result is not None
    d, s = result
    assert d in gen.DAILY_SIZES and 0 <= s < gen.SEED_LIMIT
    # Invalid text returns None
    assert gen.daily_house("TIDE-K7F2Q") is None


def test_make_rejects_invalid_inputs():
    # Difficulty out of range
    for diff in (0, 6, -1):
        assert gen.make(diff, 0) is None, diff
    # Seed out of range or wrong type
    assert gen.make(1, -1) is None
    assert gen.make(1, gen.SEED_LIMIT) is None
    assert gen.make(1, 1.5) is None


def test_next_seed_bounds():
    # Always returns an integer within [0, SEED_LIMIT)
    for played in (0, 100, gen.SEED_LIMIT - 1):
        for diff in gen.DIFFICULTIES:
            s = gen.next_seed(played, diff)
            assert isinstance(s, int) and 0 <= s < gen.SEED_LIMIT, (played, diff)


def test_to_base36_edge_cases():
    # Zero maps to "0"
    assert gen.to_base36(0) == "0"
    # Smallest positive
    assert gen.to_base36(1) == "1"
    # Max single digit
    assert gen.to_base36(35) == "z"
    # Rollover to two digits
    assert gen.to_base36(36) == "10"
    # Largest valid seed
    assert len(gen.to_base36(gen.SEED_LIMIT - 1)) == 6
