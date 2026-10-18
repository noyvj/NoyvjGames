"""Click handlers: every on_* function that changes the game, plus the factories that build them."""

from js import document

import loop_runstate as runstate
from loop_achievements import _check_new_achievements_for_toast, _seed_achievement_toast_baseline
from loop_bridge import _confirm_dialog_ask, _copy_to_clipboard, _haptic, _setting_number, _window
from loop_career import _update_career, secret_unlocked
from loop_effects import (
    LOOP_CLOSED_BANNER_DURATION_MS, _invest_juice, _milestone_step, _show_loop_closed_banner,
    _trigger_circular_burst, _trigger_funds_burst, _trigger_trade_network_pulse,
)
from loop_ghost_codes import build_run_code, clear_ghost, ghost_message, load_ghost
from loop_ledger import LEDGER_SORTS, archive_chain
from loop_model import ChainState
from loop_planner import (
    PLANNER_SLOTS, plan, plan_add, plan_added, plan_buys_text, plan_clear, plan_cost, plan_shift, plan_undo,
)
from loop_readouts import (
    _report_pool_donation, _requested_count, cycle_summary_text, reset_chain_message, spend_confirm_text,
)
from loop_renderer import render
from loop_rules import (
    BUY_KINDS, CIRCULARITY_INVESTMENTS, GAME_ID, SECRET_GOODS_CATEGORY, SECRET_HEAD_START_UNITS, clean_note,
)
from loop_savegame import load_report


def on_ledger_sort(event=None):
    value = getattr(document.getElementById("ledger-sort-select"), "value", runstate.ledger_sort)
    if value in LEDGER_SORTS:
        runstate.ledger_sort = value
    render()


def on_toggle_rival(event=None):
    _run_action(lambda: setattr(runstate.chain, "rival_on", not runstate.chain.rival_on))


def on_toggle_market_shocks(event=None):
    _run_action(lambda: setattr(runstate.chain, "market_shocks", not runstate.chain.market_shocks))


def on_rewind(event=None):
    """GH-18 / FY-39: spend the chain's one rewind token (asks first, since it is used up)."""
    if not runstate.chain.can_rewind():
        render()
        return
    target = runstate.chain.rewind_snapshot["cycle_number"]

    def _confirmed():
        _run_action(runstate.chain.rewind)
        _seed_achievement_toast_baseline()
        document.getElementById("cycle-live-summary").innerText = f"Rewound to the start of cycle {target}."

    _confirm_dialog_ask(
        action_id="loop-rewind",
        message=(
            f"Rewind to the start of cycle {target}? The last cycle and anything you bought since are undone, "
            "and this chain's rewind token is spent."
        ),
        confirm_label="Rewind",
        on_confirm=_confirmed,
    )


def on_buy_insurance(event=None):
    _run_action(runstate.chain.buy_insurance)


def on_toggle_pool_donation(event=None):
    runstate.chain.donate_surplus = not runstate.chain.donate_surplus
    render()


def on_advance_cycle(event=None):
    # H-28: the optional one-line note for the cycle being advanced goes into its ledger row.
    note_box = document.getElementById("cycle-note-input")
    note = clean_note(getattr(note_box, "value", ""))

    def _advance():
        runstate.chain.advance_cycle(note)
        plan_shift()  # H-3: the next cycle's plan is now this cycle's

    _run_action(_advance)
    note_box.value = ""
    _report_pool_donation()
    # H-4: announce the finished cycle in the polite live region.
    document.getElementById("cycle-live-summary").innerText = cycle_summary_text()


def _purchase(kind, label, event=None):
    """One click on a buy button: applies the chip count, asking first when the spend crosses the
    optional confirmation threshold from Settings (H-20; off by default)."""
    count = runstate.chain.affordable_count(kind, _requested_count(event))
    if count <= 0:
        render()  # nothing affordable: keep the buttons' disabled state honest, as before
        return
    total = count * runstate.chain.unit_cost(kind)
    percent = _setting_number("confirmThreshold", 0)

    def _do():
        before = runstate.chain.new_extraction_needed()
        _run_action(lambda: runstate.chain.invest_many(kind, count))
        _invest_juice(kind, before - runstate.chain.new_extraction_needed())  # GH-13
        _haptic(20)  # GH-29

    if percent > 0 and runstate.chain.funds > 0 and total > runstate.chain.funds * percent / 100.0:
        _confirm_dialog_ask(
            action_id="loop-spend",
            message=spend_confirm_text(count, runstate.chain.unit_cost(kind), label),
            confirm_label="Spend",
            on_confirm=_do,
        )
    else:
        _do()


def _make_circularity_handler(measure):
    def handler(event=None):
        _purchase(measure, CIRCULARITY_INVESTMENTS[measure]["label"], event)
    return handler


def on_invest_trade_link(event=None):
    _purchase("trade", "Trade Link", event)


def on_invest_regional_trade(event=None):
    _purchase("regional", "Regional Partner", event)


