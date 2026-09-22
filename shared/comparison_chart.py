"""Shared "comparison/benchmark" chart component (Z17, site-wide goal).

`planning/TODO.md`'s Z17: before this module existed, three games each
hand-rolled their own version of the same idea -- "plot the player's own
value(s) against some reference value(s)" -- with the actual comparison
logic duplicated per game:

- Grid's C15/Pass-2 "global comparison" line: `trend_graph_svg()`'s own
  combined-min-max normalization + per-point hoverable `<circle>` markers,
  used to plot the player's emissions against a hardcoded global-average
  reference line on the same scale.
- Continuum's K13/K19/K25 "your city vs. history" chart (`trajectory.py`):
  its own log-scale normalization, plotting output-per-person against a
  real historical (Maddison Project) reference curve.
- Herd's F15 real-world-percentage comparison: a plain text sentence with
  no chart at all (`real_world_comparison_message()`).

This module is the generalized version: two small "building block"
functions (`normalize_together()`, `xs_for()`, `line_fragment()`,
`marker_fragment()`) that Grid now composes directly (its own trend graph
also needs an unrelated third line, so it isn't a clean fit for the
higher-level wrapper below), plus two higher-level convenience wrappers
(`two_series_chart_svg()`, `bar_comparison_svg()`) that Continuum and Herd
call directly.

Like every other shared Python module in this hub (see `shared/info_page.py`
for the reference pattern), a game's `index.html` boot script fetches this
file's source and writes it into Pyodide's virtual filesystem as
"comparison_chart.py" *before* running that game's own `game.py`/engine
modules, so `import comparison_chart` resolves normally.

## "Swappable reference-data sources" -- what that means concretely here

Every rendering function below takes its reference value(s) through one
`reference` argument that accepts any of three shapes, with no separate
code path needed per shape:

- a single number -- a hardcoded, never-changing real-world constant (a
  global-average benchmark, a documented real-world percentage, ...),
  broadcast flat across every point on a trend chart, or used as-is for a
  single-value comparison;
- a list of numbers, one per point -- a reference *curve* that itself
  varies per round/season (a historical trajectory, a per-round
  global-average series);
- `None` -- "no reference available yet." This is the seam a *live*
  source (e.g. Grid's own `window.gridCompare`/Herd's `window.herdCompare`
  community-percentile hooks -- a different, already-shared architecture
  documented in each of those games' own CLAUDE.md files, and
  deliberately NOT what this module's rollout touches) would plug into:
  render once with `None` while the fetch is in flight (this module
  degrades to "not enough data" output rather than crashing), then
  re-render with the resolved number once the hook's callback fires. No
  function in this module needs to know or care whether the number it
  receives came from a constant, a curve, or a just-resolved fetch.

See `as_reference_series()` below for where that normalization happens.
"""

import math


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def as_reference_series(reference, n):
    """Normalizes a `reference` argument (see module docstring) into a
    length-`n` list of floats, or `None` if there isn't a usable reference
    yet (missing, wrong length, or a non-numeric value)."""
    if reference is None:
        return None
    if isinstance(reference, (list, tuple)):
        if len(reference) != n or not all(_is_number(v) for v in reference):
            return None
        return [float(v) for v in reference]
    if _is_number(reference):
        return [float(reference)] * n
    return None


def xs_for(n, width, pad=0.0):
    """Evenly spaced x-coordinates for `n` points across `width` (inset by
    `pad` on each side). A single point sits at the horizontal center,
    matching every trend-chart convention already in this hub."""
    if n <= 0:
        return []
    if n == 1:
        return [width / 2.0]
    return [pad + i * ((width - 2 * pad) / (n - 1)) for i in range(n)]


