"""Continuum -- K19/K13/K25/K8: the per-season trajectory record and its charts.

One small, saved per-season record (`CityState.trajectory`) feeds three
readouts, all pure functions of that record so they are testable without a
DOM:

- K8: an always-visible "output per person" number.
- K19/K13: the settlement's output-per-person line, drawn against a real
  historical reference curve (world GDP per person) for whatever era the
  settlement was in that season.
- K25: a livability-vs-population scatter across the whole playthrough.

## What the numbers mean (be honest about this in the UI, too)

The game's "output per person" is NOT money. It is what the settlement
produced in a season (food + materials + tools + knowledge) divided by its
population, then divided by `sim.FOOD_PER_PERSON` -- so 1.0 means "made
just about what one person needs to eat", 2.0 means twice that. The
reference line is a *multiple of the year-1 CE world level*, so both lines
are dimensionless growth multiples and only their shape is comparable,
never their absolute height. Plotted on a log axis for that reason.

## The reference curve and where it comes from

World GDP per person, Maddison Project Database long-run estimates (Angus
Maddison's series, 1990 international dollars, rounded), divided by the
year-1 CE value (about $470): about 1.0 at 1 CE, about 1.0 at 1000, about
1.2 at 1500, about 1.4 at 1820, about 1.9 at 1870, about 2.7 at 1900, about
4.5 at 1950, about 13 at 2000. The era mapping below is a modelling choice,
not a measurement:

- Tribal: Maddison starts at 1 CE; earlier is assumed to be at subsistence
  (1.0). Growth before agriculture is not measured, only inferred.
- Agrarian / Classical: 1 CE level (1.0), the earliest Maddison datum.
- Medieval: c. 1500 (1.2).
- Industrial: c. 1870 (1.9), the middle of the industrialising century.
- Digital: c. 2000 (13.0).
- Space Age: there is no data. Held at the 2000 level and labelled as such;
  it is deliberately not extrapolated.
"""

import math

import comparison_chart
import sim

# One entry per era: (reference year label, multiple of the 1 CE level, is_measured)
REFERENCE = {
    "tribal": ("before 1 CE (assumed subsistence)", 1.0, False),
    "agrarian": ("c. 1 CE", 1.0, True),
    "classical": ("c. 1 CE", 1.0, True),
    "medieval": ("c. 1500", 1.2, True),
    "industrial": ("c. 1870", 1.9, True),
    "digital": ("c. 2000", 13.0, True),
    "space": ("no data - held at the 2000 level", 13.0, False),
}

SOURCE_NOTE = (
    "Reference line: world GDP per person, Maddison Project Database long-run "
    "estimates (1990 international dollars, rounded), shown as a multiple of "
    "the year-1 CE level. Tribal is an assumption (no data that early) and "
    "Space Age has no data at all, so it is held at the 2000 level rather than "
    "extrapolated. Your line is output per person (food, materials, tools and "
    "knowledge) divided by what one person eats in a season - it is not money, "
    "so compare the shape of the two lines, not their height."
)

MAX_POINTS = 300  # oldest points drop first, so a long run never grows the save unbounded

# One point: [output_index, era_index, population, livability_0_to_100]
POINT_LENGTH = 4


def output_index(report, population):
    """Output per person as a multiple of one person's food need."""
    try:
        total = (
            float(report.get("food_gathered", 0.0))
            + float(report.get("materials_gathered", 0.0))
            + float(report.get("tools_made", 0.0))
            + float(report.get("knowledge_made", 0.0))
        )
        pop = max(1, int(population))
    except (TypeError, ValueError, AttributeError, OverflowError):
        return 0.0
    value = total / pop / sim.FOOD_PER_PERSON
    return value if math.isfinite(value) and value >= 0 else 0.0


def reference_index(era):
    entry = REFERENCE.get(era)
    return entry[1] if entry else 1.0


