"""Click handlers for the panels (reset, difficulty, stakeholder requests, notes, sheet, carbon, layout, lab, specialist, adopt, pace, scenario, challenge)."""

import canopy_runstate as runstate
from canopy_almanac import _check_rare_wildlife
from canopy_carbon import CARBON_CREDIT_CAP, CARBON_OFFER_CREDITS, sale_preview
from canopy_handlers_core import on_clear, on_clear_cut, on_replant
from canopy_helpers import _announce, _el, _log_event, _ordinal_word, _plot_ref, plot_coordinate_label
from canopy_labui import lab_pending
from canopy_layout import _draft_cells, _request_snapshot, clean_layout_cells
from canopy_plotsheet import (
    close_plot_sheet, is_phone_layout, open_plot_sheet, plot_index_from_tile_id, set_plot_note,
)
from canopy_renderer import render, reset_session, select_plot
from canopy_rules import (
    REPLANT_GRANT_INCOME_BONUS, REPLANT_GRANT_RELATIONS_DELTA, SPECIALIZATION_BIODIVERSITY,
    SPECIALIZATION_ECONOMIC, SPECIALIZATION_LABEL, STAKEHOLDER_DECLINE_RELATIONS_DELTA,
    STAKEHOLDER_GRANT_RELATIONS_DELTA, STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA,
    STAKEHOLDER_INCENTIVE_INCOME_BONUS, STAKEHOLDER_KIND_CLEAR, STAKEHOLDER_KIND_INCENTIVE,
    STAKEHOLDER_KIND_REPLANT_GRANT, carbon, lab_active,
)
from canopy_session import RESET_CONFIRM_ID, _confirm_dialog_ask, reset_confirm_message
from canopy_stakeholders import (
    _note_community_relations_change, _record_request_choice, _stakeholder_target_is_still_standing,
    counter_offer_plan,
)
from canopy_tend import _sync_name_inputs
from canopy_valuation import standing_forest_value


def on_reset_session(event=None):
    if standing_forest_value() <= 0 and runstate.total_income <= 0:
        reset_session()
        return
    _confirm_dialog_ask(
        RESET_CONFIRM_ID,
        reset_confirm_message(),
        "Reset session",
        reset_session,
    )


def on_difficulty_change(event=None):
    """B7: bound to the difficulty <select>; always a full reset, like
    on_grid_size_change()."""
    if event is None:
        return
    reset_session(difficulty=event.target.value)


def on_grid_size_change(event=None):
    """Bound to the grid-size <select>'s "change" event in index.html (see
    setup()) -- `event.target.value` is the chosen preset key ("normal"/
    "large"), same as any real DOM change handler. Changing it always
    triggers a full reset_session() at the new size; there's no meaningful
    way to resize a grid with an in-progress session's plots still on it."""
    if event is None:
        return
    reset_session(grid_size=event.target.value)


def counter_stakeholder_request(event=None):
    plan = counter_offer_plan()
    if plan is None or not _stakeholder_target_is_still_standing():
        return False
    target = plan["target"]
    snapshot = _request_snapshot(runstate.pending_stakeholder_request, STAKEHOLDER_KIND_CLEAR)
    if plan["kind"] == "replant":
        for index in plan["plots"]:
            if runstate.plots[index].replant():
                runstate.total_replants += 1
        _log_event("preserve", f"Countered the request to clear {plot_coordinate_label(target)}: replanting "
                   + ", ".join(plot_coordinate_label(i) for i in plan["plots"]) + " instead", target)
    else:
        runstate.plots[target].value = round(runstate.plots[target].value - plan["income"], 2)
        runstate.total_income += plan["income"]
        _log_event("preserve", f"Countered the request to clear {plot_coordinate_label(target)}: harvested half of its value "
                   f"({plan['income']:.1f}) and kept it standing", target)
    runstate.plots[target].requests_survived += 1
    runstate.community_relations = min(100, runstate.community_relations + plan["relations"])
    _note_community_relations_change()
    _record_request_choice("countered", snapshot)
    runstate.pending_stakeholder_request = None
    render()
    return True


