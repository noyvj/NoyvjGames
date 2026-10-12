"""Tests for the confirm stamp feature (R4-PX-28)."""
import json

from game import handle


def test_confirm_action_returns_stamp_flag():
    """Calling confirm should return a confirm_stamp flag."""
    result = json.loads(handle(json.dumps({"action": "confirm", "forms": ["0101"]})))
    assert "confirm_stamp" in result
    assert result["confirm_stamp"] is True


def test_non_confirm_action_omits_stamp_flag():
    """Other actions should not include the confirm_stamp flag."""
    result = json.loads(handle(json.dumps({"action": "open"})))
    assert "confirm_stamp" not in result