def normalize_together(series_a, series_b, height, pad=0.0, log_scale=False, low=None, high=None):
    """Maps two series to SVG y-coordinates within [pad, height - pad],
    scaled TOGETHER against their combined range (not each independently)
    so the two stay directly, visually comparable on one chart -- this is
    the one piece of math every "you vs. a reference" chart in this hub
    needs and used to hand-roll separately (Grid's combined-min-max
    trend-graph scaling, Continuum's log-scale trajectory scaling).

    `low`/`high` override the auto-computed combined range -- Continuum's
    own chart needs this (a fixed 0.5 floor and a padded ceiling, not the
    raw combined min/max), everyone else can leave them as None.
    """
    combined = list(series_a) + list(series_b)
    if not combined:
        return [], []
    if log_scale:
        lo = low if low is not None else max(1e-9, min(combined))
        hi = high if high is not None else max(lo * 2.0, max(combined) * 1.15)

        def _y(v):
            v = min(max(v, lo), hi)
            if hi <= lo:
                return height / 2.0
            frac = (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
            return pad + (1.0 - frac) * (height - 2 * pad)
    else:
        lo = low if low is not None else min(combined)
        hi = high if high is not None else max(combined)
        span = hi - lo

        def _y(v):
            if span < 1e-9:
                return height / 2.0
            return pad + (1.0 - (min(max(v, lo), hi) - lo) / span) * (height - 2 * pad)

    return [_y(v) for v in series_a], [_y(v) for v in series_b]


def line_fragment(xs, ys, css_class, dash=None):
    """One `<polyline>` fragment. `dash` sets an inline `stroke-dasharray`
    -- leave it `None` when a game's own CSS already carries the dash
    pattern (Grid's convention) rather than doubling it up inline."""
    if not xs:
        return ""
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{points}" class="{css_class}" fill="none"{dash_attr} />'


def marker_fragment(xs, ys, values, css_class, series_label, *, index_label="Point", value_format="{:.2f}"):
    """Small hoverable `<circle>` markers, one per point, each carrying a
    native SVG `<title>` tooltip with that point's exact value -- no JS
    event wiring needed, the browser's own hover-title behavior does the
    work (the same idiom Grid's own C15 markers established)."""
    return "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="{css_class}">'
        f"<title>{index_label} {i + 1} -- {series_label}: {value_format.format(v)}</title></circle>"
        for i, (x, y, v) in enumerate(zip(xs, ys, values))
    )


def two_series_chart_svg(
    history,
    reference,
    *,
    width=240,
    height=48,
    pad=0.0,
    min_points=1,
    log_scale=False,
    low=None,
    high=None,
    your_class="comparison-line comparison-line--you",
    reference_class="comparison-line comparison-line--reference",
    reference_dash=None,
    markers=False,
    your_marker_class="comparison-point comparison-point--you",
    reference_marker_class="comparison-point comparison-point--reference",
    your_label="You",
    reference_label="Reference",
    index_label="Point",
    value_format="{:.2f}",
    background_class=None,
    svg_class="comparison-chart-svg",
    aria_label=None,
):
    """The shared "trend line vs. reference line" chart: your own history
    of values plotted against a reference that can be a flat constant or
    its own per-point series (see `as_reference_series()`). Used directly
    by Continuum's `trajectory.trajectory_svg()`; Herd's F15 chart uses
    the simpler `bar_comparison_svg()` below instead, since it has a
    single current value rather than a history. Grid's own trend graph
    composes the smaller building-block functions above directly instead
    of this wrapper, since it draws a third, unrelated series alongside
    the comparison pair.

    Returns `""` when there isn't enough data yet (fewer than `min_points`
    values, or no usable reference) rather than a malformed chart.
    """
    if not history or len(history) < min_points:
        return ""
    ref_series = as_reference_series(reference, len(history))
    if ref_series is None:
        return ""
    xs = xs_for(len(history), width, pad)
    your_ys, ref_ys = normalize_together(history, ref_series, height, pad=pad, log_scale=log_scale, low=low, high=high)

    fragments = []
    if background_class:
        fragments.append(f'<rect x="0" y="0" width="{width}" height="{height}" class="{background_class}"/>')
    fragments.append(line_fragment(xs, ref_ys, reference_class, dash=reference_dash))
    fragments.append(line_fragment(xs, your_ys, your_class))
    if markers:
        fragments.append(
            marker_fragment(
                xs, ref_ys, ref_series, reference_marker_class, reference_label,
                index_label=index_label, value_format=value_format,
            )
        )
        fragments.append(
            marker_fragment(
                xs, your_ys, history, your_marker_class, your_label,
                index_label=index_label, value_format=value_format,
            )
        )

    role_attr = ' role="img"' if aria_label else ""
    label_attr = f' aria-label="{aria_label}"' if aria_label else ""
    return f'<svg viewBox="0 0 {width} {height}" class="{svg_class}"{role_attr}{label_attr}>' + "".join(fragments) + "</svg>"


