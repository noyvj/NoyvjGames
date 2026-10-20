"""Edge-case tests for lang.py: parsing limits, domain normalization, rule evaluation boundaries."""


import lang


def test_parse_rule_rejects_invalid_formats():
    """parse_rule returns None for empty lits, wrong ops count, too many clauses, or unknown clause ids."""
    # Empty lits
    assert lang.parse_rule(lang.NUM, {"lits": [], "ops": []}) is None
    # Ops length mismatch (2 lits need exactly 1 op)
    assert lang.parse_rule(lang.NUM, {"lits": [["even", 0], ["odd", 0]], "ops": ["and", "or"]}) is None
    # Too many clauses (MAX_CLAUSES is 3)
    assert lang.parse_rule(lang.NUM, {"lits": [["even", 0], ["odd", 0], ["prime", 0], ["ge:10", 0]], "ops": ["and", "or", "and"]}) is None
    # Unknown clause id
    assert lang.parse_rule(lang.NUM, {"lits": [["nonexistent", 0]], "ops": []}) is None
    # Empty string raw input
    assert lang.parse_rule(lang.NUM, "") is None
    # None raw input
    assert lang.parse_rule(lang.NUM, None) is None


def test_rule_accepts_boundary_items():
    """rule_accepts correctly evaluates rules on the smallest and largest items of each domain."""
    # NUM: 0 is even, 99 is odd
    rule_even = lang.make_rule([("even", 0)])
    assert lang.rule_accepts(lang.NUM, rule_even, "0") is True
    assert lang.rule_accepts(lang.NUM, rule_even, "99") is False

    # SHAPE: smallest "ccc" (len 3), largest "dddddd" (len 6)
    rule_len4 = lang.make_rule([("len_ge:4", 0)])
    assert lang.rule_accepts(lang.SHAPE, rule_len4, "ccc") is False
    assert lang.rule_accepts(lang.SHAPE, rule_len4, "dddddd") is True

    # GRID: all empty (0 filled), all filled (9 filled)
    rule_count_even = lang.make_rule([("count_even", 0)])
    assert lang.rule_accepts(lang.GRID, rule_count_even, ".........") is True
    assert lang.rule_accepts(lang.GRID, rule_count_even, "#########") is False


def test_first_difference_boundaries():
    """first_difference finds the earliest differing item and respects skip list."""
    rule_a = lang.make_rule([("even", 0)])
    rule_b = lang.make_rule([("even", 1)])

    # Default (no skip) finds the first difference in domain order
    diff = lang.first_difference(lang.NUM, rule_a, rule_b)
    assert diff is not None and int(diff) == 0  # 0 differs (even vs odd)

    # Skipping the differing item should find the next one
    diff2 = lang.first_difference(lang.NUM, rule_a, rule_b, skip=["0"])
    assert diff2 is not None and int(diff2) == 1


def test_families_deduplication_and_order():
    """families returns a deduplicated list of family ids in clause order."""
    # Single clause
    r1 = lang.make_rule([("even", 0)])
    assert lang.families(lang.NUM, r1) == ["parity"]

    # Multiple clauses, same family
    r2 = lang.make_rule([("ge:50", 0), ("ge:60", 0)], ["and"])
    assert lang.families(lang.NUM, r2) == ["size"]

    # Multiple clauses, different families
    r3 = lang.make_rule([("even", 0), ("has:1", 0)], ["and"])
    fams = lang.families(lang.NUM, r3)
    assert "parity" in fams and "digits" in fams
    assert fams.index("parity") < fams.index("digits")


def test_domain_normalize_edge_cases():
    """Domain.normalize handles booleans, out-of-range numbers, leading zeros, and invalid strings."""
    dom = lang.domain(lang.NUM)

    # Boolean is explicitly rejected
    assert dom.normalize(True) is None

    # Out of range (0-99)
    assert dom.normalize(100) is None
    assert dom.normalize(-1) is None

    # Leading zeros are stripped and normalized
    assert dom.normalize("007") == "7"
    assert dom.normalize("0") == "0"

    # Invalid string format
    assert dom.normalize("abc") is None
    assert dom.normalize("12 34") is None
