"""Tests for charts.packs_for()."""

import gen
import daily
import charts


def test_packs_for_normal_practice_chart():
    cid = gen.chart_id(3, 100)
    assert charts.packs_for(cid) == [charts.PRACTICE_PACK]


def test_packs_for_two_ships_practice_chart():
    chart = gen.make_chart(3, 42, two=True)
    assert chart is not None
    cid = chart["id"]
    assert charts.packs_for(cid) == [charts.PRACTICE_PACK, charts.TWO_SHIPS_PACK]


def test_packs_for_daily_chart():
    did = "daily-2026-10-17"
    assert daily.is_daily_id(did)
    assert charts.packs_for(did) == [charts.PRACTICE_PACK]


def test_packs_for_campaign_chart():
    cid = next(iter(charts.CHARTS))
    chapter = charts.CHAPTER_OF.get(cid)
    if chapter:
        expected_pack = charts._BY_ID[chapter]["pack"]
        expected = [expected_pack] if expected_pack else []
        assert charts.packs_for(cid) == expected


def test_packs_for_unknown_chart():
    assert charts.packs_for("bogus-chart") == []
