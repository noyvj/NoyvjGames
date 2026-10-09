"""Wrong circuits fail with a plain reason, and a loop that never settles is reported, not guessed at."""

from check import check_level
from levels import BY_ID, REGISTRY
from net import parse_circuit


def circuit(level, text):
    return parse_circuit(text, level["ins"], level["outs"], REGISTRY)


def test_an_empty_board_fails_with_a_row_to_look_at():
    lv = BY_ID["both"]
    result = check_level(lv, {"chips": [], "wires": {}})
    assert not result["ok"] and result["right"] == 3 and result["total"] == 4
    assert "lamp Y shows 0 but should show 1" in result["message"]
    assert [r["ok"] for r in result["rows"]] == [True, True, True, False]


def test_a_near_miss_names_the_first_wrong_setting():
    lv = BY_ID["odd-one-out"]
    result = check_level(lv, circuit(lv, "Y := or(A, B)"))
    assert not result["ok"] and result["right"] == 3
    assert "A=1, B=1" in result["message"]


def test_a_sequence_failure_names_the_step_and_lamp():
    lv = BY_ID["toggle"]
    result = check_level(lv, circuit(lv, "Q := dff(1, CLK)"))
    assert not result["ok"]
    assert result["message"].startswith("Step ")
    assert "lamp Q" in result["message"]


def test_an_oscillating_loop_is_reported_unsettled():
    lv = BY_ID["toggle"]
    result = check_level(lv, circuit(lv, "n = not(n); Q := n"))
    assert not result["ok"] and not result["settled"]
    assert "never settles" in result["message"]


def test_every_lamp_must_be_right_not_just_one():
    lv = BY_ID["comparator"]
    result = check_level(lv, circuit(lv, "x = xor(A, B); LT := and(B, x); GT := and(A, x)"))
    assert not result["ok"]


def test_results_list_every_row_of_a_small_table_and_only_the_wrong_ones_of_a_big_one():
    small = check_level(BY_ID["three-keys"], {"chips": [], "wires": {}})
    assert len(small["rows"]) == 8
    big = BY_ID["alu"]
    wrong = check_level(big, {"chips": [], "wires": {}})
    assert len(wrong["rows"]) <= 8 and all(not r["ok"] for r in wrong["rows"])
