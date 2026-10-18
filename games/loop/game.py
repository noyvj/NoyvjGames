"""Loop — Circular Economy & Overconsumption Game.

Runs in-browser via Pyodide. Milestone 2: circularity investments —
repair networks, reuse systems, and recycling loops that each supply
a chunk of the production target without new extraction. Investing
enough in any combination can push new extraction to zero: a fully
closed loop, the clearest win-state in the whole hub.

Post-milestone backlog pass (planning/TODO.md "Per-game: Loop" H1-H20,
H16 parked in LATER.md) added: a goods-category picker at game start
(H2/H20), a second, differently-priced trade partner (H8), a "Start New
Chain" reset control (H7), a closed-loop streak tracker (H19), a "time to
close the loop" projection (H6), decorative loop-ring highlighting tied
to real investment (H5), cost-per-unit-of-supply + running-contribution
readouts (H4/H15), a live score breakdown (H17), alternate real-world
sector comparisons (H9), a hard-ceiling note on the cost multiplier
(H10), a lighter first-cycle message (H11), alternate vignette phrasings
(H14), a first-time-closed-loop banner (H3), and reactive visual pulses
on funds/trade-network changes (H12/H18) — plus the hub-wide achievements
framework (ACHIEVEMENTS-SYSTEM-DESIGN.md), and an H1 bug fix (see
`ChainState.exportable_surplus()`'s docstring).
"""

import importlib
import sys
import types

from js import document
from pyodide.ffi import create_proxy

import loop_runstate as runstate
from loop_achievements import _seed_achievement_toast_baseline, on_toggle_achievements
from loop_changelog import on_toggle_changelog
from loop_ghost_codes import restore_ghost
from loop_handlers import (
    _make_buy_multiple_handler, _make_circularity_handler, _make_focus_handler,
    _make_goods_category_handler, _make_mode_handler, _make_planner_add_handler, _make_redesign_handler,
    _make_relabel_handler, on_advance_cycle, on_assist_change, on_buy_insurance, on_dismiss_load_note,
    on_dismiss_regional_hint, on_ghost_clear, on_ghost_copy, on_ghost_load, on_invest_culture,
    on_invest_overseas_trade, on_invest_regional_trade, on_invest_trade_link, on_ledger_sort,
    on_planner_clear, on_planner_commit, on_planner_horizon, on_planner_slot, on_planner_undo,
    on_replay_tips, on_reset_chain, on_rewind, on_toggle_market_shocks, on_toggle_pool_donation,
    on_toggle_rival,
)
from loop_info_panel import on_toggle_info_page
from loop_ledger import on_copy_ledger
from loop_renderer import render
from loop_rules import ALL_GOODS, BUY_KINDS, BUY_MULTIPLES, CIRCULARITY_INVESTMENTS, GOODS_CATEGORIES
from loop_summaries import on_copy_summary
from loop_visual_maps import VISUAL_VIEWS, _load_visual_prefs, _make_visual_toggle_handler

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/loop/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "loop_rules",
    "loop_model",
    "loop_runstate",
    "loop_bridge",
    "loop_career",
    "loop_ledger",
    "loop_messages",
    "loop_info_panel",
    "loop_achievements",
    "loop_effects",
    "loop_changelog",
    "loop_readouts",
    "loop_visual_maps",
    "loop_sparklines",
    "loop_summaries",
    "loop_assist",
    "loop_planner",
    "loop_ghost_codes",
    "loop_narrator",
    "loop_savegame",
    "loop_renderer",
    "loop_handlers",
    "loop_loading",
)
_PARTS = [importlib.import_module(_name) for _name in _PART_NAMES]
_LIVE = frozenset(runstate.LIVE_NAMES)

# Every name the old single-file game.py had is still reachable as game.<name> (tests and the page use them).
for _part in _PARTS:
    for _name, _value in vars(_part).items():
        if not _name.startswith("__") and _name not in _LIVE:
            globals()[_name] = _value
del _part, _name, _value


class _GameModule(types.ModuleType):
    """game.chain & co. live in runstate (they get replaced while playing), so reads go there; a write to any
    name copies to every module that holds the name, so monkeypatching game._window or setting
    game.buy_multiple = 5 still changes what the code uses."""

    def __getattr__(self, name):
        if name in _LIVE:
            return getattr(runstate, name)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _LIVE:
            setattr(runstate, name, value)
            return
        for _part in _PARTS:
            if name in vars(_part):
                setattr(_part, name, value)
        super().__setattr__(name, value)

    def __dir__(self):
        return sorted(set(super().__dir__()) | _LIVE)


try:
    sys.modules[__name__].__class__ = _GameModule
except TypeError:  # a host without module subclassing: plain names still work, only the forwarding is lost
    pass


