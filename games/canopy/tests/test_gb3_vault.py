"""GB batch 3: the Seed Vault skill tree (GB-10) with idle ranger crews (GB-26), built on shared/skill_tree.py."""

import json
import sys
import types
from pathlib import Path

import pytest

import skill_tree

from .gb_helpers import make_mature


def _give_points(m, count):
    """Earns `count` seed points the honest way: that many levels completed."""
    m.levels_state["done"] = list(m.LEVEL_ORDER[:count])


# --- the tree -------------------------------------------------------------------------------------------------------

def test_the_tree_is_valid_by_the_shared_rules(game_env):
    m = game_env.module
    assert skill_tree.validate(m.VAULT_TREE) == []
    assert m.VAULT_TREE["id"] == "seed_vault" and m.VAULT_TREE["currency"] == "seed points"


def test_every_node_has_its_own_effect_and_a_plain_description(game_env):
    m = game_env.module
    nodes = m.VAULT_TREE["nodes"]
    effects = [n["effect"] for n in nodes]
    assert len(set(effects)) == len(effects)
    for node in nodes:
        assert node["description"] and "<" not in node["description"] and node["label"]
        assert node["branch"] in {b["id"] for b in m.VAULT_TREE["branches"]}


def test_the_whole_tree_is_easy_to_one_hundred_percent(game_env):
    """All perks cost less than the points the game can ever give (levels + tiers + achievement points)."""
    m = game_env.module
    total_cost = skill_tree.totals(m.VAULT_TREE, [])["total_cost"]
    most_points = len(m.LEVEL_ORDER) + len(m.STANDING_TIERS) + m.VAULT_ACHIEVEMENT_POINTS_MAX
    assert total_cost <= most_points
    assert total_cost <= len(m.LEVEL_ORDER) + len(m.STANDING_TIERS) + 4  # even a modest achievement count gets there


def test_crews_are_a_branch_of_the_same_tree(game_env):
    m = game_env.module
    crews = [n for n in m.VAULT_TREE["nodes"] if n["branch"] == "crews"]
    assert {n["effect"] for n in crews} == {"crew_tend", "crew_seedling", "crew_replant", "crew_lead"}


# --- earning points -------------------------------------------------------------------------------------------------

def test_a_fresh_browser_has_no_points(game_env):
    m = game_env.module
    assert m.vault_points_earned() == 0 and m.vault_points_free() == 0
    assert m.vault_owned == []


def test_points_come_from_levels_tiers_and_achievements(game_env):
    m = game_env.module
    _give_points(m, 3)
    assert m.vault_points_earned() == 3
    m.vault_meta["best_tier"] = 2
    assert m.vault_points_earned() == 5
    m.vault_meta["best_ach"] = 9
    assert m.vault_points_earned() == 7  # 9 achievements // 4 = 2
    m.vault_meta["best_ach"] = 999
    assert m.vault_points_earned() == 3 + 2 + m.VAULT_ACHIEVEMENT_POINTS_MAX


def test_spending_never_changes_what_was_earned(game_env):
    m = game_env.module
    _give_points(m, 4)
    assert m.buy_vault_node("deep_roots")["ok"]
    assert m.vault_points_earned() == 4 and m.vault_points_free() == 3
    m.refund_all_vault()
    assert m.vault_points_free() == 4


def test_the_best_tier_and_achievement_counts_are_remembered_across_resets(game_env):
    m = game_env.module
    m.milestone_tier = 2
    m._note_vault_progress()
    assert m.vault_meta["best_tier"] == 2
    game_env.reset_session()
    assert m.milestone_tier == 0 and m.vault_meta["best_tier"] == 2
    stored = json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))
    assert stored["seed_vault"]["best_tier"] == 2


def test_a_new_point_toasts_once(game_env):
    m = game_env.module
    m._last_vault_points = m.vault_points_earned()
    del m._gb_toast_queue[:]
    m.record_level_result("wren_hollow", 30, "30 ticks")
    m._note_vault_progress()
    assert any("seed point" in t for t in m._gb_toast_queue)
    del m._gb_toast_queue[:]
    m._note_vault_progress()
    assert not any("seed point" in t for t in m._gb_toast_queue)


