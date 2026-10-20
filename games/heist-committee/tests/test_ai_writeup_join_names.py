import writeup


def test_join_names_two_people():
    """Two names joined with ' and '."""
    assert writeup.join_names(["dot", "pip"]) == "dot and pip"


def test_join_names_three_people():
    """Three names joined with commas and ' and ' before the last."""
    assert writeup.join_names(["dot", "pip", "bea"]) == "dot, pip and bea"


def test_join_names_single_person():
    """A single name is returned unchanged (no comma or 'and')."""
    assert writeup.join_names(["hank"]) == "hank"


def test_join_names_empty_list():
    """An empty list returns an empty string."""
    assert writeup.join_names([]) == ""
