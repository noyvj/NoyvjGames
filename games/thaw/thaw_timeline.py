"""The forecast planner (G-5), the one-rewind-per-run undo (GG-17) and the round replay (G-3)."""

from js import document

import thaw_runstate as runstate
from thaw_bridge import _escape
from thaw_graphs import graph_indexes
from thaw_model import RegionState, deg, region, region_b, region_c, region_d
from thaw_rules import (
    CATEGORIES, INVEST_COST, MELT_THRESHOLD, PLANNER_H, PLANNER_MAX_UNITS, PLANNER_ROUNDS, PLANNER_W,
    PLAN_ORDER,
)
from thaw_saveparts import _apply_region_state, _region_state_dict
from thaw_sciencelog import science_log
from thaw_views import FOCUS_KEYS, _focus_region_for


# ===========================================================================
# G-5: the forecast planner. Draw a hypothetical funding split for one region (units of Output,
# Preservation and Monitoring to buy now, optionally repeated every round) and see a dashed
# 10-round temperature projection beside the "no change" one. It runs on a scratch copy of the
# region, so nothing about the real game changes. Tipping cascades, convoys and carbon grants are
# not modelled (they would make the line depend on the other regions), which the page says.
# ===========================================================================


def _plan_int(raw):
    """A units box as a whole number 0..PLANNER_MAX_UNITS (blank, text and negatives become 0)."""
    try:
        value = int(float(str(raw).strip() or "0"))
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(PLANNER_MAX_UNITS, value))


def _scratch_copy(r):
    scratch = RegionState()
    _apply_region_state(scratch, _region_state_dict(r))
    return scratch


def _buy_plan(scratch, plan):
    """Buys what the plan asks for and the scratch region can afford; returns the units skipped."""
    skipped = 0
    for category in PLAN_ORDER:
        for _ in range(plan.get(category, 0)):
            if not scratch.invest(category):
                skipped += 1
    return skipped


def planner_projection(r, plan, repeat=False, rounds=PLANNER_ROUNDS):
    """The region's temperature now and after each of the next `rounds` rounds if it buys `plan`
    first (and again every round when `repeat`). Returns (temperatures, units skipped overall)."""
    scratch = _scratch_copy(r)
    skipped = _buy_plan(scratch, plan)
    temps = [scratch.temperature]
    for _ in range(rounds):
        scratch.advance_round()
        if repeat:
            skipped += _buy_plan(scratch, plan)
        temps.append(scratch.temperature)
    return temps, skipped


def plan_cost(plan):
    return sum(INVEST_COST[c] * plan.get(c, 0) for c in CATEGORIES)


def planner_chart_svg(base, planned, name):
    values = list(base) + list(planned)
    top = max(max(values), MELT_THRESHOLD) * 1.08
    plot_w, plot_h = PLANNER_W - 34 - 4, PLANNER_H - 16 - 4

    def point(i, v):
        return f"{34 + i * plot_w / max(len(base) - 1, 1):.1f},{4 + plot_h - v / top * plot_h:.1f}"

    melt_y = 4 + plot_h - MELT_THRESHOLD / top * plot_h
    label = _escape(
        f"{name}, next {len(base) - 1} rounds: with no change the temperature ends at {deg(base[-1], plus=True)}; "
        f"with your plan it ends at {deg(planned[-1], plus=True)}."
    )
    return (
        f'<svg viewBox="0 0 {PLANNER_W} {PLANNER_H}" class="planner-svg" role="img" aria-label="{label}"><title>{label}</title>'
        f'<line x1="34" y1="{melt_y:.1f}" x2="{PLANNER_W - 4}" y2="{melt_y:.1f}" class="focus-guide focus-guide--melt" />'
        f'<text x="31" y="{melt_y + 3:.1f}" class="focus-tick" text-anchor="end">{deg(MELT_THRESHOLD, 0, plus=True)}</text>'
        f'<text x="34" y="{PLANNER_H - 3}" class="focus-tick" text-anchor="start">now</text>'
        f'<text x="{PLANNER_W - 4}" y="{PLANNER_H - 3}" class="focus-tick" text-anchor="end">+{len(base) - 1} rounds</text>'
        f'<polyline points="{" ".join(point(i, v) for i, v in enumerate(base))}" class="compare-line compare-line--first" />'
        f'<polyline points="{" ".join(point(i, v) for i, v in enumerate(planned))}" class="compare-line compare-line--second" />'
        f"</svg>"
    )


