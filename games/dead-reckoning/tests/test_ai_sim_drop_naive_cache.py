from sim import drop_naive_cache, naive_miss
from tests.golden_charts import GOLDEN_A


def test_drop_naive_cache_clears_stored_values():
    """Calling drop_naive_cache() removes cached results so they are recomputed."""
    drop_naive_cache()
    miss_a = naive_miss(GOLDEN_A)
    assert isinstance(miss_a, float)

    drop_naive_cache()
    miss_a_after_drop = naive_miss(GOLDEN_A)
    assert miss_a == miss_a_after_drop


def test_drop_naive_cache_populates_fresh():
    """After dropping, a new call to naive_miss populates the cache again."""
    drop_naive_cache()
    import sim
    assert len(sim._NAIVE_CACHE) == 0

    naive_miss(GOLDEN_A)
    assert GOLDEN_A["id"] in sim._NAIVE_CACHE


def test_drop_naive_cache_on_empty_cache_does_not_raise():
    """Calling drop_naive_cache() when the cache is already empty should not raise."""
    drop_naive_cache()
    drop_naive_cache()  # second call on empty cache
    miss_a = naive_miss(GOLDEN_A)
    assert isinstance(miss_a, float)
