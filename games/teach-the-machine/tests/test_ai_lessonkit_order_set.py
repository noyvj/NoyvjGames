"""Tests for lessonkit.order_set()."""


import lessonkit
import lessons


def test_order_set_preserves_lesson_feature_order():
    """When given a subset of features, order_set returns them in the lesson's defined order."""
    lesson = lessons.BY_ID["lab-samples"]
    fids = lesson["fids"]
    subset = {fids[0], fids[-1]}
    result = lessonkit.order_set(lesson, subset)
    assert result == [fids[0], fids[-1]]


def test_order_set_filters_unknown_ids():
    """order_set drops ids that are not in the lesson's feature list."""
    lesson = lessons.BY_ID["lab-samples"]
    mixed = {lesson["fids"][1], "unknown_feature", lesson["fids"][3]}
    result = lessonkit.order_set(lesson, mixed)
    assert result == [lesson["fids"][1], lesson["fids"][3]]


def test_order_set_handles_empty_input():
    """An empty set of ids should return an empty list."""
    lesson = lessons.BY_ID["lab-samples"]
    result = lessonkit.order_set(lesson, set())
    assert result == []
