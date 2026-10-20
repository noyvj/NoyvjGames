import writeup


def test_plural_returns_singular_for_one():
    """plural(1, 'lock') should return '1 lock'."""
    assert writeup.plural(1, "lock") == "1 lock"


def test_plural_returns_plural_for_two():
    """plural(2, 'problem') should return '2 problems'."""
    assert writeup.plural(2, "problem") == "2 problems"


def test_plural_returns_plural_for_many():
    """plural(5, 'alarm') should return '5 alarms'."""
    assert writeup.plural(5, "alarm") == "5 alarms"


def test_plural_handles_zero_as_plural():
    """plural(0, 'clue') should return '0 clues' (adds 's' for any n != 1)."""
    assert writeup.plural(0, "clue") == "0 clues"
