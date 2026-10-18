"""Plain-language status sentences: trend, real-world comparison, scorecard, vignette, chain-flow message."""

import math

from js import document

import loop_runstate as runstate
from loop_rules import CATEGORY_LOOP_DETAIL, REAL_WORLD_CIRCULARITY_BENCHMARK, SECTOR_COMPARISONS
from loop_runstate import current_vignette_item


def circular_trend_message(trend):
    if trend is None:
        return "Not enough cycles yet to show a trend."
    first_half_avg, second_half_avg = trend
    first_pct, second_pct = first_half_avg * 100, second_half_avg * 100
    if second_half_avg > first_half_avg:
        return f"Your chain is closing the loop over time ({first_pct:.0f}% → {second_pct:.0f}% circular) — the redesign is paying off."
    if second_half_avg < first_half_avg:
        return f"Your chain has drifted back toward a straight line ({first_pct:.0f}% → {second_pct:.0f}% circular)."
    return f"Your chain's circular share has held steady at {second_pct:.0f}%."


def real_world_comparison_message(lifetime_fraction):
    """Iteration-pass addition: a rough, honestly-hedged real-world
    comparison point for the player's lifetime circular share."""
    pct = lifetime_fraction * 100
    benchmark_pct = REAL_WORLD_CIRCULARITY_BENCHMARK * 100
    if lifetime_fraction > REAL_WORLD_CIRCULARITY_BENCHMARK:
        return (
            f"Your chain is running at {pct:.0f}% circular — well above the "
            f"roughly {benchmark_pct:.0f}% average estimated for real-world material "
            f"circularity today (a ballpark figure, not a precise benchmark)."
        )
    return (
        f"Your chain is running at {pct:.0f}% circular, versus a roughly "
        f"{benchmark_pct:.0f}% estimated real-world average today (a ballpark figure, "
        f"not a precise benchmark)."
    )


def sector_comparison_message(lifetime_fraction):
    """H9: a few alternate real-world sector comparisons beyond the
    single static REAL_WORLD_CIRCULARITY_BENCHMARK line above, so the
    player sees more than one real-world reference point. Same hedge
    language throughout — these are ballpark figures, not a precise or
    authoritative dataset."""
    clauses = []
    for label, rate in SECTOR_COMPARISONS:
        rate_pct = rate * 100
        relation = "above" if lifetime_fraction > rate else "below"
        clauses.append(f"{relation} the ~{rate_pct:.0f}% estimated for {label}")
    return "For context, your circular share is also " + "; ".join(clauses) + " (again, ballpark figures, not precise benchmarks)."


def scorecard_rows(lifetime_fraction):
    """H19: the player's lifetime circular share against EVERY benchmark at
    once (the overall real-world figure plus each sector), as plain data:
    label, the benchmark, the signed gap in percentage points and a text
    verdict. Same hedge as the two single-line comparisons above: ballparks,
    not a precise dataset."""
    rows = []
    entries = [("overall real-world average", REAL_WORLD_CIRCULARITY_BENCHMARK)] + list(SECTOR_COMPARISONS)
    for label, rate in entries:
        gap = (lifetime_fraction - rate) * 100
        if abs(gap) < 0.5:
            verdict = "level with"
            symbol = "\u25C6"
        elif gap > 0:
            verdict = f"{gap:.0f} points above"
            symbol = "\u25B2"
        else:
            verdict = f"{-gap:.0f} points below"
            symbol = "\u25BC"
        rows.append({
            "label": label, "benchmark": rate, "gap_points": gap, "verdict": verdict, "symbol": symbol,
            "mine_width": min(100.0, lifetime_fraction * 100), "benchmark_width": min(100.0, rate * 100),
        })
    return rows


def render_scorecard():
    container = document.getElementById("scorecard-list")
    container.innerHTML = ""
    for row in scorecard_rows(runstate.chain.lifetime_circular_fraction()):
        line = document.createElement("div")
        line.className = "scorecard-row"
        text = document.createElement("p")
        text.className = "scorecard-text"
        text.innerText = f"{row['symbol']} {row['verdict']} the ~{row['benchmark'] * 100:.0f}% for {row['label']}"
        line.appendChild(text)
        bars = document.createElement("div")
        bars.className = "scorecard-bars"
        mine = document.createElement("div")
        mine.className = "scorecard-bar scorecard-bar--mine"
        mine.style.width = f"{row['mine_width']:.0f}%"
        bench = document.createElement("div")
        bench.className = "scorecard-bar scorecard-bar--benchmark"
        bench.style.width = f"{row['benchmark_width']:.0f}%"
        bars.appendChild(mine)
        bars.appendChild(bench)
        line.appendChild(bars)
        container.appendChild(line)


