"""Hold the Line run end and titles, the AI stewards, Field Notes, the compare overlay and the run result panel."""

import json

from js import document

import thaw_runstate as runstate
from thaw_bridge import _decimate, _num, _read_local_storage_item, _write_local_storage_item
from thaw_model import (
    RegionState, _managed, average_saved, base_rise_per_round, can_toggle_hold_the_line, deg,
    escalation_event_name, escalation_level, line_holds, max_dampening, region, region_d, tipped_labels,
    untipped_count,
)
from thaw_presets import hard_mode_reveal_lines
from thaw_records import ARCHIVE_REGIONS
from thaw_rules import (
    CATEGORIES, FIELD_NOTES_KEY, FIELD_NOTES_MAX, HOLD_LINE_ESCALATION_EVERY, HOLD_LINE_MAX_ROUNDS,
    HOLD_LINE_MIN_UNTIPPED, INVEST_COST, MELT_THRESHOLD, RUN_TITLES,
)
from thaw_sciencelog import SCIENCE_LOG_MAX, _cap_science_log, science_log


# ===========================================================================
# GG-2: Hold the Line. The run-based mode: keep at least two of the three managed regions out of
# the critical tier for as many rounds as possible while escalation events make the background
# harsher. This is the one place a Thaw run has an end, so it also feeds GG-24 (title ladder),
# GG-21 (the three AI stewards) and G-1/G-2 (Field Notes and the run overlay). There is no in-game
# reset (owner decision R24): a finished run stays on screen and a new one starts from the
# opening screen's New Game.
# ===========================================================================


def run_title(saved):
    """GG-24: (title, next title or None, saved needed for the next title or None)."""
    index = 0
    for i, (minimum, _name) in enumerate(RUN_TITLES):
        if saved >= minimum:
            index = i
    title = RUN_TITLES[index][1]
    if index + 1 < len(RUN_TITLES):
        return title, RUN_TITLES[index + 1][1], RUN_TITLES[index + 1][0]
    return title, None, None


def escalation_text():
    """The status of the escalation track: what is in force and what is coming."""
    level = escalation_level(region.round_number)
    nxt = HOLD_LINE_ESCALATION_EVERY * (level + 1) + 1 - region.round_number
    upcoming = escalation_event_name(level + 1)
    rise = base_rise_per_round(region.round_number)
    cap = max_dampening(region.round_number)
    if level == 0:
        now = f"No escalation yet: background rise {deg(rise, 2)}/round, dampening ceiling {cap * 100:.0f}%."
    else:
        now = (
            f"Escalation level {level} ({escalation_event_name(level)}): background rise "
            f"{deg(rise, 2)}/round, dampening ceiling {cap * 100:.0f}%."
        )
    return f"{now} Next: {upcoming} in {nxt} round{'' if nxt == 1 else 's'}."


def _announce_escalation(level):
    runstate.just_escalated = level
    _cap_science_log(SCIENCE_LOG_MAX - 1)
    science_log.append({
        "region": "ALL",
        "round": region.round_number - 1,
        "text": (
            f"escalation level {level}, {escalation_event_name(level)}: the background rise is now "
            f"{deg(base_rise_per_round(region.round_number), 2)}/round and the dampening ceiling "
            f"{max_dampening(region.round_number) * 100:.0f}%."
        ),
    })


def finish_run(reason):
    """Ends the run. 'tipped': two or more regions went critical this round, so the round does not
    count. 'limit': HOLD_LINE_MAX_ROUNDS rounds all held."""
    played = region.round_number - 1
    survived = played if reason == "limit" else max(0, played - 1)
    runstate.run_result = {"survived": survived, "saved": round(average_saved(), 3), "reason": reason}
    runstate.run_over = True
    record_field_note()
    title = run_title(runstate.run_result["saved"])[0]
    _cap_science_log(SCIENCE_LOG_MAX - 1)
    science_log.append({
        "region": "ALL",
        "round": played,
        "text": f"the run is over after {survived} rounds held: you are a {title}.",
    })


