"""setup(): wires every button and starts the game."""

from js import document
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_achievements import (
    _earned_snapshot, on_toggle_achievements, on_toggle_changelog, update_changelog_display,
)
from trade_blackout import BLACKOUT_INTEL
from trade_blueprints import BLUEPRINT_MAX_DESIGNS, BLUEPRINT_STAT_KEYS
from trade_captains import CAPTAINS
from trade_cartel import on_toggle_desk
from trade_chain_rules import CHAIN_MAX_PRODUCTS, CHAIN_MAX_STAGES
from trade_chain_ui import (
    _make_chain_select_handler, _make_chain_ship_handler, _make_chain_tab_handler, on_chain_clear,
    on_chain_hint, on_chain_lock, on_chain_map_click, on_toggle_chain,
)
from trade_charter import CHARTER_PERKS
from trade_charter_ui import on_toggle_captains, on_toggle_charter
from trade_crises import CRISES
from trade_exchange import EXCHANGE_MAX_SLOTS
from trade_expedition import on_toggle_lab
from trade_handlers_core import (
    _fleet_priority_toggle_handler, _make_automate_handler, _make_concession_handler, _make_depart_handler,
    _make_invest_handler, _make_load_handler, _make_purchase_ship_handler, _make_rename_handler,
    _make_research_handler, _make_reset_name_handler, _make_stockpile_buy_handler,
    _make_stockpile_sell_handler, on_found_new_corporation,
)
from trade_handlers_features import (
    _make_blackout_buy_handler, _make_blueprint_delete_handler, _make_captain_assign_handler,
    _make_captain_release_handler, _make_cartel_handler, _make_charter_perk_handler,
    _make_exchange_remove_handler, _make_expedition_handler, _make_hub_set_handler, on_add_exchange_order,
    on_blueprint_adjust, on_blueprint_reset, on_blueprint_save, on_buy_meridian_intel, on_clear_hub,
    on_guild_accept, on_guild_decline, on_toggle_blackout, on_toggle_hard_charter, on_toggle_meridian,
    on_toggle_weather, on_undercut_meridian,
)
from trade_handlers_modes import (
    _make_crisis_start_handler, on_chain_leave, on_chain_pick, on_crisis_leave, on_crisis_restart,
    on_modes_open,
)
from trade_panels_systems import (
    on_apply_run_seed, on_build_trade_post, on_copy_run_seed, on_toggle_route_hazards,
    on_toggle_route_insurance, on_toggle_seasonal_demand,
)
from trade_renderer import render
from trade_research import RESEARCH_NODES
from trade_rules import ALL_COLONIES, COLONY_FLAVOR, PURCHASABLE_SHIP_IDS, SELL_PRICE
from trade_ships import ships
from trade_summary import on_toggle_summary
from trade_tick import _start_tick_loop


