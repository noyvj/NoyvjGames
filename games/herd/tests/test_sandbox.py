"""GF-24: the practice sandbox. The rules under test: entering and leaving never changes the real farm
(get_state() is byte-identical and the very same farm object comes back), a save made while the sandbox is
on is the real game, and nothing in the sandbox earns an achievement, sets a record, files a ledger line,
writes browser storage or is compared with other players."""
import copy
import json
from pathlib import Path
from .pagefiles import page_text

ROOT = Path(__file__).resolve().parent.parent


def dump(data):
    return json.dumps(data, sort_keys=True)


def watch_storage(game_env):
    writes = []
    original = game_env.local_storage.setItem

    def spy(key, value):
        writes.append(key)
        original(key, value)

    game_env.local_storage.setItem = spy
    return writes


def play_real_game(game_env):
    """A real farm with history: levers, a flock, a few rounds, collections, a pin, a ledger line and a record."""
    g = game_env.module
    g.farm.funds += 2000
    for _ in range(6):
        game_env.grow_herd()
    for measure in ("feed", "caps", "capture", "feed"):
        game_env.invest_decoupling(measure)
    game_env.invest_plant_pivot()
    for _ in range(4):
        game_env.advance_round()
    g.set_pin("funds", True)
    g.ledger_record(g.ledger_entry())
    g.legacy_points = 2
    g.legacy_perks["family_savings"] = 1
    g.hall_of_fame.append(["Beyonmoo", 12, 1])
    g.barns_unlocked.append("stone")
    g.barn_skin = "stone"
    g.loadouts_unlocked.append("cash_rich")
    g.family_endings.append("sell")
    g.record_coupling_ratio = 0.55
    g.render()
    return g


def test_it_starts_off(game_env):
    g = game_env.module
    assert g.sandbox_is_active() is False and g.sandbox_active is False
    assert g.sandbox_leave() is True  # leaving when not in it is a harmless no-op
    assert game_env.elements["sandbox-panel"].hidden is True