def check_run_end():
    """Called once per Advance Round after every region has advanced."""
    if not runstate.hold_the_line or runstate.run_over:
        return
    if not line_holds():
        finish_run("tipped")
    elif region.round_number - 1 >= HOLD_LINE_MAX_ROUNDS:
        finish_run("limit")


# --- GG-21: three fixed AI stewards play the same mode with a fixed plan -----------------------
STEWARDS = (
    ("Cautious Kai", "kai", "buys Preservation first and keeps buying it until the ceiling"),
    ("Rash Rasmus", "rasmus", "pours everything into Output for 14 rounds, then scrambles to protect"),
    ("Balanced Bea", "bea", "protects up to half the ceiling and puts the rest into Output"),
)
STEWARD_RASH_ROUNDS = 14
_steward_cache = {}


def _steward_move(policy, r):
    """One steward's spending for one region this round (no rescue/convoy/carbon/cascade: a
    deliberately simple, fixed plan so the scoreboard is the same for everyone)."""
    if policy == "kai":
        while r.funds >= INVEST_COST["preserve"] and r.feedback_dampening_fraction() < max_dampening(r.round_number):
            r.invest("preserve")
    elif policy == "rasmus":
        if r.round_number <= STEWARD_RASH_ROUNDS:
            while r.funds >= INVEST_COST["output"]:
                r.invest("output")
        else:
            while r.funds >= INVEST_COST["preserve"] and r.feedback_dampening_fraction() < max_dampening(r.round_number):
                r.invest("preserve")
    else:
        # Bea aims for about half of the ceiling in protection and puts the rest into Output, so
        # she can afford the occasional rescue.
        while r.funds >= INVEST_COST["preserve"] and r.feedback_dampening_fraction() < max_dampening(r.round_number) * 0.5:
            r.invest("preserve")
        while r.funds >= INVEST_COST["output"]:
            r.invest("output")
    if r.can_rescue():
        r.rescue()


def simulate_steward(policy):
    """Plays a whole Hold the Line run for one steward on three fresh regions. Returns
    {"survived", "saved"} using the same rules as the player's run."""
    saved_flags = (runstate.hold_the_line, runstate.long_game)
    runstate.hold_the_line, runstate.long_game = True, False
    try:
        rs = [RegionState() for _ in range(3)]
        survived = 0
        for _ in range(HOLD_LINE_MAX_ROUNDS):
            for r in rs:
                _steward_move(policy, r)
            for r in rs:
                r.advance_round()
            if not line_holds(rs):
                break
            survived += 1
        return {"survived": survived, "saved": round(average_saved(rs), 3)}
    finally:
        runstate.hold_the_line, runstate.long_game = saved_flags


def steward_scores():
    """Cached: the stewards are deterministic, so each plan only needs playing once."""
    for _name, policy, _blurb in STEWARDS:
        if policy not in _steward_cache:
            _steward_cache[policy] = simulate_steward(policy)
    return {policy: dict(_steward_cache[policy]) for _name, policy, _blurb in STEWARDS}


def stewards_beaten(survived):
    scores = steward_scores()
    return sum(1 for _name, policy, _blurb in STEWARDS if survived > scores[policy]["survived"])


def steward_lines():
    scores = steward_scores()
    return [
        f"{name} {scores[policy]['survived']} rounds ({deg(scores[policy]['saved'])} saved on average): {blurb}."
        for name, policy, blurb in STEWARDS
    ]


# --- G-1 / G-2: Field Notes, a per-run history kept on this device ---------------------------


def _clean_curve(raw):
    if not isinstance(raw, list):
        return []
    return _decimate([float(v) for v in raw if _num(v, -1000000, 1000000000)])


