"""I29: reaching Thriving once gives every LATER region a small integration bonus."""

import sys

import pytest


class FakeStorage:
    def __init__(self, initial=None):
        self.data = dict(initial or {})
        self.writes = 0

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.data[key] = value
        self.writes += 1


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def test_starts_without_the_bonus(game_env):
    m = game_env.module
    assert m.cross_region_learning is False and m.region.learning_active is False


def test_thriving_records_the_flag_and_persists_it(game_env):
    m = game_env.module
    storage = _storage()
    m.region.thriving_round = 12
    m.render()
    assert m.cross_region_learning is True
    assert storage.data[m.LEARNING_STORAGE_KEY] == "1"


def test_the_earning_region_does_not_double_dip(game_env):
    m = game_env.module
    _storage()
    m.region.thriving_round = 5
    m.render()
    assert m.region.learning_active is False


def test_a_new_region_after_the_unlock_gets_the_bonus(game_env):
    m = game_env.module
    m.cross_region_learning = True
    fresh = m.RegionState()
    assert fresh.learning_active is True


def test_bonus_speeds_up_integration_by_exactly_the_bonus(game_env):
    m = game_env.module
    r = m.region
    r.capacity["services"] = 20.0
    r.total_arrivals = 1000.0
    base = r.integration_this_round()
    r.learning_active = True
    assert r.integration_this_round() == pytest.approx(base * (1 + m.LEARNING_INTEGRATION_BONUS))


def test_bonus_stacks_additively_with_language_access(game_env):
    m = game_env.module
    r = m.region
    r.capacity["services"] = 20.0
    r.total_arrivals = 1000.0
    base = r.integration_this_round()
    r.learning_active = True
    r.policy_level["language_access"] = 2
    assert r.integration_this_round() == pytest.approx(base * (1 + m.LEARNING_INTEGRATION_BONUS + 0.30))


def test_a_stored_flag_is_read_on_load(game_env):
    m = game_env.module
    _storage({m.LEARNING_STORAGE_KEY: "1"})
    assert m._load_cross_region_learning() is True
    _storage({m.LEARNING_STORAGE_KEY: "0"})
    assert m._load_cross_region_learning() is False
    _storage({m.LEARNING_STORAGE_KEY: "garbage"})
    assert m._load_cross_region_learning() is False


def test_missing_storage_is_harmless(game_env):
    m = game_env.module
    sys.modules["js"].localStorage = None
    assert m._load_cross_region_learning() is False


def test_storage_that_throws_is_harmless(game_env):
    m = game_env.module

    class Exploding:
        def getItem(self, key):
            raise RuntimeError("blocked")

    sys.modules["js"].localStorage = Exploding()
    assert m._load_cross_region_learning() is False


def test_display_text_for_each_state(game_env):
    m = game_env.module
    _storage()
    m.render()
    assert "Bring any region to Thriving" in game_env.elements["learning-display"].innerText
    m.cross_region_learning = True
    m.render()
    assert "every region you start from now on" in game_env.elements["learning-display"].innerText
    m.region.learning_active = True
    m.render()
    assert "Lessons from an earlier thriving region" in game_env.elements["learning-display"].innerText


def test_the_flag_is_not_part_of_the_save_but_the_regions_state_is(game_env):
    m = game_env.module
    assert "cross_region_learning" not in m.get_state()
    assert "learning_active" not in m.get_state()
    m.region.learning_active = True
    data = m.get_state()
    assert data["learning_active"] is True
    m.region.learning_active = False
    m.load_state(data)
    assert m.region.learning_active is True


def test_a_save_without_the_key_loads_as_no_bonus(game_env):
    m = game_env.module
    m.region.learning_active = True
    data = m.get_state()
    del data["learning_active"]
    m.load_state(data)
    assert m.region.learning_active is False
    for bad in ("yes", 1, None, [True]):
        data["learning_active"] = bad
        m.load_state(data)
        assert m.region.learning_active is False


def test_no_write_once_already_unlocked(game_env):
    m = game_env.module
    storage = _storage()
    m.cross_region_learning = True
    m.region.thriving_round = 3
    m.render()
    assert storage.writes == 0
