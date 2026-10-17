"""The Scarcity Run's finish, tick hook and panel (calendar, ghost section, tally)."""

import challenges
from js import document

import sol_runstate as runstate
from sol_ghost import _keep_daily_ghost, _load_daily_ghosts, _refresh_ghost_strip, _render_ghost_track
from sol_rules import PLANETS
from sol_scarcity import (
    _scarcity_mean_progress, _scarcity_refs, _scarcity_status_line, scarcity_days, scarcity_goal_met,
)
from sol_scarcity_run import scarcity_spec
from sol_util import _display_toast, _make_button, _make_text, _split_time, _today_utc


def _record_shared_daily(date_text, words, ticks, under_par):
    """Z-5b: when TODAY's Scarcity Run is finished, tell the shared record the hub's Today strip reads
    (`localStorage["noyvj-daily-v1"]`, written by `NoyvjSeed.daily.markCompleted`, which counts once per day). An older
    date from the calendar never counts. Fails soft: no shared script (pytest, an old page) or any error means nothing."""
    if date_text != _today_utc():
        return
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        daily = getattr(getattr(js.window, "NoyvjSeed", None), "daily", None)
        if daily is None:
            return
        info = js.Object.new()
        info.text = f"Scarcity Run {words} in {_split_time(ticks)}" + (", under par" if under_par else "")
        daily.markCompleted("sol", info)
    except Exception:  # noqa: BLE001 -- a courtesy record must never break the run's own result
        pass


def _scarcity_finish():
    run = runstate._scarcity
    date_text = run["spec"]["date"]
    run["done"] = runstate.total_ticks
    scarcity_days[date_text] = challenges.merge_record(scarcity_days.get(date_text), runstate.total_ticks, run["spec"]["par"])
    _keep_daily_ghost(date_text, runstate.total_ticks, run["samples"])
    under = runstate.total_ticks < run["spec"]["par"]
    _record_shared_daily(date_text, run["spec"]["words"], runstate.total_ticks, under)
    _display_toast(
        f"\U0001f3af Scarcity Run done in {_split_time(runstate.total_ticks)}"
        + (" - faster than the Governor alone!" if under else f" (the Governor alone: {_split_time(run['spec']['par'])})."))


def _scarcity_tick():
    run = runstate._scarcity
    if run is None:
        return
    if runstate.total_ticks % challenges.GHOST_STEP == 0:
        run["samples"].append(round(_scarcity_mean_progress() * 10))
        if len(run["samples"]) > challenges.GHOST_MAX_SAMPLES:
            run["samples"].pop()
        _refresh_ghost_strip()
    if run["done"] is None and scarcity_goal_met():
        _scarcity_finish()
        update_scarcity_display(force=True)


# --- the Scarcity Run panel -----------------------------------------------------------------


def _scarcity_record_text(date_text):
    record = scarcity_days.get(date_text)
    if not record:
        return "Not played yet."
    return (f"Your best: {_split_time(record['ticks'])} ({record['ticks']} ticks), {record['tries']} "
            f"{'try' if record['tries'] == 1 else 'tries'}" + (", faster than the Governor alone" if record.get("under_par") else "") + ".")


def _scarcity_rules_texts(spec):
    names = {"Earth": "Earth", "Moon": "the Moon", "Mars": "Mars"}
    lines = [f"Ecology decays {spec['decay']:g}x as fast as usual. Auto-Machines and Recyclers cost {spec['cost']:g}x. "
             f"Terraforming runs {challenges.TERRAFORM_SPEED:g}x faster, so the day is about stabilising ecology, not waiting."]
    yields = []
    for world in challenges.WORLDS:
        factor = spec["yields"][world]
        note = " (scarce)" if factor < 1 else (" (rich)" if factor > 1 else "")
        yields.append(f"{PLANETS[world]['resource_name']} x{factor:g}{note}")
    lines.append("Yields: " + ", ".join(yields) + ".")
    for world in challenges.WORLDS:
        load = spec["loadout"][world]
        cfg = PLANETS[world]
        lines.append(
            f"Start on {names[world]}: {load['stock']} {cfg['resource_name']}, "
            f"{load['generators']} {cfg['generator_singular'] if load['generators'] == 1 else cfg['generator_plural']}, "
            f"{load['recyclers']} Recycler{'s' if load['recyclers'] != 1 else ''}, ecology {load['ecology']}%.")
    lines.append("Near Bodies research is done (the Moon and Mars are open). Timed anomalies, the rhythm bonus and chain "
                 "bonuses are off, so everyone plays the same rules.")
    return lines


