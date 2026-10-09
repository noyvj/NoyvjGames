"""All 40 levels: the reference solutions solve them, the unlock chain is reachable, par and caps are sane, and checking is a pure
function of the wiring."""

import copy

import pytest

import levels
from check import check_level
from levels import BY_ID, LEVELS, REGISTRY


def test_forty_levels_in_five_chapters_with_unique_ids():
    assert len(LEVELS) == 40
    assert len({lv["id"] for lv in LEVELS}) == 40
    assert [sum(1 for lv in LEVELS if lv["chapter"] == c) for c in range(1, 6)] == [8, 9, 7, 7, 9]
    assert [lv["index"] for lv in LEVELS] == list(range(1, 41))


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv["id"])
def test_the_reference_solution_solves_its_level(level):
    result = check_level(level, level["ref"])
    assert result["ok"], result["message"]
    assert result["right"] == result["total"] > 0


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv["id"])
def test_par_is_the_reference_chip_count_and_the_cap_leaves_room(level):
    assert level["par"] == len(level["ref"]["chips"])
    assert level["cap"] >= level["par"] + 4


@pytest.mark.parametrize("level", LEVELS, ids=lambda lv: lv["id"])
def test_the_reference_uses_only_chips_unlocked_by_other_levels(level):
    assert level["unlock"] not in level["needs"]
    for chip in level["needs"]:
        assert chip in REGISTRY
        assert REGISTRY[chip]["level"] is not None and REGISTRY[chip]["level"] != level["id"]


def test_there_is_a_play_through_in_the_order_the_chips_allow():
    solved, pending = [], list(LEVELS)
    while pending:
        opened = [lv for lv in pending if levels.is_open(lv, solved)]
        assert opened, f"stuck: {[lv['id'] for lv in pending]} wait on chips nobody unlocks"
        for lv in opened:
            solved.append(lv["id"])
            pending.remove(lv)
    assert len(solved) == 40


def test_the_first_level_is_open_from_the_start_and_later_ones_wait_for_their_chips():
    assert levels.is_open(BY_ID["straight-through"], [])
    assert not levels.is_open(BY_ID["invert"], [])
    assert levels.is_open(BY_ID["invert"], ["straight-through"])
    assert levels.missing_chips(BY_ID["full-adder"], []) == ["half_add", "or"]


def test_a_level_never_offers_the_chip_it_hands_out():
    everything = [lv["id"] for lv in LEVELS]
    for lv in LEVELS:
        if lv["unlock"]:
            assert lv["unlock"] not in levels.allowed_chips(lv, everything)


def test_the_chips_are_what_the_levels_built():
    assert levels.CHIP_ORDER[:3] == ["not", "and", "or"]
    assert len(levels.CHIP_ORDER) >= 30 and len(set(levels.CHIP_ORDER)) == len(levels.CHIP_ORDER)
    full = REGISTRY["full_add"]
    assert full["ins"] == ["A", "B", "CIN"] and full["outs"] == ["SUM", "COUT"] and full["kind"] == "net"


def test_checking_is_deterministic_and_ignores_chip_order_and_ids():
    lv = BY_ID["majority"]
    first = check_level(lv, lv["ref"])
    assert check_level(lv, copy.deepcopy(lv["ref"])) == first
    # the same wiring with the chips renumbered gives the same answer
    renum = {c["id"]: 10 - c["id"] for c in lv["ref"]["chips"]}
    chips = [{"id": renum[c["id"]], "type": c["type"]} for c in lv["ref"]["chips"]]
    wires = {}
    for dest, src in lv["ref"]["wires"].items():
        if not dest.startswith("out:"):
            cid, pin = dest.split(".")
            dest = f"{renum[int(cid)]}.{pin}"
        if "." in src and not src.startswith(("in:", "const:")):
            cid, pin = src.split(".")
            src = f"{renum[int(cid)]}.{pin}"
        wires[dest] = src
    assert check_level(lv, {"chips": chips, "wires": wires}) == first


def test_the_big_truth_tables_are_checked_fast():
    import time
    lv = BY_ID["alu"]
    start = time.time()
    check_level(lv, lv["ref"])
    assert time.time() - start < 1.0
    assert check_level(lv, lv["ref"])["total"] == 1024


def test_no_clock_and_no_randomness_in_the_engine():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for banned in ("import random", "import time", "import datetime", "from random", "from time", "from datetime"):
            assert banned not in text, f"{path.name} uses {banned}"
