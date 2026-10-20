
import pytest

from textplay import play


def test_play_empty_script_returns_empty_log():
    """Empty input should yield an empty log and a fresh board."""
    board, log = play("")
    assert log == []


def test_play_only_comments_and_whitespace_returns_empty_log():
    """Lines with only comments or whitespace should be skipped entirely."""
    board, log = play("# comment\n   \n  # another\n")
    assert log == []


def test_play_show_on_empty_board_produces_rendered_grid():
    """Showing an empty board should return a string containing dots."""
    board, log = play("show")
    assert len(log) == 1 and "." in log[0]


def test_play_crate_refused_when_board_is_full():
    """Placing a crate on a full board should refuse and report it."""
    script = "crate P\n" * 31
    board, log = play(script)
    assert board.is_full()
    assert "refused: the board is full" in log[-1]


def test_play_merge_refuses_out_of_bounds_indices():
    """Merge with indices outside the board should be refused."""
    board, log = play("merge 99 100")
    assert log[0].startswith("refused:")


def test_play_sell_and_broom_refuse_empty_cells():
    """Sell and broom on an empty cell should refuse gracefully."""
    board, log = play("sell 0\nbroom 0")
    assert log[0] == "sell refused: nothing there"
    assert log[1] == "broom refused: nothing there"


def test_play_unknown_command_raises_valueerror():
    """An unrecognized command should raise a ValueError."""
    with pytest.raises(ValueError):
        play("dance")
