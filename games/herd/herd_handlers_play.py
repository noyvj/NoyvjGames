"""Click handlers for playing: buying (herd, levers, poultry, genetics, supply chain, pivot), advancing and undoing a round,
handing the farm over, the bulk stepper and the satellite and policy buttons.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import (
    DECOUPLING_MEASURES, GENETICS_COST, LEVER_LABELS, PLANT_PIVOT_COST, POULTRY_MEASURES, SUPPLY_CHAIN_COST,
    UNDO_PENALTY_FUNDS,
)
from herd_purchases import (
    _confirm_dialog_ask, _guarded_purchase, big_purchase_message, purchase_needs_confirm,
)
from herd_messages import plant_pivot_confirm_message
from herd_achievements import (
    _check_milestone_callout, _check_new_achievements_for_toast, _display_milestone_toast, _pulse,
)
from herd_loadouts import audit_result_message
from herd_succession import (
    _report_decoupling_gap, buy_legacy_perk, celebrate_round, hand_over_farm, handover_points,
)
from herd_extras import SATELLITE_LEVER_KEYS, _satellite_action_cost
from herd_round import (
    _herd_slider_target, _schedule_delta_fade, can_undo, herd_slider_plan, round_announcement, round_deltas,
    save_nudge_message,
)
from herd_savegame import get_state
from herd_renderer import render
from herd_loading import load_state


def on_event_choice(slot):
    """Apply the chosen effect for the active farm event."""
    if not runstate.farm.event_active or runstate.farm.event_choice_made:
        return
    choice = runstate.farm.event_data["choice_a"] if slot == "a" else runstate.farm.event_data["choice_b"]
    if choice["effect"]:
        choice["effect"](runstate.farm)
    runstate.farm.event_choice_made = True
    render()


def _make_satellite_handler(action, button_id):
    def handler(event=None):
        def do_buy():
            if getattr(runstate.farm, action)():
                _pulse(button_id)
            render()

        _guarded_purchase(LEVER_LABELS[SATELLITE_LEVER_KEYS[action]], _satellite_action_cost(action), do_buy)
    return handler


def _make_bulk_handler(mode):
    def handler(event=None):
        runstate.bulk_mode = mode
        render()
    return handler


def on_herd_slider_buy(event=None):
    units, cost, _methane, _income = herd_slider_plan(_herd_slider_target())
    if not units:
        return

    def do_buy():
        for _ in range(units):
            if not runstate.farm.grow_herd():
                break
        _pulse("herd-slider-buy-button")
        render()
        _check_new_achievements_for_toast()

    _guarded_purchase("Grow Herd", cost, do_buy)


def undo_last_round():
    """Puts the farm back to the moment before the last Advance Round and charges the fee.
    Succession (generation, legacy points and perks, hall of fame) and collected breeds are
    kept as they are now; everything on the farm itself comes from the snapshot."""
    if not can_undo():
        return False
    snapshot = runstate.farm.undo_snapshot
    kept = (runstate.generation, runstate.legacy_points, dict(runstate.legacy_perks), list(runstate.hall_of_fame), list(runstate.breeds_collected))
    kept_barns = (list(runstate.barns_unlocked), runstate.barn_skin, list(runstate.loadouts_unlocked), runstate.loadout_choice)  # GF-17: unlocked barns are collected for good too
    load_state(snapshot)
    runstate.generation, runstate.legacy_points, runstate.legacy_perks, runstate.hall_of_fame = kept[0], kept[1], kept[2], kept[3]
    for breed_id in kept[4]:
        if breed_id not in runstate.breeds_collected:
            runstate.breeds_collected.append(breed_id)
    for barn_id in kept_barns[0]:
        if barn_id not in runstate.barns_unlocked:
            runstate.barns_unlocked.append(barn_id)
    runstate.barn_skin = kept_barns[1]
    for loadout_id in kept_barns[2]:
        if loadout_id not in runstate.loadouts_unlocked:
            runstate.loadouts_unlocked.append(loadout_id)
    runstate.loadout_choice = kept_barns[3]
    runstate.farm.funds -= UNDO_PENALTY_FUNDS
    if runstate.farm.funds_history:
        runstate.farm.funds_history[-1] = runstate.farm.funds
    runstate.farm.undo_used = True
    runstate.farm.undo_snapshot = None
    runstate.farm.just_hit_callout = None
    runstate.last_deltas = {}
    runstate.delta_faded = False
    render()
    return True


def on_undo_round(event=None):
    if not can_undo():
        return
    _confirm_dialog_ask(
        action_id="herd-undo-round",
        message=(
            f"Rewind the last round? The farm goes back to just before you pressed Advance Round, "
            f"anything bought since is undone, and it costs {UNDO_PENALTY_FUNDS} funds. "
            "You can do this once per game."
        ),
        confirm_label="Rewind",
        on_confirm=undo_last_round,
        allow_skip=False,
    )


def on_grow_poultry(event=None):
    def do_buy():
        if runstate.farm.grow_poultry():
            _pulse("poultry-grow-button")
        render()

    _guarded_purchase("Grow Flock", runstate.farm.poultry_grow_cost(), do_buy)


def _make_poultry_handler(measure):
    def handler(event=None):
        def do_buy():
            if runstate.farm.invest_poultry(measure):
                _pulse(f"{measure}-count")
            render()

        _guarded_purchase(POULTRY_MEASURES[measure]["label"], POULTRY_MEASURES[measure]["cost"], do_buy)
    return handler


def on_invest_genetics(event=None):
    def do_buy():
        if runstate.farm.invest_genetics():
            _pulse("genetics-invest-button")
        render()

    _guarded_purchase("Breeding Program", GENETICS_COST, do_buy)


def on_invest_supply_chain(event=None):
    def do_buy():
        if runstate.farm.invest_supply_chain():
            _pulse("supply-chain-invest-button")
        render()

    _guarded_purchase("Processing & Distribution", SUPPLY_CHAIN_COST, do_buy)


def on_toggle_variation(event=None):
    runstate.farm.variation_enabled = bool(document.getElementById("variation-checkbox").checked)
    render()


def on_toggle_cap(event=None):
    runstate.farm.regional_cap_enabled = bool(document.getElementById("cap-checkbox").checked)
    render()


def _make_policy_handler(slot):
    def handler(event=None):
        runstate.farm.choose_policy(runstate.farm.current_policy_offer()[slot])
        render()
    return handler


def on_grow_herd(event=None):
    def do_buy():
        if runstate.farm.buy_bulk("herd", runstate.bulk_mode):
            _pulse("grow-herd-button")
        render()
        _check_new_achievements_for_toast()

    _guarded_purchase("Grow Herd", runstate.farm.bulk_plan("herd", runstate.bulk_mode)[1], do_buy)


def _make_decoupling_handler(measure):
    def handler(event=None):
        def do_buy():
            ratio_before = runstate.farm.coupling_ratio()
            if runstate.farm.buy_bulk(measure, runstate.bulk_mode):
                _pulse(f"{measure}-count")
                if runstate.farm.coupling_ratio() < ratio_before - 1e-9:
                    _pulse("gauge-range-display")  # F22 — new session-best
            render()
            _check_new_achievements_for_toast()

        _guarded_purchase(DECOUPLING_MEASURES[measure]["label"], runstate.farm.bulk_plan(measure, runstate.bulk_mode)[1], do_buy)
    return handler


def on_hand_over_farm(event=None):
    def do_handover():
        if hand_over_farm() is not None:
            render()
            _check_new_achievements_for_toast()

    _confirm_dialog_ask(
        action_id="herd-succession",
        message=(
            f"Hand the farm to the next generation? The farm restarts from scratch and you earn "
            f"{handover_points()} legacy point(s) to spend on permanent perks."
        ),
        confirm_label="Hand over",
        on_confirm=do_handover,
        allow_skip=False,
    )


def _make_perk_handler(name):
    def handler(event=None):
        if buy_legacy_perk(name):
            render()
    return handler


def on_invest_plant_pivot(event=None):
    # F16 (planning/TODO.md's shared confirmation-dialog goal) -- this is
    # the pricier of the two decoupling investments (25, vs. 15/20/20 for
    # feed/caps/capture) and, unlike those three, it changes *what* the
    # herd produces rather than just how efficiently -- worth a beat of
    # confirmation before committing funds to it. Pre-action confirm
    # only, per the shared pattern's own shape (no undo window); a player
    # who invests repeatedly can check "don't ask again" once.
    def do_invest():
        ratio_before = runstate.farm.coupling_ratio()
        if runstate.farm.invest_plant_pivot():
            _pulse("plant-pivot-count")
            if runstate.farm.coupling_ratio() < ratio_before - 1e-9:
                _pulse("gauge-range-display")  # F22 — new session-best
        render()
        _check_new_achievements_for_toast()

    if purchase_needs_confirm(PLANT_PIVOT_COST):
        # F-18: the setting says this is a big purchase, so ask every time (no "don't ask again").
        _confirm_dialog_ask(
            action_id="herd-big-purchase",
            message=f"{big_purchase_message('Plant-Based Pivot', PLANT_PIVOT_COST)} {plant_pivot_confirm_message()}",
            confirm_label="Invest",
            on_confirm=do_invest,
            allow_skip=False,
        )
        return
    _confirm_dialog_ask(
        action_id="herd-plant-pivot-invest",
        message=plant_pivot_confirm_message(),
        confirm_label="Invest",
        on_confirm=do_invest,
    )


def on_advance_round(event=None):
    income_this_round = runstate.farm.income_breakdown()["total"]
    funds_before, methane_before = runstate.farm.funds, runstate.farm.methane
    welfare_before, pressure_before = runstate.farm.welfare(), runstate.farm.pressure_fraction()
    runstate.farm.undo_snapshot = None if runstate.sandbox_active else get_state()  # GF-18: the state to rewind to
    runstate.farm.advance_round()
    runstate.session_rounds += 1
    runstate.last_deltas = round_deltas(funds_before, methane_before, welfare_before, pressure_before)
    _schedule_delta_fade()
    _report_decoupling_gap()
    render()
    beat = runstate.last_round_income is not None and income_this_round > runstate.last_round_income + 1e-9
    runstate.last_round_income = income_this_round
    celebrate_round(income_this_round, beat)
    audit_text = audit_result_message(runstate.farm.just_audit) if runstate.farm.just_audit else ""
    runstate.farm.just_audit = None
    document.getElementById("round-announcer").innerText = (round_announcement(funds_before, methane_before) + " " + audit_text).strip()
    nudge = save_nudge_message()
    if audit_text:
        nudge = f"{audit_text} {nudge}".strip()
    if runstate.farm.just_streak_bonus is not None:
        streak, bonus = runstate.farm.just_streak_bonus
        runstate.farm.just_streak_bonus = None
        message = f"\U0001F525 Perfect-round streak of {streak}: +{bonus} funds."
        _display_milestone_toast(f"{message} {nudge}".strip())
    elif nudge:
        _display_milestone_toast(nudge)
    _check_milestone_callout(audit_text)
    _check_new_achievements_for_toast()
    if runstate.farm.just_flattened:
        runstate.farm.just_flattened = False
        _pulse("methane-trend-graph")  # F16
