"""The carbon credit market (GB-29): price, trend, selling and the chart."""

import math

import canopy_runstate as runstate
from canopy_rules import ACCRUING_STATES, carbon


# GB-29 (2026-10-09): carbon-credit market. Standing plots earn credits every tick. The price moves on a known cycle (a pure
# function of the tick, no dice) and the next few ticks are shown, so the skill is timing, not luck. Selling pays now,
# but the forest takes a short growth slump that grows with the amount sold, so a sale only pays when the price is high.
# Accepting a carbon-credit offer from the broker gifts credits. Entirely optional: credits can sit unsold forever.
CARBON_CREDIT_PER_PLOT_TICK = 0.01
CARBON_CREDIT_CAP = 100.0
CARBON_BASE_PRICE = 25.0
CARBON_FORECAST_TICKS = 6
CARBON_HISTORY_TICKS = 40

CARBON_SLUMP_BASE_TICKS = 5
CARBON_SLUMP_TICKS_PER_CREDIT = 0.5
CARBON_SLUMP_MAX_TICKS = 40
CARBON_OFFER_CREDITS = 10.0


def carbon_price_factor(tick):
    """Price relative to the base: between about 0.55 and 1.45, from two slow waves added together."""
    return 1.0 + 0.30 * math.sin(tick / 9.0) + 0.15 * math.sin(tick / 3.7 + 1.0)


def carbon_price(tick=None):
    return round(CARBON_BASE_PRICE * carbon_price_factor(runstate.forest_tick if tick is None else tick), 2)


def carbon_trend(tick=None):
    """'rising', 'falling' or 'steady' over the next three ticks."""
    tick = runstate.forest_tick if tick is None else tick
    change = carbon_price(tick + 3) - carbon_price(tick)
    return "rising" if change > 0.75 else "falling" if change < -0.75 else "steady"


def carbon_slump_ticks_for(credits):
    return min(CARBON_SLUMP_MAX_TICKS, CARBON_SLUMP_BASE_TICKS + int(credits * CARBON_SLUMP_TICKS_PER_CREDIT))


def sale_preview(amount=None):
    """What selling `amount` credits (all by default) would pay and cost right now."""
    credits = carbon["credits"] if amount is None else min(float(amount), carbon["credits"])
    credits = max(0.0, credits)
    return {"credits": credits, "price": carbon_price(), "income": round(credits * carbon_price(), 2),
            "slump_ticks": carbon_slump_ticks_for(credits) if credits > 0 else 0}


def _carbon_tick():
    standing = sum(1 for p in runstate.plots if p.state in ACCRUING_STATES)
    carbon["credits"] = min(CARBON_CREDIT_CAP, carbon["credits"] + standing * CARBON_CREDIT_PER_PLOT_TICK)
    if carbon["slump"] > 0:
        carbon["slump"] -= 1


def carbon_status_text():
    preview = sale_preview()
    slump = f" Growth slump: {carbon['slump']} more ticks." if carbon["slump"] > 0 else ""
    return (f"Carbon credits: {carbon['credits']:.1f} (cap {CARBON_CREDIT_CAP:.0f}). Price now {carbon_price():.1f}, {carbon_trend()}. "
            f"Selling all would pay {preview['income']:.1f} and slow growth for {preview['slump_ticks']} ticks.{slump}")


def carbon_chart_svg():
    """The recent price as a line with the coming ticks dotted, so the cycle can be learned and timed."""
    width, height = 260, 70
    first = max(0, runstate.forest_tick - CARBON_HISTORY_TICKS)
    ticks = list(range(first, runstate.forest_tick + CARBON_FORECAST_TICKS + 1))
    prices = [carbon_price(t) for t in ticks]
    low, high = CARBON_BASE_PRICE * 0.5, CARBON_BASE_PRICE * 1.5
    step = width / max(1, len(ticks) - 1)

    def point(i):
        return f"{i * step:.1f},{height - (prices[i] - low) / (high - low) * height:.1f}"
    now = runstate.forest_tick - first
    past = " ".join(point(i) for i in range(0, now + 1))
    future = " ".join(point(i) for i in range(now, len(ticks)))
    return (f'<svg viewBox="0 0 {width} {height}" class="session-sparkline" role="img" aria-label="Carbon price: now {prices[now]:.1f}, {carbon_trend()}">'
            f'<polyline points="{past}" fill="none" stroke="#66b2e8" stroke-width="2"/>'
            f'<polyline points="{future}" fill="none" stroke="#66b2e8" stroke-width="2" stroke-dasharray="3 3"/>'
            f'<circle cx="{now * step:.1f}" cy="{height - (prices[now] - low) / (high - low) * height:.1f}" r="3" fill="currentColor"/></svg>')