def grant_stakeholder_request(event=None):
    if runstate.pending_stakeholder_request is None:
        return False
    if not _stakeholder_target_is_still_standing():
        runstate.pending_stakeholder_request = None
        render()
        return False
    kind = runstate.pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    request_snapshot = _request_snapshot(runstate.pending_stakeholder_request, kind)
    if kind == STAKEHOLDER_KIND_REPLANT_GRANT:
        idx = runstate.pending_stakeholder_request["plot_index"]
        if runstate.plots[idx].replant():
            runstate.total_replants += 1
        runstate.total_income += REPLANT_GRANT_INCOME_BONUS
        runstate.community_relations = min(100, runstate.community_relations + REPLANT_GRANT_RELATIONS_DELTA)
        _log_event(
            "replant",
            f"Accepted a replanting grant: replanted {plot_coordinate_label(idx)} (+{REPLANT_GRANT_INCOME_BONUS:.0f})",
            idx,
        )
    elif kind == STAKEHOLDER_KIND_INCENTIVE:
        # B11: the whole point of a positive trade-off is that accepting it
        # does NOT clear the plot -- it stays standing untouched, and the
        # player is rewarded with a relations boost plus a funding bonus
        # that (deliberately unlike a normal Clear) doesn't come from the
        # plot's own standing value.
        runstate.community_relations = min(
            100, runstate.community_relations + STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA
        )
        runstate.total_income += STAKEHOLDER_INCENTIVE_INCOME_BONUS
        if runstate.pending_stakeholder_request.get("reason") == "carbon_credit":  # GB-29: the buyer pays in credits too
            carbon["credits"] = min(CARBON_CREDIT_CAP, carbon["credits"] + CARBON_OFFER_CREDITS)
    else:
        plot = runstate.plots[runstate.pending_stakeholder_request["plot_index"]]
        payout = plot.clear()
        if payout is not None:
            runstate.total_income += payout
            runstate.season_cleared = True  # GB-30: a granted clear still cuts standing value
            _log_event(
                "clear",
                f"Granted the community's request: cleared {_plot_ref(plot.index)} for {payout:.1f} income",
                plot.index,
            )
        runstate.community_relations = min(100, runstate.community_relations + STAKEHOLDER_GRANT_RELATIONS_DELTA)
    if kind == STAKEHOLDER_KIND_INCENTIVE:
        idx = runstate.pending_stakeholder_request["plot_index"]
        _log_event("preserve", f"Accepted an incentive to keep {plot_coordinate_label(idx)} standing", idx)
    _note_community_relations_change()
    runstate.stakeholder_grants_count += 1
    _record_request_choice("granted", request_snapshot)
    runstate.pending_stakeholder_request = None
    render()
    return True


def decline_stakeholder_request(event=None):
    if runstate.pending_stakeholder_request is None:
        return False
    if not _stakeholder_target_is_still_standing():
        runstate.pending_stakeholder_request = None
        render()
        return False
    kind = runstate.pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    request_snapshot = _request_snapshot(runstate.pending_stakeholder_request, kind)
    if kind not in (STAKEHOLDER_KIND_INCENTIVE, STAKEHOLDER_KIND_REPLANT_GRANT):
        runstate.community_relations = max(0, runstate.community_relations + STAKEHOLDER_DECLINE_RELATIONS_DELTA)
        # B22/B3: declining a clear-request is a real preserve decision, and
        # the plot survived one more request without ever being cleared.
        idx = runstate.pending_stakeholder_request["plot_index"]
        runstate.plots[idx].requests_survived += 1
        if idx == runstate.adopted_plot_index and runstate.adopted_plot_nickname:
            # GB-14: the adopted, nicknamed plot gets narrated ("Old Bramble survived a third clearing request").
            _log_event(
                "preserve",
                f"{runstate.adopted_plot_nickname} survived {_ordinal_word(runstate.plots[idx].requests_survived)} clearing request",
                idx,
            )
        else:
            _log_event("preserve", f"Declined a request to clear {plot_coordinate_label(idx)}: kept it standing", idx)
    # Declining a positive-trade-off incentive costs nothing -- turning down
    # a gift isn't the same as refusing the community's ask for the plot
    # itself, so there's no relations penalty for this kind.
    _note_community_relations_change()
    runstate.stakeholder_declines_count += 1
    _record_request_choice("declined", request_snapshot)
    runstate.pending_stakeholder_request = None
    _check_rare_wildlife()  # GB-20: the wary fox turns up after three refusals
    render()
    return True


def on_save_plot_note(event=None):
    if runstate.selected_index is None:
        return
    box = _el("plot-note-input")
    if box is None:
        return
    note = set_plot_note(runstate.selected_index, getattr(box, "value", ""))
    _announce(f"Note saved on {_plot_ref(runstate.selected_index)}: {note}" if note else f"Note removed from {_plot_ref(runstate.selected_index)}")
    render()


