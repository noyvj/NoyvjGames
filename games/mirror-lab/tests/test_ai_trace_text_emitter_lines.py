"""Tests for trace_text.emitter_lines()."""

import benches
import optics
import trace_text


def test_emitter_lines_returns_one_line_for_single_emitter():
    """Normal case: a bench with one emitter produces exactly one description string."""
    bench = benches.BY_ID["c1-1"]
    lines = trace_text.emitter_lines(bench.board)
    assert len(lines) == 1
    assert lines[0].startswith("Emitter at ")
    assert "sends a white beam" in lines[0]
    assert lines[0].endswith(".")


def test_emitter_lines_formats_coordinates_and_direction_correctly():
    """Normal case: the string matches optics.cell_name and optics.DIR_NAMES exactly."""
    bench = benches.BY_ID["c1-1"]
    r, c, d = bench.board.emitters[0]
    expected = "Emitter at %s sends a white beam %s." % (optics.cell_name(r, c), optics.DIR_NAMES[d])
    lines = trace_text.emitter_lines(bench.board)
    assert lines == [expected]


def test_emitter_lines_handles_empty_emitters():
    """Edge case: a board with no emitters returns an empty list."""
    class FakeBoard:
        emitters = []
    lines = trace_text.emitter_lines(FakeBoard())
    assert lines == []
