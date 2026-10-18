"""Tests for Case.room_text() in casework.py."""

import casework as cw
import cases
import progress


def test_room_text_normal_still():
    """A normal, non-restless room says it is still."""
    case = cw.Case(cases.ALL[0])
    # Pick a room that is not in any restless slot to ensure it says "still"
    all_slot_rooms = {r for slot in case.slots for r in slot}
    still_room = next(r for r in range(len(case.rooms)) if r not in all_slot_rooms)
    text = case.room_text(still_room)
    assert "This room is still." in text
    assert "The air here is restless." not in text


def test_room_text_restless():
    """A restless room says the air is restless."""
    case = cw.Case(cases.ALL[1])
    if not case.slots:
        case = cw.Case(progress.DATA[progress.CHAPTERS[2]["cases"][0]])
    slot_room = case.slots[0][0]
    text = case.room_text(slot_room)
    assert "The air here is restless." in text
    assert "This room is still." not in text


def test_room_text_keepsake_edge():
    """The keepsake room appends the keepsake prompt."""
    # Chapter 3 cases all have a keepsake
    case = cw.Case(progress.DATA[progress.CHAPTERS[3]["cases"][0]])
    text = case.room_text(case.keep_room)
    assert "sits here. Look at it." in text
