"""Announcements, the damage popup, the run summary and copy text, tab title, skill help text, the damage waterfall, the epitaph, the schedule strip and the countdown and run timer."""

from js import document, localStorage, setTimeout
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_bonuses import format_duration, founding_silenced, run_timer_enabled
from aftermath_pastruns import expected_next_event_damage
from aftermath_persist import VERY_BAD_RUN_SCORE, _el, _now
from aftermath_rules import (
    EVENT_BASE_DAMAGE, EVENT_CATEGORY, EVENT_ICON, EVENT_LABEL, FLAWLESS_BONUS_KNOWLEDGE,
    FLAWLESS_DAMAGE_FRACTION, GROWTH_COST, GROWTH_INCOME_PER_UNIT, MAX_MITIGATION, RESILIENCE_COST,
    SCENARIOS, adjusted_text, entry_is_flawless, entry_mitigation, entry_prevented, flawless_count,
    held_streak, severity_label,
)


# ---- GE-15 hint, GE-13 popup, E-5 announcements -------------------------
def flawless_threshold(event_type):
    return EVENT_BASE_DAMAGE[event_type] * FLAWLESS_DAMAGE_FRACTION


def flawless_hint_text(run_state):
    """GE-15: always tells the player what a Flawless Defense needs for the
    coming event, and whether the current build is on track."""
    if run_state.is_complete():
        return ""
    event_type = run_state.next_event_type()
    limit = flawless_threshold(event_type)
    damage, _severity = expected_next_event_damage(run_state)
    status = "on track" if damage <= limit + 1e-9 else f"expected {damage:.0f}"
    return (
        f"Flawless Defense (+{FLAWLESS_BONUS_KNOWLEDGE} knowledge): hold {EVENT_LABEL[event_type]} damage to "
        f"{limit:.0f} or less ({status})."
    )


def event_announcement(entry):
    prevented = entry_prevented(entry)
    text = (
        f"{EVENT_LABEL[entry['type']]} hit, {entry['damage']:.0f} damage, {prevented:.0f} prevented."
    )
    if entry_is_flawless(entry):
        text += " Flawless Defense."
    return text


