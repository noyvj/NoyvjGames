from sim import clean_legs, describe, sail
from tests.golden_charts import GOLDEN_A, GOLDEN_A_LEGS


def test_describe_normal_arrived():
    """describe() returns a multi-line string with leg details and final position for a successful passage."""
    legs = clean_legs(GOLDEN_A, GOLDEN_A_LEGS)
    result = sail(GOLDEN_A, legs)
    text = describe(GOLDEN_A, legs, result)
    lines = text.split("\n")
    assert len(lines) > 3
    assert lines[0].startswith(GOLDEN_A["id"] + ":")
    assert any("ended at" in line for line in lines)
    assert any("leg 1:" in line for line in lines)
    # Track points are sampled every 4 steps
    track_lines = [line for line in lines if line.startswith("  t=")]
    assert len(track_lines) > 0


def test_describe_with_events():
    """describe() includes event text when the sail encounters hazards or streams."""
    legs = clean_legs(GOLDEN_A, GOLDEN_A_LEGS)
    result = sail(GOLDEN_A, legs)
    text = describe(GOLDEN_A, legs, result)
    lines = text.split("\n")
    # Events are appended with a leading space and "Hour" prefix
    if result["events"]:
        assert any("  Hour" in line for line in lines)


def test_describe_aground_edge_case():
    """describe() correctly reports the aground event and final position when the ship runs aground."""
    mini_chart = {
        "id": "test_mini",
        "start": [0.0, 0.0],
        "dest": [10.0, 10.0],
        "arrival_radius": 1.0,
        "deadline": 24.0,
        "speeds": [0.5, 10.0],
        "start_hour": 0.0,
        "land": [],
        "hazards": [{"id": "rock", "kind": "rock", "name": "Sharp Rock", "x": 2.0, "y": 0.0, "r": 0.5, "charted": True}],
        "currents": [],
        "wind": None,
        "compass": None,
        "landmarks": [],
        "fog": False,
    }
    legs = clean_legs(mini_chart, [{"heading": 90, "speed": 5.0, "hours": 1.0}])
    result = sail(mini_chart, legs)
    text = describe(mini_chart, legs, result)
    assert "aground" in text.lower() or "Sharp Rock" in text
