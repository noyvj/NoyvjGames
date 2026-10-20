"""Edge-case tests for trace_text.py (QI-10-edge). Tests limits of public functions using real bench data and minimal mocks."""


import types

import benches
import trace_text


def mock_trace(lit=None, dark_hit=None, hits=None):
    """Create a minimal trace-like object with the attributes trace_text expects."""
    return types.SimpleNamespace(
        lit=frozenset() if lit is None else set(lit),
        dark_hit=frozenset() if dark_hit is None else set(dark_hit),
        hits=hits or {}
    )


def test_sensors_count_handles_zero_lit_and_singular_need():
    """sensors_count(0, 1) should return '0 of 1 sensor'."""
    result = trace_text.sensors_count(0, 1)
    assert result == "0 of 1 sensor"


def test_sensors_count_handles_plural_when_needed_exceeds_one():
    """sensors_count(5, 3) should use plural 'sensors'."""
    result = trace_text.sensors_count(5, 3)
    assert result == "5 of 3 sensors"


def test_brief_handles_bench_with_no_decoys_and_singular_sensor():
    """brief on c1-1 (no decoys, 1 sensor) should format correctly without decoy mentions."""
    bench = benches.BY_ID["c1-1"]
    text = trace_text.brief(bench)
    assert "decoy" not in text
    assert "Light the sensor." in text


def test_brief_handles_multiple_decoys():
    """brief on a bench with multiple decoys should use plural 'decoys'."""
    bench = benches.BY_ID["c4-3"]
    text = trace_text.brief(bench)
    if len(bench.board.decoys) > 1:
        assert "decoys" in text


def test_emitter_lines_handles_empty_emitter_list():
    """emitter_lines on a board with no emitters should return an empty list."""
    board = types.SimpleNamespace(emitters=[])
    result = trace_text.emitter_lines(board)
    assert result == []


def test_sensor_lines_handles_trace_with_no_lit_or_hit_sensors():
    """sensor_lines with an empty trace should mark all sensors as 'dark'."""
    bench = benches.BY_ID["c1-1"]
    tr = mock_trace()
    lines = trace_text.sensor_lines(bench.board, tr)
    for line in lines:
        assert line["lit"] is False
        assert line["hit"] is False
        assert "dark" in line["words"]


def test_bench_label_handles_empty_layout():
    """bench_label with an empty layout list should say '0 pieces placed'."""
    bench = benches.BY_ID["c1-1"]
    tr = mock_trace()
    result = trace_text.bench_label(bench, tr, [])
    assert "0 pieces placed" in result
