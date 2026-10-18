"""Per-node purchase sparklines (H-26)."""

import html

from js import document

import loop_runstate as runstate
from loop_rules import BUY_KINDS, CIRCULARITY_INVESTMENTS


# ---- H-26 spending sparklines on the ring nodes ----------------------------------------------------------------------
SPARK_CYCLES = 12


def node_spend_series(measure):
    """Funds spent on one circularity measure in each of the last SPARK_CYCLES cycles, the cycle in progress last."""
    index = BUY_KINDS.index(measure)
    cost = CIRCULARITY_INVESTMENTS[measure]["cost"]
    rows = list(runstate.chain.buy_log[-(SPARK_CYCLES - 1):]) + [runstate.chain.buys_now]
    return [row[index] * cost for row in rows]


def spend_history_text(measure):
    series = node_spend_series(measure)
    label = CIRCULARITY_INVESTMENTS[measure]["label"]
    return f"{label} spending per cycle, latest last: " + ", ".join(f"{value:.0f}" for value in series) + "."


def sparkline_svg(values, width=96.0, height=30.0):
    """A tiny line chart of `values` (a flat line at the bottom when everything is zero)."""
    top = max(values) if values else 0
    pad = 3.0
    points = []
    for i, value in enumerate(values):
        x = pad + (width - 2 * pad) * (i / (len(values) - 1) if len(values) > 1 else 0.5)
        y = height - pad - (height - 2 * pad) * (value / top if top > 0 else 0)
        points.append((x, y))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    end_x, end_y = points[-1] if points else (pad, height - pad)
    return (
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" class="spark-svg" aria-hidden="true">'
        f'<polyline points="{line}" fill="none" class="spark-line" stroke-width="1.8"/>'
        f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="2.6" class="spark-dot"/></svg>'
    )


def render_node_sparklines():
    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        series = node_spend_series(measure)
        document.getElementById(f"spark-{measure}").innerHTML = (
            f'<span class="spark-title">{html.escape(spec["label"])}</span>'
            + sparkline_svg(series)
            + f'<span class="spark-caption">{series[-1]:.0f} funds this cycle, {sum(series):.0f} over the last {len(series)}</span>'
        )
