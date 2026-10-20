import logbook


def test_line_for_returns_correct_log_entry():
    """Test that line_for returns the correct log entry for a valid board ID."""
    assert logbook.line_for("airlock-two") == "Cycled by hand again. The sensor lies about the seal, so we stopped trusting it and started trusting each other. That went fine until it didn't. - Pell, dock tech"


def test_line_for_returns_empty_string_for_invalid_board_id():
    """Test that line_for returns an empty string for a board ID that doesn't exist."""
    assert logbook.line_for("nonexistent-board") == ""


def test_line_for_returns_log_for_practice_board():
    """Test that line_for returns the correct log entry for a practice board."""
    assert logbook.line_for("spare-valve-closet") == "A shelf of valves, every one tagged 'tested'. I tested one. The tag is a promise, not a measurement. - Fenn"
