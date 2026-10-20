"""Tests for story.meet()."""

import lore
import story
from state import Keep


def test_meet_adds_sailor_to_meta_met():
    """Normal case: sailor not yet in meta, should be appended."""
    k = Keep(1)
    sid = "new_sailor"
    assert sid not in k.meta["story"]["met"]
    story.meet(k, sid)
    assert sid in k.meta["story"]["met"]


def test_meet_initializes_story_met_count():
    """Normal case: sailor not yet in story met, should default to 0."""
    k = Keep(1)
    sid = "another_sailor"
    assert sid not in k.story["met"]
    story.meet(k, sid)
    assert k.story["met"][sid] == 0


def test_meet_does_not_duplicate_in_meta_met():
    """Edge case: sailor already in meta met should not be appended again."""
    k = Keep(1)
    sid = "old_sailor"
    k.meta["story"]["met"].append(sid)
    story.meet(k, sid)
    assert k.meta["story"]["met"].count(sid) == 1


def test_meet_with_real_sailor_id():
    """Normal case: works with a real sailor ID from lore data."""
    k = Keep(2)
    sid = lore.SAILOR_ORDER[0]
    story.meet(k, sid)
    assert sid in k.meta["story"]["met"] and k.story["met"][sid] == 0
