
from deduce_bridge import Reading


def test_role_of_returns_plural_for_p():
    r = Reading("noun_first", (("p", "plural"), ("n", "negate"), ("q", "ask")))
    assert r.role_of("p") == "plural"


def test_role_of_returns_negate_for_n():
    r = Reading("marker_first", (("p", "plural"), ("n", "negate"), ("q", "ask")))
    assert r.role_of("n") == "negate"


def test_role_of_returns_none_for_unknown_letter():
    r = Reading("noun_first", (("p", "plural"), ("n", "negate"), ("q", "ask")))
    assert r.role_of("x") is None
