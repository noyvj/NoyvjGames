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


def test_chapter_one_is_seven_flat_straight_rooms():
    ch = rooms.CHAPTER_LIST[0]
    assert len(ch["rooms"]) == 7
    for rid in ch["rooms"]:
        assert "L" not in rooms.BY_ID[rid].allow and "R" not in rooms.BY_ID[rid].allow


def test_engine_modules_have_no_clock_or_random():
    import re
    from pathlib import Path
    for path in Path(rooms.__file__).parent.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random)\b", text, flags=re.M), path.name