def _request_community_comparison():
    """H5: asks the page's optional JS hook (window.loopCompare, see
    index.html) to fill #community-comparison-display with a real
    cross-player percentile for lifetime circular share, once the shared
    aggregate-stats endpoint (planning/TODO.md Z1) has enough saves to
    answer -- unlike real_world_comparison_message()/sector_comparison_message()
    above, which are static, hedged ballpark figures, not live player data.

    Same lazy `from js import window`/getattr-default shape as Grid's own
    `_request_comparison()` (games/grid/game.py C15) and this file's own
    `_confirm_dialog_ask()`: the pytest fake-DOM harness's `js` module only
    ever fakes `document`/`setTimeout` (see tests/conftest.py), never
    `window`, so this is a safe no-op under test, and a safe no-op on any
    page that never defines `window.loopCompare` either."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "loopCompare", None)
    if hook is not None:
        hook(runstate.chain.lifetime_circular_fraction())


def vignette_message(fraction, item=None, variant_seed=0):
    """A concrete, one-item side-story tracking the same underlying
    circular_fraction_this_cycle() the abstract chain view already
    shows — makes the abstraction tangible for a player who doesn't
    naturally read a flow diagram.

    H14: each fraction bucket now has a couple of alternate phrasings
    instead of exactly one. `variant_seed` (render() passes
    chain.cycle_number) picks among them so replaying doesn't always
    show identical text — defaults to 0 (the first/original phrasing in
    each bucket) so every existing direct call to this function keeps
    its original behavior."""
    item = item or current_vignette_item()
    bucket = "closed" if fraction >= 1.0 else "majority" if fraction >= 0.5 else "minority" if fraction > 0.0 else "none"

    # H20: category-specific loop mechanics (see CATEGORY_LOOP_DETAIL's own
    # comment) instead of the same generic "repaired... recycled" phrase
    # regardless of which goods category is active. Falls back to the
    # original generic wording for any category not covered there, so an
    # unlisted/future category never crashes this function.
    details = CATEGORY_LOOP_DETAIL.get(runstate.chain.goods_category, {}).get(bucket)
    if details:
        variants = [f"Follow {item}: {detail}." for detail in details]
    elif bucket == "closed":
        variants = [
            f"Follow {item}: it was repaired once, then eventually recycled — "
            "its materials became part of the casing for the next one off the line.",
            f"Follow {item}: by the time it wore out, every stage of its journey "
            "looped back — nothing about it ended up as waste.",
        ]
    elif bucket == "majority":
        variants = [
            f"Follow {item}: it gets used, and there's a good chance it comes "
            "back through repair or recycling when its owner is done with it.",
            f"Follow {item}: more than half its journey loops back somewhere — "
            "repaired, reused, or recycled rather than simply discarded.",
        ]
    elif bucket == "minority":
        variants = [
            f"Follow {item}: it gets used, then thrown away — though a little of "
            "what's inside it might still come back as recycled material someday.",
            f"Follow {item}: most of its journey is still a straight line, but a "
            "small share of what made it does loop back eventually.",
        ]
    else:
        variants = [
            f"Follow {item}: mined, made, used once, thrown away. Nothing about it "
            "comes back.",
            f"Follow {item}: extracted, manufactured, used briefly, discarded — "
            "nowhere in this chain does it loop back.",
        ]
    return variants[variant_seed % len(variants)]


def chain_flow_message(fraction, cycle_number=1):
    """H11: cycle 1's straight-line message (before the player has had a
    chance to invest in anything) is deliberately lighter than the
    starker framing shown from cycle 2 onward if the chain is still
    uninvested — an encouraging nudge for a brand-new player rather than
    a discouraging "still 100% extraction" statement on the very first
    screen they see."""
    if fraction <= 0.0:
        if cycle_number <= 1:
            return (
                "You're just getting started — invest in circularity below to "
                "start looping supply back instead of extracting new material."
            )
        return "Straight line: 100% of production needs new extraction."
    if fraction >= 1.0:
        return "Loop closed: 100% of production comes from repair, reuse & recycling. No new extraction needed."
    return f"{fraction * 100:.0f}% of the chain is looping back — {100 - fraction * 100:.0f}% still needs new extraction."


def cycles_to_close_loop_message():
    """H6: a rough plain-language projection of how many more cycles, at
    the chain's current rate of improvement, before the loop closes
    completely. Reuses circular_trend()'s own first-half/second-half
    comparison rather than inventing a second trend calculation, so this
    projection can never disagree with the trend line already shown."""
    fraction = runstate.chain.circular_fraction_this_cycle()
    if fraction >= 1.0:
        return "The loop is already closed."
    trend = runstate.chain.circular_trend()
    if trend is None:
        return "Not enough cycles yet to project when the loop might close."
    first_half_avg, second_half_avg = trend
    n = len(runstate.chain.circular_fraction_log)
    half = n // 2
    window = max(1, n - half)
    rate_per_cycle = (second_half_avg - first_half_avg) / window
    if rate_per_cycle <= 0:
        return "At the current rate, the loop isn't projected to close — try increasing circularity investment."
    cycles_needed = math.ceil((1.0 - fraction) / rate_per_cycle)
    cycle_word = "cycle" if cycles_needed == 1 else "cycles"
    return f"At the current rate of improvement, the loop could close in roughly {cycles_needed} more {cycle_word}."
