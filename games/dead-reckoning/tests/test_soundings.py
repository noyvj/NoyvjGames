"""Depth soundings: the depth under a point, a repeatable reading with a bounded error that works in fog, and which charted
areas a reading could have come from."""

import pytest

from chartkit import depth_area
from soundings import OPEN_DEPTH, SOUNDING_ERR_SHARE, depth_at, matching_areas, sounding

BANK = depth_area("bank", "The Bank", 5.0, 6.0, 2.0, 7)
DEEP = depth_area("deep", "The Deep", 5.0, 6.0, 4.0, 10)


def test_depth_area_returns_expected_dict():
    """Test that depth_area returns the expected dictionary structure."""
    result = depth_area("bank", "The Bank", 5.0, 6.0, 2.0, 7)
    expected = {"id": "bank", "kind": "depth", "name": "The Bank", "x": 5.0, "y": 6.0, "r": 2.0, "fathoms": 7}
    assert result == expected


def test_open_water_everywhere_on_a_chart_with_no_depth_areas():
    assert depth_at({}, (0.0, 0.0)) == OPEN_DEPTH == 40
    assert depth_at({"open_depth": 25}, (3.0, 3.0)) == 25


def test_a_point_takes_the_shallowest_area_covering_it_and_the_edge_counts():
    chart = {"depths": [DEEP, BANK], "open_depth": 30}
    assert depth_at(chart, (5.0, 6.0)) == 7          # inside both: the shallower
    assert depth_at(chart, (5.0, 9.0)) == 10         # inside the deep ring only
    assert depth_at(chart, (5.0, 8.0)) == 7          # exactly on the bank's edge
    assert depth_at(chart, (15.0, 15.0)) == 30       # outside both: the chart's open water


@pytest.mark.parametrize("watch", range(12))
def test_a_sounding_is_repeatable_and_within_its_stated_error(watch):
    chart = {"id": "sound-test", "depths": [BANK]}
    pos = (5.0, 6.0)
    first = sounding(chart, pos, watch)
    assert first == sounding(chart, pos, watch)
    assert first["err_pct"] == 10
    assert abs(first["depth"] - 7) <= 7 * SOUNDING_ERR_SHARE + 1


def test_readings_vary_between_watches_and_charts():
    depths = {sounding({"id": cid}, (0.0, 0.0), w)["depth"] for cid in ("a", "b") for w in range(10)}
    assert len(depths) > 1


def test_fog_does_not_stop_a_sounding():
    reading = sounding({"id": "foggy", "fog": True, "depths": [BANK]}, (5.0, 6.0), 1)
    assert isinstance(reading["depth"], int) and reading["depth"] >= 1


def test_a_sounding_never_reads_below_one_fathom():
    shallow = depth_area("flat", "The Flat", 0.0, 0.0, 1.0, 1)
    assert all(sounding({"id": "flat", "depths": [shallow]}, (0.0, 0.0), w)["depth"] >= 1 for w in range(30))


def test_matching_areas_lists_every_place_a_reading_fits():
    chart = {"depths": [BANK, DEEP], "open_depth": 100}
    assert matching_areas(chart, 7) == ["bank"]
    assert matching_areas(chart, 8) == ["bank", "deep"]         # fits both (7 +- 1.7, 10 +- 2): one sounding can be ambiguous
    assert matching_areas(chart, 10) == ["deep"]                # too deep for the bank, the deep's own depth
    assert matching_areas(chart, 20) == []
    assert matching_areas({}, 40) == ["open"]
    assert matching_areas({"depths": [BANK]}, 41) == ["open"]


def test_every_true_reading_matches_the_area_it_came_from():
    chart = {"id": "match", "depths": [BANK, DEEP], "open_depth": 30}
    for pos, area in (((5.0, 6.0), "bank"), ((5.0, 9.5), "deep"), ((15.0, 15.0), "open")):
        for w in range(20):
            assert area in matching_areas(chart, sounding(chart, pos, w)["depth"])
