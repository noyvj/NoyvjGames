"""The rules of one case: the bag, the van, entering rooms, readings, doubtful readings, the keepsake, and naming the spirit."""

import casework as cw
import lexicon as lx
from casekit import C

CASE = cw.Case(C("t-1", "Test House", "villa", "glimmer", ("glimmer", "pacer", "tangle", "scrivener"), (("conservatory", "bedroom"),), kit=2,
                 features={"conservatory": "draught", "kitchen": "wiring"}, keepsake=("bedroom", "handmirror", "curious"),
                 ending="It was a lamp-lighter."))
ROOM = {r["id"]: i for i, r in enumerate(CASE.rooms)}
GLIM, PACER, TANGLE, SCRIV = (lx.KIND_INDEX[k] for k in ("glimmer", "pacer", "tangle", "scrivener"))


def run(*acts):
    st = CASE.new_state()
    infos = []
    for a in acts:
        st2, info = CASE.apply(st, a)
        assert st2 is not None, (a, info)
        st = st2
        infos.append(info)
    return st, infos


def refused(st, act):
    st2, info = CASE.apply(st, act)
    assert st2 is None and info["kind"] == "refused"
    return info["msg"]


def test_the_bag_holds_the_kit_size_and_toggles():
    st, _ = run(("pack", 0), ("pack", 1))
    assert CASE.kit_list(st) == [0, 1]
    assert "holds 2" in refused(st, ("pack", 2))
    st, _ = CASE.apply(st, ("pack", 0))
    assert CASE.kit_list(st) == [1]


def test_walking_is_free_and_marks_restless_or_still():
    st, infos = run(("go", ROOM["conservatory"]), ("go", ROOM["hall"]))
    assert "restless" in infos[0]["msg"] and "still" in infos[1]["msg"]
    assert cw.popcount(st[cw.ENTERED]) == 2 and CASE.total_cost(st) == 0


def test_a_reading_needs_a_room_and_the_equipment_in_the_bag():
    st = CASE.new_state()
    assert "room first" in refused(st, ("use", 3))
    st, _ = run(("go", ROOM["bedroom"]))
    assert "not in the bag" in refused(st, ("use", 3))


def test_readings_are_positive_clear_or_doubtful_and_are_noted_once():
    st, infos = run(("pack", 3), ("pack", 4), ("go", ROOM["conservatory"]), ("use", 3), ("use", 4))
    assert [i["result"] for i in infos[-2:]] == [cw.POSITIVE, cw.POSITIVE]       # glimmer: lights, prints
    assert "already noted" in refused(st, ("use", 3))
    st2, infos2 = CASE.apply(run(("pack", 0), ("go", ROOM["conservatory"]))[0], ("use", 0))
    assert infos2["result"] == cw.DOUBTFUL and "draughty" in infos2["msg"] and "doubtful" in infos2["msg"]   # the draught fools cold here


def test_the_keepsake_room_makes_every_reading_doubtful_and_looking_adds_testimony():
    st, infos = run(("pack", 3), ("go", ROOM["bedroom"]), ("use", 3))
    assert infos[-1]["result"] == cw.DOUBTFUL and "hand mirror" in infos[-1]["msg"]
    assert refused(CASE.new_state(), ("look",))
    st, infos = run(("go", ROOM["bedroom"]), ("look",))
    assert "faces the door" in infos[-1]["msg"] and CASE.testimony(st, 0) == ["curious"]
    assert refused(st, ("look",))


def test_the_bag_locks_after_a_reading_and_the_van_costs_a_trip():
    st, _ = run(("pack", 3), ("go", ROOM["conservatory"]), ("use", 3))
    assert "locked" in refused(st, ("pack", 4))
    st2, info = CASE.apply(st, ("van",))
    assert st2[cw.TRIPS] == 2 and CASE.total_cost(st2) == 1 and st2[cw.KIT] == 0 and st2[cw.ROOM] == -1
    assert st2[cw.NOTES] == st[cw.NOTES], "the notebook keeps every reading"
    free, _ = CASE.apply(run(("pack", 3))[0], ("van",))
    assert free[cw.TRIPS] == 1, "emptying the bag before any reading is free"


def test_candidates_follow_the_notebook():
    st, _ = run(("go", ROOM["conservatory"]), ("go", ROOM["bedroom"]), ("look",), ("pack", 3), ("pack", 4), ("go", ROOM["conservatory"]), ("use", 3), ("use", 4))
    assert CASE.candidates(st, 0) == ["glimmer"]          # curious (the mirror) leaves three; prints are only glimmer's of those


def test_a_roaming_kind_is_ruled_out_when_only_one_restless_room_turns_up():
    one = cw.Case(C("t-2", "T", "cottage", "hearthkeeper", ("hearthkeeper", "candlewick", "glimmer"), (("parlour",),), kit=3))
    st = one.new_state()
    for r in range(len(one.rooms)):
        st, _ = one.apply(st, ("go", r))
    assert set(one.candidates(st, 0)) == {"hearthkeeper", "candlewick"}


def test_naming_the_spirit_wrong_costs_one_and_changes_nothing_else():
    st, _ = run(("go", ROOM["conservatory"]))
    wrong, info = CASE.apply(st, ("accuse", PACER))
    assert info["kind"] == "wrong" and wrong[cw.WRONG] == 1 and not wrong[cw.SOLVED]
    assert wrong[cw.NOTES] == st[cw.NOTES] and wrong[cw.ENTERED] == st[cw.ENTERED]
    right, info = CASE.apply(wrong, ("accuse", GLIM))
    assert right[cw.SOLVED] and info["msg"].endswith("It was a lamp-lighter.") and CASE.total_cost(right) == 1
    assert cw.grade_of(CASE.total_cost(right)) == 2


def test_only_kinds_on_the_sheet_can_be_named_and_a_solved_case_takes_no_more_actions():
    st = CASE.new_state()
    assert "not on the sheet" in refused(st, ("accuse", lx.KIND_INDEX["hushling"]))
    done, _ = CASE.apply(st, ("accuse", GLIM))
    assert "solved" in refused(done, ("go", 0))


def test_returning_the_keepsake_only_after_the_case_is_solved():
    assert "nothing to return" in refused(CASE.new_state(), ("return",))
    done, _ = CASE.apply(CASE.new_state(), ("accuse", GLIM))
    home, info = CASE.apply(done, ("return",))
    assert home[cw.RETURNED] and "hand mirror" in info["msg"]
    assert "already home" in refused(home, ("return",))


def test_the_same_actions_always_give_the_same_state_and_tokens_round_trip():
    acts = [("pack", 3), ("go", ROOM["conservatory"]), ("use", 3), ("accuse", GLIM)]
    a, _ = run(*acts)
    b, _ = cw.replay(CASE, [cw.to_token(x) for x in acts])
    assert a == b
    for act in acts + [("van",), ("look",), ("cover",), ("return",), ("accuse", 1, 2)]:
        assert cw.from_token(cw.to_token(act)) == act
    assert cw.from_token("nonsense") is None and cw.from_token("go:x") is None and cw.from_token("go") is None and cw.from_token(5) is None
    assert cw.replay(CASE, ["go:99"])[0] is None


def test_covering_the_sheet_toggles_and_is_allowed_after_solving():
    st, _ = run(("cover",))
    assert st[cw.COVERED] == 1
    again, _ = CASE.apply(st, ("cover",))
    assert again[cw.COVERED] == 0
