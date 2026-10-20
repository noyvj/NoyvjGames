"""Edge-case tests for goods.py."""

import pytest
import goods


class TestValidGood:
    def test_valid_standard_good(self):
        assert goods.valid_good((goods.FAMILIES[0], 1)) is True
        assert goods.valid_good((goods.FAMILIES[-1], goods.MAX_TIER)) is True

    def test_invalid_tier_bounds(self):
        assert goods.valid_good((goods.FAMILIES[0], 0)) is False
        assert goods.valid_good((goods.FAMILIES[0], goods.MAX_TIER + 1)) is False

    def test_unknown_family(self):
        assert goods.valid_good(("unknown", 1)) is False

    def test_wildcard_good(self):
        assert goods.valid_good((goods.WILD, 1)) is True
        assert goods.valid_good((goods.WILD, 2)) is False

    def test_non_tuple_inputs(self):
        assert goods.valid_good(None) is False
        assert goods.valid_good("produce") is False
        assert goods.valid_good(123) is False

    def test_bool_tier_rejected(self):
        assert goods.valid_good((goods.FAMILIES[0], True)) is False
        assert goods.valid_good((goods.FAMILIES[0], False)) is False


class TestGoodCodeAndParse:
    def test_round_trip_standard(self):
        for fam in goods.FAMILIES:
            for tier in range(1, goods.MAX_TIER + 1):
                code = goods.good_code((fam, tier))
                assert goods.parse_code(code) == (fam, tier)

    def test_wildcard_and_none_codes(self):
        wild_good = (goods.WILD, 1)
        assert goods.good_code(wild_good) == "**"
        assert goods.parse_code("**") == wild_good
        assert goods.good_code(None) == ".."
        assert goods.parse_code("..") is None

    def test_invalid_parse_raises(self):
        with pytest.raises(ValueError):
            goods.parse_code("X9")
        with pytest.raises(ValueError):
            goods.parse_code("12")


class TestCrateBeats:
    def test_tier_1_to_5(self):
        for tier in range(1, goods.MAX_TIER + 1):
            expected = 2 ** tier - 1
            assert goods.crate_beats(tier) == expected

    def test_zero_and_negative_tier(self):
        assert goods.crate_beats(0) == 0
        assert goods.crate_beats(-1) == -0.5


class TestCellsNeeded:
    def test_matches_tier(self):
        for tier in range(1, goods.MAX_TIER + 1):
            assert goods.cells_needed(tier) == tier

    def test_zero_and_negative(self):
        assert goods.cells_needed(0) == 0
        assert goods.cells_needed(-1) == -1


class TestGoodValueAndSellValue:
    def test_standard_values(self):
        for tier in range(1, goods.MAX_TIER + 1):
            good = (goods.FAMILIES[0], tier)
            assert goods.good_value(good) == goods.VALUE[tier]
            assert goods.sell_value(good) == goods.SELL[tier]

    def test_wildcard_values(self):
        wild_good = (goods.WILD, 1)
        assert goods.good_value(wild_good) == 0
        assert goods.sell_value(wild_good) == 1

    def test_none_input_raises(self):
        with pytest.raises(TypeError):
            goods.good_value(None)
        with pytest.raises(TypeError):
            goods.sell_value(None)
