import boards
import progress


def test_next_board_returns_none_when_all_restored():
    """Edge case: when every board is restored (status 2), next_board returns None."""
    st = {bid: 2 for bid in boards.ORDER}
    assert progress.next_board(st, boards.ORDER[-1]) is None


def test_next_board_returns_immediate_next_open_board():
    """Normal case: if the immediate next board is open (status 0), it is returned."""
    st = {boards.ORDER[0]: 2}
    assert progress.next_board(st, boards.ORDER[0]) == boards.ORDER[1]


def test_next_board_skips_patched_and_restored_boards():
    """Normal case: next_board skips patched (1) and restored (2) boards to find the next open one."""
    st = {boards.ORDER[0]: 2, boards.ORDER[1]: 1}
    assert progress.next_board(st, boards.ORDER[0]) == boards.ORDER[2]