def bar_comparison_svg(
    your_value,
    reference_value,
    *,
    width=220,
    height=64,
    unit="",
    your_label="You",
    reference_label="Reference",
    your_class="comparison-bar comparison-bar--you",
    reference_class="comparison-bar comparison-bar--reference",
    label_class="comparison-bar-label",
    svg_class="comparison-bar-svg",
    aria_label=None,
):
    """A single point-in-time "you vs. reference" pair of horizontal bars
    -- the simplest chart shape in this module, for a game with one
    current value and no history to plot a trend from. Built for Herd's
    F15 real-world-percentage comparison, which previously had a text
    sentence and no chart at all.

    `reference_value` follows the same swappable shape as everywhere else
    in this module: ordinarily a plain number (a hardcoded real-world
    constant), with `None` (or a non-finite value) rendering nothing.
    """
    if not _is_number(your_value) or not _is_number(reference_value):
        return ""
    if your_value < 0 or reference_value < 0:
        return ""
    scale = max(your_value, reference_value, 1e-9)
    pad = 6.0
    bar_h = (height - 3 * pad) / 2.0
    max_bar_w = width - 2 * pad
    your_w = max(1.0, (your_value / scale) * max_bar_w)
    ref_w = max(1.0, (reference_value / scale) * max_bar_w)

    def _bar(y, w, css_class, label, value):
        return (
            f'<rect x="{pad:.1f}" y="{y:.1f}" width="{w:.1f}" height="{bar_h:.1f}" class="{css_class}">'
            f"<title>{label}: {value:.1f}{unit}</title></rect>"
            f'<text x="{pad:.1f}" y="{y - 2:.1f}" class="{label_class}">{label}: {value:.1f}{unit}</text>'
        )

    fragments = [
        _bar(pad + 12, your_w, your_class, your_label, your_value),
        _bar(pad + bar_h + 2 * pad + 12, ref_w, reference_class, reference_label, reference_value),
    ]
    role_attr = ' role="img"' if aria_label else ""
    label_attr = f' aria-label="{aria_label}"' if aria_label else ""
    return f'<svg viewBox="0 0 {width} {height}" class="{svg_class}"{role_attr}{label_attr}>' + "".join(fragments) + "</svg>"


def comparison_message(
    your_value,
    reference_value,
    *,
    subject="value",
    unit="",
    higher_is_better=True,
    ahead_text=None,
    behind_text=None,
    tie_text=None,
):
    """Generic one-line "ahead of / behind / matching a reference" message
    -- generalizes Grid's own `global_comparison_message()`. A game
    supplying its own `ahead_text`/`behind_text`/`tie_text` (as Grid does,
    to keep its exact existing wording) still gets the shared not-enough-
    data guard and ahead/behind/tie branching for free; a game with no
    strong opinion on wording can rely on the generic fallback text.
    """
    if not _is_number(your_value) or not _is_number(reference_value):
        return f"Not enough data yet to compare {subject} against a reference."
    if abs(your_value - reference_value) < 1e-9:
        return tie_text or f"Your {subject} is tracking almost exactly the reference value so far."
    ahead = your_value > reference_value if higher_is_better else your_value < reference_value
    if ahead:
        return ahead_text or (
            f"Your {subject} is {your_value:.0f}{unit} vs. a reference of {reference_value:.0f}{unit} "
            "-- you're ahead of it."
        )
    return behind_text or (
        f"Your {subject} is {your_value:.0f}{unit} vs. a reference of {reference_value:.0f}{unit} "
        "-- you're behind it."
    )