def _scarcity_calendar_signature():
    return (tuple(sorted((d, r["ticks"], bool(r.get("under_par"))) for d, r in scarcity_days.items())),)


def _scarcity_structure_signature():
    run_key = None if runstate._scarcity is None else (runstate._scarcity["spec"]["date"], runstate._scarcity["done"] is not None)
    return (run_key, runstate._scarcity_selected, runstate._scarcity_month, _scarcity_calendar_signature(), runstate._scarcity_notice,
            runstate._scarcity_ghost_choice, None if runstate._scarcity_friend is None else runstate._scarcity_friend["label"], _today_utc())


def _day_label(date_text):
    d = challenges.parse_date(date_text)
    return f"{d.day} {_MONTH_NAMES[d.month - 1]} {d.year}"


_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                "November", "December"]
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _build_scarcity_panel():
    panel = document.getElementById("scarcity-panel")
    kept_field = _scarcity_refs.get("friend")
    if kept_field is not None:
        runstate._scarcity_friend_code = kept_field.value  # a rebuild must not eat a half-pasted code
    panel.innerHTML = ""
    _scarcity_refs.clear()
    today = _today_utc()
    panel.appendChild(_make_text("stats-panel-heading", "Scarcity Run"))
    panel.appendChild(_make_text(
        "chains-intro",
        "A daily challenge, the same puzzle for everyone, made from the date alone. It is played on a copy of the game: your "
        "campaign, achievements and save are never touched, and leaving costs nothing. There are no streaks, a missed day costs "
        "nothing, and any day from 1 October 2026 is open. A run is not saved: closing the page ends it."))
    if today is None:
        panel.appendChild(_make_text("chain-card-detail", "The date is not available here, so no day can be offered."))
        return
    if runstate._scarcity_selected is None or not challenges.playable(runstate._scarcity_selected, today):
        runstate._scarcity_selected = today
    if runstate._scarcity_month is None:
        runstate._scarcity_month = challenges.month_of(runstate._scarcity_selected)
    if runstate._scarcity_notice:
        panel.appendChild(_make_text("chain-card-detail", runstate._scarcity_notice))
    run = runstate._scarcity
    shown = run["spec"]["date"] if run is not None else runstate._scarcity_selected
    card = document.createElement("div")
    card.className = "chain-card chain-card--found scarcity-card"
    title = "Today" if shown == today else "Past day"
    card.appendChild(_make_text("chain-card-name", f"{title}: {_day_label(shown)}, seed {challenges.seed_words(shown)}"))
    try:
        spec = run["spec"] if run is not None else scarcity_spec(shown)
    except RuntimeError:
        spec = None
    if spec is None:
        card.appendChild(_make_text("chain-card-detail", "No fair challenge could be made for this day."))
    else:
        card.appendChild(_make_text("chain-card-detail", "Goal: " + challenges.goal_text(spec)))
        for line in _scarcity_rules_texts(spec):
            card.appendChild(_make_text("chain-card-detail", line))
        card.appendChild(_make_text("chain-card-detail", f"The Governor alone does it in {_split_time(spec['par'])} (par)."))
        card.appendChild(_make_text("chain-card-count", _scarcity_record_text(shown)))
        if run is None:
            card.appendChild(_make_button(
                "Today's Scarcity Run" if shown == today else f"Play {_day_label(shown)}",
                {"data-action": "play", "data-date": shown}, None))
        else:
            status = _make_text("chain-card-count", _scarcity_status_line())
            card.appendChild(status)
            _scarcity_refs["status"] = status
            card.appendChild(_make_button("Restart this day", {"data-action": "play", "data-date": shown}, None))
            card.appendChild(_make_button("Leave the run (back to your campaign)", {"data-action": "leave"}, None))
    panel.appendChild(card)
    _build_scarcity_ghost_section(panel, shown, spec)
    _build_scarcity_calendar(panel, today)
    _build_scarcity_tally(panel, today)
    entry = challenges.leaderboard_entry(shown, scarcity_days[shown]) if shown in scarcity_days else None
    panel.appendChild(_make_text(
        "chain-card-detail",
        "Daily board: not open yet. Your time is kept as ticks in your save under the name " +
        f"\"{(entry or {'board': 'sol-scarcity-daily'})['board']}\", ready for an opt-in board later; nothing is sent anywhere."))


