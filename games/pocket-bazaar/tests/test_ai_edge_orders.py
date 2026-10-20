
from orders import Customer, patience_for, order_is_reachable
from board import Board


def test_patience_for_clamps_to_minimum_with_empty_items():
    """patience_for should never return less than 6, even with an empty order."""
    assert patience_for([], "regular", 100) == 6


def test_pay_returns_minimum_when_only_done_is_true_and_nothing_is_done():
    """pay should return at least 1 coin when only_done is True but no items are marked done."""
    c = Customer("A", "regular", [["produce", 1, 0], ["textiles", 2, 0]], 30)
    assert c.pay(only_done=True) == 1


def test_tip_boundary_requires_exactly_half_patience_left():
    """tip should be zero if patience left is strictly less than half of max, and positive otherwise."""
    c = Customer("A", "regular", [["produce", 1, 0]], 10)
    c.left = 4
    assert c.tip() == 0
    c.left = 5
    assert c.tip() > 0


def test_match_exact_mode_rejects_better_tiers():
    """A Critic's match should return None when offered a better tier of the same family."""
    c = Customer("A", "critic", [["produce", 2, 0]], 30)
    assert c.match(("produce", 3)) is None


def test_tourist_fill_updates_the_handed_over_tier():
    """Filling a Tourist's order should update the item's tier to match what was handed over."""
    c = Customer("A", "tourist", [["produce", 1, 0]], 30)
    c.fill(0, ("produce", 4))
    assert c.items[0][1] == 4


def test_order_is_reachable_succeeds_on_small_board_with_enough_cells():
    """order_is_reachable returns True if the board has enough total cells, even if narrow."""
    c = Customer("A", "regular", [["produce", 5, 0]], 30)
    assert order_is_reachable(c, Board(3, 3)) is True
    assert order_is_reachable(c, Board(8, 8)) is True