def test_enter_then_leave_leaves_get_state_byte_identical_and_the_same_farm(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    real_farm = g.farm
    assert g.sandbox_enter() is True and g.sandbox_is_active() is True
    assert g.farm is not real_farm and g.farm.sandbox is True
    assert g.sandbox_leave() is True and g.sandbox_is_active() is False
    assert g.farm is real_farm, "the very same real farm object is back"
    assert dump(g.get_state()) == before
    assert g.sandbox_enter() and g.sandbox_enter() is True  # a second enter changes nothing
    g.sandbox_leave()
    assert dump(g.get_state()) == before


def test_get_state_while_on_is_the_real_game(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    g.sandbox_enter()
    g.set_sandbox_value("herd", 70)
    assert dump(g.get_state()) == before
    assert g.get_state()["herd_size"] == 6


def test_playing_hard_in_the_sandbox_never_reaches_the_real_farm_or_storage(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    store_before = dict(game_env.local_storage._store)
    side_before = copy.deepcopy((g.legacy_points, g.legacy_perks, g.hall_of_fame, g.barns_unlocked, g.barn_skin,
                                 g.loadouts_unlocked, g.family_endings, g.record_coupling_ratio, g.pinned_stats,
                                 g.ranch_rules, g.generation, g.breeds_collected, g.combos_found))
    writes = watch_storage(game_env)
    g.sandbox_enter()
    for name, value in (("herd", 60), ("methane", 250), ("feed", 15), ("caps", 15), ("capture", 10), ("pivot", 12), ("poultry", 25)):
        g.set_sandbox_value(name, value)
    for _ in range(25):
        game_env.advance_round()
    game_env.grow_herd()
    game_env.invest_decoupling("capture")
    g.welcome_golden_cow()
    g.set_pin("score", True)
    g.set_rule("starting_funds", 600)
    g.choose_barn("gold")
    g.choose_loadout("big_herd")
    g.legacy_points += 5
    g.record_coupling_ratio = 0.1
    g.render()
    assert writes == [], "the sandbox never writes browser storage"
    g.sandbox_leave()
    assert dump(g.get_state()) == before
    assert dict(game_env.local_storage._store) == store_before
    side_after = (g.legacy_points, g.legacy_perks, g.hall_of_fame, g.barns_unlocked, g.barn_skin, g.loadouts_unlocked,
                  g.family_endings, g.record_coupling_ratio, g.pinned_stats, g.ranch_rules, g.generation,
                  g.breeds_collected, g.combos_found)
    assert side_after == side_before


def test_nothing_in_the_sandbox_earns_an_achievement_or_a_collection(game_env):
    g = play_real_game(game_env)
    earned = list(g.achievement_ids_earned())
    breeds, combos = list(g.breeds_collected), list(g.combos_found)
    game_env.timers.flush()  # the real game's own toasts have faded by now
    assert game_env.elements["achievement-toast"].hidden is True
    g.sandbox_enter()
    for name, value in (("herd", 80), ("feed", 15), ("caps", 15), ("capture", 10), ("pivot", 12)):
        g.set_sandbox_value(name, value)
    for _ in range(12):
        game_env.advance_round()
    assert g.achievement_ids_earned() == earned
    assert game_env.elements["achievement-toast"].hidden is True
    assert g.breeds_collected == breeds and g.combos_found == combos
    assert g.get_state()["achievements_earned"] == earned
    assert all(card["progress"] is None for card in g.achievements_summary())
    g.sandbox_leave()
    assert g.achievement_ids_earned() == earned


def test_no_record_no_ledger_no_comparison_no_leaderboard(game_env):
    g = play_real_game(game_env)
    ledger_before = g.read_ledger()
    record_before = g.record_coupling_ratio
    g.sandbox_enter()
    assert g.rules_unranked() is True
    g.set_sandbox_value("capture", 10)
    g.set_sandbox_value("feed", 15)
    g.render()
    assert g.record_coupling_ratio == record_before
    game_env.elements["ledger-add-button"].dispatch("click")
    assert game_env.elements["ledger-add-button"].disabled is True
    g._clear_ledger()
    assert g.read_ledger() == ledger_before
    assert g.can_hand_over() is False and g.can_undo() is False
    fields = g.copy_result_fields()
    assert fields["game"] == "Herd (practice sandbox)"


def test_funds_are_unlimited_and_the_displays_say_so(game_env):
    g = game_env.module
    g.sandbox_enter()
    assert g.farm.funds >= g.SANDBOX_FUNDS
    for _ in range(30):
        game_env.grow_herd()
    for measure in ("feed", "caps", "capture"):
        for _ in range(6):
            game_env.invest_decoupling(measure)
    assert g.farm.funds >= g.SANDBOX_FUNDS
    assert g.farm.herd_size >= 30
    assert "unlimited" in game_env.elements["funds-display"].innerText
    assert "not counted" in game_env.elements["score-display"].innerText
    assert g.PIN_STATS["funds"][1]() == "unlimited"


def test_sliders_set_clamp_and_ignore_nonsense(game_env):
    g = game_env.module
    assert g.set_sandbox_value("herd", 10) is False, "only works inside the sandbox"
    g.sandbox_enter()
    assert g.set_sandbox_value("herd", 33) is True and g.farm.herd_size == 33
    assert g.set_sandbox_value("herd", 33) is False
    g.set_sandbox_value("herd", 9999)
    assert g.farm.herd_size == 80
    g.set_sandbox_value("herd", -5)
    assert g.farm.herd_size == 0
    g.set_sandbox_value("methane", 123)
    assert g.farm.methane == 125 and g.farm.methane_history[-1] == 125
    g.set_sandbox_value("capture", 4)
    assert g.farm.decoupling_investment["capture"] == 4
    g.set_sandbox_value("pivot", 12)
    assert abs(g.farm.plant_based_fraction() - 0.6) < 1e-9
    g.set_sandbox_value("poultry", 7)
    assert g.farm.poultry_size == 7 and g.farm.poultry_unlocked() is True
    g.set_sandbox_value("herd", 12)
    for bad in ("many", None, float("nan"), float("inf"), True):
        assert g.set_sandbox_value("herd", bad) is False
        assert g.farm.herd_size == 12
    assert g.set_sandbox_value("nonsense", 3) is False


def test_the_gauge_reacts_to_the_sliders(game_env):
    g = game_env.module
    g.sandbox_enter()
    g.set_sandbox_value("capture", 10)
    g.set_sandbox_value("feed", 15)
    g.set_sandbox_value("methane", 200)
    g.render()
    assert g.farm.coupling_ratio() <= g.MIN_COUPLING_RATIO + 1e-9
    assert "0.10" in game_env.elements["coupling-display"].innerText
    assert "Methane: 200" in game_env.elements["methane-display"].innerText
    assert float(game_env.elements["haze-overlay"].style.opacity) > 0.0
    assert game_env.elements["sandbox-panel"].hidden is False
    assert "Coupling ratio" in game_env.elements["sandbox-note"].innerText
    assert game_env.elements["sandbox-herd-value"].innerText == "0"


def test_slider_events_and_reset_button(game_env):
    g = game_env.module
    g.sandbox_enter()
    game_env.elements["sandbox-herd"].value = "40"
    game_env.elements["sandbox-herd"].dispatch("input")
    assert g.farm.herd_size == 40 and game_env.elements["sandbox-herd-value"].innerText == "40"
    game_env.elements["sandbox-herd"].value = "abc"
    game_env.elements["sandbox-herd"].dispatch("input")
    assert g.farm.herd_size == 40
    game_env.elements["sandbox-reset-button"].dispatch("click")
    assert g.farm.herd_size == 0 and g.sandbox_is_active()


def test_loading_a_save_leaves_the_sandbox_first(game_env):
    g = play_real_game(game_env)
    saved = json.loads(json.dumps(g.get_state()))
    g.sandbox_enter()
    g.set_sandbox_value("herd", 77)
    assert g.load_state(saved) is True
    assert g.sandbox_is_active() is False and g.farm.herd_size == 6 and g.farm.sandbox is False
    assert game_env.elements["sandbox-panel"].hidden is True


def test_a_broken_save_does_not_drop_the_sandbox(game_env):
    g = game_env.module
    g.sandbox_enter()
    try:
        g.load_state({"funds": "lots"})
    except ValueError:
        pass
    assert g.sandbox_is_active() is True


def test_settings_code_import_is_refused_inside_the_sandbox(game_env):
    g = game_env.module
    code = g.export_settings_code()
    g.sandbox_enter()
    ok, message = g.import_settings_code(code)
    assert ok is False and "sandbox" in message


def test_undo_and_rules_are_locked_in_the_sandbox(game_env):
    g = game_env.module
    game_env.advance_round()
    g.sandbox_enter()
    game_env.advance_round()
    assert g.farm.undo_snapshot is None
    assert g.set_rule("growth_slope", 4) is False and g.rule("growth_slope") == 2.0
    assert g.reset_rules() is False


def test_the_planner_and_audits_work_on_the_practice_farm(game_env):
    g = game_env.module
    g.sandbox_enter()
    g.set_sandbox_value("herd", 20)
    result = g.project_plan(horizon=5)
    assert len(result["rows"]) == 5
    for _ in range(10):
        game_env.advance_round()
    assert g.farm.audits_done == 1
    g.sandbox_leave()
    assert g.farm.audits_done == 0


def test_both_pages_wire_the_shared_sandbox():
    for page in ("index.html", "pc.html"):
        text = page_text(page)
        assert 'shared/sandbox-mode.js" data-game-id="herd"' in text and "shared/sandbox-mode.css" in text
        assert 'id="sandbox-toggle-button"' in text and "data-sandbox-toggle" in text
        for ident in ("sandbox-panel", "sandbox-note", "sandbox-reset-button"):
            assert f'id="{ident}"' in text, (page, ident)
        for name in ("herd", "methane", "feed", "caps", "capture", "pivot", "poultry"):
            assert f'id="sandbox-{name}"' in text and f'id="sandbox-{name}-value"' in text, (page, name)
    assert "sandbox-toggle-button" in (ROOT / "pc-config.json").read_text()
