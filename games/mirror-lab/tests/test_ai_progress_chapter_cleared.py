"""Tests for progress.chapter_cleared()."""

import json

import benches
import game
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def setup_function(_fn):
    game.game.__init__()


def test_chapter_cleared_partial_counts_correctly():
    """Clearing some benches in a chapter returns the exact count of cleared benches."""
    ch_benches = benches.CHAPTERS[0]["benches"]
    for b in ch_benches[:3]:
        game.game.cleared[b.id] = b.solution_layout()
    assert progress.chapter_cleared(game.game.cleared, 1) == 3


def test_chapter_cleared_all_benches_in_chapter_returns_total():
    """Clearing every bench in a chapter returns the total number of benches in that chapter."""
    ch5 = benches.CHAPTERS[4]["benches"]
    for b in ch5:
        game.game.cleared[b.id] = b.solution_layout()
    assert progress.chapter_cleared(game.game.cleared, 5) == len(ch5)


def test_chapter_cleared_empty_returns_zero():
    """When no benches are cleared, every chapter reports zero."""
    assert progress.chapter_cleared({}, 1) == 0
    assert progress.chapter_cleared({}, 5) == 0


def test_chapter_cleared_zero_wraps_to_last():
    """Passing 0 wraps to the last chapter due to Python list indexing, returning 0 for an empty cleared dict."""
    assert progress.chapter_cleared({}, 0) == 0
