"""Edge-case tests for hints.py public API."""

import charts
import hints


def _rules(cid):
    return charts.rules(cid)


def _chart(cid):
    return charts.BY_ID[cid]


def _letters():
    return charts.LETTERS


def test_pick_returns_none_when_figure_is_complete():
    """pick should return None when drawn matches the figure exactly."""
    cid = "orion"
    rules = _rules(cid)
    chart = _chart(cid)
    letters = _letters()
    figure_indices = {rules.index[tuple(e)] for e in chart["figure"]}
    v = hints.pick(chart, rules, figure_indices, letters)
    assert v is None


def test_pick_with_empty_drawn_returns_a_hint_dict():
    """pick should return a hint dict when no lines are drawn yet."""
    cid = "orion"
    rules = _rules(cid)
    chart = _chart(cid)
    letters = _letters()
    v = hints.pick(chart, rules, set(), letters)
    assert isinstance(v, dict)
    assert "kind" in v and "line" in v and "nudge" in v


def test_pick_with_only_wrong_lines_handles_missing_and_wrong():
    """pick should correctly identify missing figure lines when drawn contains only wrong ones."""
    cid = "orion"
    rules = _rules(cid)
    chart = _chart(cid)
    letters = _letters()
    all_edges = rules.edges
    wrong_line_idx = 0
    for idx, edge in enumerate(all_edges):
        if tuple(edge) not in set(tuple(e) for e in chart["figure"]):
            wrong_line_idx = idx
            break
    v = hints.pick(chart, rules, {wrong_line_idx}, letters)
    assert isinstance(v, dict)
    assert wrong_line_idx in v.get("wrong", [])
    assert len(v["missing"]) > 0


def test_answer_text_with_empty_lists_returns_empty_string():
    """answer_text should return '' when both missing and wrong are empty."""
    rules = _rules("orion")
    letters = _letters()
    text = hints.answer_text(rules, letters, [], [])
    assert text == ""


def test_answer_text_with_single_missing_and_wrong_formats_correctly():
    """answer_text should format one missing and one wrong line correctly."""
    cid = "orion"
    rules = _rules(cid)
    letters = _letters()
    missing = [0]
    wrong = [1] if len(rules.edges) > 1 else []
    text = hints.answer_text(rules, letters, missing, wrong)
    assert "Lines to draw:" in text
    if wrong:
        assert "Lines to erase:" in text


def test_pick_handles_logic_2_chart_with_lookahead():
    """pick should use lookahead for charts marked logic 2 and return a valid hint."""
    cid = "crux"
    rules = _rules(cid)
    chart = _chart(cid)
    letters = _letters()
    v = hints.pick(chart, rules, set(), letters)
    assert isinstance(v, dict)
    assert "kind" in v and "line" in v


def test_kinds_constant_contains_expected_deduction_types():
    """KINDS should be a tuple of the four expected deduction kinds."""
    assert hints.KINDS == ("forced", "bridge", "what-if", "remove")