def record(state, report, livability):
    """Appends this season's point to `state.trajectory` (capped)."""
    point = [
        output_index(report, state.population),
        float(sim.era_index(state.era)),
        float(state.population),
        float(livability),
    ]
    state.trajectory.append(point)
    if len(state.trajectory) > MAX_POINTS:
        del state.trajectory[: len(state.trajectory) - MAX_POINTS]
    return point


def clean_points(raw):
    """Validates a saved list: only well-formed, finite points survive."""
    if not isinstance(raw, list):
        return []
    cleaned = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != POINT_LENGTH:
            continue
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in item):
            continue
        idx, era, pop, liv = (float(v) for v in item)
        era = min(max(int(era), 0), len(sim.ERA_ORDER) - 1)
        cleaned.append([max(0.0, idx), float(era), max(0.0, pop), min(max(liv, 0.0), 100.0)])
    return cleaned[-MAX_POINTS:]


def current_output_index(state):
    """K8: last completed season's output per person, or None before season 1 ends."""
    report = state.last_report
    if not isinstance(report, dict):
        return None
    return output_index(report, state.population)


def trajectory_svg(points, width=320, height=150):
    """The K19/K13 chart as an SVG string: your line vs the reference line.

    Z17 (site-wide goal): now built on the shared shared/comparison_chart.py
    two_series_chart_svg() wrapper rather than this file's own (now-
    removed) log-scale normalization -- Continuum's K13 "vs. history"
    chart is one of the three integrations that shared component was
    generalized for (alongside Grid's C15 global-comparison line and
    Herd's new F15 chart). The reference here is genuinely per-point (each
    point's own era has its own historical reference value), exactly the
    "a reference can be a per-point series, not just a constant" shape
    that module's own docstring describes -- pure refactor, byte-for-byte
    the same rendered numbers as before this migration."""
    if not points:
        return ""
    mine = [p[0] for p in points]
    ref = [reference_index(sim.ERA_ORDER[int(p[1])]) for p in points]
    low = 0.5
    high = max(2.0, max(mine + ref) * 1.15)
    return comparison_chart.two_series_chart_svg(
        mine,
        ref,
        width=width,
        height=height,
        pad=12,
        log_scale=True,
        low=low,
        high=high,
        your_class="trajectory-line trajectory-line--mine",
        reference_class="trajectory-line trajectory-line--ref",
        reference_dash="5 3",
        background_class="trajectory-bg",
        svg_class="trajectory-svg",
        aria_label="Your output per person against the real historical reference, log scale",
    )


def scatter_svg(points, width=320, height=150):
    """The K25 chart: each season a dot at (population, livability)."""
    pad = 12
    if not points:
        return ""
    max_pop = max(p[2] for p in points) or 1.0
    dots = []
    last = len(points) - 1
    for i, p in enumerate(points):
        cx = pad + (p[2] / max_pop) * (width - 2 * pad)
        cy = pad + (1.0 - p[3] / 100.0) * (height - 2 * pad)
        cls = "trajectory-dot trajectory-dot--latest" if i == last else "trajectory-dot"
        dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{4 if i == last else 2.5}" class="{cls}"/>')
    return (
        f'<svg viewBox="0 0 {width} {height}" class="trajectory-svg" role="img" '
        f'aria-label="Livability against population, one dot per season">'
        f'<rect x="0" y="0" width="{width}" height="{height}" class="trajectory-bg"/>'
        + "".join(dots)
        + "</svg>"
    )


def summary_line(points):
    """A one-line plain-text reading of the chart, for screen readers and the note."""
    if not points:
        return "Advance a season to start the chart."
    last = points[-1]
    era = sim.ERA_ORDER[int(last[1])]
    return (
        f"Now: {last[0]:.1f}x subsistence output per person. Real-world reference for this era "
        f"({REFERENCE[era][0]}): {reference_index(era):.1f}x the year-1 CE level."
    )
