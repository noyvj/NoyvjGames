"""Reactive visual effects: bursts, banners, pulses, purchase juice and the strain-crack tier."""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import loop_runstate as runstate
from loop_bridge import _setting_flag
from loop_rules import (
    BURST_MILESTONES, CIRCULARITY_INVESTMENTS, PULSE_LARGE_UNITS, PULSE_MEDIUM_UNITS,
    STRAIN_TIER_THRESHOLDS,
)


# H3: a first-time-closed-loop celebratory banner — distinct from (and in
# addition to) the achievement-unlock toast above, since H3 explicitly
# asks for its own celebratory moment, not a reuse of the small
# achievement toast. Tracks whether the loop was already closed
# immediately before the action that just ran, so this only fires on the
# false->true transition, never on every render while it stays closed.
def _trigger_circular_burst():
    """H6: a small particle burst when circular share crosses a 25% step."""
    el = document.getElementById("circular-burst")
    el.classList.add("circular-burst--active")

    def _clear(*args):
        el.classList.remove("circular-burst--active")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 900)


def _milestone_step(fraction):
    return min(BURST_MILESTONES, int(fraction * BURST_MILESTONES + 1e-9))


# H13 audit fix: how long the loop-closed banner stays visible, shared with
# _run_action()'s toast-delay so the two constants can't drift apart.
LOOP_CLOSED_BANNER_DURATION_MS = 5000


def _show_loop_closed_banner(first=None):
    banner = document.getElementById("loop-closed-banner")
    # H16: name the exact cycle the loop first closed on.
    if first is None:
        first = runstate.chain.note_loop_closed()
    if first:
        text = (
            f"🔁 Loop closed for the first time, on cycle {runstate.chain.first_loop_closed_cycle} — 100% of "
            "this cycle's production came from repair, reuse & recycling. No new extraction needed."
        )
    else:
        text = (
            "🔁 Loop closed — 100% of this cycle's production came from repair, reuse & recycling. "
            "No new extraction needed."
        )
    document.getElementById("loop-closed-banner-text").innerText = text
    banner.hidden = False
    banner.classList.add("visible")

    def _hide(*args):
        banner.hidden = True
        banner.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, LOOP_CLOSED_BANNER_DURATION_MS)


def _trigger_funds_burst():
    """H12: a brief visible pulse on the funds display when export
    revenue is earned, instead of the number just silently changing."""
    el = document.getElementById("funds-display")
    el.classList.add("funds-display--burst")

    def _clear(*args):
        el.classList.remove("funds-display--burst")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 700)


def pulse_tier(delta_units):
    """H26: 'small' / 'medium' / 'large' by the size of the supply change."""
    delta = abs(delta_units)
    if delta >= PULSE_LARGE_UNITS:
        return "large"
    if delta >= PULSE_MEDIUM_UNITS:
        return "medium"
    return "small"


def _trigger_trade_network_pulse(delta_units=PULSE_MEDIUM_UNITS):
    """H18: a brief visible pulse on the trade-network readout whenever
    its rendered numbers actually change. H26: intensity varies with the
    size of the change (a tier class alongside the base pulse class)."""
    el = document.getElementById("trade-network-display")
    tier_class = f"trade-network-display--pulse-{pulse_tier(delta_units)}"
    el.classList.add("trade-network-display--pulse")
    el.classList.add(tier_class)

    def _clear(*args):
        el.classList.remove("trade-network-display--pulse")
        el.classList.remove(tier_class)
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 700)


JUICE_NODE_MS = 600
JUICE_RIPPLE_MS = 750
JUICE_FLOAT_MS = 1150


def _pulse_class(element_id, class_name, duration_ms, restart=True):
    """Adds `class_name` to an element for `duration_ms`, then removes it."""
    element = document.getElementById(element_id)
    if restart:
        element.classList.remove(class_name)
    element.classList.add(class_name)

    def _clear(*args):
        element.classList.remove(class_name)
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, duration_ms)


def _invest_juice(kind, units_saved):
    """GH-13: the ring node snaps (measures only), a ripple spreads and '-N raw' floats up, where N is how
    much new extraction the purchase took off this cycle. Silent when switched off or under reduced motion."""
    if not _setting_flag("effectsOn", False):
        return
    if kind in CIRCULARITY_INVESTMENTS:
        _pulse_class(f"loop-ring-node-{kind}", "loop-ring-node--snap", JUICE_NODE_MS)
    _pulse_class("invest-ripple", "invest-ripple--go", JUICE_RIPPLE_MS)
    if units_saved > 0.5:
        document.getElementById("invest-float").innerText = f"-{units_saved:.0f} raw"
        _pulse_class("invest-float", "invest-float--go", JUICE_FLOAT_MS)


def damage_strain_tier():
    """GH-16: 0..4, from the damage still hanging over an OPEN loop (damage x (1 - circular share)), so the
    cracks fade again as the loop closes even though the damage itself never heals."""
    strain = runstate.chain.damage_fraction() * (1.0 - runstate.chain.circular_fraction_this_cycle())
    tier = 0
    for threshold in STRAIN_TIER_THRESHOLDS:
        if strain >= threshold:
            tier += 1
    return tier
