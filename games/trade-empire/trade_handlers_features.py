"""Click handlers for the feature panels (guild, charter perks, captains, blackout, weather, expedition, exchange, blueprints, hub, Meridian, Cartel)."""

from js import document

import trade_runstate as runstate
from trade_blackout import BLACKOUT_WARNING, buy_blackout_intel, set_blackout
from trade_blueprints import (
    adjust_blueprint, blueprint_draft, delete_blueprint, reset_blueprint_draft, save_blueprint,
)
from trade_captains import CAPTAINS
from trade_cartel import CARTEL_BACKLASH_WINDOW, can_dump, can_squeeze, cartel_backlash_left, dump, squeeze
from trade_charter import CHARTER_PERKS, can_buy_charter_perk, set_hard_charter_next
from trade_crew import assign_captain, can_assign_captain, is_captain_swap, release_captain
from trade_exchange import add_exchange_order, remove_exchange_order
from trade_expedition import EXPEDITION_TICKS, can_send_expedition, expedition_odds_text, send_expedition
from trade_founding import buy_charter_perk
from trade_guild import guild_accept, guild_decline
from trade_handlers_core import _confirm_dialog_ask
from trade_hub import clear_hub, set_hub
from trade_meridian import MERIDIAN_INTEL_COST, meridian_has_intel, undercut_meridian
from trade_renderer import render
from trade_rules import GOOD_LABEL
from trade_ships import ships


def on_guild_accept(event=None):
    if guild_accept():
        render()


def on_guild_decline(event=None):
    if guild_decline():
        render()


def on_toggle_hard_charter(event=None):
    if set_hard_charter_next(not runstate.hard_charter_next):
        render()


def _make_charter_perk_handler(perk_id):
    def do_buy():
        buy_charter_perk(perk_id)
        render()

    def handler(event=None):
        if not can_buy_charter_perk(perk_id):
            return
        perk = CHARTER_PERKS[perk_id]
        _confirm_dialog_ask(
            f"trade-empire-charter-perk-{perk_id}",
            f"Buy the {perk['label']} perk for {perk['cost']} charter points? {perk['description']} "
            "It is permanent and carries into every later charter.",
            "Buy perk",
            do_buy,
        )
    return handler


def _make_captain_assign_handler(perk_id, ship_id):
    def do_assign():
        assign_captain(perk_id, ship_id)
        render()

    def handler(event=None):
        if not can_assign_captain(perk_id, ship_id):
            return
        if is_captain_swap(perk_id):
            captain = CAPTAINS[perk_id]
            _confirm_dialog_ask(
                f"trade-empire-captain-swap-{perk_id}",
                f"Move {captain['name']} to {ships[ship_id].name}? Each captain can be moved once per charter, "
                "so this is their last posting until you renew.",
                "Move captain",
                do_assign,
            )
        else:
            do_assign()
    return handler


def _make_captain_release_handler(perk_id):
    def handler(event=None):
        release_captain(perk_id)
        render()
    return handler


def on_toggle_blackout(event=None):
    if runstate.blackout_enabled:
        ends = runstate.blackout_clean and runstate.total_sales_count > 0
        text = "Switch Blackout off? " + (
            "This ends your dark run for this charter." if ends else "Nothing else changes."
        )
        _confirm_dialog_ask("trade-empire-blackout-off", text, "Switch off", lambda: (set_blackout(False), render()))
    else:
        _confirm_dialog_ask(
            "trade-empire-blackout-on", BLACKOUT_WARNING, "Start Blackout", lambda: (set_blackout(True), render()),
            allow_skip=False,
        )


def _make_blackout_buy_handler(kind):
    def handler(event=None):
        if buy_blackout_intel(kind):
            render()
    return handler


def on_toggle_weather(event=None):
    runstate.weather_enabled = not runstate.weather_enabled
    render()


def _make_expedition_handler(ship_id):
    def do_send():
        if send_expedition(ship_id):
            render()

    def handler(event=None):
        if not can_send_expedition(ship_id):
            return
        _confirm_dialog_ask(
            "trade-empire-expedition",
            f"Send {ships[ship_id].name} on an expedition? It cannot trade for {EXPEDITION_TICKS} ticks (that is the "
            "cost) and then returns with a reward. " + expedition_odds_text(),
            "Send it", do_send,
        )
    return handler


def on_add_exchange_order(event=None):
    kind = document.getElementById("exchange-kind-select").value
    good = document.getElementById("exchange-good-select").value
    try:
        pct = int(document.getElementById("exchange-pct-select").value)
    except (TypeError, ValueError):
        return
    if add_exchange_order(kind, good, pct):
        render()


def _make_exchange_remove_handler(index):
    def handler(event=None):
        if remove_exchange_order(index):
            render()
    return handler


def on_blueprint_adjust(stat, delta):
    def handler(event=None):
        if adjust_blueprint(stat, delta):
            render()
    return handler


def on_blueprint_save(event=None):
    input_el = document.getElementById("bp-name-input")
    if input_el is not None:
        blueprint_draft["name"] = str(input_el.value or "")
    if save_blueprint() is not None:
        reset_blueprint_draft()
        if input_el is not None:
            input_el.value = ""
        render()


def on_blueprint_reset(event=None):
    reset_blueprint_draft()
    render()


def _make_blueprint_delete_handler(index):
    def handler(event=None):
        if delete_blueprint(index):
            render()
    return handler


def _make_hub_set_handler(colony_id):
    def handler(event=None):
        if set_hub(colony_id):
            render()
    return handler


def on_clear_hub(event=None):
    if clear_hub():
        render()


def on_toggle_meridian(event=None):
    runstate.meridian_enabled = not runstate.meridian_enabled
    render()


def on_undercut_meridian(event=None):
    if undercut_meridian():
        render()


def on_buy_meridian_intel(event=None):
    if meridian_has_intel() or runstate.total_profit < MERIDIAN_INTEL_COST:
        return
    runstate.total_profit -= MERIDIAN_INTEL_COST
    runstate.meridian_intel_bought = True
    render()


def _make_cartel_handler(kind, good):
    def do_it():
        (squeeze if kind == "squeeze" else dump)(good)
        render()

    def handler(event=None):
        if not (can_squeeze(good) if kind == "squeeze" else can_dump(good)):
            return
        left = cartel_backlash_left(good)
        if left:
            _confirm_dialog_ask(
                f"trade-empire-cartel-{kind}",
                f"{GOOD_LABEL[good]} was moved {CARTEL_BACKLASH_WINDOW - left} tick(s) ago, so this {kind} will BACKFIRE "
                f"for the next {left} tick(s) of the window. Do it anyway?",
                "Do it anyway", do_it, allow_skip=False,
            )
        else:
            do_it()
    return handler
