"""The emissions and cost trend graph (SVG, table and description), the Info Page content and the comparison messages.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import comparison_chart
import ghost as ghost_lib

import grid_runstate as runstate
from grid_rules import DAMAGE_SEVERITY_THRESHOLD
from grid_career_data import _ghost_from_history, _validate_career_ghost


TREND_GRAPH_WIDTH = 280
TREND_GRAPH_HEIGHT = 80

# Shown once, the first time a player builds any renewable plant —
# grounds the cost-curve mechanic (Milestone 2) in the real trend it's
# modeling. Iteration-pass addition: a light factual anchor, not a
# lecture, per the cross-cutting note in CLAUDE.md.
RENEWABLE_UNLOCK_BLURB = (
    "In the real world, each doubling of solar deployment has "
    "historically cut its cost by roughly 20% — economists call this a "
    "learning curve, and it's exactly what's driving your renewable "
    "prices down here."
)

# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Electricity generation is one of the largest single sources of "
        "global emissions, and the fastest way to cut it is building out "
        "cleaner capacity — not rationing power. Renewables have gotten "
        "dramatically cheaper the more of them get built, a real economic "
        "trend called a learning curve. That's the same tension Grid asks "
        "you to manage: lean into that cheaper long-run path, or lean on "
        "familiar fossil capacity."
    ),
    "mechanic_tie_in": (
        "Grid's cost curve and its global-comparison line are grounded in "
        "published wind/solar learning-rate data (roughly 15%/24% cost "
        "decline per capacity doubling), not an invented number."
    ),
    "sources": [
        {
            "label": "IEA — Rapid rollout of clean technologies makes energy cheaper, not more costly",
            "url": "https://www.iea.org/news/rapid-rollout-of-clean-technologies-makes-energy-cheaper-not-more-costly",
            "note": "Real-world backing for Grid's central claim: leaning renewable is the cheaper long-run path, not a sacrifice.",
        },
        {
            "label": "Oxford Institute for Energy Studies — A critical assessment of learning curves for solar and wind",
            "url": "https://www.oxfordenergy.org/publications/a-critical-assessment-of-learning-curves-for-solar-and-wind-power-technologies/",
            "note": "A balanced, critical look at the same cost-decline concept Grid's core mechanic is built on.",
        },
        {
            "label": "US DOE / Lawrence Berkeley National Lab — Learning a Better Way To Forecast Wind and Solar Energy Costs",
            "url": "https://www.energy.gov/cmei/solar/articles/learning-better-way-forecast-wind-and-solar-energy-costs",
            "note": "The actual learning-rate figures (wind ~15%, solar ~24% per capacity doubling) behind Grid's cost curve.",
        },
        {
            "label": "IEA — Breakthrough Agenda Report 2025: Power",
            "url": "https://www.iea.org/reports/breakthrough-agenda-report-2025/power",
            "note": "Current real-world electricity cost figures, grounding the global-comparison line.",
        },
    ],
}


def _normalize_series(series, height, lo=None, hi=None):
    """Maps a series to SVG y-coordinates within [0, height]. Defaults to
    scaling against its own min/max so differently-scaled series
    (emissions counts, renewable costs) can share one chart; an explicit
    lo/hi lets two series (a player's emissions vs. the global-reference
    benchmark) share one scale instead, so they stay directly comparable."""
    if lo is None:
        lo = min(series)
    if hi is None:
        hi = max(series)
    if hi - lo < 1e-9:
        return [height / 2 for _ in series]
    return [height - ((v - lo) / (hi - lo)) * height for v in series]


TREND_LINE_KEYS = ("emissions", "cost", "benchmark", "funds", "demand", "clean")
TREND_LINE_LABEL = {
    "emissions": "Your emissions",
    "cost": "Avg renewable cost",
    "benchmark": "Global-average benchmark",
    "funds": "Funds",
    "demand": "Demand",
    "clean": "Clean share",
}
# C-12: what the graph shows when nothing is passed in (the three lines it always had).
DEFAULT_TREND_LINES = frozenset({"emissions", "cost", "benchmark"})
TREND_TABLE_MAX_ROWS = 15


def visible_trend_lines():
    """C-12: the trend lines the player has switched on."""
    return {key for key in TREND_LINE_KEYS if runstate.prefs.get("trend_" + key)}


def ghost_record():
    """GC-9 / Z-3c: the best finished run in the career as a small dict (label, grade, score, rounds and the
    clean-share and funds ghost traces, funds None when it was not kept), or None if there is none yet. The
    stored career ghost wins; a career that has none (a save from before it) is read from the history."""
    saved = runstate.career.get("ghost")
    found = _validate_career_ghost(saved) if saved is not None else None
    if found is None:
        found = _ghost_from_history(runstate.career["history"], runstate.career["runs"])
    if found is None:
        return None
    found["rounds"] = found["clean"]["turns"]
    return found


def _whole_points(result):
    """Grid reads its gaps in whole points: a gap under one half is level, any other is rounded."""
    if result is None or result["status"] in ("ended", "level"):
        return result
    lead = int(round(result["lead"]))
    if lead == 0:
        return dict(result, status="level", lead=0)
    return dict(result, lead=lead)


def ghost_delta_text(clean_history, funds_history, ghost):
    """GC-9: where the run stands against the ghost at the latest round, in words. Z-3c: the ahead/behind/level
    sentences are the shared ghost.summary ones, one for the clean share and one for funds."""
    if not ghost:
        return "No finished run to race yet. Finish a run from the Career panel and your best one appears here as a ghost."
    n = len(clean_history)
    head = f"Ghost: {ghost['label']} (grade {ghost['grade']}, score {ghost['score']:.0f}/100, {ghost['rounds']} rounds)."
    if n == 0:
        return head + " Play a round to start the comparison."
    name = ghost["label"]
    clean = _whole_points(ghost_lib.compare([v * 100 for v in clean_history], ghost["clean"]))
    if clean is None or clean["status"] == "ended":
        return head + f" That run ended before round {n}, so there is nothing to compare with now."
    text = f"{head} Clean share (now {clean_history[-1] * 100:.0f}%, ghost {clean['ghost']:.0f}%): " \
        + ghost_lib.summary(clean, label=name, unit=" points") + "."
    if ghost.get("funds") and funds_history and len(funds_history) == n:
        funds = _whole_points(ghost_lib.compare(funds_history, ghost["funds"]))
        if funds is not None and funds["status"] != "ended":
            text += f" Funds (now {funds_history[-1]:.0f}, ghost {funds['ghost']:.0f}): " \
                + ghost_lib.summary(funds, label=name) + "."
    return text


def trend_series(emissions_history, cost_history, global_reference_history, clean_fraction_history,
                 funds_history, demand_history):
    """C-12 / C-19: every trend series as plain lists aligned to the emissions history (a series that is not
    the same length, such as the funds of a save from before they were kept, is None)."""
    n = len(emissions_history)

    def aligned(values, scale=1.0):
        if values is None or len(values) != n:
            return None
        return [v * scale for v in values]

    return {
        "emissions": list(emissions_history),
        "cost": aligned(cost_history),
        "benchmark": aligned(global_reference_history),
        "funds": aligned(funds_history),
        "demand": aligned(demand_history),
        "clean": aligned(clean_fraction_history, 100.0),
    }


def trend_graph_svg(emissions_history, cost_history, global_reference_history, clean_fraction_history=None,
                    visible=None, funds_history=None, demand_history=None, ghost=None):
    """Trend graph. Always built from the player's emissions (rising, red), average renewable cost (falling
    as investment compounds) and a hardcoded global-average emissions benchmark (dashed grey) -- the Pass 2
    addition that gives the player's own emissions line something concrete to be measured against.

    C-12: `visible` (a set of TREND_LINE_KEYS, default the three above) switches lines on or off, and three
    more lines can be shown: funds, demand and clean share. Each line has its own colour AND its own dash
    pattern. The best-round diamond stays on whichever visible line is first in the order emissions, clean
    share, cost, funds, demand, benchmark, so it is never lost when a line is hidden.
    GC-9: `ghost` (see ghost_record()) draws the best earlier run's clean share and funds as faint lines.

    C15: every point on every line also gets a small hoverable marker carrying the exact round/value in a
    native <title> tooltip.

    Z17: the emissions-vs-global-reference pair is built from shared/comparison_chart.py's
    normalize_together()/marker_fragment() building blocks."""
    if len(emissions_history) < 2:
        return ""
    visible = DEFAULT_TREND_LINES if visible is None else set(visible)
    n = len(emissions_history)
    series = trend_series(
        emissions_history, cost_history, global_reference_history, clean_fraction_history,
        funds_history, demand_history,
    )
    xs = comparison_chart.xs_for(n, TREND_GRAPH_WIDTH)
    # Normalized together (not each series against its own min/max) so the player's emissions line and the
    # global-reference line stay comparable to each other on the same scale, whichever of the two is hidden.
    emissions_ys, global_ys = comparison_chart.normalize_together(
        emissions_history, global_reference_history, TREND_GRAPH_HEIGHT
    )
    ys = {"emissions": emissions_ys, "benchmark": global_ys}
    if series["cost"] is not None:
        ys["cost"] = _normalize_series(series["cost"], TREND_GRAPH_HEIGHT)
    if series["demand"] is not None:
        ys["demand"] = _normalize_series(series["demand"], TREND_GRAPH_HEIGHT)
    if series["clean"] is not None:
        ys["clean"] = _normalize_series(series["clean"], TREND_GRAPH_HEIGHT, 0.0, 100.0)

    ghost_parts = []
    ghost_funds_points = []
    if series["funds"] is not None:
        funds_lo, funds_hi = min(series["funds"]), max(series["funds"])
        if ghost and ghost.get("funds") and "funds" in visible:
            ghost_funds_points = [
                (i, ghost_lib.value_at(ghost["funds"], i + 1)) for i in range(n)
            ]
            ghost_funds_points = [(i, v) for i, v in ghost_funds_points if v is not None]
            if ghost_funds_points:
                funds_lo = min(funds_lo, min(v for _, v in ghost_funds_points))
                funds_hi = max(funds_hi, max(v for _, v in ghost_funds_points))
        ys["funds"] = _normalize_series(series["funds"], TREND_GRAPH_HEIGHT, funds_lo, funds_hi)
        if ghost_funds_points:
            gpts = " ".join(
                f"{xs[i]:.1f},{_normalize_series([v], TREND_GRAPH_HEIGHT, funds_lo, funds_hi)[0]:.1f}"
                for i, v in ghost_funds_points
            )
            ghost_parts.append(
                f'<polyline points="{gpts}" class="trend-line trend-line--ghost trend-line--funds-ghost">'
                f"<title>Ghost funds ({ghost['label']})</title></polyline>"
            )
    if ghost and "clean" in visible:
        clean_points = [(i, ghost_lib.value_at(ghost["clean"], i + 1)) for i in range(n)]
        clean_points = [(i, v) for i, v in clean_points if v is not None]
        if clean_points:
            gpts = " ".join(
                f"{xs[i]:.1f},{_normalize_series([v], TREND_GRAPH_HEIGHT, 0.0, 100.0)[0]:.1f}"
                for i, v in clean_points
            )
            ghost_parts.append(
                f'<polyline points="{gpts}" class="trend-line trend-line--ghost trend-line--clean-ghost">'
                f"<title>Ghost clean share ({ghost['label']})</title></polyline>"
            )

    lines = ""
    markers = ""
    formats = {"emissions": "{:.0f}", "cost": "{:.0f}", "benchmark": "{:.0f}", "funds": "{:.0f}",
               "demand": "{:.0f}", "clean": "{:.0f}%"}
    # Drawing order is the original one (benchmark, emissions, cost) and the new lines after it.
    for key in ("benchmark", "emissions", "cost", "funds", "demand", "clean"):
        if key not in visible or key not in ys or series[key] is None:
            continue
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys[key]))
        css = "global" if key == "benchmark" else key
        lines += f'<polyline points="{points}" class="trend-line trend-line--{css}" />'
        marker_class = f"trend-point trend-point--{css}"
        markers += comparison_chart.marker_fragment(
            xs, ys[key], series[key], marker_class, TREND_LINE_LABEL[key], index_label="Round",
            value_format=formats[key],
        )

    # C12: a diamond marker (shape, not just color) at the player's best round -- highest clean share,
    # earliest on ties. C-12 (checkboxes): it moves to the first visible line so hiding emissions keeps it.
    best_marker = ""
    if clean_fraction_history and len(clean_fraction_history) == n and max(clean_fraction_history) > 0:
        best_i = clean_fraction_history.index(max(clean_fraction_history))
        anchor = next((k for k in ("emissions", "clean", "cost", "funds", "demand", "benchmark")
                       if k in visible and k in ys), None)
        bx = xs[best_i]
        by = ys[anchor][best_i] if anchor else TREND_GRAPH_HEIGHT / 2
        best_marker = (
            f'<polygon points="{bx:.1f},{by - 6:.1f} {bx + 5:.1f},{by:.1f} {bx:.1f},{by + 6:.1f} {bx - 5:.1f},{by:.1f}" '
            f'class="trend-best-marker"><title>Best round: Round {best_i + 1} '
            f"({clean_fraction_history[best_i] * 100:.0f}% clean)</title></polygon>"
        )

    return (
        f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="trend-graph-svg">'
        f"{''.join(ghost_parts)}"
        f"{lines}"
        f"{markers}"
        f"{best_marker}"
        f"</svg>"
    )


def _trend_direction(values, unit=""):
    first, last = values[0], values[-1]
    word = "rose" if last > first else ("fell" if last < first else "held at")
    if word == "held at":
        return f"held at {last:.0f}{unit}"
    return f"{word} from {first:.0f}{unit} to {last:.0f}{unit}"


def trend_description(series, visible):
    """C-19: the trend in a sentence or two, for the table view (and for anyone who does not use the graph)."""
    n = len(series["emissions"])
    if n < 2:
        return "Not enough rounds yet to describe a trend."
    parts = []
    for key in TREND_LINE_KEYS:
        if key not in visible or series[key] is None:
            continue
        unit = "%" if key == "clean" else ""
        parts.append(f"{TREND_LINE_LABEL[key].lower()} {_trend_direction(series[key], unit)}")
    if not parts:
        return "No lines are switched on, so there is nothing to describe."
    return f"Over {n} rounds: " + "; ".join(parts) + "."


def trend_table_html(series, visible, clean_fraction_history=None, ghost=None):
    """C-19: the trend graph's numbers as a plain table (last TREND_TABLE_MAX_ROWS rounds, newest last)."""
    n = len(series["emissions"])
    if n < 1:
        return ""
    keys = [k for k in TREND_LINE_KEYS if k in visible and series[k] is not None]
    best_i = None
    if clean_fraction_history and len(clean_fraction_history) == n and max(clean_fraction_history) > 0:
        best_i = clean_fraction_history.index(max(clean_fraction_history))
    head = "<th scope=\"col\">Round</th>" + "".join(f'<th scope="col">{TREND_LINE_LABEL[k]}</th>' for k in keys)
    if ghost and "clean" in visible:
        head += '<th scope="col">Ghost clean share</th>'
    if ghost and "funds" in visible:
        head += '<th scope="col">Ghost funds</th>'
    rows = []
    first = max(0, n - TREND_TABLE_MAX_ROWS)
    for i in range(first, n):
        best = " (best round)" if best_i == i else ""
        cells = f'<th scope="row">{i + 1}{best}</th>'
        for k in keys:
            unit = "%" if k == "clean" else ""
            cells += f"<td>{series[k][i]:.0f}{unit}</td>"
        if ghost and "clean" in visible:
            g = ghost_lib.value_at(ghost["clean"], i + 1)
            cells += f"<td>{'-' if g is None else f'{g:.0f}%'}</td>"
        if ghost and "funds" in visible:
            g = ghost_lib.value_at(ghost.get("funds"), i + 1)
            cells += f"<td>{'-' if g is None else f'{g:.0f}'}</td>"
        rows.append(f"<tr>{cells}</tr>")
    note = f" Showing the last {TREND_TABLE_MAX_ROWS} of {n} rounds." if n > TREND_TABLE_MAX_ROWS else ""
    return (
        f'<table class="chart-table"><caption>Trend numbers by round.{note}</caption>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def global_comparison_message(emissions, global_reference_emissions):
    """Z17: delegates its ahead/behind/tie branching to the shared
    shared/comparison_chart.py's comparison_message() -- this game's own
    wording is kept verbatim via the ahead_text/behind_text/tie_text
    overrides, so this is a pure refactor with no player-visible change."""
    return comparison_chart.comparison_message(
        emissions,
        global_reference_emissions,
        subject="grid's emissions",
        higher_is_better=False,
        ahead_text=(
            f"Your grid has emitted {emissions:.0f} vs. an estimated {global_reference_emissions:.0f} "
            "for a grid built to the global-average fossil mix — you're ahead of the curve."
        ),
        behind_text=(
            f"Your grid has emitted {emissions:.0f} vs. an estimated {global_reference_emissions:.0f} "
            "for a grid built to the global-average fossil mix — you're behind the curve."
        ),
        tie_text="Your grid is tracking almost exactly the global-average fossil mix so far.",
    )


def business_as_usual_message(emissions, bau_emissions):
    """C17: the closing counterfactual -- what this exact same installed
    capacity would have emitted had it all been built as coal, compared
    to what this grid actually emitted with its real fuel mix. Distinct
    from global_comparison_message() above: that one benchmarks against a
    real-world-ish average mix, this one isolates this player's own
    fuel-mix decisions specifically, holding how much got built constant."""
    if bau_emissions <= 0:
        return "Not enough rounds yet to compare against a business-as-usual grid."
    avoided = max(0.0, bau_emissions - emissions)
    if avoided <= 0:
        return (
            f"A business-as-usual grid built entirely from coal would have emitted "
            f"{bau_emissions:.0f} by now -- yours has emitted {emissions:.0f}, "
            "no better than staying all-coal so far."
        )
    pct_avoided = (avoided / bau_emissions) * 100
    return (
        f"A business-as-usual grid built entirely from coal would have emitted "
        f"{bau_emissions:.0f} by now. Yours has emitted {emissions:.0f} -- "
        f"{avoided:.0f} avoided ({pct_avoided:.0f}% less)."
    )


def disruption_risk_message(probability, severity):
    """Iteration Pass 3: makes the emissions-meter -> disruption-risk
    coupling explicit in words. The probability/severity math already
    scales directly off the emissions meter (Milestone 3) — this just
    makes sure the player can *read* that connection instead of only
    inferring it after the fact from event timing, so the meter reads as
    the actual mechanism gating success, not a side-score next to it."""
    if probability <= 0.0:
        return "No disruption risk yet — emissions are still at zero."
    pct = probability * 100
    if severity >= DAMAGE_SEVERITY_THRESHOLD:
        return (
            f"Rising emissions mean a {pct:.0f}% chance of a disruption next round — "
            "severe enough to damage a fossil plant if it hits."
        )
    return f"Rising emissions mean a {pct:.0f}% chance of a disruption next round."


def clean_trend_message(trend):
    if trend is None:
        return "Not enough rounds yet to show a trend."
    first_half_avg, second_half_avg = trend
    first_pct, second_pct = first_half_avg * 100, second_half_avg * 100
    if second_half_avg > first_half_avg:
        return f"Your grid is getting cleaner over time ({first_pct:.0f}% → {second_pct:.0f}%) — the transition is paying off."
    if second_half_avg < first_half_avg:
        return f"Your grid has gotten dirtier over time ({first_pct:.0f}% → {second_pct:.0f}%)."
    return f"Your grid's cleanliness has held steady at {second_pct:.0f}%."
