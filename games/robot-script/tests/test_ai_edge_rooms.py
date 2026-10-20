import rooms


def test_silver_limit_with_zero_and_small_pars():
    """silver_limit should return at least par + 2, even when par is 0."""
    assert rooms.silver_limit(0) == 2
    assert rooms.silver_limit(1) == 3
    assert rooms.silver_limit(10) == 13


def test_medal_returns_gold_when_size_equals_par():
    """A run exactly at par should always earn gold (3)."""
    assert rooms.medal(5, 5) == 3
    assert rooms.medal(0, 0) == 3


def test_medal_returns_silver_at_boundary():
    """Size equal to silver_limit should yield silver (2), one over yields bronze."""
    par = 10
    limit = rooms.silver_limit(par)
    assert rooms.medal(par, limit) == 2
    assert rooms.medal(par, limit + 1) == 1


def test_limits_for_zero_par():
    """limits should handle par=0 gracefully for all difficulties."""
    assert rooms.limits(0, "easy") == (2, 4)
    assert rooms.limits(0, "normal") == (0, 2)
    assert rooms.limits(0, "hard") == (0, 1)


def test_medal_for_hard_boundary():
    """Hard silver limit is par + max(1, par // 6). Test at and over boundary."""
    par = 7
    gold, silver = rooms.limits(par, "hard")
    assert gold == par
    assert silver == par + 1
    assert rooms.medal_for(par, silver, "hard") == 2
    assert rooms.medal_for(par, silver + 1, "hard") == 1


def test_medal_for_easy_boundary():
    """Easy loosens both bars by exactly EASY_EXTRA (2)."""
    par = 5
    gold, silver = rooms.limits(par, "easy")
    assert gold == par + 2
    assert silver == rooms.silver_limit(par) + 2
    assert rooms.medal_for(par, gold, "easy") == 3
    assert rooms.medal_for(par, gold + 1, "easy") == 2


def test_medal_with_actual_room_par():
    """Use a real room's par to ensure the functions work with game data."""
    room = rooms.ALL_ROOMS[0]
    assert rooms.medal(room.par, room.par) == 3
    assert rooms.medal(room.par, room.silver) == 2
    assert rooms.medal(room.par, room.silver + 1) == 1
