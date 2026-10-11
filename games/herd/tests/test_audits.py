"""GF-3: regulator audits every 10th round. Visible targets, a perk for passing, a fine and a short
trust hit for failing, deterministic, and the baseline farm is never touched."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def farm_with(g, herd=6, feed=0, caps=0, capture=0, funds=2000.0):
    farm = g.FarmState()
    farm.herd_size = herd
    farm.funds = farm.counterfactual_funds = funds
    farm.decoupling_investment.update({"feed": feed, "caps": caps, "capture": capture})
    return farm


def advance_to_end_of(farm, round_number):
    while farm.round_number <= round_number:
        farm.advance_round()


def test_targets_rise_with_each_audit_and_stop_at_the_spec_values(game_env):
    g = game_env.module
    assert [g.audit_coupling_target(n) for n in (1, 2, 3, 4, 5, 9)] == [0.9, 0.8, 0.7, 0.6, 0.6, 0.6]
    assert [g.audit_welfare_target(n) for n in (1, 2, 3, 9)] == [55.0, 60.0, 60.0, 60.0]


def test_audit_rounds_are_every_tenth_round(game_env):
    g = game_env.module
    farm = g.FarmState()
    assert farm.next_audit_round() == 10
    farm.round_number = 10
    assert farm.next_audit_round() == 10
    farm.round_number = 11
    assert farm.next_audit_round() == 20


def test_audit_runs_at_the_end_of_round_ten_only(game_env):
    g = game_env.module
    farm = farm_with(g)
    advance_to_end_of(farm, 9)
    assert farm.audits_done == 0
    farm.advance_round()
    assert farm.round_number == 11 and farm.audits_done == 1
    assert farm.audit_log == [[1, 10, 0]]
    farm.advance_round()
    assert farm.audits_done == 1


def test_passing_earns_a_permanent_perk_and_the_income_bonus(game_env):
    g = game_env.module
    farm = farm_with(g, feed=1, capture=1)
    assert farm.audit_passes() is True
    advance_to_end_of(farm, 10)
    assert farm.audit_perks == ["goodwill"] and farm.just_audit == (1, True, 0.0, "goodwill")
    assert abs(farm.audit_multiplier() - 1.03) < 1e-9
    assert farm.income_breakdown()["audit"] == farm.audit_multiplier()
    advance_to_end_of(farm, 20)
    assert farm.audits_done == 2 and "goodwill" in farm.audit_perks


def test_failing_costs_a_fine_of_one_rounds_income_and_a_trust_hit(game_env):
    g = game_env.module
    farm = farm_with(g, herd=8)
    advance_to_end_of(farm, 9)
    funds_before = farm.funds
    farm.advance_round()
    income = farm.funds_history[-1]  # funds now, after the fine
    number, passed, fine, perk = farm.just_audit
    assert (number, passed, perk) == (1, False, None) and fine > 0
    assert farm.trust_rounds_left == g.AUDIT_TRUST_ROUNDS
    assert income == farm.funds and farm.funds < funds_before + fine
    assert abs(farm.audit_multiplier() - (1 - g.AUDIT_TRUST_PENALTY)) < 1e-9


def test_trust_hit_wears_off_after_three_rounds(game_env):
    g = game_env.module
    farm = farm_with(g, herd=8)
    advance_to_end_of(farm, 10)
    assert farm.trust_rounds_left == 3
    for left in (2, 1, 0):
        farm.advance_round()
        assert farm.trust_rounds_left == left
    assert farm.audit_multiplier() == 1.0


def test_a_farm_with_no_income_owes_no_fine(game_env):
    g = game_env.module
    farm = g.FarmState()
    advance_to_end_of(farm, 10)
    assert farm.just_audit[1] is False and farm.just_audit[2] == 0.0
    assert farm.score() == 300.0 - 0, "doing nothing is never fined"


def test_fine_never_exceeds_the_funds(game_env):
    g = game_env.module
    farm = farm_with(g, herd=30, funds=0.0)
    farm.round_number = 10
    farm.herd_size = 30
    farm.funds = 3.0
    farm.advance_round()
    assert farm.funds >= 0.0


def test_friendly_inspector_halves_the_fine_and_the_trust_hit(game_env):
    g = game_env.module
    plain = farm_with(g, herd=8)
    friend = farm_with(g, herd=8)
    friend.audit_perks = ["friendly_inspector"]
    advance_to_end_of(plain, 10)
    advance_to_end_of(friend, 10)
    assert abs(friend.just_audit[2] - plain.just_audit[2] / 2) <= 1
    assert abs(friend.audit_multiplier() - (1 - g.AUDIT_TRUST_PENALTY / 2)) < 1e-9


def test_perks_come_in_order_then_pay_funds(game_env):
    g = game_env.module
    farm = farm_with(g, feed=6, caps=6, capture=3, herd=4)
    advance_to_end_of(farm, 30)
    assert farm.audit_perks == [p["id"] for p in g.AUDIT_PERKS]
    funds = farm.funds
    farm.decoupling_investment.update({"feed": 8, "caps": 8, "capture": 5})
    advance_to_end_of(farm, 40)
    assert farm.just_audit == (4, True, 0.0, None)
    assert farm.funds > funds


def test_green_loan_makes_decoupling_a_fund_cheaper_but_never_free(game_env):
    g = game_env.module
    farm = g.FarmState()
    base = {m: farm.decoupling_cost(m) for m in g.DECOUPLING_MEASURES}
    farm.audit_perks = ["green_loan"]
    for measure, cost in base.items():
        assert farm.decoupling_cost(measure) == cost - 1
    farm.subsidy_rounds_left = 3
    assert farm.decoupling_cost("feed") == (g.DECOUPLING_MEASURES["feed"]["cost"] - 1) * (1 - g.POLICY_SUBSIDY_DISCOUNT)


def test_the_baseline_farm_is_untouched(game_env):
    g = game_env.module
    good = farm_with(g, herd=8, feed=2, capture=1)
    bad = farm_with(g, herd=8)
    advance_to_end_of(good, 12)
    advance_to_end_of(bad, 12)
    assert bad.counterfactual_funds == good.counterfactual_funds
    assert bad.counterfactual_methane == good.counterfactual_methane


def test_the_income_inspector_still_matches_the_game_around_an_audit(game_env):
    g = game_env.module
    for perks, trust in (([], 0), (["goodwill"], 0), ([], 3), (["goodwill", "friendly_inspector"], 2)):
        farm = farm_with(g, herd=7, feed=1, capture=1)
        farm.audit_perks = list(perks)
        farm.trust_rounds_left = trust
        expected = farm.income_breakdown()["total"]
        before = farm.funds
        farm.advance_round()
        assert abs((farm.funds - before) - expected) < 1e-6


def test_audit_text_in_the_panel_counts_down_and_warns(game_env):
    g = game_env.module
    els = game_env.elements
    g.render()
    assert "Audit 1 is at the end of round 10 (9 rounds from now)" in els["audit-headline"].innerText
    assert not els["audit-panel"].classList.contains("audit-warning")
    assert "Coupling ratio 0.90 or lower: now 1.00 (not met yet)" in els["audit-target-coupling"].innerText
    assert "Welfare 55 or more: now 50 (not met yet)" in els["audit-target-welfare"].innerText
    g.farm.round_number = 7
    g.render()
    assert els["audit-panel"].classList.contains("audit-warning")
    assert els["audit-headline"].innerText.startswith("Warning:")
    g.farm.round_number = 10
    g.render()
    assert "end of this round" in els["audit-headline"].innerText


def test_pressing_advance_round_shows_the_result(game_env):
    g = game_env.module
    g.farm.round_number = 10
    g.farm.herd_size = 5
    game_env.advance_round()
    assert "Regulator audit 1: not passed" in game_env.elements["milestone-toast-text"].innerText
    assert "Regulator audit 1" in game_env.elements["round-announcer"].innerText
    assert "Audits passed: 0 of 1" in game_env.elements["audit-record"].innerText
    assert "Regulator audits: 0 passed of 1" in g.report_card_html()


def test_an_audit_result_is_not_hidden_by_a_callout_toast(game_env):
    g = game_env.module
    g.farm.round_number = 10
    g.farm.herd_size = 5
    g.farm.methane = 14.0  # the methane-penalty nudge fires on this round
    game_env.advance_round()
    text = game_env.elements["milestone-toast-text"].innerText
    assert "Regulator audit 1" in text and "methane" in text.lower()


def test_pass_message_names_the_perk(game_env):
    g = game_env.module
    g.farm.round_number = 10
    g.farm.herd_size = 5
    g.farm.decoupling_investment.update({"feed": 1, "capture": 1})
    game_env.advance_round()
    assert "passed" in game_env.elements["milestone-toast-text"].innerText
    assert "Regulator's Goodwill" in game_env.elements["audit-record"].innerText


def test_planner_never_changes_the_real_audit_record(game_env):
    g = game_env.module
    g.farm.round_number = 8
    g.farm.herd_size = 4
    g.project_plan(horizon=5)
    assert g.farm.audits_done == 0 and g.farm.audit_log == [] and g.farm.audit_perks == []


def test_saved_only_after_the_first_audit_and_round_trips(game_env):
    g = game_env.module
    keys = {"audits_done", "audit_log", "audit_perks", "trust_rounds_left"}
    assert not keys & set(g.get_state())
    g.farm.round_number = 10
    g.farm.herd_size = 5
    game_env.advance_round()
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["audits_done"] == 1 and saved["audit_log"] == [[1, 10, 0]] and saved["trust_rounds_left"] == 3
    g.farm.audits_done, g.farm.audit_log, g.farm.trust_rounds_left = 0, [], 0
    assert g.load_state(saved)
    assert g.farm.audits_done == 1 and g.farm.audit_log == [[1, 10, 0]] and g.farm.trust_rounds_left == 3


def test_hostile_save_values_are_cleaned(game_env):
    g = game_env.module
    base = g.get_state()
    for bad in ({"audits_done": "3", "audit_log": "x", "audit_perks": "goodwill", "trust_rounds_left": "9"},
                {"audits_done": 2, "audit_log": [[1, 10, 5], [0, 3, 1], ["a"], [1, 2], [2, 20, True], None, [1, 10, 1]],
                 "audit_perks": ["goodwill", "goodwill", "nope", 7], "trust_rounds_left": 99},
                {"audits_done": -4, "audit_log": [[1, 10, 1]], "audit_perks": None, "trust_rounds_left": -1},
                {"audits_done": 0, "audit_log": [[1, 10, 1]]}):
        data = dict(base)
        data.update(bad)
        assert g.load_state(data)
        assert 0 <= g.farm.trust_rounds_left <= g.AUDIT_TRUST_ROUNDS
        assert len(set(g.farm.audit_perks)) == len(g.farm.audit_perks) and set(g.farm.audit_perks) <= {"goodwill", "green_loan", "friendly_inspector"}
        for number, rnd, ok in g.farm.audit_log:
            assert number >= 1 and rnd >= 1 and ok in (0, 1)
        assert g.farm.audits_done >= 0
        if g.farm.audits_done == 0:
            assert g.farm.audit_log == []


def test_an_old_save_midgame_gets_its_first_audit_at_the_next_multiple_of_ten(game_env):
    g = game_env.module
    old = g.get_state()
    old["round_number"] = 37
    old["methane_history"] = [0.0] * 37
    assert g.load_state(old)
    assert g.farm.audits_done == 0 and g.farm.next_audit_round() == 40
    assert "audit 1 is at the end of round 40" in game_env.elements["audit-headline"].innerText


def test_handover_starts_a_fresh_audit_record(game_env):
    g = game_env.module
    g.farm.audit_perks = ["goodwill"]
    g.farm.audits_done = 2
    g.farm.certified = True
    g.hand_over_farm()
    assert g.farm.audits_done == 0 and g.farm.audit_perks == []


def test_both_pages_have_the_ids():
    for page in ("index.html", "pc.html"):
        text = (ROOT / page).read_text()
        for ident in ("audit-panel", "audit-headline", "audit-target-coupling", "audit-target-welfare", "audit-reward", "audit-record"):
            assert f'id="{ident}"' in text, (page, ident)
