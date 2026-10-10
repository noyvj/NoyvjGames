"""Round-4 collector achievements: Codex Keeper, Weather Watcher, Charter Member, The Great Works."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
NEW = ["codex_keeper", "weather_watcher", "charter_member", "great_works"]


def test_catalog_has_the_four_with_checks(game_env):
    m = game_env.module
    ids = [a["id"] for a in json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]]
    assert len(ids) == 30 and len(set(ids)) == 30
    for new in NEW:
        assert new in ids and new in m.ACHIEVEMENT_CHECKS


def test_none_earned_on_a_fresh_game(game_env):
    earned = game_env.module.achievement_ids_earned()
    assert not set(NEW) & set(earned)


def test_each_is_earned_by_its_collection(game_env):
    m = game_env.module
    m.codex_found[:] = [c["id"] for c in m.CLUES]
    m.anomalies_seen.update(a["id"] for a in m.ANOMALIES)
    m.mission_stamps[:] = [x["id"] for x in m.MISSIONS[:5]]
    m.megaprojects_all_ever = True
    assert set(NEW) <= set(m.achievement_ids_earned())


def test_four_stamps_is_not_enough_and_progress_shows(game_env):
    m = game_env.module
    m.mission_stamps[:] = [x["id"] for x in m.MISSIONS[:4]]
    assert "charter_member" not in m.achievement_ids_earned()
    assert m.ACHIEVEMENT_PROGRESS["charter_member"]() == (4, 5)
    assert m.ACHIEVEMENT_PROGRESS["codex_keeper"]() == (0, 7)
    assert m.ACHIEVEMENT_PROGRESS["weather_watcher"]() == (0, 6)


def test_a_prestige_never_unearns_them(game_env):
    m = game_env.module
    m.codex_found[:] = [c["id"] for c in m.CLUES]
    m.anomalies_seen.update(a["id"] for a in m.ANOMALIES)
    m.mission_stamps[:] = [x["id"] for x in m.MISSIONS[:5]]
    m.megaprojects_all_ever = True
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert set(NEW) <= set(m.achievement_ids_earned())
