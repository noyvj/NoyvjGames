"""G23: the persistent multi-session climate archive."""

import json
import sys


class FakeStorage:
    def __init__(self, initial=None):
        self.data = dict(initial or {})
        self.writes = 0

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.data[key] = value
        self.writes += 1


def _install_storage(game_env, initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def test_starts_blank_without_storage(game_env):
    m = game_env.module
    for label in "ABC":
        assert m.climate_archive[label] == {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}


def test_panel_hidden_until_toggled(game_env):
    panel = game_env.elements["archive-panel"]
    game_env.module.render()
    assert panel.hidden is True
    game_env.elements["archive-toggle-button"].dispatch("click", None)
    assert panel.hidden is False
    assert "Hide" in game_env.elements["archive-toggle-button"].innerText
    game_env.elements["archive-toggle-button"].dispatch("click", None)
    assert panel.hidden is True


def test_rows_show_each_region(game_env):
    m = game_env.module
    m.climate_archive["B"]["best_saved"] = 4.25
    m.render()
    text = game_env.elements["archive-row-b"].innerText
    assert "Region B" in text and "4.2" in text or "4.3" in text
    assert "Region A" in game_env.elements["archive-row-a"].innerText
    assert "Region C" in game_env.elements["archive-row-c"].innerText


def test_records_improve_and_persist(game_env):
    m = game_env.module
    storage = _install_storage(game_env)
    m.region_b.capacity["preserve"] = 6
    m.region_b.temperature = 14.0
    m.region_b.counterfactual_temperature = 20.0
    m.region_b.round_number = 9
    m.render()
    entry = m.climate_archive["B"]
    assert entry["best_saved"] == 6.0
    assert entry["furthest_round"] == 9
    assert abs(entry["peak_dampening"] - 0.48) < 1e-9
    assert storage.writes >= 1
    stored = json.loads(storage.data[m.ARCHIVE_STORAGE_KEY])
    assert stored["B"]["best_saved"] == 6.0


def test_records_never_go_down(game_env):
    m = game_env.module
    _install_storage(game_env)
    m.climate_archive["A"] = {"best_saved": 10.0, "furthest_round": 50, "peak_dampening": 0.8}
    m.render()  # the live (fresh) region A is far below every record
    assert m.climate_archive["A"] == {"best_saved": 10.0, "furthest_round": 50, "peak_dampening": 0.8}


def test_no_write_when_nothing_improved(game_env):
    m = game_env.module
    storage = _install_storage(game_env)
    m.render()
    m.render()
    assert storage.writes == 0


def test_loads_a_stored_archive(game_env):
    m = game_env.module
    _install_storage(game_env, {m.ARCHIVE_STORAGE_KEY: json.dumps(
        {"A": {"best_saved": 3.5, "furthest_round": 12, "peak_dampening": 0.4}}
    )})
    archive = m.load_climate_archive()
    assert archive["A"] == {"best_saved": 3.5, "furthest_round": 12, "peak_dampening": 0.4}
    assert archive["B"] == {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}


def test_malformed_storage_falls_back_to_blank(game_env):
    m = game_env.module
    blank = {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}
    for raw in ("not json", "[]", "7", "null", json.dumps({"A": "x", "B": [1], "C": None})):
        _install_storage(game_env, {m.ARCHIVE_STORAGE_KEY: raw})
        assert m.load_climate_archive() == {"A": blank, "B": blank, "C": blank}


def test_bad_field_values_are_reset_individually(game_env):
    m = game_env.module
    entry = m._clean_archive_entry({"best_saved": -3, "furthest_round": True, "peak_dampening": 5})
    assert entry == {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}
    entry = m._clean_archive_entry({"best_saved": float("nan"), "furthest_round": 0, "peak_dampening": float("inf")})
    assert entry == {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}
    entry = m._clean_archive_entry({"best_saved": 2.0, "furthest_round": "9", "peak_dampening": 0.3})
    assert entry == {"best_saved": 2.0, "furthest_round": 1, "peak_dampening": 0.3}


def test_archive_is_not_part_of_the_save(game_env):
    data = game_env.module.get_state()
    assert "climate_archive" not in data and "archive" not in data


def test_region_d_has_no_entry(game_env):
    assert set(game_env.module.climate_archive) == {"A", "B", "C"}
