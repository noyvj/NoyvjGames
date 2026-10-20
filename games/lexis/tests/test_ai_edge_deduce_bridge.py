
from bridge_scenes import bridge_scenes
from deduce_bridge import all_readings, consistent_readings, determinate, disagreements, evaluate


def test_all_readings_yields_expected_count():
    """all_readings yields exactly 4^3 * 2 = 128 combinations."""
    readings = list(all_readings())
    assert len(readings) == 128


def test_evaluate_empty_message_returns_original_stock():
    """evaluate with an empty message leaves stock unchanged and returns empty reply."""
    start = bridge_scenes()[0].before
    r = next(all_readings())
    got_stock, reply = evaluate(r, "", start)
    assert got_stock == start
    assert reply == ""


def test_consistent_readings_empty_scenes_returns_all():
    """consistent_readings with no scenes returns every possible reading."""
    assert len(consistent_readings([])) == 128


def test_determinate_false_for_insufficient_scenes():
    """determinate is False when scenes do not settle the language (e.g., empty list)."""
    assert determinate([]) is False


def test_disagreements_empty_on_full_curriculum():
    """disagreements returns an empty list when the full curriculum settles the language."""
    assert disagreements(bridge_scenes()) == []


def test_reading_role_of_unknown_letter_returns_none():
    """role_of returns None for letters not assigned in the reading."""
    r = next(all_readings())
    assert r.role_of("z") is None
