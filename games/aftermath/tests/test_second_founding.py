"""GE-10: the Second Founding, an optional prestige for a player who owns every skill."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _own_all(m, knowledge=0):
    m.skill_tree.unlocked = set(m.SKILLS)
    m.skill_tree.knowledge_points = knowledge


def _found(m, stars=1, owned=()):
    m.meta["founding"] = {"stars": stars, "owned": list(owned)}


def _capture_confirm(m, monkeypatch):
    asked = {}

    def ask(action_id, message, confirm_label, on_confirm, allow_skip=None):
        asked.update(action_id=action_id, message=message, confirm_label=confirm_label, on_confirm=on_confirm, allow_skip=allow_skip)

    monkeypatch.setattr(m, "_confirm_dialog_ask", ask)
    return asked


# ------------------------------------------------------------------------------ state and defaults
def test_a_player_who_never_founds_anything_sees_no_change(game_env):
    m = game_env.module
    assert m.meta["founding"] == {"stars": 0, "owned": []}
    assert m.founding_owned() == frozenset() and m.founding_star_resources() == 0
    assert m.starting_resources_bonus() == 0 and m.adaptive_growth_bonus() == 0
    assert m.RunState().resources == m.STARTING_RESOURCES
    _own_all(m)
    assert m.starting_resources_bonus() == 50 and m.early_warning_mitigation_bonus() == 0.10 and m.mutual_aid_mitigation_bonus() == 0.05
    assert m.founding_silenced() == set()


def test_founding_data_is_validated_and_old_saves_load_without_it(game_env):
    m = game_env.module
    assert m._sanitize_meta({})["founding"] == {"stars": 0, "owned": []}
    assert m._sanitize_founding({"stars": 2, "owned": ["stormwall_doctrine", "nonsense", "stormwall_doctrine"]}) == {
        "stars": 2, "owned": ["stormwall_doctrine"]}
    assert m._sanitize_founding({"stars": 99, "owned": []})["stars"] == m.FOUNDING_MAX_STARS
    assert m._sanitize_founding({"stars": -4, "owned": ["open_granaries"]}) == {"stars": 0, "owned": []}
    assert m._sanitize_founding({"stars": True, "owned": ["open_granaries"]}) == {"stars": 0, "owned": []}
    assert m._sanitize_founding({"stars": 0, "owned": ["open_granaries"]})["owned"] == []   # no star, no Founding skills
    assert m._sanitize_founding("x") == {"stars": 0, "owned": []} and m._sanitize_founding(None) == {"stars": 0, "owned": []}
    assert m._sanitize_founding({"stars": 1, "owned": "frontier_charter"})["owned"] == []


def test_founding_is_saved_and_travels_with_the_progress_code(game_env):
    m = game_env.module
    _found(m, 2, ["open_granaries"])
    m.save_meta()
    assert m.load_meta()["founding"] == {"stars": 2, "owned": ["open_granaries"]}
    code = m.export_progress_code()
    _found(m, 0, [])
    assert m.import_progress_code(code) is True
    assert m.meta["founding"] == {"stars": 2, "owned": ["open_granaries"]}


# ------------------------------------------------------------------------------ beginning one
def test_it_needs_every_skill_and_a_star_still_to_earn(game_env):
    m = game_env.module
    assert not m.founding_ready()
    ok, message = m.begin_second_founding()
    assert ok is False and "all skills owned" in message
    m.skill_tree.unlocked = set(list(m.SKILLS)[:-1])
    assert not m.founding_ready() and "so far" in m.founding_status_text()
    _own_all(m)
    assert m.founding_ready() and "may begin" in m.founding_status_text()
    _found(m, m.FOUNDING_MAX_STARS)
    assert not m.founding_ready() and "all three earned" in m.founding_status_text()


def test_beginning_one_resets_the_tree_keeps_everything_else_and_adds_a_star(game_env):
    m = game_env.module
    _own_all(m, knowledge=7)
    m.skill_tree.lifetime_knowledge = 61
    m.run_history.append(120.0)
    m.meta["skill_progress"] = {"early_warning": 30}
    m.meta["pinned_skills"] = ["early_warning"]
    m.meta["presets"] = [{"name": "Flood plan", "resilience": 3, "growth": 1}]
    m.achievement_progress["ever_faced_event"] = True
    before_history = list(m.run_history)
    ok, message = m.begin_second_founding()
    assert ok and "Founding star 1 of 3" in message
    assert m.skill_tree.unlocked == set()
    assert m.skill_tree.knowledge_points == 7                        # the balance is kept, the spent 32 are not refunded
    assert m.skill_tree.lifetime_knowledge == 61
    assert m.meta["founding"] == {"stars": 1, "owned": []}
    assert m.run_history == before_history and m.meta["skill_progress"] == {"early_warning": 30}
    assert m.meta["presets"] and m.meta["pinned_skills"] == ["early_warning"] and m.achievement_progress["ever_faced_event"]
    # saved, and the tree's storage format is exactly what it was
    stored = json.loads(game_env.local_storage.getItem(m.SKILL_TREE_STORAGE_KEY))
    assert stored == {"knowledge_points": 7, "unlocked": [], "lifetime_knowledge": 61}
    assert json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))["founding"]["stars"] == 1


def test_the_tree_can_be_bought_again_and_a_second_star_is_possible(game_env):
    m = game_env.module
    _own_all(m)
    m.begin_second_founding()
    assert m.skill_status("early_warning") in ("unaffordable", "available")
    _own_all(m)
    assert m.founding_ready()
    assert m.begin_second_founding()[0] and m.meta["founding"]["stars"] == 2
    _own_all(m)
    assert m.begin_second_founding()[0] and m.meta["founding"]["stars"] == 3
    _own_all(m)
    assert not m.founding_ready() and m.begin_second_founding()[0] is False


def test_the_confirm_says_what_is_lost_kept_and_gained_and_nothing_happens_until_it_is_confirmed(game_env, monkeypatch):
    m = game_env.module
    asked = _capture_confirm(m, monkeypatch)
    _own_all(m, knowledge=7)
    m.on_founding_begin()
    message = asked["message"]
    assert asked["action_id"] == "aftermath-second-founding" and asked["allow_skip"] is False
    assert "Lost: all 7 skills you own" in message and "32 knowledge" in message and "not refunded" in message
    assert "Kept: the 7 knowledge" in message and "skill ranks" in message and "run history" in message and "achievements" in message
    assert "Gained: Founding star 1 of 3" in message and "+10 starting resources" in message
    assert "nothing in the game needs it" in message and "cannot be undone" in message
    assert m.skill_tree.unlocked == set(m.SKILLS) and m.meta["founding"]["stars"] == 0      # still untouched
    asked["on_confirm"]()
    assert m.skill_tree.unlocked == set() and m.meta["founding"]["stars"] == 1
    assert "The Second Founding has begun" in game_env.elements["founding-message"].innerText


def test_the_confirm_is_not_even_asked_when_it_is_not_possible(game_env, monkeypatch):
    m = game_env.module
    asked = _capture_confirm(m, monkeypatch)
    m.on_founding_begin()
    assert asked == {}


def test_held_founding_skills_are_put_away_for_a_full_refund_when_beginning_another(game_env):
    m = game_env.module
    _found(m, 1, ["frontier_charter"])
    _own_all(m, knowledge=1)
    m.begin_second_founding()
    assert m.meta["founding"] == {"stars": 2, "owned": []}
    assert m.skill_tree.knowledge_points == 1 + 10


# ------------------------------------------------------------------------------ the star perk
def test_each_star_adds_ten_starting_resources_to_every_normal_run(game_env):
    m = game_env.module
    for stars in (0, 1, 2, 3):
        _found(m, stars)
        assert m.RunState().resources == m.STARTING_RESOURCES + 10 * stars
        assert m.RunState().starting_resources == m.STARTING_RESOURCES + 10 * stars
    _found(m, 2)
    assert m.RunState(normalised=True, draw=3).resources == m.STARTING_RESOURCES      # a friend's challenge ignores it


# ------------------------------------------------------------------------------ the Founding skills
def test_founding_skills_are_locked_until_a_star_and_cost_knowledge(game_env):
    m = game_env.module
    m.skill_tree.knowledge_points = 50
    assert all(m.founding_skill_status(s) == "locked" for s in m.FOUNDING_SKILLS)
    assert m.buy_founding_skill("stormwall_doctrine") is False and m.skill_tree.knowledge_points == 50
    _found(m, 1)
    m.skill_tree.knowledge_points = 7
    assert m.founding_skill_status("stormwall_doctrine") == "short" and m.buy_founding_skill("stormwall_doctrine") is False
    m.skill_tree.knowledge_points = 8
    assert m.founding_skill_status("stormwall_doctrine") == "affordable"
    assert m.buy_founding_skill("stormwall_doctrine") is True
    assert m.skill_tree.knowledge_points == 0 and m.founding_owned() == {"stormwall_doctrine"}
    assert m.buy_founding_skill("stormwall_doctrine") is False                          # not twice
    assert m.buy_founding_skill("nonsense") is False
    assert json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))["founding"]["owned"] == ["stormwall_doctrine"]


def test_putting_a_founding_skill_away_refunds_all_of_it(game_env):
    m = game_env.module
    _found(m, 1, ["open_granaries"])
    m.skill_tree.knowledge_points = 2
    assert m.put_away_founding_skill("open_granaries") is True
    assert m.skill_tree.knowledge_points == 10 and m.founding_owned() == frozenset()
    assert m.put_away_founding_skill("open_granaries") is False


def test_stormwall_doctrine_cuts_weather_damage_and_costs_starting_resources(game_env):
    m = game_env.module
    _found(m, 1, ["stormwall_doctrine"])
    run = m.RunState(run_number=1)
    assert run.resources == m.STARTING_RESOURCES - 80 + 10
    assert run.category_bonus("flood") == 0.40 and run.category_bonus("heatwave") == 0.40 and run.category_bonus("storm") == 0.40
    assert run.category_bonus("civil_unrest") == 0 and run.category_bonus("supply_chain") == 0
    held = run.mitigation_for("flood")
    _found(m, 0)
    base = m.RunState(run_number=1)
    assert abs(held - (base.mitigation_for("flood") + 0.40)) < 1e-9 and held <= m.MAX_MITIGATION


def test_open_granaries_cuts_non_weather_and_health_damage_and_costs_starting_resources(game_env):
    m = game_env.module
    _found(m, 1, ["open_granaries"])
    run = m.RunState(run_number=1)
    assert run.resources == m.STARTING_RESOURCES - 60 + 10
    for kind in ("supply_chain", "infrastructure_failure", "heat_mortality"):
        assert run.category_bonus(kind) == 0.30, kind
    for kind in ("flood", "civil_unrest"):
        assert run.category_bonus(kind) == 0, kind


def test_frontier_charter_trades_early_warning_and_mutual_aid_for_a_bigger_start(game_env):
    m = game_env.module
    _own_all(m)
    run = m.RunState(run_number=1)
    with_both = run.mitigation_fraction()
    _found(m, 1, ["frontier_charter"])
    run = m.RunState(run_number=1)
    assert run.resources == m.STARTING_RESOURCES + 50 + 100 + 10
    assert run.growth_capacity == 1 + 2
    assert m.founding_silenced() == {"early_warning", "mutual_aid_network"}
    assert m.early_warning_mitigation_bonus() == 0.0 and m.mutual_aid_mitigation_bonus() == 0.0
    assert abs(run.mitigation_fraction() - (with_both - 0.10 - 0.05)) < 1e-9
    # resilience still counts, and the skills are still owned (and still earn ranks)
    run.resilience_capacity += 2
    assert abs(run.mitigation_fraction() - (with_both - 0.15 + 0.10)) < 1e-9
    assert {"early_warning", "mutual_aid_network"} <= m.skill_tree.unlocked


def test_the_damage_waterfall_still_adds_up_with_founding_skills(game_env):
    m = game_env.module
    _own_all(m)
    _found(m, 2, ["stormwall_doctrine", "open_granaries", "frontier_charter"])
    run = m.RunState(run_number=4)
    run.resilience_capacity += 3
    for _ in range(len(run.schedule)):
        event_type, severity = run.next_event_type(), run.severity_at(run.event_index)
        breakdown = run.damage_breakdown(event_type, severity)
        run.resolve_next_event()
        entry = run.event_log[-1]
        assert abs(breakdown["final"] - entry["damage"]) < 1e-6
        prevented = sum(s["damage"] for s in breakdown["sources"]) - breakdown["cap_added_back"]
        assert abs(breakdown["unmitigated"] - prevented - entry["damage"]) < 1e-6


def test_a_challenge_run_ignores_every_founding_effect(game_env):
    m = game_env.module
    _found(m, 3, list(m.FOUNDING_SKILLS))
    _own_all(m)
    run = m.RunState(run_number=2, normalised=True, draw=5)
    assert run.resources == m.STARTING_RESOURCES and run.growth_capacity == 0 and run.resilience_capacity == 0
    for kind in m.EVENT_LABEL:
        assert run.category_bonus(kind) == 0 and run.mitigation_for(kind) == 0


def test_a_silenced_skill_says_so_in_its_helps_line(game_env):
    m = game_env.module
    _found(m, 1, ["frontier_charter"])
    assert "Frontier Charter" in m.skill_helps_text("early_warning")


# ------------------------------------------------------------------------------ the panel
def test_the_panel_shows_stars_the_kept_and_lost_text_and_the_three_rows(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["founding-status"].innerText.startswith("☆☆☆ 0 of 3 Founding stars")
    assert game_env.elements["founding-begin-button"].disabled is True
    rows = game_env.elements["founding-skills"].children
    assert len(rows) == 3
    assert all("Locked until you have a Founding star" in r.children[0].innerText for r in rows)
    assert all(r.children[1].hidden and r.children[2].hidden for r in rows)
    _own_all(m, knowledge=12)
    m.render()
    assert game_env.elements["founding-begin-button"].disabled is False
    assert "Lost: all 7 skills" in game_env.elements["founding-kept-lost"].innerText
    assert "Kept:" in game_env.elements["founding-kept-lost"].innerText


def test_buying_and_putting_away_through_the_panel_buttons(game_env):
    m = game_env.module
    _found(m, 1)
    m.skill_tree.knowledge_points = 10
    m.render()
    rows = game_env.elements["founding-skills"].children
    buy = rows[2].children[1]                                            # Frontier Charter, 10
    assert buy.hidden is False and buy.disabled is False and buy.innerText == "Buy (10)"
    event = type("E", (), {"target": buy})()
    m.on_founding_event(event)
    assert m.founding_owned() == {"frontier_charter"} and m.skill_tree.knowledge_points == 0
    assert "Frontier Charter is yours" in game_env.elements["founding-message"].innerText
    assert "Yours" in rows[2].children[0].innerText and rows[2].children[1].hidden is True and rows[2].children[2].hidden is False
    away = rows[2].children[2]
    assert away.innerText == "Put away (refund 10)"
    m.on_founding_event(type("E", (), {"target": away})())
    assert m.founding_owned() == frozenset() and m.skill_tree.knowledge_points == 10
    # a button for a skill that does not exist, or no target at all, does nothing
    bogus = rows[0].children[1]
    bogus.setAttribute("data-founding", "nonsense")
    m.on_founding_event(type("E", (), {"target": bogus})())
    m.on_founding_event(None)
    assert m.skill_tree.knowledge_points == 10


def test_every_founding_skill_writes_out_its_gain_and_its_price(game_env):
    m = game_env.module
    for skill_id, skill in m.FOUNDING_SKILLS.items():
        assert skill["gain"] and skill["price"] and skill["cost"] >= 8
        text = m.founding_skill_text(skill_id)
        assert skill["label"] in text and "The price:" in text and skill["gain"] in text


def test_the_game_never_asks_for_a_founding_anywhere_else(game_env):
    """Optional: nothing but the panel mentions or needs it (no achievement, no unlock gate)."""
    achievements = (GAME_DIR / "achievements.json").read_text(encoding="utf-8").lower()
    assert "founding" not in achievements


def test_both_pages_carry_the_panel_and_the_desktop_menu_opens_it():
    classic = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    desktop = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    for page in (classic, desktop):
        for element_id in ("founding-panel", "founding-status", "founding-kept-lost", "founding-begin-button", "founding-skills",
                           "founding-message"):
            assert f'id="{element_id}"' in page, element_id
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert any(c["id"] == "pc-founding-panel" and "#founding-panel" in c["members"] for c in cfg["composites"])
    assert "founding-panel" in (GAME_DIR / "pc.js").read_text(encoding="utf-8")


def test_the_changelog_mentions_the_second_founding():
    entries = [c["entry"].lower() for c in json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))]
    assert any("second founding" in e for e in entries)
