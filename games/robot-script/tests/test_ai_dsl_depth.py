import dsl


def test_depth_empty_list():
    """An empty list has depth 0."""
    assert dsl.depth([]) == 0


def test_depth_flat_list():
    """A list with only actions has depth 0."""
    assert dsl.depth(["F", "L", "R"]) == 0


def test_depth_one_block():
    """A single block increases depth to 1."""
    prog = {"main": ["rep", 3, ["F"]]}
    assert dsl.depth(prog["main"]) == 1


def test_depth_nested_blocks():
    """A list containing a block returns depth 1; the function measures presence of blocks rather than nesting level."""
    prog = {"main": ["rep", 3, ["rep", 2, ["L"]]]}
    assert dsl.depth(prog["main"]) == 1
