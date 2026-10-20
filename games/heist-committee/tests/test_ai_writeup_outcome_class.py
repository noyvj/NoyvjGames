import writeup

CREW = ("dot", "pip", "bea", "tomasz", "hank")


def test_clean_outcome_returns_clean_when_escaped_and_no_alarm(C):
    """Normal case: escaped without alarm yields 'clean'."""
    outcome = {"escaped": True, "alarm": False}
    assert writeup.outcome_class(outcome) == "clean"


def test_loud_outcome_returns_loud_when_escaped_with_alarm(C):
    """Normal case: escaped with alarm yields 'loud'."""
    outcome = {"escaped": True, "alarm": True}
    assert writeup.outcome_class(outcome) == "loud"


def test_stranded_outcome_returns_stranded_when_stranded_is_true(C):
    """Edge case: stranded flag overrides bust even without escaping."""
    outcome = {"escaped": False, "stranded": True}
    assert writeup.outcome_class(outcome) == "stranded"


def test_bust_outcome_returns_bust_by_default(C):
    """Default case: no escape and no stranded yields 'bust'."""
    outcome = {"escaped": False}
    assert writeup.outcome_class(outcome) == "bust"
