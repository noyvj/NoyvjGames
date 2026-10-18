"""Perfect Fit, the Crisis Calendar with Surge Tests, the Mayor's Council upgrade tree and the spoken round summary (round_announcement_text)."""

from js import document

import drift_runstate as runstate
from drift_ledger import latest_recap
from drift_messages import integration_turning_point_message, thriving_callout_message
from drift_model_region import region
from drift_rules import (
    BOSS_ROUNDS, CALENDAR_KINDS, CALENDAR_LAST_ROUND, COUNCIL_BRANCHES, COUNCIL_INTERVAL, COUNCIL_PROGRAMS,
    PERFECT_FIT_FUNDS_PER_STREAK, PERFECT_FIT_MARGIN, PERFECT_FIT_STREAK_CAP, calendar_event_for_round,
    council_next_program,
)


def _round_marks():
    """The one-time round-end facts worth saying only when they change: second-wave status and the two
    milestone rounds. Taken before a round and compared after."""
    return (region.second_wave_status, region.net_positive_round, region.thriving_round)


def round_announcement_text(marks_before=None):
    """What a player sees change after a round resolves, as short sentences built from the game's own readouts:
    the round recap line, a calendar event's result, a second wave or milestone that just changed, the new
    round's arrivals, funds and wellbeing. Empty before the first round."""
    recap = latest_recap()
    if recap is None:
        return ""
    parts = [recap]
    if region.calendar_enabled and region.calendar_log:
        last = region.calendar_log[-1]
        if last["round"] == region.round_number - 1:
            parts.append(calendar_result_message(last))
    before = marks_before if marks_before is not None else _round_marks()
    if region.second_wave_status != before[0] and region.second_wave_message():
        parts.append(region.second_wave_message())
    if before[1] is None and region.net_positive_round is not None:
        parts.append(integration_turning_point_message(region))
    if before[2] is None and region.thriving_round is not None:
        parts.append(thriving_callout_message(region))
    parts.append(
        f"Round {region.round_number} begins: {region.arrivals_this_round():.0f} people arriving. "
        f"Funds {region.funds:.0f}. Strain {region.strain_fraction() * 100:.0f}% ({region.strain_level()}). "
        f"Wellbeing score {region.wellbeing_score():.0f}"
    )
    return " ".join(p.strip() if p.strip().endswith((".", "!", "?")) else p.strip() + "." for p in parts if p)


def perfect_fit_message():
    """GI-13: the streak line shown beside the forecast."""
    streak = region.perfect_fit_streak
    bonus = PERFECT_FIT_FUNDS_PER_STREAK * min(streak, PERFECT_FIT_STREAK_CAP)
    best = region.best_perfect_fit_streak
    if region.total_capacity() > 0 and region.total_arrivals > 0:
        slack = region.total_capacity() + region.coverage_bonus() - region.total_arrivals
        if region.is_perfect_fit():
            now = f"Holding a Perfect Fit right now ({slack:.0f} spare)."
        elif slack < 0:
            now = f"Not a Perfect Fit right now: {-slack:.0f} short."
        else:
            now = f"Not a Perfect Fit right now: {slack:.0f} spare (the limit is {PERFECT_FIT_MARGIN:.0f})."
    else:
        now = "Build some capacity to start."
    if streak > 0:
        head = f"Perfect Fit streak: {streak} round(s), +{bonus:.0f} funds a round."
    else:
        head = (
            f"Perfect Fit: end a round with capacity covering everyone who has arrived and no more than "
            f"{PERFECT_FIT_MARGIN:.0f} to spare. Each round in a row adds {PERFECT_FIT_FUNDS_PER_STREAK:.0f} funds of "
            f"income, up to {PERFECT_FIT_FUNDS_PER_STREAK * PERFECT_FIT_STREAK_CAP:.0f}."
        )
    tail = f" Best streak this region: {best}." if best > 0 else ""
    return f"{head} {now}{tail}"


def calendar_next_event(after_round):
    """The first scheduled event on a round after `after_round`, or None."""
    for r in range(after_round + 1, CALENDAR_LAST_ROUND + 1):
        event = calendar_event_for_round(r)
        if event is not None:
            return event
    return None


def calendar_describe(event, braced=False):
    spec = CALENDAR_KINDS[event["kind"]]
    label = event["name"] if event["kind"] == "boss" else spec["label"]
    if event["kind"] == "boss":
        label = f"Surge Test, {event['name']}"
    tag = " Braced." if braced else ""
    return f"{spec['icon']} {label}: {spec['text']}.{tag}"


def calendar_message():
    """GI-2: the Next Round preview, from fixed data only."""
    if not region.calendar_enabled:
        return (
            "Off. Switch it on for a fixed, visible schedule of events: surges, budget cuts, floods and bumper "
            "harvests every 4 rounds from round 8, and three named Surge Tests at rounds 25, 50 and 75. Each "
            "is shown a round ahead and can be softened by paying to brace. Nothing is random and nothing ends a run."
        )
    lines = []
    here = region.calendar_event()
    if here is not None:
        lines.append(f"This round (round {region.round_number}): " + calendar_describe(here, region.round_number in region.braced_rounds))
    ahead = region.calendar_event(region.round_number + 1)
    if ahead is not None:
        lines.append(f"Next round (round {ahead['round']}): " + calendar_describe(ahead, ahead["round"] in region.braced_rounds))
    if not lines:
        later = calendar_next_event(region.round_number)
        if later is None:
            lines.append("No more events are scheduled in this run.")
        else:
            lines.append(f"Nothing this round or next. Next event: round {later['round']}, {later['name']}.")
    return " ".join(lines)