def _build_scarcity_ghost_section(panel, date_text, spec):
    section = document.createElement("div")
    section.className = "chain-card scarcity-ghost"
    section.appendChild(_make_text("chain-card-name", "Race a ghost (optional)"))
    section.appendChild(_make_text(
        "chain-card-detail",
        "A ghost is a recording of terraform progress, checked every 25 ticks. It shows how many points ahead (+) or behind (-) "
        "you are, in words as well as symbols. Chosen before the run starts."))
    best = _load_daily_ghosts().get(date_text)
    options = [("none", "No ghost", True), ("best", "My best for this day" + ("" if best else " (none yet)"), best is not None),
               ("par", "The Governor alone", spec is not None)]
    row = document.createElement("div")
    row.className = "scarcity-ghost-row"
    for key, label, enabled in options:
        row.appendChild(_make_button(label, {"data-action": "ghost-choice", "data-value": key}, None,
                                     selected=(runstate._scarcity_ghost_choice == key), disabled=not enabled or runstate._scarcity is not None))
    friend_label = runstate._scarcity_friend["label"] if runstate._scarcity_friend is not None and runstate._scarcity_friend["date"] == date_text else None
    row.appendChild(_make_button("A friend's blueprint" + (f": {friend_label}" if friend_label else ""),
                                 {"data-action": "ghost-choice", "data-value": "friend"}, None,
                                 selected=(runstate._scarcity_ghost_choice == "friend"),
                                 disabled=friend_label is None or runstate._scarcity is not None))
    section.appendChild(row)
    if runstate._scarcity is None:
        section.appendChild(_make_text(
            "chain-card-detail",
            "A friend's blueprint code (from Blueprint Swap in the Build Plan) races as the Governor playing this day with their "
            "Doctrines and rule twists."))
        field = document.createElement("input")
        field.type = "text"
        field.placeholder = "Paste a SOLPLAN1: code"
        field.setAttribute("aria-label", "Friend blueprint code")
        field.className = "build-plan-input capsule-name"
        field.value = runstate._scarcity_friend_code
        section.appendChild(field)
        _scarcity_refs["friend"] = field
        section.appendChild(_make_button("Make this friend's ghost", {"data-action": "friend-ghost", "data-date": date_text}, None))
    else:
        track = document.createElement("div")
        track.className = "ghost-track"
        section.appendChild(track)
        _scarcity_refs["track"] = track
        _render_ghost_track(track, runstate._scarcity["samples"], runstate._scarcity["ghost"], runstate._scarcity["ghost_label"])
    panel.appendChild(section)