def setup():
    # index.html already marks these hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true. Same pattern as Grid's setup().
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("loop-closed-banner").hidden = True

    document.getElementById("pool-donate-button").addEventListener("click", create_proxy(on_toggle_pool_donation))
    for count in BUY_MULTIPLES:
        document.getElementById(f"buy-x{count}-button").addEventListener(
            "click", create_proxy(_make_buy_multiple_handler(count))
        )
    document.getElementById("advance-cycle-button").addEventListener(
        "click", create_proxy(on_advance_cycle)
    )
    for measure in CIRCULARITY_INVESTMENTS:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_circularity_handler(measure))
        )
    document.getElementById("trade-link-invest-button").addEventListener(
        "click", create_proxy(on_invest_trade_link)
    )
    document.getElementById("regional-trade-invest-button").addEventListener(
        "click", create_proxy(on_invest_regional_trade)
    )
    document.getElementById("reset-chain-button").addEventListener(
        "click", create_proxy(on_reset_chain)
    )
    for category in ALL_GOODS:
        document.getElementById(f"goods-category-{category}-button").addEventListener(
            "click", create_proxy(_make_goods_category_handler(category))
        )
    document.getElementById("insurance-button").addEventListener("click", create_proxy(on_buy_insurance))
    document.getElementById("rewind-button").addEventListener("click", create_proxy(on_rewind))
    document.getElementById("market-shocks-button").addEventListener("click", create_proxy(on_toggle_market_shocks))
    document.getElementById("rival-button").addEventListener("click", create_proxy(on_toggle_rival))
    document.getElementById("ledger-sort-select").addEventListener("change", create_proxy(on_ledger_sort))
    document.getElementById("ledger-copy-button").addEventListener("click", create_proxy(on_copy_ledger))
    document.getElementById("copy-summary-button").addEventListener("click", create_proxy(on_copy_summary))
    document.getElementById("culture-invest-button").addEventListener("click", create_proxy(on_invest_culture))
    for measure in CIRCULARITY_INVESTMENTS:
        document.getElementById(f"focus-{measure}-button").addEventListener(
            "click", create_proxy(_make_focus_handler(measure))
        )
        document.getElementById(f"redesign-{measure}-button").addEventListener(
            "click", create_proxy(_make_redesign_handler(measure))
        )
    for which in ("challenge", "zero-waste"):
        document.getElementById(f"{which}-mode-button").addEventListener(
            "click", create_proxy(_make_mode_handler("challenge" if which == "challenge" else "zero"))
        )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("overseas-trade-invest-button").addEventListener(
        "click", create_proxy(on_invest_overseas_trade)
    )
    document.getElementById("load-note-dismiss").addEventListener("click", create_proxy(on_dismiss_load_note))
    # H-3 planner, H-8 Assist, GH-28 / H-7 ghost codes.
    for kind in BUY_KINDS:
        document.getElementById(f"planner-add-{kind}-button").addEventListener(
            "click", create_proxy(_make_planner_add_handler(kind))
        )
    document.getElementById("planner-horizon-select").addEventListener("change", create_proxy(on_planner_horizon))
    document.getElementById("planner-slot-select").addEventListener("change", create_proxy(on_planner_slot))
    document.getElementById("planner-undo-button").addEventListener("click", create_proxy(on_planner_undo))
    document.getElementById("planner-clear-button").addEventListener("click", create_proxy(on_planner_clear))
    document.getElementById("planner-commit-button").addEventListener("click", create_proxy(on_planner_commit))
    document.getElementById("assist-select").addEventListener("change", create_proxy(on_assist_change))
    document.getElementById("ghost-copy-button").addEventListener("click", create_proxy(on_ghost_copy))
    document.getElementById("ghost-load-button").addEventListener("click", create_proxy(on_ghost_load))
    document.getElementById("ghost-clear-button").addEventListener("click", create_proxy(on_ghost_clear))
    document.getElementById("replay-tips-button").addEventListener("click", create_proxy(on_replay_tips))
    document.getElementById("regional-hint-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_regional_hint)
    )
    for category in GOODS_CATEGORIES:
        document.getElementById(f"relabel-{category}-button").addEventListener(
            "click", create_proxy(_make_relabel_handler(category))
        )
    document.getElementById("reset-chain-message").hidden = True
    document.getElementById("regional-hint").hidden = True
    # H25b/H29b: opt-in rich map toggles (remembered per browser).
    for kind, spec in VISUAL_VIEWS.items():
        document.getElementById(spec["button"]).addEventListener(
            "click", create_proxy(_make_visual_toggle_handler(kind))
        )
    _load_visual_prefs()
    restore_ghost()  # GH-28: the ghost loaded on a previous visit comes back
    # H20: random per-session vignette-variant offset (real browser only;
    # the pytest fake `js` has no Math, so tests stay deterministic).
    try:
        from js import Math  # noqa: PLC0415
        runstate.vignette_session_offset = int(Math.random() * 1000)
    except ImportError:
        runstate.vignette_session_offset = 0
    _seed_achievement_toast_baseline()
    render()


setup()
