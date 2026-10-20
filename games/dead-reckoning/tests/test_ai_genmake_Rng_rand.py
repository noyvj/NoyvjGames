from genmake import Rng


def test_rand_returns_floats_between_zero_and_one():
    rng = Rng(42)
    for _ in range(10):
        val = rng.rand()
        assert 0.0 <= val <= 1.0


def test_rand_is_deterministic_across_instances_with_the_same_seed():
    rng_a = Rng(7)
    rng_b = Rng(7)
    for _ in range(5):
        assert rng_a.rand() == rng_b.rand()


def test_rand_yields_different_values_on_successive_calls():
    rng = Rng(100)
    first = rng.rand()
    second = rng.rand()
    assert first != second


def test_rand_handles_seed_zero_edge_case():
    rng = Rng(0)
    val = rng.rand()
    assert 0.0 <= val <= 1.0
