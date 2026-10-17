"""Tests for trace_text.sensor_lines()."""

import benches
from trace_text import sensor_lines


class MockTrace:
    """Minimal mock of the trace result object."""

    def __init__(self, lit=None, dark_hit=None, hits=None):
        self.lit = set(lit) if lit else set()
        self.dark_hit = set(dark_hit) if dark_hit else set()
        self.hits = dict(hits) if hits else {}


def test_all_sensors_lit():
    """Verify that all sensors report as lit when the trace covers them."""
    board = benches.BY_ID["c1-1"].board
    tr = MockTrace(lit=board.sensors.keys())
    lines = sensor_lines(board, tr)
    assert len(lines) == len(board.sensors)
    for line in lines:
        assert line["lit"] is True
        assert line["hit"] is False
        assert "dark" not in line["text"].lower()


def test_mixed_sensor_states():
    """Verify correct reporting for a mix of lit, wrong-kind, and dark sensors."""
    board = benches.BY_ID["c1-1"].board
    keys = list(board.sensors.keys())
    lit_keys = keys[:len(keys) // 2] if len(keys) > 1 else keys
    wrong_kind_keys = [k for k in keys if k not in lit_keys][:1]
    tr = MockTrace(lit=lit_keys, hits={k: ["S"] for k in wrong_kind_keys})
    lines = sensor_lines(board, tr)
    for line in lines:
        r, c = line["r"], line["c"]
        if (r, c) in lit_keys:
            assert line["lit"] is True
        elif (r, c) in wrong_kind_keys:
            assert "wrong kind" in line["text"]
        else:
            assert line["lit"] is False
            assert "dark" in line["text"]


def test_decoy_sensor_states():
    """Verify that decoy sensors report correctly when lit versus dark."""
    class MockBoard:
        def __init__(self):
            self.sensors = {(0, 0): "A", (1, 1): "X"}

    board = MockBoard()

    tr_lit = MockTrace(lit=set(), dark_hit={(1, 1)})
    lines_lit = sensor_lines(board, tr_lit)
    decoy_line = next(line for line in lines_lit if line["need"] == "X")
    assert "lit, which is wrong" in decoy_line["text"]

    tr_dark = MockTrace(lit=set(), dark_hit=set())
    lines_dark = sensor_lines(board, tr_dark)
    decoy_line = next(line for line in lines_dark if line["need"] == "X")
    assert "dark, good" in decoy_line["text"]
