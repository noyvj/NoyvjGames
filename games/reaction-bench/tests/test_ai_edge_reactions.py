"""Edge-case tests for reactions.py public functions."""

import reactions


def test_chapter_shelved_with_empty_shelf():
    """Empty shelf should return 0 for any chapter index."""
    assert reactions.chapter_shelved({}, 0) == 0
    assert reactions.chapter_shelved(set(), 1) == 0


def test_chapter_shelved_with_full_shelf():
    """Full shelf should return the total number of reactions in that chapter."""
    full = {r.id for r in reactions.CHAPTERS[0]["reactions"]}
    assert reactions.chapter_shelved(full, 0) == len(reactions.CHAPTERS[0]["reactions"])


def test_chapter_need_clamps_to_open_at():
    """chapter_need should never exceed OPEN_AT (5), even for smallest and largest allowed indices."""
    assert reactions.chapter_need(0) == 5
    assert reactions.chapter_need(len(reactions.CHAPTERS) - 1) == 5


def test_chapter_open_ci_zero_always_true():
    """Chapter 0 is always open regardless of the shelf."""
    assert reactions.chapter_open({}, 0) is True
    assert reactions.chapter_open(set(), 0) is True


def test_chapter_open_requires_five_from_previous():
    """Chapter n opens only when OPEN_AT (5) orders from chapter n-1 are shelved."""
    partial = {reactions.CHAPTERS[0]["reactions"][i].id for i in range(4)}
    assert reactions.chapter_open(partial, 1) is False

    full_five = {reactions.CHAPTERS[0]["reactions"][i].id for i in range(5)}
    assert reactions.chapter_open(full_five, 1) is True


def test_reaction_open_step_two_needs_step_one():
    """A step-two reaction is only open if its chapter is open and its step-one counterpart is on the shelf."""
    step2 = next(r for r in reactions.ALL if r.step == 2)
    assert reactions.reaction_open({}, step2.id) is False

    step1_id = step2.after
    assert step1_id is not None

    # Open the chapter containing step2 by shelving enough from the previous chapter
    shelf = set()
    if step2.chapter > 0:
        prev_ch = reactions.CHAPTERS[step2.chapter - 1]
        for r in prev_ch["reactions"]:
            shelf.add(r.id)
    shelf.add(step1_id)

    assert reactions.reaction_open(shelf, step2.id) is True


def test_route_locked_returns_true_for_waiting_step_two():
    """route_locked should be True for a step-two order whose step-one is not shelved (when its chapter is open)."""
    step2 = next(r for r in reactions.ALL if r.step == 2)

    # Open the chapter containing step2 by shelving enough from previous chapters
    shelf = set()
    for ci in range(step2.chapter):
        for r in reactions.CHAPTERS[ci]["reactions"]:
            shelf.add(r.id)

    assert reactions.route_locked(shelf, step2.id) is True

    # Once step-one is shelved, it should be unlocked
    shelf.add(step2.after)
    assert reactions.route_locked(shelf, step2.id) is False


def test_chapters_done_counts_fully_completed_chapters():
    """chapters_done returns the number of chapters where every reaction is shelved."""
    assert reactions.chapters_done({}) == 0

    c0_full = {r.id for r in reactions.CHAPTERS[0]["reactions"]}
    assert reactions.chapters_done(c0_full) == 1

    all_shelved = {r.id for r in reactions.ALL}
    assert reactions.chapters_done(all_shelved) == len(reactions.CHAPTERS)
