import boards
import pytest
import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_board_dimensions_reject_out_of_range():
    """Board rejects dimensions smaller than MIN_SIDE or larger than MAX_SIDE."""
    for size in (3, 10):
        rows = [f"{'A' * size}"] + [f"{'.' * size}"] * (size - 1)
        with pytest.raises(ValueError):
            rules.Board({"id": "t", "rows": rows})


def test_decode_rejects_malformed_inputs():
    """decode returns None for non-strings, too-long strings, and odd-length digit sequences."""
    b = mk(["A.a..", ".....", ".....", "....."])
    assert rules.decode(b, 123) is None
    assert rules.decode(b, "A" + "00" * 1001) is None
    assert rules.decode(b, "A000") is None
    assert rules.decode(b, "A0a") is None


def test_encode_decode_round_trip():
    """encode and decode are inverses for valid layouts."""
    b = boards.ALL_BOARDS[0]
    encoded = rules.encode(b.solution)
    decoded = rules.decode(b, encoded)
    assert decoded == b.solution