def _build_scarcity_calendar(panel, today):
    year, month = runstate._scarcity_month
    wrap = document.createElement("div")
    wrap.className = "scarcity-calendar"
    head = document.createElement("div")
    head.className = "scarcity-calendar-head"
    can_back = challenges.shift_month(year, month, -1) >= challenges.month_of(challenges.EPOCH)
    can_forward = challenges.shift_month(year, month, 1) <= challenges.month_of(today)
    head.appendChild(_make_button("‹ Earlier", {"data-action": "month", "data-value": "-1"}, None, disabled=not can_back))
    head.appendChild(_make_text("scarcity-month", f"{_MONTH_NAMES[month - 1]} {year}", tag="span"))
    head.appendChild(_make_button("Later ›", {"data-action": "month", "data-value": "1"}, None, disabled=not can_forward))
    wrap.appendChild(head)
    grid = document.createElement("div")
    grid.className = "scarcity-grid-calendar"
    grid.setAttribute("role", "group")
    grid.setAttribute("aria-label", "Past days")
    for name in _WEEKDAYS:
        grid.appendChild(_make_text("scarcity-weekday", name, tag="span"))
    chosen = runstate._scarcity["spec"]["date"] if runstate._scarcity is not None else runstate._scarcity_selected
    for week in challenges.month_weeks(year, month):
        for cell in week:
            if cell is None:
                grid.appendChild(_make_text("scarcity-day scarcity-day--blank", "", tag="span"))
                continue
            record = scarcity_days.get(cell)
            mark = " ★" if record and record.get("under_par") else (" ✓" if record else "")
            day = challenges.parse_date(cell).day
            label = f"{day}{mark}"
            open_day = challenges.playable(cell, today)
            words = [_day_label(cell)]
            if cell == today:
                words.append("today")
            if record:
                words.append(f"done in {_split_time(record['ticks'])}" + (", faster than the Governor alone" if record.get("under_par") else ""))
            elif open_day:
                words.append("not played yet")
            else:
                words.append("not open")
            button = _make_button(label, {"data-action": "pick", "data-date": cell, "aria-label": ", ".join(words)}, None,
                                  selected=(cell == chosen), disabled=not open_day)
            button.className += " scarcity-day"
            if cell == chosen:
                button.setAttribute("aria-pressed", "true")
            grid.appendChild(button)
    wrap.appendChild(grid)
    wrap.appendChild(_make_text("chain-card-detail", "✓ played, ★ played and faster than the Governor alone. Pick a day to read its rules first."))
    panel.appendChild(wrap)


def _build_scarcity_tally(panel, today):
    tally = challenges.tally(scarcity_days, today)
    panel.appendChild(_make_text(
        "chain-card-count", f"Days played: {tally['played']} of the {tally['open']} open so far. Faster than the Governor alone: {tally['under_par']}."))
    if not tally["open"]:
        return
    first = challenges.parse_date(challenges.EPOCH)
    rows = []
    cells = []
    for offset in range(tally["open"]):
        text = challenges.add_days(challenges.EPOCH, offset)
        record = scarcity_days.get(text)
        cells.append("★" if record and record.get("under_par") else ("■" if record else "□"))
    lead = first.weekday()
    cells = [" "] * lead + cells
    for index in range(0, len(cells), 7):
        rows.append("".join(cells[index:index + 7]))
    rows = rows[-10:]
    grid = _make_text("scarcity-tally-grid", "\n".join(rows), tag="pre")
    grid.setAttribute("aria-label", f"Days played grid: {tally['played']} of {tally['open']}")
    panel.appendChild(grid)
    panel.appendChild(_make_text("chain-card-detail", "■ played, ★ faster than the Governor alone, □ not played. Rows are weeks (Monday first), newest last."))


def update_scarcity_display(force=False):
    toggle = document.getElementById("scarcity-toggle-button")
    panel = document.getElementById("scarcity-panel")
    strip = document.getElementById("scarcity-strip")
    toggle.innerText = ("Hide Scarcity Run" if runstate.scarcity_open else "\U0001f3af Scarcity Run") + (" (on)" if runstate._scarcity is not None else "")
    strip.hidden = runstate._scarcity is None
    if runstate._scarcity is not None:
        document.getElementById("scarcity-strip-text").innerText = _scarcity_status_line()
    panel.hidden = not runstate.scarcity_open
    if not runstate.scarcity_open:
        runstate._scarcity_signature = None
        return
    signature = _scarcity_structure_signature()
    if force or signature != runstate._scarcity_signature:
        _build_scarcity_panel()
        runstate._scarcity_signature = _scarcity_structure_signature()
    status = _scarcity_refs.get("status")
    if status is not None and runstate._scarcity is not None:
        status.innerText = _scarcity_status_line()
