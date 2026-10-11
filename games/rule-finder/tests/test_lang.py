"""The rule language: items, clauses, rules, tables and the one judge of whether two rules agree."""

import re
from pathlib import Path

import lang

GAME_DIR = Path(__file__).resolve().parent.parent


def test_the_three_domains_have_the_stated_sizes_and_orders():
    assert lang.domain("num").items == [str(n) for n in range(100)]
    shapes = lang.domain("shape")
    assert shapes.size == 4 ** 3 + 4 ** 4 + 4 ** 5 + 4 ** 6 and shapes.items[0] == "ccc" and shapes.items[-1] == "d" * 6
    assert [len(k) for k in shapes.items] == sorted(len(k) for k in shapes.items)
    grid = lang.domain("grid")
    assert grid.size == 512 and grid.items[0] == "." * 9 and grid.items[-1] == "#" * 9
    for dom in (lang.domain(k) for k in lang.KINDS):
        assert len(set(dom.items)) == dom.size and dom.full == (1 << dom.size) - 1


def test_items_are_normalised_or_refused():
    n = lang.domain("num")
    assert n.normalize(42) == "42" and n.normalize("042") == "42" and n.normalize("7") == "7"
    for bad in (-1, 100, "100", "a", "", True, 4.5, None, [4], "٣"):
        assert n.normalize(bad) is None, bad
    s = lang.domain("shape")
    assert s.normalize("cst") == "cst" and s.normalize("cs") is None and s.normalize("cstdcst") is None and s.normalize("cxt") is None
    g = lang.domain("grid")
    assert g.normalize("#........") == "#........" and g.normalize("#.......") is None and g.normalize("#.......x") is None and g.normalize(5) is None


def test_every_clause_has_words_a_family_and_works_on_every_item():
    for kind in lang.KINDS:
        dom = lang.domain(kind)
        seen = set()
        for c in dom.clauses:
            assert c.id not in seen
            seen.add(c.id)
            assert c.family in lang.FAMILIES and c.yes and c.no and c.yes != c.no
            assert re.match(r"^[a-z0-9_:]+$", c.id)
            table = dom.table(c.id)
            assert 0 < table < dom.full, "%s %s accepts everything or nothing" % (kind, c.id)


def test_no_two_clauses_are_the_same_table_so_the_menu_has_no_twins():
    for kind in lang.KINDS:
        dom = lang.domain(kind)
        tables = {}
        for c in dom.clauses:
            for table, name in ((dom.table(c.id), c.id), (dom.full ^ dom.table(c.id), "not " + c.id)):
                assert table not in tables, "%s: %s is the same as %s" % (kind, name, tables[table])
                tables[table] = name


def test_number_clauses_say_what_they_mean():
    d = lang.domain("num")

    def has(cid, n):
        return bool(d.table(cid) >> n & 1)
    assert has("even", 0) and has("even", 98) and not has("even", 7)
    assert has("ge:50", 50) and not has("ge:50", 49)
    assert has("mult:7", 63) and not has("mult:7", 64)
    assert has("has:7", 7) and has("has:7", 70) and has("has:7", 97) and not has("has:7", 8)
    assert has("square", 0) and has("square", 81) and not has("square", 82)
    assert has("prime", 2) and has("prime", 97) and not has("prime", 1) and not has("prime", 91) and not has("prime", 0)
    assert [n for n in range(100) if has("prime", n)] == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
    assert has("tens_gt", 52) and not has("tens_gt", 25) and not has("tens_gt", 55) and not has("tens_gt", 5)
    assert has("ones_gt", 25) and has("ones_gt", 5) and not has("ones_gt", 52)
    assert has("dsum_even", 11) and not has("dsum_even", 12) and has("dsum_ge:10", 55) and not has("dsum_ge:10", 54)


def test_shape_clauses_say_what_they_mean():
    d = lang.domain("shape")

    def has(cid, s):
        return bool(d.table(cid) >> d.index[s] & 1)
    assert has("pair", "csttc") and not has("pair", "cstc")
    assert has("mirror", "cstsc") and not has("mirror", "cstc")
    assert has("up", "cst") and has("up", "cstd") and not has("up", "cct") and not has("up", "tsc")
    assert has("nodown", "cct") and not has("nodown", "cts")
    assert has("down", "dtsc") and has("noup", "ddtc") and not has("noup", "ccd")
    assert has("kinds_ge:3", "cstt") and not has("kinds_ge:3", "csss")
    assert has("next:cd", "sdcs") and has("next:cd", "scds") and not has("next:cd", "cstd")
    assert has("first:s", "scc") and has("last:d", "ccd") and has("ends_same", "cstc") and has("twice:c", "cscs") and not has("twice:c", "csst")
    assert has("len_even", "cstd") and not has("len_even", "cst") and has("len_ge:5", "cstdc") and not has("len_ge:5", "cstd")


