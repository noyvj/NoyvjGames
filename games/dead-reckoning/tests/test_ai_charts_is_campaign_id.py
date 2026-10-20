"""Tests for charts.is_campaign_id()."""

import charts


def test_is_campaign_id_returns_true_for_a_real_campaign_chart():
    # Use an actual campaign chart id from the loaded registry
    cid = charts.ORDER[0]
    assert charts.is_campaign_id(cid) is True


def test_is_campaign_id_returns_false_for_practice_charts():
    # Practice chart ids follow the pattern "practice-<d>-<seed>"
    assert charts.is_campaign_id("practice-1-abc") is False
    assert charts.is_campaign_id("practice-5-ZZZ") is False


def test_is_campaign_id_returns_false_for_daily_charts():
    # Daily chart ids follow the pattern "daily-YYYY-MM-DD"
    assert charts.is_campaign_id("daily-2026-10-17") is False


def test_is_campaign_id_returns_false_for_unknown_ids():
    assert charts.is_campaign_id("") is False
    assert charts.is_campaign_id("unknown-chart-99") is False