def _shared_announce(text):
    """B-7: speak through shared/announcer.js when the page has it (returns True); otherwise the game's own
    live region is used. Never both, so a screen reader does not read a message twice."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    shared = getattr(window, "NoyvjAnnounce", None)
    if shared is None:
        return False
    try:
        shared.say(str(text))
    except Exception:  # noqa: BLE001 -- an announcement must never break the game
        return False
    return True


def announce(text):
    element = document.getElementById("event-announcer")
    if text and _shared_announce(text):
        element.innerText = ""
        return
    element.innerText = text


def render_damage_popup():
    popup = document.getElementById("damage-prevented-popup")
    streak_el = document.getElementById("damage-streak-display")
    if not runstate.run.event_log:
        popup.hidden = True
        streak_el.hidden = True
        popup.innerText = ""
        streak_el.innerText = ""
        return
    last = runstate.run.event_log[-1]
    prevented = entry_prevented(last)
    popup.hidden = False
    if prevented >= 1:
        popup.innerText = f"-{prevented:.0f} damage prevented!"
    else:
        popup.innerText = "No damage prevented. More resilience softens the next hit."
    popup.dataset.prevented = str(int(round(prevented)))
    popup.dataset.eventKey = f"{runstate.run.run_number}-{len(runstate.run.event_log)}"
    parts = []
    streak = held_streak(runstate.run.event_log)
    if streak >= 2:
        parts.append(f"🔥 Held {streak} events in a row")
    if entry_is_flawless(last):
        parts.append(f"✨ Flawless Defense: +{FLAWLESS_BONUS_KNOWLEDGE} knowledge at the end of the run")
    streak_el.innerText = " · ".join(parts)
    streak_el.hidden = not parts


# ---- E-23: knowledge itemisation ---------------------------------------
def knowledge_breakdown_lines(run_state):
    info = run_state.knowledge_breakdown()
    lines = [f"Resources left {info['resources']:.0f} ÷ 20 = {info['raw']} knowledge"]
    if info.get("schedule_factor", 1.0) < 1.0:
        lines.append(
            f"Custom schedule: {info['schedule_factor'] * 100:.0f}% of the Classic mix's damage, "
            "so the base knowledge is scaled to match"
        )
    if info["floor_applied"]:
        lines.append("Minimum of 1 applied: no run ever earns nothing")
    if info["flawless"]:
        lines.append(
            f"Flawless Defense x{info['flawless']}: +{info['flawless_bonus']} knowledge"
        )
    lines.append(f"Total: {info['total']} knowledge point{'s' if info['total'] != 1 else ''}")
    return lines


def knowledge_preview_detail(run_state):
    info = run_state.knowledge_breakdown()
    detail = f"{info['base']} from {info['resources']:.0f} resources"
    if info["flawless"]:
        detail += f", +{info['flawless_bonus']} Flawless Defense"
    return f" ({detail})"


# ---- E-24: copy run summary --------------------------------------------
def run_summary_text(run_state=None):
    run_state = run_state or runstate.run
    name = runstate.meta["settlement_name"] or "My settlement"
    scenario = SCENARIOS[run_state.scenario]["label"]
    done = run_state.is_complete()
    lines = [
        f"Aftermath: {name}, run {run_state.run_number} ({scenario}{', extended' if run_state.extended else ''})"
        + ("" if done else " - in progress")
        + (f" - with neighbour aid +{run_state.aid_given:.0f}" if run_state.aid_given else ""),  # R-31
        f"{'Score' if done else 'Resources so far'}: {run_state.run_score():.0f}"
        + (f" ({adjusted_text(run_state.run_score(), run_state.event_log)})" if done else "")
        + (f" | Knowledge earned: {run_state.knowledge_points_earned()}" if done else ""),
        f"Resilience {run_state.resilience_capacity}, growth {run_state.growth_capacity}, "
        f"damage taken {run_state.damage_taken:.0f}",
    ]
    for index, entry in enumerate(run_state.event_log, start=1):
        extra = " (flawless)" if entry_is_flawless(entry) else ""
        lines.append(
            f"{index}. {EVENT_LABEL[entry['type']]}: {entry['damage']:.0f} damage, "
            f"{entry_prevented(entry):.0f} prevented, {severity_label(entry['severity'])}{extra}"
        )
    return "\n".join(lines)


def copy_result_fields(run_state=None):
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Aftermath, 340 resources left, run 3 (Coastal), 5 events, ...". Read
    by the page's own inline script through pyodide.globals when the shared
    Copy result button is pressed, so it always matches the run right now."""
    run_state = run_state or runstate.run
    events = len(run_state.event_log)
    flawless = flawless_count(run_state.event_log)
    stats = [
        f"run {run_state.run_number} ({SCENARIOS[run_state.scenario]['label']})" + ("" if run_state.is_complete() else ", in progress"),
        {"n": events, "one": "event weathered", "many": "events weathered"},
        f"{run_state.damage_taken:.0f} damage taken",
    ]
    if flawless:
        stats.append({"n": flawless, "one": "flawless defense", "many": "flawless defenses"})
    if run_state.aid_given:  # R-31
        stats.append(f"with neighbour aid +{run_state.aid_given:.0f}")
    return {
        "game": "Aftermath",
        "score": round(run_state.run_score()),
        "unit": "resources left" if run_state.is_complete() else "resources so far",
        "stats": stats,
    }


def _copy_to_clipboard(text):
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    navigator = getattr(_js, "navigator", None)
    clipboard = getattr(navigator, "clipboard", None) if navigator is not None else None
    if clipboard is None:
        return False
    try:
        clipboard.writeText(text)
        return True
    except Exception:
        return False


# ---- E-27: live tab title ----------------------------------------------
def tab_title(run_state=None):
    run_state = run_state or runstate.run
    if run_state.is_complete():
        return f"Aftermath - Run {run_state.run_number} complete, score {run_state.run_score():.0f}"
    return (
        f"Aftermath - Run {run_state.run_number}, event {run_state.event_index + 1} of {len(run_state.schedule)} "
        f"({EVENT_LABEL[run_state.next_event_type()]} next)"
    )


def update_tab_title():
    try:
        document.title = tab_title()
    except Exception:
        pass


