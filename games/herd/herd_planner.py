"""The what-if planner (F-9): queue purchases, project the next rounds and draw the projection chart.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import html

from js import document

import herd_runstate as runstate
from herd_rules import DECOUPLING_MEASURES, LEVER_LABELS
from herd_model import clone_farm
from herd_blind import blind_hidden


# ---- F-7 dry-run planner ------------------------------------------------------------------
# Queue purchases for the next few rounds and see where a COPY of the farm would be. Nothing here
# touches the real farm, the save or any achievement; the plan itself is not saved.
PLAN_LEVERS = ["herd", "feed", "caps", "capture", "pivot", "genetics", "supply"]
PLAN_HORIZONS = (5, 10)
PLAN_COUNTS = (1, 2, 5)
PLAN_MAX_STEPS = 12


def _plan_buy(scratch, key):
    if key == "herd":
        return scratch.grow_herd()
    if key in DECOUPLING_MEASURES:
        return scratch.invest_decoupling(key)
    return {
        "pivot": scratch.invest_plant_pivot, "genetics": scratch.invest_genetics,
        "supply": scratch.invest_supply_chain,
    }[key]()


def project_plan(steps=None, horizon=None):
    """Plays the queued purchases on a scratch copy for `horizon` rounds. Returns {"rows", "idle", "skipped"}:
    rows are the plan's state after each round, idle the same rounds with no purchases at all."""
    steps = runstate.plan_steps if steps is None else steps
    horizon = runstate.plan_horizon if horizon is None else horizon
    scratch, idle = clone_farm(runstate.farm), clone_farm(runstate.farm)
    rows, idle_rows, skipped = [], [], []

    def snapshot(f, number):
        return {
            "round": number, "funds": f.funds, "per_round": f.methane_this_round(), "methane": f.methane,
            "coupling": f.coupling_ratio(), "score": f.score(), "baseline": f.counterfactual_score(),
        }

    for offset in range(horizon):
        for step_offset, key, count in steps:
            if step_offset != offset:
                continue
            bought = 0
            for _ in range(count):
                if not _plan_buy(scratch, key):
                    break
                bought += 1
            if bought < count:
                skipped.append(f"Round +{offset}: {LEVER_LABELS[key]} x{count - bought} not bought (funds or cap)")
        scratch.advance_round()
        idle.advance_round()
        rows.append(snapshot(scratch, runstate.farm.round_number + offset))
        idle_rows.append(snapshot(idle, runstate.farm.round_number + offset))
    return {"rows": rows, "idle": idle_rows, "skipped": skipped}


def add_plan_step(offset, key, count):
    if key not in PLAN_LEVERS or count not in PLAN_COUNTS or not 0 <= offset < max(PLAN_HORIZONS):
        return False
    if len(runstate.plan_steps) >= PLAN_MAX_STEPS:
        return False
    runstate.plan_steps.append([int(offset), key, int(count)])
    runstate.plan_steps.sort(key=lambda step: step[0])
    return True


def plan_step_text(step):
    offset, key, count = step
    when = "now, before this round ends" if offset == 0 else f"{offset} round{'s' if offset != 1 else ''} from now"
    return f"{LEVER_LABELS[key]} x{count}, {when}"


def plan_queue_html():
    visible = [s for s in runstate.plan_steps if s[0] < runstate.plan_horizon]
    if not runstate.plan_steps:
        return "<li>Nothing queued. Pick a lever and a round, then press Add to plan.</li>"
    items = "".join(f"<li>{html.escape(plan_step_text(step))}</li>" for step in runstate.plan_steps)
    hidden = len(runstate.plan_steps) - len(visible)
    if hidden:
        items += f"<li>{hidden} step(s) fall beyond the {runstate.plan_horizon}-round view and are left out of the projection.</li>"
    return items


