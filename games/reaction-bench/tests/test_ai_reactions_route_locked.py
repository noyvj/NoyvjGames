"""Tests for route_locked() in reactions.py."""

import reactions


def _find_step_two_reaction():
    """Return a step-two reaction object from the game data."""
    for r in reactions.ALL:
        if r.step == 2:
            return r
    raise RuntimeError("No step-two reaction found in game data")


def test_route_locked_returns_true_when_step_one_is_missing():
    """Step-two order in an open chapter, but step-one is not on the shelf."""
    r = _find_step_two_reaction()
    # Build a shelf that opens the chapter by shelving all orders from previous chapters.
    shelf = {prev_r.id: 1 for ci in range(r.chapter) for prev_r in reactions.CHAPTERS[ci]["reactions"]}

    assert reactions.route_locked(shelf, r.id) is True


def test_route_locked_returns_false_when_step_one_is_shelved():
    """Step-two order in an open chapter, step-one IS on the shelf."""
    r = _find_step_two_reaction()
    shelf = {prev_r.id: 1 for ci in range(r.chapter) for prev_r in reactions.CHAPTERS[ci]["reactions"]}
    shelf[r.after] = 1  # Add the required step-one order

    assert reactions.route_locked(shelf, r.id) is False


def test_route_locked_returns_false_when_chapter_is_closed():
    """Step-two order whose chapter is not yet open."""
    r = _find_step_two_reaction()
    if r.chapter == 0:
        # Fallback: find a step-2 in a later chapter
        for alt_r in reactions.ALL:
            if alt_r.step == 2 and alt_r.chapter > 0:
                r = alt_r
                break

    assert reactions.route_locked({}, r.id) is False