# ---- E-29: what a locked skill would help against ---------------------------
# Extra mitigation a skill adds, as {skill_id: (category or None for every event, amount)}.
SKILL_MITIGATION_EXTRA = {
    "early_warning": (None, 0.10),
    "mutual_aid_network": (None, 0.05),
    "civic_preparedness": ("social", 0.35),
    "climate_hardening": ("weather", 0.20),
}


def skill_helps_against(skill_id, run_state=None):
    """For a mitigation skill: ({event label: count}, total damage it would save)
    over the events still to come in this run, from the exact deterministic
    severities, so the line matches what would really happen. None for a skill
    that changes the starting build instead (it applies from the next run)."""
    rule = SKILL_MITIGATION_EXTRA.get(skill_id)
    if rule is None:
        return None
    run_state = run_state or runstate.run
    category, amount = rule
    counts = {}
    saved = 0.0
    for index in range(run_state.event_index, len(run_state.schedule)):
        event_type = run_state.schedule[index]
        if category is not None and EVENT_CATEGORY[event_type] != category:
            continue
        current = run_state.mitigation_for(event_type)
        gain = min(MAX_MITIGATION, current + amount) - current
        severity = run_state.severity_at(index)
        saved += EVENT_BASE_DAMAGE[event_type] * severity * gain
        counts[EVENT_LABEL[event_type]] = counts.get(EVENT_LABEL[event_type], 0) + 1
    return counts, saved


def skill_helps_text(skill_id, run_state=None):
    """The 'Helps against' line shown under a locked skill. Empty once unlocked."""
    if skill_id in runstate.skill_tree.unlocked:
        return ""
    run_state = run_state or runstate.run
    if run_state.normalised:
        return "Skills are switched off in a challenge run."
    if skill_id in founding_silenced():  # GE-10
        return "Your Frontier Charter switches this skill's mitigation off, so buying it would add nothing."
    result = skill_helps_against(skill_id, run_state)
    if result is None:
        if skill_id == "reinforced_infrastructure":
            return "Helps from your next run's first event: +2 resilience is +10% mitigation against every kind of event."
        if skill_id == "community_reserves":
            return "Helps from your next run's first event: 50 more resources to absorb whatever comes first."
        if skill_id == "adaptive_growth":
            events = len(run_state.schedule)
            return f"Helps every event of your next run: +{GROWTH_INCOME_PER_UNIT} resources per event, about +{GROWTH_INCOME_PER_UNIT * events} over {events} events."
        return ""
    counts, saved = result
    if not counts:
        kind = SKILL_MITIGATION_EXTRA[skill_id][0]
        if run_state.is_complete():
            return f"Helps against: {kind or 'every'} events in your next run."
        return f"Helps against: nothing left in this run's schedule (it softens {kind} events, which return in your next run)."
    names = ", ".join(f"{label} \u00d7{count}" if count > 1 else label for label, count in counts.items())
    return f"Helps against: {names}. About {saved:.0f} less damage over the rest of this run at your current build."


# ---- E-18: damage waterfall -----------------------------------------------
def waterfall_lines(breakdown):
    """The text equivalent of the waterfall, one step per line."""
    lines = [f"Base damage: {breakdown['base']:.0f}"]
    change = breakdown["unmitigated"] - breakdown["base"]
    sign = "+" if change >= 0 else "\u2212"
    lines.append(
        f"Severity {breakdown['severity']:.2f}\u00d7 ({severity_label(breakdown['severity'])}): "
        f"{sign}{abs(change):.0f}, so {breakdown['unmitigated']:.0f} before any protection"
    )
    for source in breakdown["sources"]:
        lines.append(f"{source['label']}: \u2212{source['damage']:.0f} ({source['fraction'] * 100:.0f}% of the damage)")
    if breakdown["cap_added_back"] > 0.5:
        lines.append(
            f"Mitigation cap ({MAX_MITIGATION * 100:.0f}%): +{breakdown['cap_added_back']:.0f} damage the protection could not stop"
        )
    lines.append(f"Damage taken: {breakdown['final']:.0f}")
    return lines


