"""Edge-case tests for puzzle.py."""

import pytest

import puzzle as pz


def test_make_puzzle_handles_huge_round_numbers(sample):
    """make_puzzle wraps large round numbers using modulo, so it never crashes on huge inputs."""
    p = pz.make_puzzle(sample, "s1", 999999)
    assert p.size == sample.section("s1")["size"]
    assert len(p.answer) == p.size


def test_make_puzzle_rejects_invalid_section(sample):
    """make_puzzle raises ValueError when given a section id that does not exist in the set."""
    with pytest.raises(ValueError, match="unknown section"):
        pz.make_puzzle(sample, "nonexistent_section", 0)


def test_grade_with_completely_empty_placement(sample):
    """grade marks every slot as empty when placement is an empty list (zero input)."""
    p = pz.make_puzzle(sample, "s1", 0)
    g = pz.grade(p, [])
    assert all(s["status"] == "empty" for s in g["slots"])
    assert g["placed"] == 0 and g["right"] == 0


def test_grade_ignores_extra_placement_cards(sample):
    """grade only evaluates slots up to puzzle.size; extra cards in placement are ignored."""
    p = pz.make_puzzle(sample, "s1", 0)
    extra_card = sample.section_pool("s1")[0]
    g = pz.grade(p, p.answer + [extra_card])
    assert g["placed"] == p.size
    assert g["right"] == p.size


def test_main_rounds_returns_exact_pool_length(sample):
    """main_rounds returns the exact number of events in a section's pool for every section."""
    for sid in sample.section_ids:
        assert pz.main_rounds(sample, sid) == len(sample.section_pool(sid))


def test_rng_below_rejects_zero_and_negative(sample):
    """Rng.below raises ValueError for zero or negative bounds."""
    r = pz.Rng("edge-test")
    with pytest.raises(ValueError):
        r.below(0)
    with pytest.raises(ValueError):
        r.below(-5)
