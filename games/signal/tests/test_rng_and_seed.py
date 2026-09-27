"""RNG, hashing and seed strings are integer-only and frozen."""

import re


def test_fnv1a32_known_vectors(game):
    # Standard FNV-1a 32-bit test vectors.
    assert game.fnv1a32("") == 0x811C9DC5
    assert game.fnv1a32("a") == 0xE40C292C
    assert game.fnv1a32("foobar") == 0xBF9CF968


def test_rng_is_deterministic_and_in_range(game):
    a, b = game.Rng(12345), game.Rng(12345)
    seq_a = [a.random() for _ in range(50)]
    assert seq_a == [b.random() for _ in range(50)]
    assert all(0.0 <= x < 1.0 for x in seq_a)


def test_mulberry32_matches_the_reference_implementation(game):
    # mulberry32(1)'s first output is the widely quoted 0.6270739405881613.
    assert abs(game.Rng(1).random() - 0.6270739405881613) < 1e-12


def test_rng_frozen_pin(game):
    r = game.Rng(1)
    assert [r.below(1000) for _ in range(5)] == [627, 2, 527, 981, 968]


def test_rng_masks_the_seed_to_32_bits(game):
    assert game.Rng(2 ** 32 + 7).random() == game.Rng(7).random()


def test_seed_strings_are_versioned(game):
    assert game.daily_seed("2026-09-27", "easy") == "signal:v1:2026-09-27:easy"
    assert game.practice_seed("hard", "P-H12345") == "signal:v1:practice:hard:P-H12345"


def test_parse_date_is_strict(game):
    assert game.parse_date("2026-09-27").isoformat() == "2026-09-27"
    for bad in ("2026-9-27", "2026-02-30", "", "20260927", "2026-09-27T00:00", None, 5, ["2026-09-27"], "٢٠٢٦-٠٩-٢٧"):
        assert game.parse_date(bad) is None


def test_puzzle_number_counts_from_the_epoch(game):
    assert game.puzzle_number(game.EPOCH) == 1
    assert game.puzzle_number("2026-09-28") == 2
    assert game.puzzle_number("2027-01-05") == 101


def test_cell_labels(game):
    assert game.cell_label(0, 0) == "A1"
    assert game.cell_label(3, 3) == "D4"
    assert game.cell_label(14, 14) == "O15"


def test_practice_code_round_trip_and_forgiveness(game):
    game.set_random_source(__import__("random").Random(5))
    for mode in game.PRESET_ORDER:
        code = game.new_practice_code(mode)
        assert re.fullmatch(r"P-[EHWB][0-9A-Z]{5}", code)
        assert game.parse_practice_code(code) == (mode, code)
        assert game.parse_practice_code(code.lower()) == (mode, code)
        assert game.parse_practice_code(code[2:]) == (mode, code)
        assert game.parse_practice_code(" " + code.replace("-", " ") + " ") == (mode, code)


def test_practice_code_normalises_lookalikes_and_rejects_junk(game):
    assert game.parse_practice_code("P-HOIL00") == ("hard", "P-H01100")
    for bad in ("", "P-", "P-X12345", "P-H1234", "P-H123456", "P-H1234U", None, 5, ["P-H12345"], {"a": 1}):
        assert game.parse_practice_code(bad) is None
