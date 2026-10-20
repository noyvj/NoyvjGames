import pytest
from board import Board
from day import Day
from orders import Customer
from rng import Rng

THREE = ["produce", "textiles", "ceramics"]


def C(items, arch="regular", patience=30, name="Tomas"):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience)


def test_summary_handles_zero_total_gracefully():
    """summary() should default to 100% and 3 stars when total is zero."""
    day = Day(1, Board(), [], Rng(1))
    day.total = 0
    assert day.summary()["stars"] == 3 and day.summary()["served"] == 0


def test_summary_stars_boundaries():
    """summary() stars should clamp correctly at the 60% and 90% thresholds."""
    day = Day(1, Board(), [C([("produce", 1)])], Rng(1))
    day.total = 10
    day.served = 5
    assert day.summary()["stars"] == 1  # 50%
    day.served = 6
    assert day.summary()["stars"] == 2  # 60%
    day.served = 8
    assert day.summary()["stars"] == 2  # 80%
    day.served = 9
    assert day.summary()["stars"] == 3  # 90%


def test_deliver_rejects_boolean_and_out_of_bounds_indices():
    """deliver() must reject boolean indices and indices outside the window."""
    day = Day(1, Board.from_text("P1 .. .. .. .."), [C([("produce", 1)])], Rng(1))
    out_bool = day.deliver(0, True)
    assert out_bool["ok"] is False and "nobody" in out_bool["message"].lower()

    out_neg = day.deliver(0, -1)
    assert out_neg["ok"] is False

    out_big = day.deliver(0, 99)
    assert out_big["ok"] is False


def test_broom_rejects_invalid_and_empty_cells():
    """broom() should refuse invalid indices and cells with no good."""
    day = Day(1, Board.from_text("P1 .. .. .. .."), [], Rng(1))
    out_invalid = day.broom(-5)
    assert out_invalid["ok"] is False

    out_empty = day.broom(3)  # cell 3 is empty in the text above
    assert out_empty["ok"] is False and "nothing" in out_empty["message"].lower()


def test_crate_refuses_full_board():
    """crate() must return an error when the counter has no empty cells."""
    board = Board(5, 6)
    for i in range(board.size):
        board.cells[i] = ("produce", 1)
    day = Day(1, board, [], Rng(1))
    out = day.crate("produce")
    assert out["ok"] is False and "full" in out["message"].lower()


def test_from_dict_validates_number_and_total_boundaries():
    """from_dict() should accept boundary values for number and total, but reject out-of-range."""
    rng_data = Rng(1).to_dict()
    base_data = {"board": Board().to_dict(), "queue": [], "rng": rng_data}

    data_min = {**base_data, "number": 1, "total": 1, "served": 1}
    day_min = Day.from_dict(data_min, THREE)
    assert day_min.number == 1 and day_min.total == 1

    data_max = {**base_data, "number": 10**5, "total": 64, "served": 32, "left": 32}
    day_max = Day.from_dict(data_max, THREE)
    assert day_max.number == 10**5 and day_max.total == 64

    data_bad_num = {**base_data, "number": 0, "total": 1}
    with pytest.raises(ValueError):
        Day.from_dict(data_bad_num, THREE)

    data_bad_total = {**base_data, "number": 1, "total": 65}
    with pytest.raises(ValueError):
        Day.from_dict(data_bad_total, THREE)