def calendar_result_message(entry):
    """What the most recent event did, with the Surge Test 'held the line' card."""
    kind = entry["kind"]
    spec = CALENDAR_KINDS[kind]
    if kind == "boss":
        name = BOSS_ROUNDS.get(entry["round"], "Surge Test")
        if entry["held"]:
            return (
                f"🏛️ Held the line! {name} (round {entry['round']}) came and your capacity covered "
                "everyone who arrived. That is what preparing ahead of a surge looks like."
            )
        return (
            f"🏛️ {name} (round {entry['round']}) outran your capacity this time, so strain will show it. "
            "Nothing is lost for good: build and it recovers."
        )
    if entry["held"] is True:
        return f"{spec['icon']} {spec['label']} at round {entry['round']}: capacity still covers everyone who has arrived."
    if entry["held"] is False:
        return f"{spec['icon']} {spec['label']} at round {entry['round']}: it outran capacity for now. Build and it recovers."
    return f"{spec['icon']} {spec['label']} at round {entry['round']}: done."


def _reset_civic_notes():
    runstate.calendar_note_text = ""
    runstate.council_note_text = ""
    runstate.template_note = ""


def render_calendar():
    toggle = document.getElementById("calendar-toggle-button")
    toggle.innerText = "Crisis Calendar: ON" if region.calendar_enabled else "Crisis Calendar: OFF"
    if region.calendar_enabled:
        toggle.classList.add("active")
    else:
        toggle.classList.remove("active")
    document.getElementById("calendar-display").innerText = calendar_message()
    brace = document.getElementById("calendar-brace-button")
    target = region.brace_target()
    brace.hidden = not region.calendar_enabled
    if target is not None:
        cost = CALENDAR_KINDS[target["kind"]]["brace_cost"]
        brace.innerText = f"Brace for {target['name']} ({cost:.0f} funds)"
        brace.disabled = region.funds < cost
    else:
        brace.innerText = "Nothing to brace for"
        brace.disabled = True
    note = document.getElementById("calendar-note")
    text = runstate.calendar_note_text
    if not text and region.calendar_enabled and region.calendar_log:
        last = region.calendar_log[-1]
        if last["round"] == region.round_number - 1:
            text = calendar_result_message(last)
    note.innerText = text
    note.hidden = text == ""


# -- GI-1: Mayor's Council --
def council_pending_picks(r=None):
    r = region if r is None else r
    completed = max(0, r.round_number - 1)
    earned = min(completed // COUNCIL_INTERVAL, len(COUNCIL_PROGRAMS))
    return max(0, earned - len(r.council_picks))


def council_options(r=None):
    r = region if r is None else r
    options = {}
    for branch in COUNCIL_BRANCHES:
        program = council_next_program(branch, r.council_picks)
        if program is not None:
            options[branch] = program
    return options


def council_pick(branch):
    if council_pending_picks() <= 0:
        return False
    program = council_options().get(branch)
    if program is None:
        return False
    region.council_picks.append(program["id"])
    return True


def council_status_message():
    if len(region.council_picks) >= len(COUNCIL_PROGRAMS):
        return "Every program has been adopted."
    pending = council_pending_picks()
    if pending > 0:
        return f"The council meets: choose one program ({pending} pick{'s' if pending != 1 else ''} waiting)."
    completed = max(0, region.round_number - 1)
    next_at = (completed // COUNCIL_INTERVAL + 1) * COUNCIL_INTERVAL
    return f"Next council pick after round {next_at}. Programs adopted: {len(region.council_picks)} of {len(COUNCIL_PROGRAMS)}."


def council_tree_html():
    rows = []
    for branch, label in COUNCIL_BRANCHES.items():
        rows.append(f"<li><strong>{label}</strong><ul>")
        for program in COUNCIL_PROGRAMS:
            if program["branch"] != branch:
                continue
            mark = "✓" if program["id"] in region.council_picks else "○"
            rows.append(f"<li>{mark} <strong>{program['name']}</strong> (tier {program['tier']}): {program['text']}</li>")
        rows.append("</ul></li>")
    return "<ul class=\"council-tree\">" + "".join(rows) + "</ul>"


def render_council():
    document.getElementById("council-status").innerText = (runstate.council_note_text + " " if runstate.council_note_text else "") + council_status_message()
    pending = council_pending_picks()
    options = council_options()
    for branch, label in COUNCIL_BRANCHES.items():
        button = document.getElementById(f"council-pick-{branch}")
        program = options.get(branch)
        if program is None:
            button.innerText = f"{label}: complete"
            button.disabled = True
            button.title = "Every program on this branch has been adopted."
        else:
            button.innerText = f"{label}: {program['name']}"
            button.disabled = pending <= 0
            button.title = program["text"]
    document.getElementById("council-tree").innerHTML = council_tree_html()