def planner_readout(r, key, plan, repeat, base, planned, skipped):
    parts = [f"Region {key.upper()} in {PLANNER_ROUNDS} rounds: {deg(base[-1], plus=True)} if nothing changes."]
    if not any(plan.values()):
        parts.append("Type a number of units below to see what a different split would do.")
        return " ".join(parts)
    diff = base[-1] - planned[-1]
    if abs(diff) < 0.05:
        parts.append(f"Your plan ends at {deg(planned[-1], plus=True)}: no real difference over {PLANNER_ROUNDS} rounds.")
    elif diff > 0:
        parts.append(f"Your plan ends at {deg(planned[-1], plus=True)}, {deg(diff)} cooler.")
    else:
        parts.append(f"Your plan ends at {deg(planned[-1], plus=True)}, {deg(-diff)} warmer (Output earns funds, not protection).")
    cost = plan_cost(plan)
    parts.append(
        f"The plan costs {cost} funds{' each round' if repeat else ''}; Region {key.upper()} has {r.funds:.0f}."
    )
    if skipped:
        parts.append(f"{skipped} unit{'s' if skipped != 1 else ''} could not be afforded and are left out.")
    return " ".join(parts)


def _planner_inputs():
    key = document.getElementById("planner-region").value
    key = key if key in FOCUS_KEYS else "a"
    plan = {c: _plan_int(document.getElementById(f"planner-{c}").value) for c in CATEGORIES}
    repeat = bool(document.getElementById("planner-repeat").checked)
    return key, plan, repeat


def render_planner():
    if runstate.hard_mode:  # GG-23
        document.getElementById("planner-chart").innerHTML = ""
        document.getElementById("planner-readout").innerText = (
            "Hard mode is on, so the forecast planner is switched off. Use the forecast box to test your own read."
        )
        return
    key, plan, repeat = _planner_inputs()
    r = _focus_region_for(key)
    base, _none = planner_projection(r, {c: 0 for c in CATEGORIES})
    planned, skipped = planner_projection(r, plan, repeat)
    document.getElementById("planner-chart").innerHTML = planner_chart_svg(base, planned, f"Region {key.upper()}")
    document.getElementById("planner-readout").innerText = planner_readout(r, key, plan, repeat, base, planned, skipped)


def outlook_lines():
    """The 10-round no-change outlook for the three managed regions, for the Advance Round tooltip."""
    parts = []
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        temps, _none = planner_projection(r, {c: 0 for c in CATEGORIES})
        parts.append(f"{label} {deg(temps[-1], plus=True)}")
    return f"In {PLANNER_ROUNDS} rounds with no change: " + ", ".join(parts)


# ===========================================================================
# GG-17: one rewind per run. Just before every Advance Round the whole game is snapshotted; the
# "Rewind" button puts it back as it stood right before that click, once, for UNDO_COST funds from
# Region A. Nothing is random and nothing is lost: the investments made that round are still there.
# A finished Hold the Line run cannot be rewound (its result is already recorded). Records kept in
# the browser (personal best, archive) are bests and stay as they are.
# ===========================================================================
UNDO_COST = 40.0


def can_undo():
    if runstate.undo_used or runstate.run_over or runstate._undo_snapshot is None:
        return False
    snap_region = runstate._undo_snapshot.get("region", {})
    return snap_region.get("funds", 0) >= UNDO_COST


def undo_text():
    if runstate.undo_used:
        return "Rewind used: this run's one rewind has been spent."
    if runstate.run_over:
        return "The run is over, so there is nothing to rewind."
    if runstate._undo_snapshot is None:
        return (
            f"Once per run you can rewind the last round for {UNDO_COST:.0f} funds from Region A. "
            f"It becomes available after your first Advance Round."
        )
    if not can_undo():
        return f"Rewinding costs {UNDO_COST:.0f} funds from Region A, and Region A did not have that much before the round."
    return (
        f"Rewind puts everything back to just before you pressed Advance Round "
        f"(round {runstate._undo_snapshot['region']['round_number']}), once per run, for {UNDO_COST:.0f} funds from Region A."
    )


def render_undo():
    button = document.getElementById("undo-button")
    button.disabled = not can_undo()
    button.innerText = "Rewind used" if runstate.undo_used else f"Rewind last round ({UNDO_COST:.0f} funds, once)"
    document.getElementById("undo-display").innerText = undo_text()


# ===========================================================================
# G-3: the round-replay scrubber. A slider over the rounds played so far shows where each of the
# three regions stood at that round, with the scientist's-log entries that still exist pinned at
# their rounds on the chart. Read-only: it never changes the game. The log keeps only its newest 40
# entries (plus pins), so older rounds simply have no marker.
# ===========================================================================
REPLAY_W = 320
REPLAY_H = 120


def replay_rounds():
    """How many rounds can be scrubbed (rounds played by Region A)."""
    return len(region.temperature_history)


def replay_selected():
    raw = document.getElementById("replay-slider").value
    try:
        value = int(float(str(raw)))
    except (TypeError, ValueError, OverflowError):
        value = replay_rounds()
    return max(1, min(max(1, replay_rounds()), value))


