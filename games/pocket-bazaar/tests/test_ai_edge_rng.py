import pytest

from rng import Rng, mix, MASK, MAX_DRAWS


def test_rng_constructor_accepts_boundary_seeds_and_draws():
    """Rng accepts seed 0 and MASK, and draws 0 and MAX_DRAWS without error."""
    r_min = Rng(0)
    assert r_min.seed == 0
    r_max_seed = Rng(MASK)
    assert r_max_seed.seed == MASK
    r_zero_draws = Rng(123, draws=0)
    assert r_zero_draws.draws == 0
    r_max_draws = Rng(456, draws=MAX_DRAWS)
    assert r_max_draws.draws == MAX_DRAWS


def test_below_returns_zero_for_one_and_handles_large_n():
    """below(1) always returns 0; below(MAX_DRAWS) stays in range."""
    r = Rng(99)
    assert r.below(1) == 0
    val = r.below(MAX_DRAWS)
    assert 0 <= val < MAX_DRAWS


def test_between_handles_equal_bounds_and_inverted_bounds():
    """between(x, x) returns x; between(high, low) raises ValueError."""
    r = Rng(42)
    assert r.between(5, 5) == 5
    with pytest.raises(ValueError):
        r.between(10, 5)


def test_choice_rejects_empty_sequences():
    """choice([]), choice(()), and choice('') all raise ValueError."""
    r = Rng(7)
    for seq in ([], (), ""):
        with pytest.raises(ValueError):
            r.choice(seq)


def test_weighted_rejects_zero_total_weight():
    """weighted with total weight 0 raises ValueError."""
    r = Rng(1)
    with pytest.raises(ValueError):
        r.weighted([("a", 0), ("b", 0)])


def test_mix_handles_large_and_negative_inputs():
    """mix masks inputs to 32-bit and stays within MASK range."""
    result = mix(MASK, -1, 0)
    assert isinstance(result, int) and 0 <= result <= MASK
