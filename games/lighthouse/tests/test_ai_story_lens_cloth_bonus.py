"""Tests for story.lens_cloth_bonus()."""

import story
from state import Keep


def test_lens_cloth_bonus_returns_one_when_active():
    """When the story is on and the lens cloth buff is positive, it returns 1."""
    k = Keep(1)
    k.story["buffs"]["lens_cloth"] = 3
    assert story.lens_cloth_bonus(k) == 1


def test_lens_cloth_bonus_returns_zero_when_inactive():
    """When the story is on but the lens cloth buff is zero, it returns 0."""
    k = Keep(1)
    k.story["buffs"]["lens_cloth"] = 0
    assert story.lens_cloth_bonus(k) == 0


def test_lens_cloth_bonus_returns_zero_when_quiet():
    """When quiet mode is on, it returns 0 regardless of the buff."""
    k = Keep(1)
    k.quiet = True
    k.story["buffs"]["lens_cloth"] = 5
    assert story.lens_cloth_bonus(k) == 0
