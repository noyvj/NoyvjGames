"""Tests for trace_text.bench_label()."""

import benches
import trace_text


def mock_tr(lit):
    class Tr:
        pass
    tr = Tr()
    tr.lit = lit
    return tr


def test_bench_label_single_piece_no_lit_sensors():
    bench = benches.BY_ID["c1-1"]
    tr = mock_tr(set())
    layout = [{"r": 0, "c": 1}]
    n = len(bench.board.required)
    label = trace_text.bench_label(bench, tr, layout)
    expected = "Optics bench %s, %d by %d. 0 of %d sensor%s lit. 1 piece placed." % (
        bench.name, bench.board.w, bench.board.h, n, "" if n == 1 else "s"
    )
    assert label == expected


def test_bench_label_multiple_pieces_with_lit_sensors():
    bench = benches.BY_ID["c2-1"]
    tr = mock_tr({(0, 0), (1, 1)})
    layout = [{"r": 0, "c": 0}, {"r": 1, "c": 1}]
    n = len(bench.board.required)
    label = trace_text.bench_label(bench, tr, layout)
    assert "2 of %d sensor%s lit." % (n, "" if n == 1 else "s") in label
    assert "2 pieces placed." in label


def test_bench_label_edge_case_empty_layout():
    bench = benches.BY_ID["c1-1"]
    tr = mock_tr(set())
    layout = []
    n = len(bench.board.required)
    label = trace_text.bench_label(bench, tr, layout)
    assert "0 of %d sensor%s lit." % (n, "" if n == 1 else "s") in label
    assert "0 pieces placed." in label