def replay_state_at(r, round_number):
    """(temperature, status word, change since the round before) for region `r` at `round_number`,
    or None when it has no record that far."""
    history = r.temperature_history
    if not 1 <= round_number <= len(history):
        return None
    temp = history[round_number - 1]
    before = history[round_number - 2] if round_number >= 2 else 0.0
    status = "melting" if temp >= MELT_THRESHOLD else "stable"
    return temp, status, temp - before


def replay_log_at(round_number):
    """Log entries written for exactly this round, oldest first."""
    return [e for e in science_log if e["round"] == round_number]


def replay_chart_svg(round_number):
    n = replay_rounds()
    if n < 2:
        return ""
    series = [("a", region), ("b", region_b), ("c", region_c)]
    top = max(max(r.temperature_history or [0.0]) for _k, r in series)
    top = max(top, MELT_THRESHOLD) * 1.08
    left, plot_w, plot_h = 34, REPLAY_W - 34 - 4, REPLAY_H - 22 - 4

    def x_of(i):
        return left + i * plot_w / (n - 1)

    def y_of(v):
        return 4 + plot_h - v / top * plot_h

    lines = ""
    for key, r in series:
        shown = r.temperature_history[:n]
        pts = " ".join(f"{x_of(i):.1f},{y_of(shown[i]):.1f}" for i in graph_indexes(shown))  # G-11
        lines += f'<polyline points="{pts}" class="replay-line replay-line--{key}" />'
    marks = ""
    for entry in science_log:
        rnd = entry["round"]
        if 1 <= rnd <= n:
            marks += f'<polygon points="{x_of(rnd - 1) - 2.5:.1f},3 {x_of(rnd - 1) + 2.5:.1f},3 {x_of(rnd - 1):.1f},8" class="replay-mark" />'
    cx = x_of(round_number - 1)
    melt_y = y_of(MELT_THRESHOLD)
    label = _escape(
        f"Temperature of Regions A, B and C over {n} rounds; the cursor is at round {round_number}. "
        f"The triangles mark rounds that have a scientist's log entry."
    )
    return (
        f'<svg viewBox="0 0 {REPLAY_W} {REPLAY_H}" class="replay-svg" role="img" aria-label="{label}"><title>{label}</title>'
        f'<line x1="{left}" y1="{melt_y:.1f}" x2="{REPLAY_W - 4}" y2="{melt_y:.1f}" class="focus-guide focus-guide--melt" />'
        f'<text x="{left - 3}" y="{melt_y + 3:.1f}" class="focus-tick" text-anchor="end">{deg(MELT_THRESHOLD, 0, plus=True)}</text>'
        f'<text x="{left}" y="{REPLAY_H - 4}" class="focus-tick" text-anchor="start">R1</text>'
        f'<text x="{REPLAY_W - 4}" y="{REPLAY_H - 4}" class="focus-tick" text-anchor="end">R{n}</text>'
        f"{lines}{marks}"
        f'<line x1="{cx:.1f}" y1="8" x2="{cx:.1f}" y2="{4 + plot_h}" class="replay-cursor" />'
        f"</svg>"
    )


def render_replay():
    n = replay_rounds()
    slider = document.getElementById("replay-slider")
    slider.max = str(max(1, n))
    slider.disabled = n < 1
    if runstate.replay_follow or not str(slider.value).strip():
        slider.value = str(max(1, n))
    chosen = replay_selected()
    slider.value = str(chosen)
    if n < 1:
        document.getElementById("replay-label").innerText = "Play a round and the replay appears here."
        document.getElementById("replay-chart").innerHTML = ""
        document.getElementById("replay-readouts").innerHTML = ""
        document.getElementById("replay-log").innerHTML = ""
        return
    document.getElementById("replay-label").innerText = f"Round {chosen} of {n}"
    document.getElementById("replay-chart").innerHTML = replay_chart_svg(chosen)
    regions = [("A", region), ("B", region_b), ("C", region_c)]
    if runstate.worst_case_region_revealed:
        regions.append(("D", region_d))
    rows = []
    for label, r in regions:
        got = replay_state_at(r, chosen)
        if got is None:
            rows.append(f"<li><span>Region {label}</span><span>no record</span></li>")
            continue
        temp, status, change = got
        rows.append(
            f"<li><span>Region {label}</span><span>{deg(temp, plus=True)} ({deg(change, 2, plus=True)} that round), {status}</span></li>"
        )
    document.getElementById("replay-readouts").innerHTML = "".join(rows)
    entries = replay_log_at(chosen)
    if entries:
        log_html = "".join(f"<li>Region {e['region']}: {_escape(e['text'])}</li>" for e in entries)
    else:
        log_html = '<li class="replay-quiet">Nothing was logged in this round.</li>'
    document.getElementById("replay-log").innerHTML = log_html
