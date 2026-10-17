"""Tests for Rng.rand() in gen.py."""

import gen


def test_rand_returns_a_float_between_zero_and_one():
    rng = gen.Rng(42)
    val = rng.rand()
    assert 0.0 <= val < 1.0


def test_rand_is_deterministic_given_the_same_seed():
    seed = gen._fnv1a64("EVIDENCEHUNT-K7F2Q")
    rng_a = gen.Rng(seed)
    rng_b = gen.Rng(seed)
    assert rng_a.rand() == rng_b.rand()


def test_rand_differs_on_consecutive_calls():
    rng = gen.Rng(42)
    v1 = rng.rand()
    v2 = rng.rand()
    assert v1 != v2


def test_rand_with_zero_seed_does_not_crash_and_returns_valid_range():
    rng = gen.Rng(0)
    val = rng.rand()
    assert 0.0 <= val < 1.0