# --- buying through the shared rules --------------------------------------------------------------------------------

def test_buy_checks_points_and_prerequisites(game_env):
    m = game_env.module
    assert m.buy_vault_node("deep_roots")["reason"] == "points"
    _give_points(m, 1)
    assert m.buy_vault_node("canopy_cover")["reason"] == "locked"
    assert m.buy_vault_node("deep_roots")["ok"] and m.vault_owned == ["deep_roots"]
    assert m.buy_vault_node("deep_roots")["reason"] == "owned"
    assert m.buy_vault_node("nonsense")["reason"] == "unknown"
    assert m.vault_points_free() == 0


def test_refund_only_when_nothing_needs_the_node(game_env):
    m = game_env.module
    _give_points(m, 6)
    m.buy_vault_node("deep_roots")
    m.buy_vault_node("canopy_cover")
    assert m.refund_vault_node("deep_roots")["reason"] == "needed"
    assert m.refund_vault_node("canopy_cover")["ok"]
    assert m.refund_vault_node("deep_roots")["ok"] and m.vault_owned == []
    assert m.refund_vault_node("deep_roots")["reason"] == "not-owned"


def test_buying_is_saved_per_browser_at_once(game_env):
    m = game_env.module
    _give_points(m, 2)
    m.buy_vault_node("mulch_bed")
    stored = json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))
    assert stored["seed_vault"]["owned"] == ["mulch_bed"]


# --- effects (deterministic, no randomness) -------------------------------------------------------------------------

def test_no_perks_means_exactly_the_old_numbers(game_env):
    m = game_env.module
    assert m.vault_growth_multiplier() == 1.0 and m.vault_soil_factor() == 1.0 and m.vault_recovery_ticks_saved() == 0
    assert m.current_degrade_per_clear() == m.DEGRADE_PER_CLEAR


def test_growth_perks_add_up(game_env):
    m = game_env.module
    m.vault_owned[:] = ["deep_roots"]
    assert m.vault_growth_multiplier() == pytest.approx(1.03)
    m.vault_owned[:] = ["deep_roots", "canopy_cover", "old_growth_memory"]
    assert m.vault_growth_multiplier() == pytest.approx(1.12)


def test_growth_perks_reach_a_plots_real_accrual(game_env):
    m = game_env.module
    plain = m.Plot(0)
    base = plain.accrue_tick()
    m.vault_owned[:] = ["deep_roots", "canopy_cover", "old_growth_memory"]
    boosted = m.Plot(0).accrue_tick()
    assert boosted == pytest.approx(base * 1.12)


def test_the_counterfactual_includes_the_growth_perks(game_env):
    m = game_env.module
    game_env.tick(10)
    base = m._ideal_accrual_for_ticks(10)
    m.vault_owned[:] = ["deep_roots"]
    assert m._ideal_accrual_for_ticks(10) == pytest.approx(base * 1.03)


def test_soil_perks_cut_the_loss_per_clear(game_env):
    m = game_env.module
    m.vault_owned[:] = ["mulch_bed"]
    assert m.current_degrade_per_clear() == pytest.approx(m.DEGRADE_PER_CLEAR * 0.9)
    m.vault_owned[:] = ["mulch_bed", "leaf_litter"]
    assert m.current_degrade_per_clear() == pytest.approx(m.DEGRADE_PER_CLEAR * 0.81)
    plot = m.plots[0]
    plot.clear()
    assert plot.productivity_multiplier() == pytest.approx(1 - m.DEGRADE_PER_CLEAR * 0.81)


def test_fast_sprouts_shorten_replanting_but_partner_replanting_stays_shorter(game_env):
    m = game_env.module
    m.vault_owned[:] = ["mulch_bed", "fast_sprouts"]
    plot = m.plots[0]
    plot.clear()
    assert plot.replant() and plot.replant_ticks_remaining == m.RECOVERY_TICKS - 2
    other = m.plots[1]
    other.clear()
    assert other.replant(partner=True) and other.replant_ticks_remaining == m.PARTNER_RECOVERY_TICKS


