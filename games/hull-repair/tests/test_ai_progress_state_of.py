import progress


def test_state_of_returns_patched_status_when_board_is_in_st():
    """When a board id is present in the state dict, state_of returns its stored status (1 for patched)."""
    st = {"air-scrubbers": 1}
    assert progress.state_of(st, "air-scrubbers") == 1


def test_state_of_returns_restored_status_when_board_is_in_st():
    """When a board id is present in the state dict, state_of returns its stored status (2 for restored)."""
    st = {"air-scrubbers": 2}
    assert progress.state_of(st, "air-scrubbers") == 2


def test_state_of_returns_zero_for_unknown_board():
    """When a board id is not in the state dict, state_of returns 0 (open)."""
    st = {"air-scrubbers": 1}
    assert progress.state_of(st, "power-core") == 0


def test_state_of_handles_empty_state_dict():
    """Edge case: an empty state dict should return 0 for any board id."""
    st = {}
    assert progress.state_of(st, "air-scrubbers") == 0
