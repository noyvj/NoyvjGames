"""The lexicon is hand-written data, so check its internal promises."""

import lexicon as lx


def test_every_reference_in_the_lexicon_exists():
    for c in lx.COND.values():
        assert c["signs"] <= set(lx.SIGN_IDS), c["id"]
        assert c["findings"] <= set(lx.TEST_IDS), c["id"]
        assert all(t in lx.TX_BY_ID for t in c["cures"]) and c["ease"] in lx.TX_BY_ID, c["id"]
        assert c["ease"] not in c["cures"], c["id"]
    for t in lx.TEST_BY_ID.values():
        assert t["item"] in lx.ITEM_NAME
    for t in lx.TX_BY_ID.values():
        assert t["item"] in lx.ITEM_NAME
        assert t["tags"] <= {tag for tag, _n in lx.TRAITS.values()}
    assert lx.BAND_ITEM in lx.ITEM_NAME


def test_every_condition_has_two_cures_with_different_tags_so_a_chart_note_never_blocks_all_cures():
    for c in lx.COND.values():
        assert len(c["cures"]) == 2, c["id"]
        a, b = (lx.TX_BY_ID[t]["tags"] for t in c["cures"])
        for trait, (tag, _text) in lx.TRAITS.items():
            assert not (tag in a and tag in b), (c["id"], trait)


def test_conditions_with_the_same_signs_are_told_apart_by_their_scans():
    groups = {}
    for c in lx.COND.values():
        groups.setdefault(c["signs"], []).append(c)
    for signs, members in groups.items():
        readings = [c["findings"] for c in members]
        assert len({frozenset(r) for r in readings}) == len(members), sorted(signs)


def test_names_are_unique_and_only_contagious_conditions_show_flecks():
    names = [c["name"] for c in lx.COND.values()]
    assert len(names) == len(set(names))
    assert len(lx.COND) >= 30
    for c in lx.COND.values():
        if c["spreads"]:
            assert lx.FLECKS in c["signs"], c["id"]


def test_supplies_have_distinct_letters_so_a_shelf_is_never_told_apart_by_colour():
    glyphs = list(lx.ITEM_GLYPH.values())
    assert len(glyphs) == len(set(glyphs))


def test_shared_shelves_exist_for_the_shared_supplies_chapter():
    users = {}
    for t in lx.TEST_BY_ID.values():
        users.setdefault(t["item"], []).append(t["name"])
    for t in lx.TX_BY_ID.values():
        users.setdefault(t["item"], []).append(t["name"])
    shared = {i for i, names in users.items() if len(names) > 1}
    assert {"roll", "vials"} <= shared