def test_perks_rest_during_a_challenge_run(game_env):
    m = game_env.module
    m.vault_owned[:] = ["deep_roots", "mulch_bed", "tending_crew"]
    assert m.vault_effects()
    m.start_level("pacifist", force=True)
    assert m.vault_effects() == frozenset()
    assert m.vault_growth_multiplier() == 1.0 and m.vault_soil_factor() == 1.0
    game_env.change_challenge("none")
    assert m.vault_growth_multiplier() == pytest.approx(1.03)


def test_the_vault_note_explains_the_rest_during_challenges(game_env):
    m = game_env.module
    m.vault_open = True
    m.start_level("pacifist", force=True)
    assert "challenge" in game_env.elements["vault-note"].innerText
    game_env.change_challenge("none")
    assert game_env.elements["vault-note"].innerText == ""


# --- crews ----------------------------------------------------------------------------------------------------------

def test_no_crew_does_anything_without_its_perk(game_env):
    m = game_env.module
    m.start_level("scorched_start", force=True)  # a challenge: crews rest anyway
    game_env.tick(40)
    assert m.crew_stats == {"tends": 0, "seedlings": 0, "replants": 0}
    game_env.change_challenge("none")
    for plot in m.plots[:6]:
        plot.state = m.BARE
    game_env.tick(60)
    assert m.crew_stats == {"tends": 0, "seedlings": 0, "replants": 0}
    assert all(p.state == m.BARE for p in m.plots[:6])