def setup():
    document.getElementById("seasonal-demand-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_seasonal_demand)
    )
    document.getElementById("trade-post-button").addEventListener("click", create_proxy(on_build_trade_post))
    for good in SELL_PRICE:
        buy_button = document.getElementById(f"stockpile-{good}-buy-button")
        if buy_button is not None:
            buy_button.addEventListener("click", create_proxy(_make_stockpile_buy_handler(good)))
            document.getElementById(f"stockpile-{good}-sell-button").addEventListener(
                "click", create_proxy(_make_stockpile_sell_handler(good))
            )
    for colony_id in ALL_COLONIES:
        concede_button = document.getElementById(f"colony-{colony_id}-concede-button")
        if concede_button is not None:
            concede_button.addEventListener("click", create_proxy(_make_concession_handler(colony_id)))
    for colony_id in ALL_COLONIES:
        invest_button = document.getElementById(f"colony-{colony_id}-invest-button")
        if invest_button is not None:
            invest_button.addEventListener("click", create_proxy(_make_invest_handler(colony_id)))
    document.getElementById("route-hazards-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_route_hazards)
    )
    document.getElementById("route-insurance-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_route_insurance)
    )
    document.getElementById("run-seed-apply-button").addEventListener("click", create_proxy(on_apply_run_seed))
    document.getElementById("run-seed-copy-button").addEventListener("click", create_proxy(on_copy_run_seed))
    for colony_id, colony in ALL_COLONIES.items():
        document.getElementById(f"colony-{colony_id}-name").innerText = colony["name"]
        document.getElementById(f"colony-{colony_id}-flavor").innerText = COLONY_FLAVOR[colony_id]
    for ship in ships.values():
        document.getElementById(f"ship-{ship.id}-load-button").innerText = "Load Cargo"
        document.getElementById(f"ship-{ship.id}-load-button").addEventListener(
            "click", create_proxy(_make_load_handler(ship.id))
        )
        for colony_id, colony in ALL_COLONIES.items():
            button = document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button")
            button.innerText = f"Depart to {colony['name']}"
            button.addEventListener("click", create_proxy(_make_depart_handler(ship.id, colony_id)))
        document.getElementById(f"ship-{ship.id}-automate-button").addEventListener(
            "click", create_proxy(_make_automate_handler(ship.id))
        )
        # J10 — every ship can be renamed, not just the purchasable ones.
        document.getElementById(f"ship-{ship.id}-rename-button").addEventListener(
            "click", create_proxy(_make_rename_handler(ship.id))
        )
        reset_button = document.getElementById(f"ship-{ship.id}-reset-name-button")
        if reset_button is not None:
            reset_button.addEventListener("click", create_proxy(_make_reset_name_handler(ship.id)))
        if ship.id in PURCHASABLE_SHIP_IDS:
            document.getElementById(f"ship-{ship.id}-purchase-button").addEventListener(
                "click", create_proxy(_make_purchase_ship_handler(ship.id))
            )
    for node_id in RESEARCH_NODES:
        document.getElementById(f"research-{node_id}-unlock-button").addEventListener(
            "click", create_proxy(_make_research_handler(node_id))
        )
    document.getElementById("fleet-priority-button").addEventListener(
        "click", create_proxy(_fleet_priority_toggle_handler)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary)
    )
    document.getElementById("guild-accept-button").addEventListener("click", create_proxy(on_guild_accept))
    document.getElementById("guild-decline-button").addEventListener("click", create_proxy(on_guild_decline))
    document.getElementById("found-new-corporation-button").addEventListener(
        "click", create_proxy(on_found_new_corporation)
    )
    document.getElementById("hard-charter-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_charter)
    )
    document.getElementById("charter-toggle-button").addEventListener("click", create_proxy(on_toggle_charter))
    document.getElementById("captains-toggle-button").addEventListener("click", create_proxy(on_toggle_captains))
    document.getElementById("blackout-toggle-button").addEventListener("click", create_proxy(on_toggle_blackout))
    document.getElementById("weather-toggle-button").addEventListener("click", create_proxy(on_toggle_weather))
    document.getElementById("lab-toggle-button").addEventListener("click", create_proxy(on_toggle_lab))
    document.getElementById("desk-toggle-button").addEventListener("click", create_proxy(on_toggle_desk))
    document.getElementById("crisis-restart-button").addEventListener("click", create_proxy(on_crisis_restart))
    document.getElementById("crisis-leave-button").addEventListener("click", create_proxy(on_crisis_leave))
    for crisis_id in CRISES:
        document.getElementById(f"crisis-{crisis_id}-start-button").addEventListener(
            "click", create_proxy(_make_crisis_start_handler(crisis_id))
        )
    document.getElementById("chain-toggle-button").addEventListener("click", create_proxy(on_toggle_chain))
    document.getElementById("chain-pick-button").addEventListener("click", create_proxy(on_chain_pick))
    document.getElementById("chain-leave-button").addEventListener("click", create_proxy(on_chain_leave))
    document.getElementById("chain-lock-button").addEventListener("click", create_proxy(on_chain_lock))
    document.getElementById("chain-clear-button").addEventListener("click", create_proxy(on_chain_clear))
    document.getElementById("chain-hint-button").addEventListener("click", create_proxy(on_chain_hint))
    document.getElementById("chain-map").addEventListener("click", create_proxy(on_chain_map_click))
    document.getElementById("modes-open-button").addEventListener("click", create_proxy(on_modes_open))
    for index in range(CHAIN_MAX_PRODUCTS):
        document.getElementById(f"chain-product-{index}-tab").addEventListener("click", create_proxy(_make_chain_tab_handler(index)))
        for stage in range(CHAIN_MAX_STAGES):
            document.getElementById(f"chain-p{index}-s{stage}-select").addEventListener(
                "change", create_proxy(_make_chain_select_handler(index, stage)))
            document.getElementById(f"chain-p{index}-l{stage}-down-button").addEventListener(
                "click", create_proxy(_make_chain_ship_handler(index, stage, -1)))
            document.getElementById(f"chain-p{index}-l{stage}-up-button").addEventListener(
                "click", create_proxy(_make_chain_ship_handler(index, stage, 1)))
    document.getElementById("meridian-toggle-button").addEventListener("click", create_proxy(on_toggle_meridian))
    document.getElementById("meridian-undercut-button").addEventListener("click", create_proxy(on_undercut_meridian))
    document.getElementById("meridian-intel-button").addEventListener("click", create_proxy(on_buy_meridian_intel))
    for good in SELL_PRICE:
        document.getElementById(f"cartel-{good}-squeeze-button").addEventListener(
            "click", create_proxy(_make_cartel_handler("squeeze", good))
        )
        document.getElementById(f"cartel-{good}-dump-button").addEventListener(
            "click", create_proxy(_make_cartel_handler("dump", good))
        )
    document.getElementById("hub-clear-button").addEventListener("click", create_proxy(on_clear_hub))
    for colony_id in ALL_COLONIES:
        document.getElementById(f"hub-set-{colony_id}-button").addEventListener(
            "click", create_proxy(_make_hub_set_handler(colony_id))
        )
    for stat_key in BLUEPRINT_STAT_KEYS:
        document.getElementById(f"bp-{stat_key}-down-button").addEventListener(
            "click", create_proxy(on_blueprint_adjust(stat_key, -1))
        )
        document.getElementById(f"bp-{stat_key}-up-button").addEventListener(
            "click", create_proxy(on_blueprint_adjust(stat_key, 1))
        )
    document.getElementById("bp-save-button").addEventListener("click", create_proxy(on_blueprint_save))
    document.getElementById("bp-reset-button").addEventListener("click", create_proxy(on_blueprint_reset))
    for i in range(BLUEPRINT_MAX_DESIGNS):
        document.getElementById(f"bp-design-{i}-delete-button").addEventListener(
            "click", create_proxy(_make_blueprint_delete_handler(i))
        )
    document.getElementById("exchange-add-button").addEventListener("click", create_proxy(on_add_exchange_order))
    for i in range(EXCHANGE_MAX_SLOTS):
        document.getElementById(f"exchange-order-{i}-remove-button").addEventListener(
            "click", create_proxy(_make_exchange_remove_handler(i))
        )
    for ship_id in ships:
        document.getElementById(f"expedition-ship-{ship_id}-button").addEventListener(
            "click", create_proxy(_make_expedition_handler(ship_id))
        )
    for kind in BLACKOUT_INTEL:
        document.getElementById(f"blackout-buy-{kind}-button").addEventListener(
            "click", create_proxy(_make_blackout_buy_handler(kind))
        )
    for perk_id in CAPTAINS:
        document.getElementById(f"captain-{perk_id}-release-button").addEventListener(
            "click", create_proxy(_make_captain_release_handler(perk_id))
        )
        for ship_id in ships:
            document.getElementById(f"captain-{perk_id}-ship-{ship_id}-button").addEventListener(
                "click", create_proxy(_make_captain_assign_handler(perk_id, ship_id))
            )
    for perk_id in CHARTER_PERKS:
        document.getElementById(f"charter-perk-{perk_id}-buy-button").addEventListener(
            "click", create_proxy(_make_charter_perk_handler(perk_id))
        )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()/
    # its own hide callback (unlike every *panel*, which gets its `hidden`
    # state re-set on every render()), so it needs its own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    notice_toast = document.getElementById("notice-toast")
    if notice_toast is not None:
        notice_toast.hidden = True
    _start_tick_loop()
    update_changelog_display()
    render()
    # A fresh session's already-earned achievements (there shouldn't be
    # any at this point, but a defensive baseline is cheap) shouldn't
    # toast on the very first render.
    runstate._previously_earned_ids = _earned_snapshot()
