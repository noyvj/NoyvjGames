import star_map


def test_tune_star_valid_smallest_id():
    """Test tuning the first valid star with an empty discovered set."""
    discovered = set()
    result = star_map.tune_star("s1", discovered)
    assert result == {"id": "s1", "x": 2, "y": 3, "strength": 4, "label": "Faint pulse"}
    assert "s1" in discovered


def test_tune_star_valid_largest_id():
    """Test tuning the last valid star."""
    discovered = set()
    result = star_map.tune_star("s8", discovered)
    assert result == {"id": "s8", "x": 4, "y": 5, "strength": 7, "label": "Pulsed carrier"}
    assert "s8" in discovered


def test_tune_star_invalid_id_rejected():
    """Test that an invalid star ID returns None and leaves the discovered set unchanged."""
    initial_discovered = {"s1", "s2"}
    result = star_map.tune_star("nonexistent", initial_discovered)
    assert result is None
    assert initial_discovered == {"s1", "s2"}


def test_tune_star_empty_string_id():
    """Test that an empty string ID is rejected and does not modify the discovered set."""
    discovered = set()
    result = star_map.tune_star("", discovered)
    assert result is None
    assert len(discovered) == 0


def test_tune_star_already_discovered():
    """Test that tuning an already discovered star does not duplicate it in the set."""
    discovered = set()
    star_map.tune_star("s3", discovered)
    assert len(discovered) == 1
    result = star_map.tune_star("s3", discovered)
    assert result is not None
    assert len(discovered) == 1
