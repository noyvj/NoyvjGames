"""Tests for chapter_cleared() in charts.py."""

import charts


def test_chapter_cleared_counts_charts_with_stars():
    # Normal case: some charts cleared, some not
    chapter = charts.CHAPTERS[0]
    c1 = chapter["charts"][0]["id"]
    c2 = chapter["charts"][1]["id"] if len(chapter["charts"]) > 1 else None
    records = {c1: {"stars": 2}}
    if c2 is not None:
        records[c2] = {"stars": 0}
    assert charts.chapter_cleared(chapter, records) == 1


def test_chapter_cleared_all_cleared():
    # Normal case: all charts in the chapter have at least one star
    chapter = charts.CHAPTERS[0]
    records = {c["id"]: {"stars": 1} for c in chapter["charts"]}
    assert charts.chapter_cleared(chapter, records) == len(chapter["charts"])


def test_chapter_cleared_no_records():
    # Edge case: empty records dict
    chapter = charts.CHAPTERS[0]
    assert charts.chapter_cleared(chapter, {}) == 0