def on_invest_overseas_trade(event=None):
    _purchase("overseas", "Overseas Consortium", event)


def _make_buy_multiple_handler(count):
    def handler(event=None):
        runstate.buy_multiple = count
        render()
    return handler


def on_dismiss_regional_hint(event=None):
    runstate.regional_hint_seen = True
    render()


def on_replay_tips(event=None):
    """H-30: brings the one-time tips back. The Regional Partner hint (kept in the save) shows again
    the next time the partner is affordable, and the tutorial offers itself again on the next visit
    (its seen flag lives in the browser). Nothing about the game itself changes."""
    runstate.regional_hint_seen = False
    window = _window()
    if window is not None:
        try:
            window.localStorage.removeItem(f"tutorial-seen:{GAME_ID}")
        except Exception:  # noqa: BLE001 -- no storage (private mode): the in-game hint still resets
            pass
    render()
    document.getElementById("replay-tips-status").innerText = (
        "Tips reset. The Regional Partner hint will show again once you can afford it, and the tutorial will "
        "offer itself again on your next visit (or press Tutorial to run it now)."
    )


def _make_relabel_handler(category):
    """H4: cosmetic-only -- changes labels/vignette item, deliberately
    does NOT add to goods_categories_tried (that counter and the
    achievements built on it measure real picks at chain start)."""
    def handler(event=None):
        def _do_relabel():
            runstate.chain.goods_category = category
        _run_action(_do_relabel)
    return handler


def on_reset_chain(event=None):
    """H7: an in-game "Start New Chain" reset control. Wipes the current
    chain back to a fresh ChainState() (funds, cycle number, every
    investment) — the two module-level counters that exist specifically
    to measure things *across* resets (chains_completed_count,
    goods_categories_tried) are deliberately not touched here.

    Z22 cross-game audit: unlike every other game's reset/retire-style
    action, this one fired instantly with no confirmation at all --
    gated now behind the shared ConfirmDialog (same helper shape as
    Grid's retire-last-plant and Herd's pivot-investment guards) rather
    than left as a silent one-click wipe."""

    def _do_reset():
        runstate.chain = ChainState()
        plan_clear()  # H-3: a what-if for the old chain means nothing on the new one

    def _confirmed():
        runstate.chains_completed_count += 1
        archive_chain()  # H-1: the chain that is ending is filed in Past Chains first
        _run_action(_do_reset)
        message = document.getElementById("reset-chain-message")
        message.innerText = reset_chain_message()
        message.hidden = False

    _confirm_dialog_ask(
        action_id="loop-reset-chain",
        message=(
            "Start a new chain? This wipes your current funds, cycle, and every "
            "circularity/trade investment. Chains completed and goods categories "
            "tried are kept."
        ),
        confirm_label="Start New Chain",
        on_confirm=_confirmed,
    )


def _make_goods_category_handler(category):
    def handler(event=None):
        def _do_select():
            if category == SECRET_GOODS_CATEGORY:
                # GH-14: only once unlocked, and only before the chain has produced
                # anything (the yard's scrap line changes the numbers).
                if not secret_unlocked() or runstate.chain.total_produced > 0:
                    return
                runstate.chain.head_start = SECRET_HEAD_START_UNITS
            else:
                runstate.chain.head_start = 0.0
            runstate.chain.goods_category = category
            runstate.chain.picked_category = category
            runstate.goods_categories_tried.add(category)
        _run_action(_do_select)
    return handler


def on_invest_culture(event=None):
    _run_action(runstate.chain.invest_culture)


def _make_redesign_handler(measure):
    def handler(event=None):
        _run_action(lambda: runstate.chain.redesign(measure))
    return handler


def _make_focus_handler(measure):
    def handler(event=None):
        def _do_focus():
            # Clicking the focused measure again clears the emphasis.
            runstate.chain.set_waste_focus(None if runstate.chain.waste_focus == measure else measure)
        _run_action(_do_focus)
    return handler


def _make_mode_handler(which):
    def handler(event=None):
        def _do_toggle():
            if which == "challenge":
                runstate.chain.set_challenge_mode(not runstate.chain.challenge_mode)
            else:
                runstate.chain.set_zero_waste(not runstate.chain.zero_waste)
        _run_action(_do_toggle)
    return handler


def supply_after_minus(supply_before):
    return runstate.chain.imported_supply() + runstate.chain.exportable_surplus() - supply_before