def waterfall_segments(breakdown):
    """(label, share of the unmitigated damage 0..1, kind) for the stacked
    bar: what each source really prevented (scaled down proportionally when
    the cap bit) and what got through."""
    unmitigated = breakdown["unmitigated"] or 1.0
    raw = sum(s["fraction"] for s in breakdown["sources"])
    scale = (breakdown["mitigation"] / raw) if raw > 0 else 0.0
    segments = [(s["label"], s["fraction"] * scale, "prevented") for s in breakdown["sources"]]
    segments.append(("Damage taken", breakdown["final"] / unmitigated, "taken"))
    return segments


def render_damage_waterfall():
    wrapper = document.getElementById("damage-waterfall")
    body = document.getElementById("damage-waterfall-body")
    if wrapper is None or body is None:
        return
    breakdown = runstate.run.last_breakdown
    if not runstate.run.event_log or breakdown is None:
        wrapper.hidden = True
        body.innerHTML = ""
        return
    wrapper.hidden = False
    body.innerHTML = ""
    bar = document.createElement("div")
    bar.className = "waterfall-bar"
    bar.setAttribute("role", "img")
    bar.setAttribute("aria-label", "; ".join(waterfall_lines(breakdown)))
    for label, share, kind in waterfall_segments(breakdown):
        if share <= 0.0005:
            continue
        seg = document.createElement("div")
        seg.className = f"waterfall-seg waterfall-seg--{kind}"
        seg.style.width = f"{share * 100:.1f}%"
        seg.title = f"{label}: {share * 100:.0f}%"
        bar.appendChild(seg)
    body.appendChild(bar)
    for text in waterfall_lines(breakdown):
        line = document.createElement("p")
        line.className = "waterfall-line"
        line.innerText = text
        body.appendChild(line)


# ---- GE-21: closing line (epitaph) on the run summary --------------------------
# One short line per finished run, picked from a bank keyed to how the run went. The pick is
# deterministic (run number, so it never flickers between renders and replaying the same run reads
# the same). Lines for a hard run stay gentle on purpose; the dry jokes are kept for runs that went
# well. A Settings checkbox hides it (key written by settings.js).
HIDE_EPITAPH_STORAGE_KEY = "aftermath-hide-epitaph"
EPITAPHS = {
    "ruin": [
        "The settlement is still standing. It just needs a long sit-down.",
        "Every shock left a lesson, and the notes are already in the tree.",
        "A rough run. The people remember what worked, and so does your skill tree.",
        "Tomorrow's plan starts from today's scars, and that is how plans improve.",
        "Nothing is wasted: this run's hard hits are next run's early warnings.",
        "Rebuilding is also a result. Take what it taught you.",
    ],
    "flawless": [
        "The levee held. The mayor, as ever, took the credit.",
        "At least one disaster arrived and found nobody home to hurt.",
        "A shock walked in, read the sea wall, and left.",
        "Perfectly defended, and not one person had to be heroic about it.",
        "The best disaster plan is the one nobody notices until afterwards.",
        "Insurance adjusters were seen weeping with happiness.",
    ],
    "rich": [
        "Weathered it all and still finished with money in the bank.",
        "The settlement ended the year richer than it started. Suspicious, but welcome.",
        "Growth and good luck? No, growth and good planning.",
        "The treasurer would like it noted that this was never in doubt.",
        "Disasters came, the budget stayed standing.",
        "A surplus after seven shocks. The history books will need a bigger margin.",
    ],
    "resilience": [
        "Built to last, and it did.",
        "The walls were thick, the people were prepared, and the weather had to take notes.",
        "Everything was reinforced, including the committee meetings.",
        "A settlement that spent early and slept well.",
        "Concrete, drills and good habits: boring on purpose, and it worked.",
        "When the storm came, the most dramatic thing was the forecast.",
    ],
    "growth": [
        "Fast growth, thin margins, and it still came through.",
        "The economy kept humming through every shock.",
        "Income first, armour later, and the bet paid off this time.",
        "A busy settlement: too busy to be flattened.",
        "The market stalls reopened before the water had finished draining.",
        "Prosperity is also a kind of preparedness.",
    ],
    "steady": [
        "Seven shocks, one settlement, still here.",
        "Nothing glamorous, nothing lost. That is what resilience looks like.",
        "A steady run: the kind that does not make the news, which is the point.",
        "The shocks came and went, and so did the worry.",
        "A solid year. Next year's weather will not care, and neither will you.",
        "Survival, with room for improvement.",
    ],
}
SCENARIO_EPITAPHS = {
    "heat_season": "The summer is over. The shade, the water and the neighbours who checked in all counted.",
    "coastal": "The tide went out again and the harbour was still there.",
    "urban": "The city kept its lights on, its trains running and its arguments civil, mostly.",
}


