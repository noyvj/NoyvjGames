"""Tests for reaction_open() in reactions.py."""

import reactions


def test_chapter_0_reaction_is_always_open():
    """A chapter-0 order is open regardless of what is on the shelf."""
    assert reactions.reaction_open({}, "carbon-dioxide") is True
    assert reactions.reaction_open({"water": 1}, "carbon-dioxide") is True


def test_chapter_1_reaction_opens_after_five_from_chapter_0():
    """A chapter-1 order opens only when at least five orders from chapter 0 are shelved."""
    shelf_few = {"carbon-dioxide", "table-salt"}
    assert reactions.reaction_open(shelf_few, "methane") is False

    shelf_enough = {"carbon-dioxide", "table-salt", "water", "magnesium-oxide", "rust"}
    assert reactions.reaction_open(shelf_enough, "methane") is True


def test_step_2_reaction_requires_step_1_on_shelf():
    """A step-two order in an open chapter requires its step-one partner on the shelf."""
    step2_reactions = [r for r in reactions.ALL if getattr(r, "step", 0) == 2]
    assert len(step2_reactions) > 0, "Test requires at least one step-2 reaction in the data"
    rid = step2_reactions[0].id
    step1_id = step2_reactions[0].after

    # Build a shelf that opens chapter 4 (where step-2 reactions live) by satisfying all gates.
    shelf_open_ch4 = set(r.id for r in reactions.CHAPTERS[3]["reactions"][:5]) | \
        set(r.id for r in reactions.CHAPTERS[2]["reactions"][:5]) | \
        set(r.id for r in reactions.CHAPTERS[1]["reactions"][:5]) | \
        set(r.id for r in reactions.CHAPTERS[0]["reactions"][:5])

    shelf_no_step1 = shelf_open_ch4
    assert reactions.reaction_open(shelf_no_step1, rid) is False

    shelf_with_step1 = shelf_open_ch4 | {step1_id}
    assert reactions.reaction_open(shelf_with_step1, rid) is True
