import dsl
import rooms
import run
from solver import shortest

import pytest

IDS = rooms.ORDER


def test_ids_unique_and_nonempty():
    assert len(IDS) == len(set(IDS)) and IDS


@pytest.mark.parametrize("rid", IDS)
def test_reference_solution_clears_the_room_at_par(rid):
    r = rooms.BY_ID[rid]
    assert dsl.check(r.ref, r.allow) is None, "the reference may only use what the room allows"
    result = run.run(r.layout, r.ref)
    assert result.status == "cleared", result.message
    assert dsl.size(r.ref) == r.par


@pytest.mark.parametrize("rid", IDS)
def test_flat_rooms_have_the_true_minimum_as_par(rid):
    r = rooms.BY_ID[rid]
    if dsl.allowed_ops(r.allow) & {"rep", "until", "if", "A", "B"}:
        pytest.skip("loops: par is the reference length")
    best = shortest(r.layout, [a for a in "FLRGPS" if a in r.allow])
    assert best is not None and len(best) == r.par, (best, r.par)


@pytest.mark.parametrize("rid", IDS)
def test_room_text_is_present_and_plain(rid):
    r = rooms.BY_ID[rid]
    assert r.name and r.nudge and r.nudge.endswith(".")
    assert "—" not in r.nudge + r.intro      # no em dashes in game text


def test_medal_thresholds():
    assert [rooms.medal(10, s) for s in (3, 10, 11, 13, 14, 40)] == [3, 3, 2, 2, 1, 1]
    assert rooms.silver_limit(3) == 5 and rooms.silver_limit(30) == 40


def test_every_chapter_has_rooms_and_each_room_belongs_to_one():
    seen = []
    for c in rooms.CHAPTER_LIST:
        assert c["rooms"]
        seen += c["rooms"]
    assert seen == IDS


def test_chapter_one_is_flat_and_turning_comes_in_from_room_four():
    """AN-4 (owner answer Rs4): rooms 1-3 are straight lines with no turning; from room 4 the toolbox holds Left and Right."""
    ch = rooms.CHAPTER_LIST[0]
    assert len(ch["rooms"]) == 9
    for number, rid in enumerate(ch["rooms"], start=1):
        r = rooms.BY_ID[rid]
        assert not dsl.allowed_ops(r.allow) & {"rep", "until", "if", "A", "B"}, rid
        has_turns = {"L", "R"} <= dsl.allowed_ops(r.allow)
        assert has_turns == (number >= 4), (number, rid)
    assert ch["rooms"][3] == "face-the-pad" and ch["rooms"][4] == "left-at-the-corner"


def test_the_two_new_turning_rooms_really_need_a_turn_and_teach_one_each():
    right = rooms.BY_ID["face-the-pad"]
    left = rooms.BY_ID["left-at-the-corner"]
    assert "R" in right.ref_text and "L" not in right.ref_text.replace("Left", "")
    assert "L" in left.ref_text.split(":")[1].split() and "R" not in left.ref_text.split(":")[1].split()
    for r in (right, left):
        flat = shortest(r.layout, [a for a in "FLRGPS" if a in r.allow])
        assert len(flat) == r.par and ("L" in flat or "R" in flat)
        assert shortest(r.layout, ["F"]) is None, "going straight must not clear a turning room"


def test_the_older_chapter_one_rooms_keep_their_ids_and_layouts_so_old_bests_still_clear():
    keep = {"first-switch": "main: F F S F F F", "first-delivery": "main: F F G F F P F F",
            "in-order": "main: F G F F S F F P F F", "the-shaft": "main: F S F F F G F S F F P F F"}
    for rid, old_list in keep.items():
        r = rooms.BY_ID[rid]
        assert run.run(r.layout, dsl.from_text(old_list)).status == "cleared", rid


def test_engine_modules_have_no_clock_or_random():
    import re
    from pathlib import Path
    for path in Path(rooms.__file__).parent.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random)\b", text, flags=re.M), path.name