def epitaph_kind(run_state):
    """Which bucket of EPITAPHS fits a finished run, checked in this order."""
    if run_state.resources <= 0 or run_state.run_score() <= VERY_BAD_RUN_SCORE:
        return "ruin"
    if flawless_count(run_state.event_log) >= 1:
        return "flawless"
    if run_state.resources > run_state.starting_resources:
        return "rich"
    if run_state.resilience_capacity >= 3 and run_state.resilience_capacity > run_state.growth_capacity:
        return "resilience"
    if run_state.growth_capacity >= 3 and run_state.growth_capacity > run_state.resilience_capacity:
        return "growth"
    return "steady"


def epitaph_text(run_state):
    """The closing line for a finished run: a scenario line on every third run of that scenario
    (never over a ruinous run), otherwise from the outcome bucket."""
    kind = epitaph_kind(run_state)
    if kind != "ruin" and run_state.scenario in SCENARIO_EPITAPHS and run_state.run_number % 3 == 0:
        return SCENARIO_EPITAPHS[run_state.scenario]
    bank = EPITAPHS[kind]
    return bank[(run_state.run_number * 5 + len(run_state.event_log)) % len(bank)]


def epitaph_hidden():
    return localStorage.getItem(HIDE_EPITAPH_STORAGE_KEY) == "true"


# ---- E-17: schedule strip -------------------------------------------------
def schedule_strip_entries(run_state):
    """One entry per event in the run's schedule: what it is, whether it is
    done / next / upcoming, and the numbers to show. Upcoming damage is exact
    for this run number (severity is deterministic) at the CURRENT build, so
    it moves as the player invests."""
    entries = []
    for index, event_type in enumerate(run_state.schedule):
        category = EVENT_CATEGORY[event_type]
        entry = {
            "index": index,
            "number": index + 1,
            "type": event_type,
            "label": EVENT_LABEL[event_type],
            "icon": EVENT_ICON[event_type],
            "category": category,
            "category_bonus": run_state.category_bonus(event_type),
        }
        if index < run_state.event_index and index < len(run_state.event_log):
            logged = run_state.event_log[index]
            entry.update(
                state="done",
                damage=logged["damage"],
                severity=logged.get("severity", 1.0),
                mitigation=entry_mitigation(logged),
            )
        else:
            severity = run_state.severity_at(index)
            mitigation = run_state.mitigation_for(event_type)
            entry.update(
                state="next" if index == run_state.event_index else "upcoming",
                damage=EVENT_BASE_DAMAGE[event_type] * severity * (1 - mitigation),
                severity=severity,
                mitigation=mitigation,
            )
        entries.append(entry)
    return entries


def schedule_entry_text(entry):
    """The plain-text detail for one strip entry (hover, focus and screen readers)."""
    head = f"Event {entry['number']}: {entry['label']} ({entry['category']} shock)."
    severity = f"{entry['severity']:.2f}\u00d7 severity, {severity_label(entry['severity'])}"
    if entry["state"] == "done":
        mitigation = entry["mitigation"]
        held = f", {mitigation * 100:.0f}% prevented" if mitigation is not None else ""
        return f"{head} Faced: {entry['damage']:.0f} damage ({severity}{held})."
    bonus = entry["category_bonus"]
    bonus_text = f"a {bonus * 100:.0f}% category bonus" if bonus else "no category bonus"
    when = "Next" if entry["state"] == "next" else "Upcoming"
    return (
        f"{head} {when}: about {entry['damage']:.0f} damage at your current build "
        f"({severity}; {entry['mitigation'] * 100:.0f}% mitigation, {bonus_text})."
    )