def test_the_tending_crew_waits_a_few_ticks_then_tends_the_youngest_plot(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew"]
    for index, plot in enumerate(m.plots):
        plot.ticks_intact = 30 + index  # plot 0 is the youngest standing plot
    for _ in range(m.CREW_TEND_DELAY_TICKS - 1):
        game_env.tick()
    assert m._tended_plot() is None
    game_env.tick()
    tended = m._tended_plot()
    assert tended is not None and tended.index == 0
    assert m.crew_stats["tends"] == 1
    assert any(e["kind"] == "crew" and "Tending crew" in e["text"] for e in m.forest_log)


def test_you_can_tend_before_the_crew_does(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew"]
    game_env.tick(1)
    assert m.tend_plot(5)
    game_env.tick(m.CREW_TEND_DELAY_TICKS + 1)
    assert m.crew_stats["tends"] == 0 and m._tended_plot() is not None


def test_the_tending_crew_prefers_a_replanting_plot(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew"]
    for plot in m.plots:
        plot.ticks_intact = 10
    m.plots[7].state = m.REPLANTING
    m.plots[7].replant_ticks_remaining = 6
    assert m._crew_tend_target().index == 7


def test_the_tending_crew_works_again_after_the_cooldown(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew"]
    game_env.tick(m.CREW_TEND_DELAY_TICKS + m.TEND_DURATION_TICKS + m.TEND_COOLDOWN_TICKS + m.CREW_TEND_DELAY_TICKS + 3)
    assert m.crew_stats["tends"] >= 2


def test_the_seedling_watch_catches_a_seedling_in_its_last_tick(game_env):
    m = game_env.module
    m.vault_owned[:] = ["seedling_watch"]
    m.plots[0].state = m.BARE
    m.golden_seedling = {"plot": 0, "ticks_left": 3}
    game_env.tick()
    assert m.golden_seedling is not None and m.crew_stats["seedlings"] == 0
    game_env.tick()
    assert m.crew_stats["seedlings"] == 1 and m.seedlings_caught == 1


def test_the_replant_crew_replants_the_first_bare_plot_on_its_interval(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew", "replant_crew"]
    for plot in m.plots[2:5]:
        plot.state = m.BARE
    game_env.tick(m.CREW_REPLANT_INTERVAL_TICKS - 1)
    assert m.plots[2].state == m.BARE
    replants = m.total_replants
    game_env.tick()
    assert m.plots[2].state == m.REPLANTING and m.plots[3].state == m.BARE
    assert m.total_replants == replants + 1 and m.crew_stats["replants"] == 1
    game_env.tick(m.CREW_REPLANT_INTERVAL_TICKS)
    assert m.plots[3].state in (m.REPLANTING, m.RECOVERED) and m.crew_stats["replants"] == 2


def test_the_crew_lead_speeds_the_replant_crew_up(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew", "replant_crew", "crew_lead"]
    m.plots[4].state = m.BARE
    fast = m.CREW_REPLANT_INTERVAL_TICKS - m.CREW_LEAD_FASTER_TICKS
    game_env.tick(fast - 1)
    assert m.plots[4].state == m.BARE
    game_env.tick()
    assert m.plots[4].state == m.REPLANTING


def test_the_replant_crew_replants_the_next_bare_plot_as_soon_as_one_appears(game_env):
    m = game_env.module
    m.vault_owned[:] = ["tending_crew", "replant_crew"]
    game_env.tick(m.CREW_REPLANT_INTERVAL_TICKS + 3)  # nothing bare yet
    assert m.crew_stats["replants"] == 0
    make_mature(m, 9)
    game_env.select(9)
    game_env.clear()
    game_env.tick()
    assert m.plots[9].state == m.REPLANTING and m.crew_stats["replants"] == 1


def test_crew_runs_repeat_exactly(game_env):
    def run():
        m = game_env.module
        m.current_legacy_multiplier = lambda: 1.0  # the legacy bonus (B15) legitimately differs between sessions
        m.reset_session()
        m.vault_owned[:] = ["tending_crew", "seedling_watch", "replant_crew", "crew_lead"]
        for plot in m.plots[:5]:
            plot.state = m.BARE
        game_env.tick(90)
        return dict(m.crew_stats), round(m.standing_forest_value(), 6), [e["text"] for e in m.forest_log if e["kind"] == "crew"]
    assert run() == run()


# --- the panel ------------------------------------------------------------------------------------------------------

def test_the_toggle_names_the_free_points_and_opens_the_panel(game_env):
    m = game_env.module
    _give_points(m, 2)
    game_env.tick()
    toggle = game_env.elements["vault-toggle-button"]
    assert "2 pts" in toggle.innerText
    assert game_env.elements["vault-panel"].hidden is True
    toggle.dispatch("click", None)
    assert game_env.elements["vault-panel"].hidden is False and toggle.innerText == "Hide Seed Vault"
    assert "2 seed points to spend" in game_env.elements["vault-summary"].innerText
    assert "Crew work this session" in game_env.elements["vault-crews"].innerText
    toggle.dispatch("click", None)
    assert game_env.elements["vault-panel"].hidden is True


class RecordingSkillTree:
    def __init__(self):
        self.rendered = []
        self.updates = []

    def render(self, container, options):
        self.rendered.append((container, options))
        outer = self

        class View:
            def update(self, state):
                outer.updates.append(state)

        return View()


def test_the_panel_draws_the_shared_skill_tree_once_then_updates_it(game_env):
    m = game_env.module
    tree = RecordingSkillTree()
    sys.modules["js"].window = types.SimpleNamespace(NoyvjSkillTree=tree)
    sys.modules["js"].Object = types.SimpleNamespace(fromEntries=None)
    sys.modules["pyodide.ffi"].to_js = lambda value, **_kw: value
    _give_points(m, 3)
    m._vault_view = None
    m.vault_open = True
    game_env.tick()
    game_env.tick()
    assert len(tree.rendered) == 1
    container, options = tree.rendered[0]
    assert container is game_env.elements["vault-tree"]
    assert options["tree"] is m.VAULT_TREE and options["earned"] == 3 and options["refundNodes"] is True
    options["onBuy"]("deep_roots", None)  # the renderer's Buy button
    assert m.vault_owned == ["deep_roots"]
    options["onRefund"]("deep_roots", None)
    assert m.vault_owned == []
    options["onBuy"]("mulch_bed", None)
    options["onRefundAll"]()
    assert m.vault_owned == []
    assert tree.updates and tree.updates[-1]["earned"] == 3


# --- saved state ----------------------------------------------------------------------------------------------------

def test_the_vault_round_trips_in_a_save(game_env):
    m = game_env.module
    _give_points(m, 5)
    m.buy_vault_node("deep_roots")
    m.buy_vault_node("tending_crew")
    m.crew_stats["tends"] = 4
    state = json.loads(json.dumps(m.get_state()))
    assert state["seed_vault"]["owned"] == ["deep_roots", "tending_crew"]
    assert state["seed_vault"]["crews"]["tends"] == 4
    m.reset_session()
    del m.vault_owned[:]
    m.load_state(state)
    assert m.vault_owned == ["deep_roots", "tending_crew"]
    assert m.crew_stats["tends"] == 4


def test_loading_never_leaves_more_spent_than_earned(game_env):
    m = game_env.module
    _give_points(m, 1)
    state = m.get_state()
    state["seed_vault"] = {"owned": ["deep_roots", "canopy_cover", "old_growth_memory", "tending_crew"], "best_tier": 0, "best_ach": 0}
    m.load_state(state)
    assert m.vault_points_free() >= 0
    assert m.vault_owned == ["deep_roots"]  # trimmed from the end until it fits


def test_loading_drops_perks_whose_prerequisites_are_missing(game_env):
    m = game_env.module
    _give_points(m, 15)
    state = m.get_state()
    state["seed_vault"] = {"owned": ["canopy_cover", "crew_lead", "mulch_bed"], "best_tier": 0, "best_ach": 0}
    m.load_state(state)
    assert m.vault_owned == ["mulch_bed"]


@pytest.mark.parametrize("garbage", [
    None, 4, "deep_roots", [], {}, {"owned": "deep_roots"}, {"owned": [None, 3, {}, ["deep_roots"], "bogus", "deep_roots", "deep_roots"]},
    {"owned": ["deep_roots"], "best_tier": "x", "best_ach": [1], "crews": 5},
    {"owned": [], "best_tier": float("nan"), "best_ach": -4, "crews": {"tends": -3, "seedlings": "x", "replants": True}},
    {"owned": [], "best_tier": 999, "best_ach": 99999999, "crews": {"tends": float("inf")}},
])
def test_garbage_vault_values_never_break_a_load(game_env, garbage):
    m = game_env.module
    _give_points(m, 3)
    state = m.get_state()
    state["seed_vault"] = garbage
    m.load_state(state)
    assert all(isinstance(i, str) for i in m.vault_owned)
    assert skill_tree.sanitize_owned(m.VAULT_TREE, m.vault_owned) == m.vault_owned
    assert m.vault_points_free() >= 0
    assert 0 <= m.vault_meta["best_tier"] <= len(m.STANDING_TIERS)
    assert 0 <= m.vault_meta["best_ach"] <= len(m.ACHIEVEMENTS)
    assert all(isinstance(v, int) and v >= 0 for v in m.crew_stats.values())
    game_env.tick(3)


def test_loading_does_not_toast_points_the_save_already_had(game_env):
    m = game_env.module
    state = m.get_state()
    state["levels"] = {"done": ["wren_hollow", "fern_glade"], "best": {}}
    del m._gb_toast_queue[:]
    m.load_state(state)
    assert not any("seed point" in t for t in m._gb_toast_queue)
    game_env.tick()
    assert not any("seed point" in t for t in m._gb_toast_queue)


def test_a_page_without_the_skill_tree_still_plays(game_env):
    m = game_env.module
    m.vault_open = True
    game_env.tick(2)  # no NoyvjSkillTree on the page: the text summary still renders, nothing raises
    assert game_env.elements["vault-summary"].innerText


def test_the_python_mirror_is_the_one_the_page_loads():
    root = Path(__file__).resolve().parent.parent
    assert (root.parent.parent / "shared" / "skill_tree.py").exists()
    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'fetch("../../shared/skill_tree.py")' in html and 'writeFile("skill_tree.py"' in html
