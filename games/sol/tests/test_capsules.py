"""A-17 (Time Capsules and the sandbox branch) and A-18 (the diff against a capsule)."""

import copy
import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _panel_text(env):
    return "\n".join(t for t in _texts(env.elements["capsules-panel"]) if t)


def _open(env):
    env.elements["capsules-toggle-button"].dispatch("click")


def _a_busy_game(env):
    """Two worlds with machines, routes and some banked resources, so a branch has something to do."""
    env.unlock_tier(1)
    env.earth.update({"resource_count": 4000.0, "generator_count": 12, "recycler_count": 3})
    env.mars.update({"resource_count": 900.0, "generator_count": 4, "recycler_count": 1, "ecology_health": 70.0})
    env.earth["trade_routes"] = {"Mars": 2}


# --- freezing ------------------------------------------------------------------------------


def test_freezing_keeps_a_named_copy_and_never_touches_the_game(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    before = json.dumps(m.serialize_state(), sort_keys=True)
    capsule = m.freeze_capsule("  Before   the   Belt  ")
    assert capsule["name"] == "Before the Belt" and capsule["tick"] == m.total_ticks
    assert capsule["metrics"]["worlds"] == 3 and capsule["metrics"]["machines"] == 12 + 3 + 4 + 1
    assert capsule["planets"]["Earth"]["generator_count"] == 12
    assert json.dumps(m.serialize_state(), sort_keys=True) == before
    game_env.earth["generator_count"] = 99  # the capsule is a copy, not a view
    assert capsule["planets"]["Earth"]["generator_count"] == 12


def test_a_blank_name_gets_a_default_and_long_names_are_cut(game_env):
    m = game_env.module
    assert m.freeze_capsule("")["name"].startswith("Capsule 1 at ")
    assert len(m.freeze_capsule("x" * 100)["name"]) == m.CAPSULE_NAME_MAX


def test_at_most_three_capsules_and_deleting_makes_room(game_env):
    m = game_env.module
    first = m.freeze_capsule("a")
    m.freeze_capsule("b")
    m.freeze_capsule("c")
    assert m.freeze_capsule("d") is None and len(m.capsules) == 3
    assert m.delete_capsule(first["id"]) is True and m.delete_capsule(9999) is False
    assert m.freeze_capsule("d")["id"] > first["id"] and [c["name"] for c in m.capsules] == ["b", "c", "d"]


def test_capsules_are_not_in_the_save_code(game_env):
    m = game_env.module
    m.freeze_capsule("x")
    assert "capsules" not in json.dumps(m.serialize_state())


# --- the sandbox branch (A-17) -----------------------------------------------------------------


def test_a_replay_changes_nothing_in_the_real_game(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    game_env.earth["resource_count"] = 123.0  # the live game moves on after the capsule
    m.tick()
    before_state = json.dumps(m.serialize_state(), sort_keys=True)
    before_counters = (m.total_ticks, m.governor_purchase_count, m.lifetime_generators_built, m.lifetime_recyclers_built,
                       m.current_planet, set(m.unlocked_bodies), m.sandbox_mode, set(m.achievement_ids_earned()))
    text = m.capsule_replay(capsule["id"])
    assert text and "Nothing in your game changed" in text
    assert json.dumps(m.serialize_state(), sort_keys=True) == before_state
    assert before_counters == (m.total_ticks, m.governor_purchase_count, m.lifetime_generators_built, m.lifetime_recyclers_built,
                               m.current_planet, set(m.unlocked_bodies), m.sandbox_mode, set(m.achievement_ids_earned()))


def test_a_replay_actually_runs_from_the_capsule_not_from_now(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    for planet in m.PLANETS:  # now wreck the live game
        m.planet_state[planet]["generator_count"] = 0
        m.planet_state[planet]["resource_count"] = 0.0
    after = m.branch_from_capsule(capsule, 600)
    assert after["machines"] >= capsule["metrics"]["machines"]  # the capsule's machines were there
    assert after["banked"] > 0
    assert m.planet_state["Earth"]["generator_count"] == 0 and m.planet_state["Earth"]["resource_count"] == 0.0


def test_the_branch_is_put_back_even_if_it_fails_halfway(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    live = copy.deepcopy(m.planet_state)
    unlocked = set(m.unlocked_bodies)
    original = m.governor_step

    def boom():
        raise RuntimeError("boom")
    m.governor_step = boom
    try:
        try:
            m.branch_from_capsule(capsule, 50)
            raised = False
        except RuntimeError:
            raised = True
    finally:
        m.governor_step = original
    assert raised
    assert m.planet_state == live and m.unlocked_bodies == unlocked and m._dry_run is False


def test_a_replay_uses_the_governor_so_a_rich_capsule_buys_things(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    game_env.earth["resource_count"] = 50000.0
    capsule = m.freeze_capsule("rich")
    after = m.branch_from_capsule(capsule, m.CAPSULE_BRANCH_TICKS)
    assert after["machines"] > capsule["metrics"]["machines"]


def test_replay_text_names_the_terms_and_is_kept_for_the_card(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    text = m.capsule_replay(capsule["id"])
    assert "3:00 with nobody at the controls" in text and "terraform" in text and "machines" in text and "banked" in text
    assert m._capsule_notes[capsule["id"]]["replay"] == text
    assert m.capsule_replay(777) is None


# --- the diff (A-18) ---------------------------------------------------------------------------------


def test_the_diff_says_nothing_has_changed_straight_after_freezing(game_env):
    m = game_env.module
    capsule = m.freeze_capsule("now")
    assert m.capsule_diff(capsule["id"]) == "Nothing has changed since this capsule was frozen."


def test_the_diff_compares_you_with_the_governor_alone_over_the_same_time(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    for _ in range(120):
        m.tick()
    game_env.earth["generator_count"] += 20  # something only the player did
    text = m.capsule_diff(capsule["id"])
    assert text.startswith("You, 0:12 later: terraform")
    assert "The Governor alone over the same 0:12" in text and "Gap (you minus the Governor alone)" in text
    assert "machines +" in text
    assert m._capsule_notes[capsule["id"]]["diff"] == text


def test_a_long_gap_only_shows_your_own_change(game_env):
    m = game_env.module
    capsule = m.freeze_capsule("old")
    m.total_ticks += m.CAPSULE_DIFF_CAP + 10
    text = m.capsule_diff(capsule["id"])
    assert text.startswith("You, ") and "no same-length replay was run" in text and "Governor alone" not in text


def test_a_capsule_from_another_run_or_save_is_not_compared(game_env):
    m = game_env.module
    capsule = m.freeze_capsule("old")
    m.total_ticks = max(0, capsule["tick"] - 5) if capsule["tick"] else 0
    capsule["tick"] = 50  # frozen "in the future" relative to now
    assert "different run or save" in m.capsule_diff(capsule["id"])
    capsule["tick"] = 0
    m.prestige_level += 1
    assert "different run or save" in m.capsule_diff(capsule["id"])


def test_the_diff_leaves_the_real_game_alone(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    for _ in range(30):
        m.tick()
    before = json.dumps(m.serialize_state(), sort_keys=True)
    m.capsule_diff(capsule["id"])
    assert json.dumps(m.serialize_state(), sort_keys=True) == before


# --- keeping capsules in this browser --------------------------------------------------------------------


def test_capsules_survive_a_reload_through_local_storage(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    a = m.freeze_capsule("alpha")
    m.freeze_capsule("beta")
    stored = game_env.local_storage.getItem(m.CAPSULE_STORAGE_KEY)
    assert stored and json.loads(stored)[0]["name"] == "alpha"
    m.capsules.clear()
    m._load_capsules()
    assert [c["name"] for c in m.capsules] == ["alpha", "beta"]
    assert m.capsules[0]["planets"]["Earth"]["generator_count"] == 12
    assert m.capsules[0]["metrics"]["machines"] == a["metrics"]["machines"]
    assert m.freeze_capsule("gamma")["id"] == 3  # ids keep counting


def test_deleting_the_last_capsule_clears_the_storage_key(game_env):
    m = game_env.module
    c = m.freeze_capsule("one")
    m.delete_capsule(c["id"])
    assert not game_env.local_storage.getItem(m.CAPSULE_STORAGE_KEY)
    m._load_capsules()
    assert m.capsules == []


def test_malformed_stored_capsules_are_dropped_or_cleaned(game_env):
    m = game_env.module
    good = m.freeze_capsule("good")
    stored = json.loads(game_env.local_storage.getItem(m.CAPSULE_STORAGE_KEY))[0]
    bad_numbers = copy.deepcopy(stored)
    bad_numbers["id"] = 2
    bad_numbers["planets"]["Earth"].update({"resource_count": -5, "generator_count": "many", "ecology_health": float("nan")})
    bad_numbers["planets"]["Mars"] = "nonsense"
    bad_numbers["planets"]["Earth"]["trade_routes"] = {"Mars": 2, "Nowhere": 5, "Moon": -1, "Venus": True}
    junk = [
        "text", None, {"id": True, "name": "x", "tick": 0, "prestige": 0, "planets": {}},
        {"id": 3, "name": "", "tick": 0, "prestige": 0, "planets": {}},
        {"id": 4, "name": "x", "tick": -1, "prestige": 0, "planets": {}},
        {"id": 5, "name": "x", "tick": 0, "prestige": 0, "planets": []},
        dict(stored),  # a duplicate id of the good one
    ]
    game_env.local_storage.setItem(m.CAPSULE_STORAGE_KEY, json.dumps([stored, bad_numbers] + junk))
    m._load_capsules()
    assert [c["id"] for c in m.capsules] == [good["id"], 2]
    cleaned = m.capsules[1]["planets"]
    fresh = m._fresh_planet_state("Earth")
    assert cleaned["Earth"]["resource_count"] == fresh["resource_count"]  # rejected, so the fresh default
    assert cleaned["Earth"]["generator_count"] == fresh["generator_count"]
    assert cleaned["Earth"]["ecology_health"] == fresh["ecology_health"]
    assert cleaned["Earth"]["trade_routes"] == {"Mars": 2}
    assert cleaned["Mars"] == m._fresh_planet_state("Mars")


def test_unreadable_storage_means_no_capsules_and_no_crash(game_env):
    m = game_env.module
    for raw in ("{not json", "[]", "5", '{"a": 1}'):
        game_env.local_storage.setItem(m.CAPSULE_STORAGE_KEY, raw)
        m._load_capsules()
        assert m.capsules == []


def test_at_most_three_are_read_back(game_env):
    m = game_env.module
    m.freeze_capsule("a")
    m.freeze_capsule("b")
    m.freeze_capsule("c")
    items = json.loads(game_env.local_storage.getItem(m.CAPSULE_STORAGE_KEY))
    items.append(dict(items[0], id=40, name="extra"))
    game_env.local_storage.setItem(m.CAPSULE_STORAGE_KEY, json.dumps(items))
    m._load_capsules()
    assert [c["name"] for c in m.capsules] == ["a", "b", "c"]


# --- the panel -----------------------------------------------------------------------------------------------


def test_the_panel_is_closed_until_toggled_and_counts_capsules(game_env):
    m = game_env.module
    toggle = game_env.elements["capsules-toggle-button"]
    m.tick()
    assert game_env.elements["capsules-panel"].hidden is True
    assert toggle.innerText == "⏳ Time Capsules (0/3)"
    _open(game_env)
    assert game_env.elements["capsules-panel"].hidden is False and toggle.innerText.startswith("Hide Time Capsules")
    assert "No capsules yet." in _panel_text(game_env)


def test_freezing_from_the_panel_uses_the_typed_name_and_shows_a_card(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    _open(game_env)
    m._capsule_refs["name"].value = "Before the push"
    game_env.panel_click("capsules-panel", action="freeze")
    text = _panel_text(game_env)
    assert "Before the push" in text and "3 worlds" in text and "Replay 3 minutes without you" in text
    assert "Compare with now" in text and "Delete" in text
    assert m._capsule_refs["name"].value == ""  # the field is fresh for the next one


def test_replay_and_diff_buttons_put_their_lines_on_the_card(game_env):
    m = game_env.module
    _a_busy_game(game_env)
    capsule = m.freeze_capsule("busy")
    _open(game_env)
    game_env.panel_click("capsules-panel", action="replay", capsule=str(capsule["id"]))
    assert "Replay, 3:00 with nobody at the controls" in _panel_text(game_env)
    for _ in range(50):
        m.tick()
    game_env.panel_click("capsules-panel", action="diff", capsule=str(capsule["id"]))
    assert "You, 0:05 later" in _panel_text(game_env)


def test_a_half_typed_name_survives_a_rebuild(game_env):
    m = game_env.module
    capsule = m.freeze_capsule("busy")
    _open(game_env)
    m._capsule_refs["name"].value = "half typed"
    game_env.panel_click("capsules-panel", action="replay", capsule=str(capsule["id"]))
    assert m._capsule_refs["name"].value == "half typed"


def test_the_panel_deletes_and_refuses_a_fourth(game_env):
    m = game_env.module
    for name in "abc":
        m.freeze_capsule(name)
    _open(game_env)
    assert "delete one first" in _panel_text(game_env)
    freeze = [e for e in game_env.elements["capsules-panel"].descendants()
              if getattr(e, "tagName", "") == "BUTTON" and e.innerText.startswith("Freeze a capsule")][0]
    assert freeze.disabled is True
    game_env.panel_click("capsules-panel", action="freeze")  # ignored
    assert len(m.capsules) == 3
    game_env.panel_click("capsules-panel", action="delete", capsule=str(m.capsules[0]["id"]))
    assert [c["name"] for c in m.capsules] == ["b", "c"]
    game_env.panel_click("capsules-panel", action="delete", capsule="not-a-number")  # ignored
    assert len(m.capsules) == 2


# --- both pages ------------------------------------------------------------------------------------------------


def test_the_panel_and_button_exist_on_both_pages(game_env):
    for name in ("index.html", "pc.html"):
        html = (GAME_DIR / name).read_text(encoding="utf-8")
        for element_id in ("capsules-toggle-button", "capsules-panel"):
            assert re.search(rf'id="{element_id}"', html), (name, element_id)
    assert '"panel": "capsules-panel"' in (GAME_DIR / "pc.html").read_text(encoding="utf-8")