def render_schedule_strip():
    strip = document.getElementById("schedule-strip")
    if strip is None:
        return  # a cached older page without the strip (service worker serves stale HTML once)
    strip.innerHTML = ""
    entries = schedule_strip_entries(runstate.run)
    default_text = ""
    for entry in entries:
        text = schedule_entry_text(entry)
        if entry["state"] == "next":
            default_text = text
        mark = {"done": "\u2713 ", "next": "\u25b6 ", "upcoming": ""}[entry["state"]]
        chip = document.createElement("li")
        chip.className = f"schedule-chip schedule-chip--{entry['state']} event-category--{entry['category']}"
        chip.innerText = f"{mark}{entry['number']} {entry['icon']} {entry['label']}"
        chip.title = text
        chip.setAttribute("tabindex", "0")
        chip.setAttribute("aria-label", text)
        chip.setAttribute("data-detail", text)
        strip.appendChild(chip)
    if not default_text:
        default_text = f"Run complete: all {len(entries)} events faced."
    detail = document.getElementById("schedule-detail")
    detail.innerText = default_text
    detail.setAttribute("data-default", default_text)
    stage = countdown_stage(runstate.run)  # GE-26
    strip.setAttribute("data-countdown", str(stage))
    note = _el("countdown-note")
    if note is not None:
        note.innerText = countdown_note_text(runstate.run)
        note.hidden = stage == 0


# ---------------------------------------------------------------------------
# GE-26: the countdown pulse. The next event's chip on the schedule strip pulses gently, and grows a little
# more the closer the player is to having nothing left to do but Face Next Event: the "countdown" is the
# purchases the resources can still make (stage 1: four or more, stage 2: one to three, stage 3: none, so
# Resolve is the natural next step). A hint in words says the same, always. CSS-only; the Settings effects
# switch and Reduce motion turn the animation off and leave the words.
# ---------------------------------------------------------------------------
COUNTDOWN_STAGE_1_UNITS = 4


def purchases_left(run_state):
    """How many more single units the current resources could buy at the cheaper price (growth)."""
    return int(max(0.0, run_state.resources) // min(RESILIENCE_COST, GROWTH_COST))


def countdown_stage(run_state):
    """0 once the run is over, else 1 (plenty left to spend), 2 (a few purchases left) or 3 (nothing left to buy)."""
    if run_state.is_complete():
        return 0
    left = purchases_left(run_state)
    if left >= COUNTDOWN_STAGE_1_UNITS:
        return 1
    return 2 if left >= 1 else 3


def countdown_note_text(run_state):
    stage = countdown_stage(run_state)
    if stage == 0:
        return ""
    if stage == 3:
        return f"Nothing left you can afford: {EVENT_LABEL[run_state.next_event_type()]} is the next step."
    left = purchases_left(run_state)
    return f"You could still buy up to {left} unit{'s' if left != 1 else ''} before {EVENT_LABEL[run_state.next_event_type()]}."


def run_timer_text(run_state):
    """The words for #run-timer-display (shown only while the Settings switch is on)."""
    if not run_timer_enabled():
        return ""
    if run_state.timed:
        return f"Run time: {format_duration(run_state.elapsed)}" + (" (final)" if run_state.is_complete() else "")
    if run_state.timed is None:
        return "Run time: starts with your first move"
    return "Run time: not timed (the timer was off when this run began); it times your next run"


def _timer_chain_step(*args):
    runstate._timer_chain_pending = False
    if run_timer_enabled() and runstate.run.timed and not runstate.run.is_complete():
        runstate.run.tick_timer(_now())
        render_run_timer()


def _schedule_timer_tick():
    if runstate._timer_chain_pending:
        return
    runstate._timer_chain_pending = True

    def _fire(*args):
        proxy.destroy()
        _timer_chain_step()

    proxy = create_proxy(_fire)
    setTimeout(proxy, 1000)


def render_run_timer():
    element = _el("run-timer-display")
    if element is None:
        return
    text = run_timer_text(runstate.run)
    element.innerText = text
    element.hidden = not text
    if run_timer_enabled() and runstate.run.timed and not runstate.run.is_complete():
        _schedule_timer_tick()
