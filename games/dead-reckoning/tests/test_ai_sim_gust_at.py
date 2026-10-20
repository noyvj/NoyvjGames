from sim import gust_at
from tests.golden_charts import GOLDEN_A


def test_gust_at_returns_deterministic_tuple_when_true():
    """Normal case: model is 'true' and amplitude > 0 returns a deterministic tuple in [-amp, amp]."""
    chart = dict(GOLDEN_A, gusts=2.0)
    res1 = gust_at(chart, seed=42, k=5, model="true")
    res2 = gust_at(chart, seed=42, k=5, model="true")
    assert res1 == res2
    assert -2.0 <= res1[0] <= 2.0 and -2.0 <= res1[1] <= 2.0


def test_gust_at_returns_zero_when_model_is_not_true():
    """Normal case: model is 'charted' or 'nominal' returns (0.0, 0.0)."""
    chart = dict(GOLDEN_A, gusts=2.0)
    for model in ("charted", "nominal"):
        assert gust_at(chart, seed=42, k=5, model=model) == (0.0, 0.0)


def test_gust_at_returns_zero_when_amplitude_is_missing_or_zero():
    """Edge case: missing or zero amplitude returns (0.0, 0.0)."""
    chart_no_gusts = dict(GOLDEN_A)
    chart_zero_gusts = dict(GOLDEN_A, gusts=0.0)
    assert gust_at(chart_no_gusts, seed=42, k=5, model="true") == (0.0, 0.0)
    assert gust_at(chart_zero_gusts, seed=42, k=5, model="true") == (0.0, 0.0)
