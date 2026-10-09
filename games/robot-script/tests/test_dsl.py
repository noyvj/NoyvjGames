import pytest

import dsl


def test_text_round_trip_for_every_construct():
    text = "main: F rep 3 { F L } until !blocked { F } if part { G } else { R } call A\nA: F S"
    prog = dsl.from_text(text)
    assert prog["main"][1] == ["rep", 3, ["F", "L"]]
    assert prog["main"][2] == ["until", "!blocked", ["F"]]
    assert prog["main"][3] == ["if", "part", ["G"], ["R"]]
    assert prog["main"][4] == ["call", "A"]
    assert dsl.from_text(dsl.to_text(prog)) == prog


def test_bare_routine_name_is_a_call():
    assert dsl.from_text("main: A\nA: F")["main"] == [["call", "A"]]


def test_size_counts_every_instruction_including_block_headers_and_routines():
    assert dsl.size(dsl.from_text("main: F F F")) == 3
    assert dsl.size(dsl.from_text("main: rep 4 { F L }")) == 3
    assert dsl.size(dsl.from_text("main: if part { G } else { F R }")) == 4
    assert dsl.size(dsl.from_text("main: A A\nA: F F F")) == 5
    assert dsl.size({"main": []}) == 0


def test_uses_lists_constructs():
    assert dsl.uses(dsl.from_text("main: F")) == set()
    assert dsl.uses(dsl.from_text("main: rep 2 { if part { G } } A\nA: until blocked { F }")) == {"rep", "if", "call", "until"}


@pytest.mark.parametrize("bad", [
    "F F", "main: Q", "main: rep 1 { F }", "main: rep 10 { F }", "main: rep x { F }", "main: until sky { F }",
    "main: if part { G", "main: } F", "main: F\nmain: F", "main: call C", "A: call A\nmain: F", "main: A\nA: B\nB: F",
    "main: rep 2 { rep 2 { rep 2 { rep 2 { rep 2 { F } } } } }", "main: until !!blocked { F }", "x" * 5000,
])
def test_bad_text_is_refused(bad):
    assert dsl.parse(bad) is None
    with pytest.raises(ValueError):
        dsl.from_text(bad)


def test_a_can_not_call_but_b_may_call_a():
    assert dsl.parse("main: B\nB: A\nA: F") is not None
    assert dsl.parse("main: A\nA: B\nB: F") is None


def test_list_length_cap():
    assert dsl.parse("main: " + "F " * dsl.MAX_SIZE) is not None
    assert dsl.parse("main: " + "F " * (dsl.MAX_SIZE + 1)) is None


def test_check_respects_what_a_room_allows():
    prog = dsl.from_text("main: F rep 2 { F }")
    assert dsl.check(prog, "F rep") is None
    assert "not available" in dsl.check(prog, "F")
    assert "not available" in dsl.check(dsl.from_text("main: F L"), "F")
    assert "not available" in dsl.check(dsl.from_text("main: A\nA: F"), "F")
    assert dsl.check(dsl.from_text("main: A\nA: F"), "F A") is None


def test_pretty_lines_read_as_plain_words():
    lines = dsl.to_lines(dsl.from_text("main: F rep 2 { G } if part { S } else { R }"))
    assert lines[0] == "Main"
    assert "  Repeat 2 times" in lines and "    Pick up" in lines and "  Otherwise" in lines


def test_copy_is_deep():
    prog = dsl.from_text("main: rep 2 { F }")
    clone = dsl.copy(prog)
    clone["main"][0][2].append("L")
    assert prog["main"][0][2] == ["F"]


def test_an_empty_program_is_valid():
    assert dsl.from_text("") == {"main": []}