def plan_table_html(result):
    head = (
        '<caption>Projected farm after each round</caption><thead><tr><th scope="col">Round</th>'
        '<th scope="col">Funds</th><th scope="col">Methane per round</th><th scope="col">Coupling</th>'
        '<th scope="col">Score</th><th scope="col">Score vs doing nothing</th>'
        + ('' if blind_hidden() else '<th scope="col">Score vs pure-growth baseline</th>') + '</tr></thead>'
    )
    body = ""
    for row, idle in zip(result["rows"], result["idle"]):
        body += (
            f'<tr><th scope="row">{row["round"]}</th><td>{row["funds"]:.0f}</td><td>{row["per_round"]:.1f}</td>'
            f'<td>{row["coupling"]:.2f}</td><td>{row["score"]:.0f}</td><td>{row["score"] - idle["score"]:+.0f}</td>'
            + ('' if blind_hidden() else f'<td>{row["score"] - row["baseline"]:+.0f}</td>') + '</tr>'
        )
    return f'<table class="compare-table plan-table">{head}<tbody>{body}</tbody></table>'


def plan_chart_svg(result):
    """Score over the projected rounds: solid = your plan, dashed = doing nothing, dotted = pure-growth baseline
    (line style as well as colour, with a letter at each line's end)."""
    width, height, pad = 260, 90, 8
    series = (
        ("plan", "P", [r["score"] for r in result["rows"]], "plan-line--plan"),
        ("doing nothing", "N", [r["score"] for r in result["idle"]], "plan-line--idle"),
        ("pure-growth baseline", "B", [r["baseline"] for r in result["rows"]], "plan-line--base"),
    )
    if blind_hidden():
        series = series[:2]
    values = [v for _n, _l, vs, _c in series for v in vs]
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    count = len(result["rows"])
    parts = []
    for name, letter, vs, css in series:
        points = []
        for i, v in enumerate(vs):
            x = pad + (width - 2 * pad - 12) * (i / max(1, count - 1))
            y = height - pad - (height - 2 * pad) * ((v - low) / span)
            points.append((x, y))
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        ex, ey = points[-1]
        parts.append(
            f'<polyline class="plan-line {css}" points="{path}"><title>{name}</title></polyline>'
            f'<text class="plan-line-letter" x="{ex + 3:.1f}" y="{ey + 3:.1f}">{letter}</text>'
        )
    label = (
        "Projected score by round: plan (P, solid), doing nothing (N, dashed)." if blind_hidden()
        else "Projected score by round: plan (P, solid), doing nothing (N, dashed), pure-growth baseline (B, dotted)."
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" class="plan-chart-svg" role="img" aria-label="{label}">'
        f'<title>{label}</title>{"".join(parts)}</svg>'
    )


def plan_summary_message(result):
    last, idle = result["rows"][-1], result["idle"][-1]
    reference = (
        f"doing nothing: {idle['score']:.0f}" if blind_hidden()
        else f"doing nothing: {idle['score']:.0f}, pure-growth baseline: {last['baseline']:.0f}"
    )
    text = (
        f"After {runstate.plan_horizon} rounds the plan reaches a score of {last['score']:.0f} ({reference}), "
        f"with {last['per_round']:.1f} methane per round and {last['funds']:.0f} funds."
    )
    if result["skipped"]:
        text += " " + " ".join(result["skipped"]) + "."
    return text


def render_planner():
    document.getElementById("plan-queue-list").innerHTML = plan_queue_html()
    for horizon in PLAN_HORIZONS:
        button = document.getElementById(f"plan-horizon-{horizon}-button")
        button.setAttribute("aria-pressed", "true" if horizon == runstate.plan_horizon else "false")
        if horizon == runstate.plan_horizon:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")
    document.getElementById("plan-undo-button").disabled = not runstate.plan_steps
    document.getElementById("plan-clear-button").disabled = not runstate.plan_steps
    result = project_plan()
    document.getElementById("plan-summary").innerText = plan_summary_message(result)
    document.getElementById("plan-chart").innerHTML = plan_chart_svg(result)
    document.getElementById("plan-table").innerHTML = plan_table_html(result)


def on_plan_add(event=None):
    lever = document.getElementById("plan-lever-select").value
    try:
        offset = int(document.getElementById("plan-round-select").value)
        count = int(document.getElementById("plan-count-select").value)
    except (TypeError, ValueError):
        return
    add_plan_step(offset, lever, count)
    render_planner()


def on_plan_remove_last(event=None):
    if runstate.plan_steps:
        runstate.plan_steps.pop()
    render_planner()


def on_plan_clear(event=None):
    del runstate.plan_steps[:]
    render_planner()


def _make_plan_horizon_handler(horizon):
    def handler(event=None):
        runstate.plan_horizon = horizon
        render_planner()
    return handler
