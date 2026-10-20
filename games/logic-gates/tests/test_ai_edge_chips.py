"""Edge-case tests for chips.py."""


from chips import pins


def test_pins_with_empty_inputs_and_outputs():
    """pins should return an empty list when both ins and outs are empty."""
    empty_chip = {"ins": [], "outs": []}
    assert pins(empty_chip) == []


def test_pins_with_single_pin_each():
    """pins should correctly order the smallest valid chip (one input, one output)."""
    single_chip = {"ins": ["A"], "outs": ["Y"]}
    assert pins(single_chip) == ["A", "Y"]


def test_pins_handles_many_pins():
    """pins should concatenate a large number of inputs and outputs without truncation."""
    many_inputs = [f"in_{i}" for i in range(50)]
    many_outputs = [f"out_{i}" for i in range(50)]
    large_chip = {"ins": many_inputs, "outs": many_outputs}
    result = pins(large_chip)
    assert len(result) == 100
    assert result[:50] == many_inputs
    assert result[50:] == many_outputs


def test_pins_preserves_input_then_output_order():
    """pins must always place all inputs before any outputs, regardless of count."""
    mixed_chip = {"ins": ["Z", "A"], "outs": ["Y", "X"]}
    assert pins(mixed_chip) == ["Z", "A", "Y", "X"]


def test_pins_rejects_missing_ins_key():
    """pins should raise KeyError when 'ins' is missing from the chip definition."""
    no_ins = {"outs": ["Y"]}
    try:
        pins(no_ins)
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_pins_rejects_missing_outs_key():
    """pins should raise KeyError when 'outs' is missing from the chip definition."""
    no_outs = {"ins": ["A"]}
    try:
        pins(no_outs)
        assert False, "Expected KeyError"
    except KeyError:
        pass
