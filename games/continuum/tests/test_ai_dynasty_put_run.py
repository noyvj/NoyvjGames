"""Tests for dynasty.put_run()."""


import dynasty


def test_put_run_sets_dynastry_run_when_non_default():
    """Normal case: puts a non-default run into ui and returns it."""
    ui = {}
    run_data = {"banked": 5, "counted": True}
    result = dynasty.put_run(ui, run_data)
    assert ui["dynasty_run"] == result
    assert result["banked"] == 5
    assert result["counted"] is True


def test_put_run_removes_key_when_run_is_default():
    """Normal case: removes the key when the run equals the default."""
    ui = {"dynasty_run": {"banked": 10}}
    default_run = {"banked": 0, "counted": False, "start": False, "failed": False}
    result = dynasty.put_run(ui, default_run)
    assert "dynasty_run" not in ui
    assert result == default_run


def test_put_run_handles_non_dict_input_gracefully():
    """Edge case: cleans non-dict input to default and removes any existing key."""
    ui = {"dynasty_run": {"banked": 1}}
    result = dynasty.put_run(ui, None)
    assert "dynasty_run" not in ui
    assert result["banked"] == 0 and result["counted"] is False