def _run_action(mutate_fn):
    """Shared wrapper for every state-mutating action: snapshot whatever
    "before" state the reactive effects below need, run the mutation,
    re-render, then fire any effect the mutation triggered (funds burst,
    trade-network pulse, loop-closed banner, achievement toast). Kept in
    one place so every handler gets the same reactive behavior instead of
    re-implementing this comparison per handler."""
    trade_text_before = document.getElementById("trade-network-display").innerText
    export_before = runstate.chain.lifetime_export_revenue
    was_closed = runstate.chain.is_loop_closed()
    step_before = _milestone_step(runstate.chain.circular_fraction_this_cycle())
    supply_before = runstate.chain.imported_supply() + runstate.chain.exportable_surplus()

    mutate_fn()
    # GH-20: the chain's first close is noted BEFORE the render, so the career panel and
    # the achievements count the render shows already include it.
    loop_just_closed = runstate.chain.is_loop_closed() and not was_closed
    first_close = runstate.chain.note_loop_closed() if loop_just_closed else False
    _update_career()
    render()

    # H6: burst on crossing upward through a 25% step (not on every render).
    if _milestone_step(runstate.chain.circular_fraction_this_cycle()) > step_before:
        _trigger_circular_burst()
        _haptic([30, 40, 30])  # GH-29: a double tap at each 25% mark

    if runstate.chain.lifetime_export_revenue > export_before:
        _trigger_funds_burst()
    if document.getElementById("trade-network-display").innerText != trade_text_before:
        _trigger_trade_network_pulse(supply_after_minus(supply_before))
    # H13 audit fix (planning/TODO.md V-E-5): closing the loop for the
    # first time also satisfies the "loop_closed" achievement check, so
    # without this the loop-closed banner and the achievement-unlock toast
    # would both appear on screen from this exact same action. Sequence
    # them instead of suppressing either: the banner (the bigger, rarer,
    # H3-specific celebratory moment) shows immediately as before, and any
    # achievement toast this same action also earned is held back until
    # the banner's own visible window has passed.
    if loop_just_closed:
        _show_loop_closed_banner(first_close)
    _check_new_achievements_for_toast(delay_ms=LOOP_CLOSED_BANNER_DURATION_MS if loop_just_closed else 0)


def _planner_pick(element_id, default, allowed):
    value = getattr(document.getElementById(element_id), "value", default)
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number in allowed else default


def on_planner_horizon(event=None):
    runstate.planner_horizon = _planner_pick("planner-horizon-select", runstate.planner_horizon, (3, 4, 5))
    for i in range(runstate.planner_horizon, PLANNER_SLOTS):  # purchases beyond the window are dropped, not hidden
        plan[i].clear()
    plan_added[:] = [(slot, kind) for slot, kind in plan_added if slot < runstate.planner_horizon]
    runstate.planner_message = ""
    render()


def on_planner_slot(event=None):
    runstate.planner_slot = _planner_pick("planner-slot-select", runstate.planner_slot, tuple(range(runstate.planner_horizon)))
    render()


def _make_planner_add_handler(kind):
    def handler(event=None):
        runstate.planner_message = "" if plan_add(kind) else "That cycle is full: remove something first."
        render()
    return handler


def on_planner_undo(event=None):
    plan_undo()
    runstate.planner_message = ""
    render()


def on_planner_clear(event=None):
    plan_clear()
    runstate.planner_message = ""
    render()


def on_planner_commit(event=None):
    """Buys this cycle's planned purchases for real (the same rules, and the same spend confirmation from Settings,
    as clicking the buttons), then empties this cycle's slot. The later cycles stay planned."""
    items = [(kind, plan[0][kind]) for kind in BUY_KINDS if plan[0].get(kind)]
    if not items:
        runstate.planner_message = "Nothing is planned for this cycle."
        render()
        return
    total = plan_cost(0)

    def _do():
        bought = {}

        def _buy():
            for kind, wanted in items:
                got = runstate.chain.invest_many(kind, wanted)
                if got:
                    bought[kind] = got

        _run_action(_buy)
        plan[0].clear()
        plan_added[:] = [(slot, kind) for slot, kind in plan_added if slot > 0]
        runstate.planner_message = "Bought: " + plan_buys_text(bought) + "." if bought else "Nothing was affordable."
        render()

    percent = _setting_number("confirmThreshold", 0)
    if percent > 0 and runstate.chain.funds > 0 and total > runstate.chain.funds * percent / 100.0:
        _confirm_dialog_ask(
            action_id="loop-spend",
            message=f"Spend {total} of {runstate.chain.funds:.0f} funds on {plan_buys_text(dict(items))}?",
            confirm_label="Spend",
            on_confirm=_do,
        )
    else:
        _do()


def on_assist_change(event=None):
    value = getattr(document.getElementById("assist-select"), "value", runstate.chain.assist)
    _run_action(lambda: runstate.chain.set_assist(value))


def on_ghost_copy(event=None):
    code, error = build_run_code()
    document.getElementById("ghost-code-output").value = code
    if error:
        ghost_message[:] = [error, True]
    elif _copy_to_clipboard(code):
        ghost_message[:] = ["Run code copied. Anyone can paste it into Load a ghost.", False]
    else:
        ghost_message[:] = ["Select the code above and copy it.", False]
    render()


def on_ghost_load(event=None):
    load_ghost(getattr(document.getElementById("ghost-code-input"), "value", ""))
    render()


def on_ghost_clear(event=None):
    clear_ghost()
    render()


def on_dismiss_load_note(event=None):
    load_report.clear()
    render()
