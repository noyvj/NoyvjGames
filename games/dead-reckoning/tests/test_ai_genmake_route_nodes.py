from genmake import route_nodes


def test_route_nodes_with_single_hazard():
    # A single circular hazard should produce 8 nodes around it.
    chart = {
        "size": 20,
        "hazards": [{"x": 10.0, "y": 10.0, "r": 1.0}],
        "land": [],
    }
    nodes = route_nodes(chart, clearance=1.0)
    assert len(nodes) == 8
    for n in nodes:
        assert 0.8 <= n[0] <= 19.2
        assert 0.8 <= n[1] <= 19.2


def test_route_nodes_with_land_polygon():
    # A rectangular land mass should produce nodes around each vertex, pushed outward by clearance + 0.4.
    poly = [(5.0, 5.0), (15.0, 5.0), (15.0, 15.0), (5.0, 15.0)]
    chart = {
        "size": 20,
        "hazards": [],
        "land": [{"poly": poly}],
    }
    nodes = route_nodes(chart, clearance=1.0)
    assert len(nodes) == 4
    for n in nodes:
        assert 0.8 <= n[0] <= 19.2
        assert 0.8 <= n[1] <= 19.2


def test_route_nodes_filters_out_of_bounds():
    # Nodes that fall outside the chart margins (0.8 to size-0.8) are filtered out.
    chart = {
        "size": 20,
        "hazards": [{"x": 0.5, "y": 10.0, "r": 0.5}],
        "land": [],
    }
    nodes = route_nodes(chart, clearance=1.0)
    assert all(n[0] >= 0.8 for n in nodes)
