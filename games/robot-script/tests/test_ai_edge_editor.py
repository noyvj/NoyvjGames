import dsl

from editor import Editor, parse_addr


def ed(allow="F L R G P S rep until if A B"):
    return Editor(None, allow)


def test_parse_addr_with_edge_cases():
    """Test parse_addr with empty, None, malformed, and valid deep inputs."""
    assert parse_addr("") is None
    assert parse_addr(None) is None
    assert parse_addr("x/1") is None
    assert parse_addr("main/a") is None
    addr = ("main", 2, 3, 4)
    assert parse_addr("main/2/3/4") == addr


def test_set_count_with_zero_and_negative():
    """Test set_count rejects zero and negative counts, accepts minimum valid."""
    e = ed()
    e.insert(["rep", 3, ["F"]])
    assert not e.set_count(("main", 0), 0)
    assert not e.set_count(("main", 0), -5)
    assert e.set_count(("main", 0), 2) and e.prog["main"][0][1] == 2


def test_remove_out_of_bounds_and_empty():
    """Test remove rejects out-of-bounds indices and missing list/index args."""
    e = ed()
    assert not e.remove(("main",))
    assert not e.remove(("main", 5))
    e.insert("F")
    assert not e.remove(("main", 10))
    assert e.prog["main"] == ["F"]


def test_move_at_boundaries():
    """Test move handles boundary indices and invalid deltas correctly."""
    e = ed()
    for _ in range(3):
        e.insert("F")
    assert e.move(("main", 0), 1)
    assert e.move(("main", 2), -1)
    assert not e.move(("main", 0), -1)
    assert not e.move(("main", 2), 1)


def test_load_invalid_and_empty_programs():
    """Test load rejects invalid structures, accepts valid empty program."""
    e = ed()
    assert not e.load({"A": []})
    assert not e.load({})  # {} is invalid (missing 'main')
    e2 = ed()
    assert e2.load({"main": []})
    assert e2.prog == {"main": []}
    big = {"main": ["F"] * (dsl.MAX_SIZE + 1)}
    assert not e.load(big)


def test_can_insert_exceeds_limits():
    """Test can_insert returns a reason string when program size limit is hit."""
    e = ed()
    for _ in range(dsl.MAX_SIZE):
        e.insert("F")
    reason = e.can_insert("F")
    assert isinstance(reason, str)
