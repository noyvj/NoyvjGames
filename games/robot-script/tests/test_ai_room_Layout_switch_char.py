from room import Layout


def test_switch_char_returns_1_for_sid_0():
    """Normal case: switch id 0 maps to '1'."""
    layout = Layout([">1"])
    assert layout.switch_char(0) == "1"


def test_switch_char_returns_2_for_sid_1():
    """Normal case: switch id 1 maps to '2'."""
    layout = Layout([">2"])
    assert layout.switch_char(1) == "2"


def test_switch_char_returns_3_for_sid_2():
    """Normal case: switch id 2 maps to '3'."""
    layout = Layout([">3"])
    assert layout.switch_char(2) == "3"


def test_switch_char_out_of_range_still_converts():
    """Edge case: sid=3 is outside the game's valid range (0-2), but the method just adds 1."""
    layout = Layout([">1"])
    assert layout.switch_char(3) == "4"