def _clean_note(raw):
    """One stored run summary with every field forced into range; None when it is unusable."""
    if not isinstance(raw, dict) or not _num(raw.get("survived"), 0, 1000000):
        return None
    mix_raw = raw.get("mix") if isinstance(raw.get("mix"), dict) else {}
    saved_raw = raw.get("region_saved") if isinstance(raw.get("region_saved"), dict) else {}
    best = raw.get("best_region")
    return {
        "survived": int(raw["survived"]),
        "saved": float(raw["saved"]) if _num(raw.get("saved"), -1000000, 1000000000) else 0.0,
        "tipped": int(raw["tipped"]) if _num(raw.get("tipped"), 0, 3) else 0,
        "avg_accel": float(raw["avg_accel"]) if _num(raw.get("avg_accel"), 0, 1000000) else 1.0,
        "mix": {c: int(mix_raw[c]) if _num(mix_raw.get(c), 0, 1000000) else 0 for c in CATEGORIES},
        "region_saved": {
            label: float(saved_raw[label]) if _num(saved_raw.get(label), -1000000, 1000000000) else 0.0
            for label in ARCHIVE_REGIONS
        },
        "best_region": best if best in ARCHIVE_REGIONS else "A",
        "curve": _clean_curve(raw.get("curve")),
        "baseline": _clean_curve(raw.get("baseline")),
    }


