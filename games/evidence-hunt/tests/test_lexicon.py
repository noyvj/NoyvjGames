"""The vocabulary: six evidence, twelve kinds with three evidence and two behaviours each, overlapping so one reading never decides alone."""

from itertools import combinations

import lexicon as lx


def test_six_pieces_of_evidence_each_with_its_own_equipment():
    assert len(lx.EVIDENCE) == 6
    assert len(set(lx.GEAR_NAME)) == 6 and len(set(lx.GEAR_LETTER)) == 6 and len(set(lx.EV_NAME)) == 6
    assert set(lx.GEAR_NAME) == {"Thermometer", "EMF reader", "Fine dust", "Violet lamp", "Camera", "Notebook"}
    assert all(lx.POSITIVE[i] and lx.CLEAR[i] and lx.GEAR_HOW[i] for i in range(6))


def test_twelve_kinds_each_three_evidence_and_two_behaviours():
    assert len(lx.KINDS) == 12 and len(set(lx.KIND_IDS)) == 12
    for k in lx.KIND_IDS:
        assert len(lx.KIND_EVIDENCE[k]) == 3
        assert len(lx.KIND_BEHAVIOURS[k]) == 2
        assert lx.KIND_BEHAVIOURS[k] <= set(lx.BH_IDS)
        assert lx.KIND_NOTE[k] and lx.KIND_NAME[k]


def test_no_two_kinds_are_the_same_in_both_evidence_and_behaviour():
    sigs = {(frozenset(lx.KIND_EVIDENCE[k]), lx.KIND_BEHAVIOURS[k]) for k in lx.KIND_IDS}
    assert len(sigs) == 12
    assert len({lx.KIND_EVIDENCE[k] for k in lx.KIND_IDS}) == 12, "every kind has its own set of three evidence"


def test_kinds_overlap_so_deduction_needs_care():
    overlaps = [len(lx.KIND_EVIDENCE[a] & lx.KIND_EVIDENCE[b]) for a, b in combinations(lx.KIND_IDS, 2)]
    assert max(overlaps) == 2 and sum(1 for o in overlaps if o == 2) >= 20
    for e in range(6):
        assert sum(1 for k in lx.KIND_IDS if e in lx.KIND_EVIDENCE[k]) == 6, "each evidence belongs to half of the kinds"


def test_fond_and_roaming_never_go_together():
    assert not any({"fond", "roamer"} <= lx.KIND_BEHAVIOURS[k] for k in lx.KIND_IDS)


def test_each_feature_fools_one_evidence_and_each_evidence_has_a_feature():
    assert sorted(lx.FT_FOOLS.values()) == list(range(6))


def test_keepsakes_and_room_types_are_complete():
    assert len(lx.KEEPSAKES) == 8 and all(lx.KS_RETURN[k] and lx.KS_WHAT[k] for k in lx.KS_IDS)
    assert set(lx.BH_KEEPSAKE) == {"tidy", "mover", "shy", "curious"}
    import houses
    for layout in houses.LAYOUTS:
        for r in houses.rooms_of(layout):
            assert r["type"] in lx.ROOM_TYPES and r["text"]
