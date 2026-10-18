import rules


def test_dir_index_returns_zero_for_up():
    assert rules.dir_index((0, -1)) == 0


def test_dir_index_returns_one_for_right():
    assert rules.dir_index((1, 0)) == 1


def test_dir_index_returns_two_for_down():
    assert rules.dir_index((0, 1)) == 2


def test_dir_index_returns_minus_one_for_unknown_delta():
    assert rules.dir_index((99, 99)) == -1
