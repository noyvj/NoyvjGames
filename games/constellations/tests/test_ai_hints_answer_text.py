"""Tests for hints.answer_text()."""


import charts
import hints


def test_answer_text_with_only_missing_lines():
    """Normal case: only lines that need to be drawn are provided."""
    rules = charts.rules(charts.ORDER[0])
    letters = charts.LETTERS
    fig = {tuple(e) for e in charts.BY_ID[charts.ORDER[0]]["figure"]}
    missing_indices = [rules.index[list(fig)[0]], rules.index[list(fig)[1]]]
    text = hints.answer_text(rules, letters, missing_indices, [])
    assert "Lines to draw:" in text
    assert "Lines to erase:" not in text


def test_answer_text_with_only_wrong_lines():
    """Normal case: only lines that need to be erased are provided."""
    rules = charts.rules(charts.ORDER[0])
    letters = charts.LETTERS
    fig = {tuple(e) for e in charts.BY_ID[charts.ORDER[0]]["figure"]}
    wrong_indices = [k for k, e in enumerate(rules.edges) if tuple(e) not in fig][:1]
    text = hints.answer_text(rules, letters, [], wrong_indices)
    assert "Lines to erase:" in text
    assert "Lines to draw:" not in text


def test_answer_text_with_both_missing_and_wrong_lines():
    """Edge case: the player has drawn some correct lines and some incorrect ones."""
    rules = charts.rules(charts.ORDER[0])
    letters = charts.LETTERS
    fig = {tuple(e) for e in charts.BY_ID[charts.ORDER[0]]["figure"]}
    missing_indices = [rules.index[list(fig)[0]]]
    wrong_indices = [k for k, e in enumerate(rules.edges) if tuple(e) not in fig][:1]
    text = hints.answer_text(rules, letters, missing_indices, wrong_indices)
    assert "Lines to draw:" in text and "Lines to erase:" in text
