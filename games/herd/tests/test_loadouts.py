"""GF-23: starting loadouts unlocked by achievements. Every loadout is a trade, applies to an untouched
farm at once and to every later generation, and makes the run unranked."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def unlock(g, loadout_id, monkeypatch):
    monkeypatch.setitem(g.ACHIEVEMENT_CHECKS, g.LOADOUTS[loadout_id]["unlock"], lambda: True)
    g.render()
    assert loadout_id in g.loadouts_unlocked


def pick(game_env, loadout_id):
    game_env.elements["loadout-select"].value = loadout_id
    game_env.elements["loadout-select"].dispatch("change")


def test_standard_by_default_and_nothing_saved(game_env):
    g = game_env.module
    assert g.farm.loadout == "standard" and g.loadout_choice == "standard" and g.loadouts_unlocked == []
    state = g.get_state()
    assert not ({"loadout", "loadouts_unlocked", "loadout_choice"} & set(state))
    assert "Standard start" in game_env.elements["loadout-select"].innerHTML
    assert "locked" in game_env.elements["loadout-list"].innerHTML


def test_each_loadout_names_a_real_achievement(game_env):
    g = game_env.module
    known = {a["id"] for a in g.ACHIEVEMENTS}
    for loadout_id, spec in g.LOADOUTS.items():
        assert (spec["unlock"] is None) == (loadout_id == "standard")
        assert spec["unlock"] is None or spec["unlock"] in known


def test_a_locked_loadout_cannot_be_chosen(game_env):
    g = game_env.module
    assert g.choose_loadout("big_herd") is None
    pick(game_env, "big_herd")
    assert g.loadout_choice == "standard" and "locked" in game_env.elements["loadout-status"].innerText
    assert g.choose_loadout("nonsense") is None


def test_big_herd_applies_at_once_and_is_symmetric(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "big_herd", monkeypatch)
    start = g.get_state()
    start_history = list(g.farm.funds_history)
    pick(game_env, "big_herd")
    assert g.farm.loadout == "big_herd" and g.farm.herd_size == 4 and g.farm.funds == 210
    assert g.farm.counterfactual_funds == 210, "the baseline pays for the same herd"
    assert g.rules_unranked() is True and "unranked" in game_env.elements["rules-badge"].innerText
    pick(game_env, "standard")
    back = g.get_state()
    for key in ("herd_size", "funds", "counterfactual_funds", "methane", "decoupling_investment", "poultry_size", "methane_history"):
        assert back[key] == start[key], key
    assert g.farm.funds_history == start_history
    assert g.farm.loadout == "standard" and g.rules_unranked() is False


def test_lean_green_leaves_the_baseline_funds_alone(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "lean_green", monkeypatch)
    pick(game_env, "lean_green")
    assert g.farm.decoupling_investment == {"feed": 1, "caps": 1, "capture": 1}
    assert g.farm.funds == 250 and g.farm.counterfactual_funds == 300
    assert abs(g.farm.coupling_ratio() - 0.8) < 1e-9


def test_poultry_start_opens_the_flock_from_round_one(game_env, monkeypatch):
    g = game_env.module
    assert g.farm.poultry_unlocked() is False
    unlock(g, "poultry_start", monkeypatch)
    pick(game_env, "poultry_start")
    assert g.farm.poultry_unlocked() is True and g.farm.poultry_size == 2 and g.farm.funds == 275
    assert game_env.elements["poultry-panel"].hidden is False


def test_cash_rich_brings_funds_and_old_methane(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "cash_rich", monkeypatch)
    pick(game_env, "cash_rich")
    assert g.farm.funds == 450 and g.farm.methane == 12.0 and g.farm.counterfactual_methane == 12.0
    assert g.farm.methane_history == [12.0] and g.farm.funds_history == [450.0]
    game_env.advance_round()
    assert g.farm.methane >= 12.0


def test_a_started_farm_keeps_its_start_and_the_choice_waits(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "big_herd", monkeypatch)
    game_env.grow_herd()
    funds_before = g.farm.funds
    pick(game_env, "big_herd")
    assert g.farm.loadout == "standard" and g.farm.funds == funds_before and g.loadout_choice == "big_herd"
    assert "next generation" in game_env.elements["loadout-status"].innerText


def test_the_chosen_loadout_opens_the_next_generation(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "lean_green", monkeypatch)
    g.choose_loadout("lean_green")
    g.farm.certified = True
    g.hand_over_farm()
    assert g.farm.loadout == "lean_green" and g.farm.decoupling_investment["capture"] == 1
    assert g.loadouts_unlocked == ["lean_green"] and g.loadout_choice == "lean_green"
    assert g.farm.funds == 250


def test_a_loadout_stacks_with_legacy_perks_and_survives_changing_the_choice(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "cash_rich", monkeypatch)
    g.legacy_perks["family_savings"] = 1
    g.choose_loadout("cash_rich")
    g.farm.certified = True
    g.hand_over_farm()
    assert g.farm.funds == 300 + g.FAMILY_SAVINGS_FUNDS + 150
    g.choose_loadout("standard")
    assert g.farm.funds == 300 + g.FAMILY_SAVINGS_FUNDS and g.farm.methane == 0.0


def test_ranch_rule_start_funds_still_apply_on_a_loadout_farm(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "big_herd", monkeypatch)
    g.choose_loadout("big_herd")
    g.set_rule("starting_funds", 400)
    assert g.farm.funds == 400 - 90 and g.farm.counterfactual_funds == 400 - 90


def test_ranked_surfaces_respect_a_loadout(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "big_herd", monkeypatch)
    g.choose_loadout("big_herd")
    assert "Starting loadout" in g.report_card_html()
    assert "unranked" in " ".join(g.copy_result_fields()["stats"])
    assert g.ledger_entry()["custom"] is True
    assert "makes this run unranked" in g.rules_summary_message()


def test_saved_and_loaded_with_validation(game_env, monkeypatch):
    g = game_env.module
    unlock(g, "big_herd", monkeypatch)
    g.choose_loadout("big_herd")
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["loadout"] == "big_herd" and saved["loadouts_unlocked"] == ["big_herd"] and saved["loadout_choice"] == "big_herd"
    monkeypatch.undo()
    g.loadouts_unlocked.clear()
    g.farm.loadout = "standard"
    assert g.load_state(saved)
    assert g.farm.loadout == "big_herd" and g.loadout_choice == "big_herd" and g.farm.herd_size == 4
    base = g.get_state()
    for bad in ({"loadout": 5, "loadouts_unlocked": "all", "loadout_choice": "cash_rich"},
                {"loadout": "mystery", "loadouts_unlocked": ["standard", "nope", "big_herd", "big_herd"], "loadout_choice": "lean_green"},
                {"loadout": None, "loadouts_unlocked": [None], "loadout_choice": ["big_herd"]}):
        data = dict(base)
        for key in ("loadout", "loadouts_unlocked", "loadout_choice"):
            data.pop(key, None)
        data.update(bad)
        assert g.load_state(data)
        assert g.farm.loadout == "standard"
        assert g.loadout_choice == "standard"
        assert "standard" not in g.loadouts_unlocked and len(set(g.loadouts_unlocked)) == len(g.loadouts_unlocked)


def test_an_old_save_loads_unchanged(game_env):
    g = game_env.module
    old = g.get_state()
    assert g.load_state(old)
    assert g.farm.loadout == "standard" and g.loadout_choice == "standard"


def test_undo_keeps_unlocked_loadouts(game_env, monkeypatch):
    g = game_env.module
    game_env.advance_round()
    unlock(g, "cash_rich", monkeypatch)
    g.choose_loadout("cash_rich")
    game_env.elements["undo-round-button"].disabled = False
    assert g.undo_last_round()
    assert "cash_rich" in g.loadouts_unlocked and g.loadout_choice == "cash_rich"


def test_both_pages_have_the_ids():
    for page in ("index.html", "pc.html"):
        text = (ROOT / page).read_text()
        for ident in ("loadout-panel", "loadout-summary", "loadout-select", "loadout-note", "loadout-list", "loadout-status"):
            assert f'id="{ident}"' in text, (page, ident)