def test_grid_clauses_say_what_they_mean():
    d = lang.domain("grid")

    def has(cid, key):
        return bool(d.table(cid) >> d.index[key] & 1)
    assert has("row", "###......") and not has("row", "##.##.#..") and has("col", "#..#..#..") and has("diag", "#...#...#")
    assert has("sym_lr", "#.#.#.#.#") and not has("sym_lr", "##.......") and has("sym_tb", "###...###") and has("sym_turn", "##.....##")
    assert has("centre", "....#....") and has("corners_ge:2", "#.#......") and not has("corners_ge:2", "#........")
    assert has("empty:top", "...###...") and has("empty:left", ".#..#..#.") and not has("empty:left", "#........")
    assert has("touch", "##.......") and has("touch", "#..#.....") and not has("touch", "#...#....")
    assert has("top_more", "###......") and not has("top_more", "###...###") and has("left_more", "#..#..#..")
    assert has("count_ge:5", "#####....") and not has("count_ge:5", "####.....") and has("count_even", "##.......")


def test_rules_read_left_to_right_and_negation_is_per_clause():
    num = lambda s: lang.parse_rule("num", s)       # noqa: E731
    t = lambda s: lang.rule_table("num", num(s))    # noqa: E731
    d = lang.domain("num")
    assert t("even") == d.table("even") and t("~even") == d.full ^ d.table("even")
    assert t("even&ge:50") == d.table("even") & d.table("ge:50")
    assert t("even|ge:50") == d.table("even") | d.table("ge:50")
    assert t("even&ge:50|has:7") == (d.table("even") & d.table("ge:50")) | d.table("has:7")
    assert t("has:7|even&ge:50") == (d.table("has:7") | d.table("even")) & d.table("ge:50")
    assert t("~even&~ge:50") == d.full ^ (d.table("even") | d.table("ge:50"))
    for text in ("even&ge:50", "~mult:3|has:7&~even", "prime"):
        r = num(text)
        assert lang.encode_rule(r) == text and lang.parse_rule("num", lang.rule_json(r)) == r
        table = lang.rule_table("num", r)
        assert all(lang.rule_accepts("num", r, k) == bool(table >> i & 1) for i, k in enumerate(d.items))


def test_bad_rules_are_refused():
    for bad in ("", "nope", "even&", "&even", "even&&ge:50", "~~even", "even&even&even&even", "has:0", "pair", None, 5, [], {},
                {"lits": []}, {"lits": [["even", 0], ["ge:50", 0]]}, {"lits": [["even", 0], ["ge:50", 0]], "ops": ["xor"]},
                {"lits": [["even", 0]], "ops": ["and"]}, {"lits": [[5, 0]]}, {"lits": [["even", "no"]]}, {"lits": "even"}, {"lits": [["even"]]}):
        assert lang.parse_rule("num", bad) is None, bad
    assert lang.parse_rule("shape", "even") is None and lang.parse_rule("shape", "pair") is not None


def test_two_rules_agree_only_when_they_agree_on_every_item():
    a, b = lang.parse_rule("num", "mult:3"), lang.parse_rule("num", "mult:3&~mult:9|mult:9")
    assert lang.agree("num", a, b) and lang.first_difference("num", a, b) is None
    c = lang.parse_rule("num", "mult:3&~has:7")
    assert not lang.agree("num", a, c)
    assert lang.first_difference("num", a, c) == "27"
    assert lang.first_difference("num", a, c, skip=["27"]) == "57"
    assert lang.first_difference("num", lang.parse_rule("num", "even"), lang.parse_rule("num", "~even")) == "0"


def test_words_read_as_plain_sentences():
    assert lang.rule_words("num", lang.parse_rule("num", "even")) == "A number goes Through if it is even."
    assert lang.rule_words("num", lang.parse_rule("num", "even&~mult:4")) == "A number goes Through if it is even and it is not a multiple of 4."
    assert lang.rule_words("num", lang.parse_rule("num", "ge:50&even|has:7")) == "A number goes Through if (it is 50 or more and it is even) or it has a 7 in it."
    assert lang.rule_words("num", lang.parse_rule("num", "ge:50&even&has:7")) == "A number goes Through if it is 50 or more and it is even and it has a 7 in it."
    assert lang.rule_words("shape", lang.parse_rule("shape", "pair")).startswith("A string goes Through if")
    assert lang.rule_words("grid", lang.parse_rule("grid", "~touch")).startswith("A pattern goes Through if")
    assert lang.item_words("shape", "cstd") == "circle square triangle diamond"
    assert lang.item_words("num", "7") == "7"
    assert lang.item_words("grid", "#........").startswith("1 filled: row 1 filled empty empty")


def test_the_menu_groups_every_clause_once_by_family():
    for kind in lang.KINDS:
        groups = lang.menu(kind)
        ids = [c["id"] for g in groups for c in g["clauses"]]
        assert ids == lang.domain(kind).clause_ids
        assert len({g["family"] for g in groups}) == len(groups), "a family appears twice in the menu"


def test_families_are_listed_in_order_without_repeats():
    assert lang.families("num", lang.parse_rule("num", "even&~ge:50|mult:3")) == ["parity", "size", "multiples"]
    assert lang.families("num", lang.parse_rule("num", "even&~mult:4")) == ["parity", "multiples"]
    assert lang.uses_not(lang.parse_rule("num", "even&~ge:50")) and not lang.uses_not(lang.parse_rule("num", "even&ge:50"))


def test_the_language_module_reads_no_clock_and_no_random_source():
    text = (GAME_DIR / "lang.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M)