def on_plot_contextmenu(event):
    """Right-click or long-press on a plot: select it and jump to the note box."""
    tile = event.target.closest(".plot-tile") if getattr(event, "target", None) is not None else None
    index = plot_index_from_tile_id(getattr(tile, "id", None))
    if index is None:
        return
    event.preventDefault()
    select_plot(index)
    if is_phone_layout():  # B-28: a long-press on a phone opens the bottom sheet instead
        open_plot_sheet()
        return
    box = _el("plot-note-input")
    if box is not None and hasattr(box, "focus"):
        box.focus()


def on_plot_sheet_action(name):
    if name == "clear":
        on_clear()
    elif name == "cut":
        on_clear_cut()  # GB-21
    elif name == "replant":
        on_replant()
    elif name == "adopt":
        on_adopt_plot()
    elif name == "note":
        box = _el("plot-note-input")
        if box is not None and hasattr(box, "focus"):
            box.focus()
    close_plot_sheet()


def sell_carbon(fraction=1.0):
    """Sells that share of the credits at today's price. The slump uses the sold amount. Returns the income."""
    amount = carbon["credits"] * max(0.0, min(1.0, fraction))
    if amount < 0.5:
        return 0.0
    preview = sale_preview(amount)
    runstate.total_income += preview["income"]
    carbon["credits"] -= amount
    carbon["sold"] += amount
    carbon["earned_from_sales"] += preview["income"]
    carbon["slump"] = max(carbon["slump"], preview["slump_ticks"])
    _log_event("carbon", f"Sold {amount:.1f} carbon credits at {preview['price']:.1f} for {preview['income']:.1f}. "
                         f"Growth dips for {preview['slump_ticks']} ticks")
    render()
    return preview["income"]


def on_sell_carbon_all(event=None):
    sell_carbon(1.0)


def on_sell_carbon_half(event=None):
    sell_carbon(0.5)


def start_layout(cells, name=""):
    """Starts a new forest on this layout (cells for the current grid size)."""
    cells = clean_layout_cells(cells)
    if cells is None:
        return False
    return reset_session(layout=(name, cells))


def on_layout_apply(event=None):
    name = " ".join(str(getattr(_el("layout-name"), "value", "") or "").split())[:20]
    start_layout(_draft_cells(), name)


def on_layout_clear(event=None):
    reset_session(layout=None)


def apply_lab():
    """Makes the staged dials live. History would be rewritten mid-forest, so this starts a new forest."""
    reset_session(lab_values=dict(lab_pending))
    return lab_active()


def on_lab_apply(event=None):
    apply_lab()


# B27 ------------------------------------------------------------------------

def on_adopt_plot(event=None):
    """Toggles adoption of the selected main-forest plot as a personal
    long-term project. One adopted plot at a time."""
    if runstate.selected_index is None:
        return False
    if runstate.adopted_plot_index == runstate.selected_index:
        runstate.adopted_plot_index = None
    else:
        runstate.adopted_plot_index = runstate.selected_index
        _log_event("adopt", f"Adopted {plot_coordinate_label(runstate.selected_index)} as a long-term project", runstate.selected_index)
    runstate.adopted_plot_nickname = ""  # GB-14: a nickname belongs to one adoption
    _sync_name_inputs()
    render()
    return True


def specialize_selected_plot(kind):
    """B21: applies a one-time permanent specialization to the selected
    main-forest plot. Returns True only on a real change."""
    if runstate.selected_index is None or kind not in SPECIALIZATION_LABEL:
        return False
    plot = runstate.plots[runstate.selected_index]
    if not plot.can_specialize():
        return False
    plot.specialization = kind
    _log_event(
        "specialize",
        f"{plot_coordinate_label(plot.index)} became a {SPECIALIZATION_LABEL[kind]} specialist",
        plot.index,
    )
    render()
    return True


def on_specialize_economic(event=None):
    specialize_selected_plot(SPECIALIZATION_ECONOMIC)


def on_specialize_biodiversity(event=None):
    specialize_selected_plot(SPECIALIZATION_BIODIVERSITY)


# B16 ------------------------------------------------------------------------

def select_stakeholder_plot(event=None):
    """B16: selects the plot named by the pending stakeholder request (bound
    to the "N" key in index.html). Returns the plot index, or None when no
    request is pending."""
    if runstate.pending_stakeholder_request is None:
        return None
    index = runstate.pending_stakeholder_request["plot_index"]
    select_plot(index)
    return index


def on_scenario_change(event=None):
    if event is None:
        return
    reset_session(scenario=event.target.value)


def on_challenge_change(event=None):
    if event is None:
        return
    reset_session(challenge=event.target.value)
