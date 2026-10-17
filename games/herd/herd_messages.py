"""The Real Story info page and the sentences that compare your farm with the pure-growth baseline, certification,
the plant pivot and the consequence of growing.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import info_page

import herd_runstate as runstate
from herd_rules import (
    CERTIFICATION_PRICE_PREMIUM, CERTIFICATION_RATIO_THRESHOLD, CERTIFICATION_ROUNDS_REQUIRED,
    DECOUPLING_MEASURES, HERD_INCOME_PER_UNIT, PLANT_BASED_INCOME_MULTIPLIER, PLANT_PIVOT_COST,
    PLANT_PIVOT_FRACTION_PER_UNIT, REAL_WORLD_REDUCTION_FRACTION,
)
from herd_model import rules_are_custom, rules_unranked
from herd_blind import BLIND_HIDDEN_NOTE, blind_hidden


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Livestock digestion is a major, distinct source of methane — a "
        "gas that traps far more heat than CO2 in the short term, but "
        "also breaks down faster, which makes reducing it one of the "
        "fastest-acting climate levers available. Herd's coupling gauge "
        "and its plant-based pivot are built around that real reduction "
        "pathway."
    ),
    "mechanic_tie_in": (
        "Herd's plant-based pivot mechanic is grounded in a real "
        "documented case — a roughly 42% methane-intensity reduction "
        "achieved through better farm practices — showing decoupling "
        "herd size from methane is achievable, not hypothetical."
    ),
    "sources": [
        {
            "label": "FAO — Livestock and enteric methane",
            "url": "https://www.fao.org/in-action/enteric-methane/en",
            "note": "The definitive real-world figures behind Herd's core mechanic — agriculture's share of methane emissions and where it comes from.",
        },
        {
            "label": "Clean Air Task Force — Accelerating climate solutions in agriculture",
            "url": "https://www.catf.us/2024/10/accelerating-climate-solutions-agriculture-why-reducing-methane-livestock-urgent-opportunity/",
            "note": "Documents a real ~42% methane-intensity reduction from better farm practices — directly supports Herd's decoupling hope angle.",
        },
        {
            "label": "US EPA — Agriculture and Aquaculture: Food for Thought",
            "url": "https://www.epa.gov/snep/agriculture-and-aquaculture-food-thought",
            "note": "Explains why methane's short-lived-but-potent warming profile makes it a distinct lever from CO2.",
        },
    ],
}


# Rendering logic lives in shared/info_page.py now (see that module's
# docstring) -- this used to be a ~25-line implementation byte-identical
# across all 8 climate games. info_page_open stays local here since it's
# part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()


# ===========================================================================
# F1/F3/F13 — pure-growth counterfactual comparison. FarmState.
# counterfactual_funds/counterfactual_methane/counterfactual_score() carry
# the actual math (see advance_round()); everything below is presentation.
# ===========================================================================
def counterfactual_comparison_message():
    """F1 — a live, one-line comparison versus a pure-growth farm with
    the exact same herd size and no decoupling investment ever made."""
    if blind_hidden():
        return BLIND_HIDDEN_NOTE
    if runstate.farm.round_number <= 1:
        return "Advance a round to see how your farm compares to a pure-growth baseline."
    gap = runstate.farm.score() - runstate.farm.counterfactual_score()
    if gap >= 0:
        return f"Your farm is {gap:.0f} points ahead of a pure-growth farm with the same herd size."
    return f"Your farm is {abs(gap):.0f} points behind a pure-growth farm with the same herd size."


COMPARE_FALLBACK = "Comparison with other farms isn't available yet."
UNRANKED_COMPARE_NOTE = "Custom ranch rules: this run is unranked, so it is not compared with other farms."
LOADOUT_UNRANKED_NOTE = "Starting loadout: this run is unranked, so it is not compared with other farms."


def unranked_compare_note():
    """Why this run is not compared with other farms: custom rules first, else a starting loadout."""
    return UNRANKED_COMPARE_NOTE if (runstate.farm.custom_rules_used or rules_are_custom()) else LOADOUT_UNRANKED_NOTE


def _request_comparison():
    """F7 — asks the page's optional JS hook (window.herdCompare, see
    index.html) to fill #report-card-compare with a cross-player
    percentile, against the shared aggregate-stats endpoint (Z1,
    planning/TODO.md). Byte-for-byte the same optional-hook shape as
    Grid's own C15 (`_request_comparison()`/`window.gridCompare`) --
    the reference integration for this exact feature -- right down to
    the lazy `from js import window` import and the `getattr` default,
    so an absent hook (pytest, or a page that never defines it) is a
    silent no-op and the fallback text above simply stays put.

    `methane` (this farm's lifetime accumulated methane) is the field
    used, not a raw coupling ratio -- `coupling_ratio()` is a live
    per-round rate with no save-state field of its own, so it isn't
    one of the numeric paths `app/stats.py`'s STATS_FIELDS whitelists
    for this game, and the single-field `/percentile` endpoint can only
    rank a whitelisted field. `methane` is the closest real stand-in:
    it's the direct cumulative output of coupling_ratio() x herd_size
    every round (see `methane_this_round()`), so two farms at a similar
    round/herd_size mostly diverge on methane by how well they've
    decoupled -- same relationship Grid's own `emissions` field has to
    its cost-curve mechanic."""
    if rules_unranked():
        return  # F-1: custom-rule runs are not compared with other farms
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "herdCompare", None)
    if hook is not None:
        hook(float(runstate.farm.methane), runstate.farm.round_number)


def beat_percentage_message():
    """F6 — the exact percentage the score beats (or trails) the
    pure-growth baseline by."""
    baseline = runstate.farm.counterfactual_score()
    if abs(baseline) < 1e-9:
        return "Baseline score is zero, so a percentage comparison isn't meaningful yet."
    pct = (runstate.farm.score() - baseline) / abs(baseline) * 100
    if pct >= 0:
        return f"Your score beats the pure-growth baseline by {pct:.1f}%."
    return f"Your score trails the pure-growth baseline by {abs(pct):.1f}%."


def investment_summary_message():
    """F26 — a summary list where the three efficiency measures carry
    their own icons and the plant-based pivot is visibly a separate
    lever (a distinct marker plus the word 'separate')."""
    parts = [
        f"{spec['icon']} {spec['label']} x{runstate.farm.decoupling_investment[m]}"
        for m, spec in DECOUPLING_MEASURES.items()
    ]
    return (
        "Efficiency measures: " + ", ".join(parts)
        + f"  |  \U0001F331 Separate lever \u2014 Plant-Based Pivot x{runstate.farm.plant_pivot_investment}"
    )


def certification_message():
    if runstate.farm.certified:
        return (
            f"Certified sustainable: permanent +{CERTIFICATION_PRICE_PREMIUM * 100:.0f}% price premium "
            "on your output."
        )
    return (
        f"Sustainable certification: {runstate.farm.certification_streak}/{CERTIFICATION_ROUNDS_REQUIRED} "
        f"rounds at a coupling ratio of {CERTIFICATION_RATIO_THRESHOLD:.2f} or lower "
        f"(earns a permanent +{CERTIFICATION_PRICE_PREMIUM * 100:.0f}% price premium)."
    )


def plant_pivot_confirm_message():
    """F12 — the confirm dialog's exact income tradeoff, computed from
    the live constants."""
    discount = (1 - PLANT_BASED_INCOME_MULTIPLIER) * 100
    total = PLANT_PIVOT_FRACTION_PER_UNIT * (1 - PLANT_BASED_INCOME_MULTIPLIER) * 100
    return (
        f"Invest {PLANT_PIVOT_COST} funds in the Plant-Based Pivot? It shifts "
        f"{PLANT_PIVOT_FRACTION_PER_UNIT * 100:.0f}% of your output to near-zero-methane plant-based "
        f"production. Tradeoff: shifted output earns {discount:.0f}% less income per unit, so this step "
        f"lowers your total income by about {total:.2f}%."
    )


# F15 — surfacing the real documented ~42% methane-intensity-reduction
# figure (also cited in INFO_PAGE) as a live in-game comparison.
def real_world_comparison_message():
    pct = runstate.farm.decoupled_fraction() * 100
    real_pct = REAL_WORLD_REDUCTION_FRACTION * 100
    if runstate.farm.decoupled_fraction() > REAL_WORLD_REDUCTION_FRACTION:
        return (
            f"Congratulations: you've cut emissions intensity by {pct:.0f}%, beating the real "
            f"~{real_pct:.0f}% benchmark documented on real farms."
        )
    if runstate.farm.decoupled_fraction() >= REAL_WORLD_REDUCTION_FRACTION:
        return (
            f"You've cut emissions intensity by {pct:.0f}% — matching the real "
            f"~{real_pct:.0f}% reduction documented on real farms."
        )
    return (
        f"You've cut emissions intensity by {pct:.0f}% so far — real farms have documented "
        f"a ~{real_pct:.0f}% reduction through better practices."
    )


# F8 — a combined readout for how the efficiency measures (feed/caps/
# capture) and the plant-based pivot interact, since coupling_ratio()
# blends both but the UI otherwise only ever shows them separately.
def combined_decoupling_message():
    efficiency_ratio = runstate.farm._efficiency_coupling_ratio()
    final_ratio = runstate.farm.coupling_ratio()
    plant_fraction = runstate.farm.plant_based_fraction()
    if plant_fraction <= 0:
        return (
            f"Efficiency measures alone bring you to {efficiency_ratio:.2f} methane/herd/round "
            "— the plant-based pivot isn't active yet."
        )
    return (
        f"Efficiency measures bring you to {efficiency_ratio:.2f}, and the {plant_fraction * 100:.0f}% "
        f"plant-based pivot blends that down further to {final_ratio:.2f} methane/herd/round."
    )


# F9 — a consequence preview next to the Grow Herd button: what the very
# next unit would cost and add, computed without mutating state.
def grow_consequence_message():
    cost = runstate.farm.grow_herd_cost()
    methane_delta = runstate.farm.coupling_ratio()
    fraction = runstate.farm.plant_based_fraction()
    income_multiplier = (1 - fraction) + fraction * PLANT_BASED_INCOME_MULTIPLIER
    income_per_unit = (
        HERD_INCOME_PER_UNIT * income_multiplier * runstate.farm.certification_multiplier()
        * (1 - runstate.farm.pressure_fraction())
    )
    # F18 — before -> after totals with a direction arrow.
    income_before = runstate.farm.herd_size * income_per_unit
    income_after = (runstate.farm.herd_size + 1) * income_per_unit
    methane_before = runstate.farm.methane_this_round()
    methane_after = methane_before + methane_delta
    return (
        f"Next unit: costs {cost:.0f}. Income/round {income_before:.1f} \u2192 {income_after:.1f} \u2191, "
        f"methane/round {methane_before:.2f} \u2192 {methane_after:.2f} \u2191."
    )
