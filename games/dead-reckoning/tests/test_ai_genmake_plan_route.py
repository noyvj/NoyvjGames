"""Tests for plan_route in genmake.py."""

from geom import dist
from genmake import plan_route


def _make_chart(start, dest, size=20.0, hazards=None, land=None):
    """Construct a minimal chart dict matching plan_route's expectations."""
    return {
        "start": start,
        "dest": dest,
        "size": size,
        "hazards": hazards or [],
        "land": land or [],
    }


def test_plan_route_returns_direct_path_in_open_water():
    """With no obstacles, plan_route should return exactly the start and destination."""
    chart = _make_chart((2.0, 5.0), (18.0, 5.0))
    path = plan_route(chart)
    assert path is not None
    assert len(path) == 2
    assert path[0] == (2.0, 5.0)
    assert path[-1] == (18.0, 5.0)


def test_plan_route_avoids_a_single_hazard():
    """When a hazard sits on the direct line, the route should detour around it."""
    chart = _make_chart(
        (2.0, 5.0),
        (18.0, 5.0),
        hazards=[{"x": 10.0, "y": 5.0, "r": 1.0}],
    )
    path = plan_route(chart)
    assert path is not None
    # The detour must be strictly longer than the straight line distance
    straight_dist = dist((2.0, 5.0), (18.0, 5.0))
    route_len = sum(dist(path[i], path[i - 1]) for i in range(1, len(path)))
    assert route_len > straight_dist + 0.1


def test_plan_route_returns_none_when_completely_blocked():
    """If a land mass spans the entire chart width between start and dest y-levels, it should return None."""
    land = [
        {"poly": [(0.0, 4.5), (0.0, 5.5), (20.0, 5.5), (20.0, 4.5)]},
    ]
    chart = _make_chart(
        (2.0, 5.0),
        (18.0, 5.0),
        size=20.0,
        land=land,
    )
    path = plan_route(chart)
    assert path is None


def test_plan_route_respects_clearance_parameter():
    """A larger clearance should force a wider detour, resulting in a longer or equal route."""
    chart = _make_chart(
        (2.0, 5.0),
        (18.0, 5.0),
        hazards=[{"x": 10.0, "y": 5.0, "r": 1.0}],
    )
    path_tight = plan_route(chart, clearance=0.5)
    path_wide = plan_route(chart, clearance=2.0)

    assert path_tight is not None and path_wide is not None

    len_tight = sum(dist(path_tight[i], path_tight[i - 1]) for i in range(1, len(path_tight)))
    len_wide = sum(dist(path_wide[i], path_wide[i - 1]) for i in range(1, len(path_wide)))

    assert len_tight <= len_wide + 0.1
