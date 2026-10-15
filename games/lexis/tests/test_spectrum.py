"""Tests for the Spectrum language module."""


def test_react_valid_signal():
    """A valid signal with bands present in stock returns understood=True."""
    from spectrum import react
    result = react("rgb", ["r", "g", "b"])
    assert result.understood is True
    assert "Signal received" in result.text


def test_react_invalid_band():
    """A signal with an unknown band returns understood=False and reason 'unknown_band'."""
    from spectrum import react
    result = react("x", ["r", "g", "b"])
    assert result.understood is False
    assert result.reason == "unknown_band"


def test_react_max_bands():
    """A signal exceeding MAX_BANDS returns understood=False and reason 'too_many_bands'."""
    from spectrum import react, MAX_BANDS
    # Create a string longer than MAX_BANDS
    long_signal = "r" * (MAX_BANDS + 1)
    result = react(long_signal, ["r", "g", "b"])
    assert result.understood is False
    assert result.reason == "too_many_bands"


def test_react_empty_line():
    """An empty line returns understood=False and reason 'empty_line'."""
    from spectrum import react
    result = react("", ["r", "g", "b"])
    assert result.understood is False
    assert result.reason == "empty_line"