def load_field_notes():
    raw = _read_local_storage_item(FIELD_NOTES_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    notes = [n for n in (_clean_note(item) for item in data) if n is not None]
    return notes[-FIELD_NOTES_MAX:]


field_notes = load_field_notes()


def _build_note():
    managed = _managed()
    saved_by = {label: max(0.0, r.temperature_saved()) for label, r in managed}
    best = max(saved_by, key=lambda label: (saved_by[label], -ord(label)))
    return {
        "survived": runstate.run_result["survived"],
        "saved": runstate.run_result["saved"],
        "tipped": sum(1 for _label, r in managed if r.melt_started_round is not None),
        "avg_accel": round(sum(r.average_acceleration_factor for _label, r in managed) / 3, 3),
        "mix": {c: sum(r.capacity[c] for _label, r in managed) for c in CATEGORIES},
        "region_saved": {label: round(v, 3) for label, v in saved_by.items()},
        "best_region": best,
        "curve": _decimate(region.temperature_history),
        "baseline": _decimate(region_d.temperature_history),
    }


def record_field_note():
    """Appends this run's summary and saves the list (keeping the newest FIELD_NOTES_MAX)."""
    field_notes.append(_clean_note(_build_note()))
    del field_notes[:-FIELD_NOTES_MAX]
    _write_local_storage_item(FIELD_NOTES_KEY, json.dumps(field_notes))


def field_note_bests():
    """Best degrees saved per region across every stored run (all zero with no runs)."""
    return {
        label: max([n["region_saved"][label] for n in field_notes] or [0.0])
        for label in ARCHIVE_REGIONS
    }


def field_note_rows():
    rows = []
    for i, n in enumerate(field_notes, start=1):
        mix = n["mix"]
        rows.append(
            f"Run {i}: held {n['survived']} rounds, {deg(n['saved'])} saved, {n['tipped']} region"
            f"{'' if n['tipped'] == 1 else 's'} melted, average acceleration {n['avg_accel']:.2f}x, "
            f"units Output {mix['output']} / Preservation {mix['preserve']} / Monitoring {mix['monitor']}, "
            f"best Region {n['best_region']}."
        )
    return rows


def field_notes_chart_svg():
    """Degrees saved per finished run, as bars (a shape the numbers in the list repeat)."""
    if not field_notes:
        return ""
    width, height = 160, 44
    top = max([n["saved"] for n in field_notes] + [0.001])
    slot = width / len(field_notes)
    bars = "".join(
        f'<rect x="{i * slot + 1:.1f}" y="{height - n["saved"] / top * (height - 4):.1f}" '
        f'width="{min(max(slot - 2, 1), 12):.1f}" height="{n["saved"] / top * (height - 4):.1f}" class="field-bar" />'
        for i, n in enumerate(field_notes)
    )
    label = f"Degrees saved in each of {len(field_notes)} finished run{'' if len(field_notes) == 1 else 's'}, best {deg(top)}."
    return (
        f'<svg viewBox="0 0 {width} {height}" class="field-notes-svg" role="img" aria-label="{label}">'
        f"<title>{label}</title>{bars}</svg>"
    )


def render_field_notes():
    rows = field_note_rows()
    bests = field_note_bests()
    document.getElementById("field-notes-count").innerText = str(len(field_notes))
    document.getElementById("field-notes-list").innerHTML = (
        "".join(f"<li>{row}</li>" for row in rows) if rows
        else "<li>No finished runs yet. Finish a Hold the Line run to start your field notes.</li>"
    )
    document.getElementById("field-notes-bests").innerText = (
        "Best degrees saved per region: "
        + ", ".join(f"Region {label} {deg(bests[label])}" for label in ARCHIVE_REGIONS)
        + "."
    )
    document.getElementById("field-notes-chart").innerHTML = field_notes_chart_svg()
    _render_compare_options()
    render_compare()


# G-2: overlay any two stored runs (or a run against its own no-action baseline) on one graph.
COMPARE_W, COMPARE_H = 160, 70


def compare_choices():
    """[(value, label)] for the two selects: each stored run and each run's no-action baseline."""
    choices = []
    for i in range(1, len(field_notes) + 1):
        choices.append((f"run:{i}", f"Run {i}"))
    for i in range(1, len(field_notes) + 1):
        choices.append((f"base:{i}", f"Run {i} if nobody intervened"))
    return choices


def compare_curve(choice):
    """The stored curve a choice names, or None when the choice does not name a stored run."""
    if not isinstance(choice, str) or ":" not in choice:
        return None
    kind, _sep, index = choice.partition(":")
    if kind not in ("run", "base") or not index.isdigit():
        return None
    i = int(index)
    if not 1 <= i <= len(field_notes):
        return None
    return field_notes[i - 1]["curve" if kind == "run" else "baseline"]


def compare_divergence(a, b):
    """Per-round gaps between two curves over the rounds both cover (empty if either is empty)."""
    return [round(abs(x - y), 3) for x, y in zip(a, b)]


def compare_readout(a, b):
    gaps = compare_divergence(a, b)
    if not gaps:
        return "Pick two runs that have recorded rounds to compare."
    biggest = max(gaps)
    at = gaps.index(biggest) + 1
    first = next((i + 1 for i, g in enumerate(gaps) if g >= 1.0), None)
    parts = [
        f"Over the {len(gaps)} rounds both cover, the gap ends at {deg(gaps[-1])} and peaks at "
        f"{deg(biggest)} in round {at}."
    ]
    parts.append(
        f"They first differ by a degree or more in round {first}." if first
        else "They never differ by a full degree."
    )
    return " ".join(parts)


def compare_chart_svg(a, b):
    if not a or not b:
        return ""
    values = list(a) + list(b)
    lo, hi = min(values + [0.0]), max(values + [MELT_THRESHOLD])
    span = max(hi - lo, 1e-9)
    longest = max(len(a), len(b))

    def points(curve):
        return " ".join(
            f"{(i / max(longest - 1, 1)) * COMPARE_W:.1f},{COMPARE_H - (v - lo) / span * COMPARE_H:.1f}"
            for i, v in enumerate(curve)
        )

    melt_y = COMPARE_H - (MELT_THRESHOLD - lo) / span * COMPARE_H
    label = (
        f"Two temperature curves over up to {longest} rounds. The first ends at {deg(a[-1], plus=True)} "
        f"and the second at {deg(b[-1], plus=True)}. The dashed line is the +{MELT_THRESHOLD:.0f} degree melt threshold."
    )
    return (
        f'<svg viewBox="0 0 {COMPARE_W} {COMPARE_H}" class="compare-svg" role="img" aria-label="{label}">'
        f"<title>{label}</title>"
        f'<line x1="0" y1="{melt_y:.1f}" x2="{COMPARE_W}" y2="{melt_y:.1f}" class="mini-temp-threshold-line" />'
        f'<polyline points="{points(a)}" class="compare-line compare-line--first" />'
        f'<polyline points="{points(b)}" class="compare-line compare-line--second" />'
        f"</svg>"
    )


def _render_compare_options():
    if runstate._compare_option_count == len(field_notes):
        return
    runstate._compare_option_count = len(field_notes)
    choices = compare_choices()
    options = "".join(f'<option value="{value}">{label}</option>' for value, label in choices)
    select_a = document.getElementById("compare-run-a")
    select_b = document.getElementById("compare-run-b")
    select_a.innerHTML = options
    select_b.innerHTML = options
    if choices:
        newest = len(field_notes)
        select_a.value = f"run:{newest}"
        select_b.value = f"base:{newest}"


def render_compare():
    a = compare_curve(document.getElementById("compare-run-a").value)
    b = compare_curve(document.getElementById("compare-run-b").value)
    document.getElementById("compare-chart").innerHTML = compare_chart_svg(a, b) if a and b else ""
    document.getElementById("compare-readout").innerText = (
        compare_readout(a, b) if a is not None and b is not None
        else "Finish a run to compare it with another run or with what would have happened with no action."
    )


# --- rendering and handlers for the mode itself ---------------------------------------------
def result_lines():
    """The end-of-run panel as a list of text lines (empty until the run is over)."""
    if not runstate.run_over or runstate.run_result is None:
        return []
    survived, saved = runstate.run_result["survived"], runstate.run_result["saved"]
    title, nxt, needed = run_title(saved)
    beaten = stewards_beaten(survived)
    if runstate.run_result["reason"] == "limit":
        head = f"You held the line for all {survived} rounds, the limit of a run."
    else:
        tipped = ", ".join(tipped_labels()) or "two regions"
        head = f"The line broke: Regions {tipped} went critical. You held it for {survived} rounds."
    lines = [head, f"Average saved across Regions A to C: {deg(saved)}. Your title: {title}."]
    if nxt is not None:
        lines.append(f"Next title: {nxt} at {deg(needed)} saved ({deg(max(0.0, needed - saved))} to go).")
    else:
        lines.append("That is the top title.")
    lines.append(f"You beat {beaten} of 3 stewards.")
    lines += steward_lines()
    lines += hard_mode_reveal_lines()
    return lines


def hold_line_status():
    if not runstate.hold_the_line:
        if runstate.long_game:
            return "Hold the Line is off (the long game is on; the two modes cannot be combined)."
        return (
            "Hold the Line is off. Turn it on before round 1 to play a run: keep at least two of "
            "the three regions out of the critical tier for as many rounds as you can while escalation "
            "events make the background harsher."
        )
    if runstate.run_over:
        return "Hold the Line: the run is over. Start a new game from the opening screen to try again."
    held = untipped_count()
    return (
        f"Hold the Line, round {region.round_number}: {held} of 3 regions are out of the critical tier "
        f"(you need {HOLD_LINE_MIN_UNTIPPED}). {escalation_text()} Runs like this are unranked: kept out of the "
        "community comparison."
    )


def render_hold_line():
    button = document.getElementById("hold-line-toggle-button")
    button.innerText = "Hold the Line: on" if runstate.hold_the_line else "Hold the Line: off"
    button.disabled = not (can_toggle_hold_the_line() and (runstate.hold_the_line or not runstate.long_game))
    status = hold_line_status()
    if not can_toggle_hold_the_line() and not runstate.hold_the_line:
        status += " (Locked once the first round has been played.)"
    document.getElementById("hold-line-display").innerText = status
    callout = document.getElementById("escalation-callout")
    if runstate.just_escalated and runstate.hold_the_line:
        callout.innerText = (
            f"Escalation: {escalation_event_name(runstate.just_escalated)}. The background rise is now "
            f"{deg(base_rise_per_round(region.round_number), 2)}/round and the most dampening "
            f"investment can hold is {max_dampening(region.round_number) * 100:.0f}%."
        )
        callout.hidden = False
    else:
        callout.hidden = True
    runstate.just_escalated = 0
    result = document.getElementById("hold-line-result")
    lines = result_lines()
    result.hidden = not lines
    result.innerHTML = "".join(f"<li>{line}</li>" for line in lines)
    advance = document.getElementById("advance-round-button")
    advance.disabled = runstate.run_over
    advance.innerText = "Run over" if runstate.run_over else "Advance Round"
