"""The ghost of your best run, shareable run codes, challenge runs, today's run, and the schedule builder."""

import ghost as ghost_lib
import run_code as shared_run_code
import seed as shared_seed
from js import document, localStorage
from pyodide.ffi import create_proxy

import aftermath_runstate as runstate
from aftermath_bonuses import neighbour_aid_plan
from aftermath_persist import (
    CHALLENGE_BEST_MAX, CUSTOM_MAX_EVENTS, CUSTOM_MIN_EVENTS, CUSTOM_NAME_MAX, CUSTOM_SCHEDULES_MAX,
    GHOST_STORAGE_KEY, _clean_name, _el, _sanitize_ghosts, ghost_mode_key, save_meta,
)
from aftermath_rules import (
    DEFAULT_SCENARIO, EVENT_BASE_DAMAGE, EVENT_CATEGORY, EVENT_ICON, EVENT_LABEL, EVENT_SCHEDULE, SCENARIOS,
    adjusted_score, adjusted_text,
)
from aftermath_runview import announce


# render() is defined in aftermath_renderer, which comes later in the module list; that module puts it here when it
# loads (see the end of aftermath_renderer.py). Calls below find it at run time.
render = None


# ---- Z-3d: the ghost of your best run (shared/ghost.py) ----------------------------------------------
# One number per event: the resources left after it. Your best finished run on each schedule (a scenario, or its
# doubled form) is kept in meta["ghosts"] as a shared ghost trace; the next run on that schedule is compared with it
# after every event, in words only (Aftermath has no chart to draw on). Challenge runs, built schedules and runs
# that received neighbour aid are kept out, like every other comparison here. Nothing is timed or lost.
def ghost_run_eligible(run_state):
    """Can this run be compared with a ghost (and become one)? Not a friend's challenge, a built schedule
    or a run with neighbour aid planned or received."""
    return not (run_state.normalised or run_state.custom_events or run_state.aid_given or neighbour_aid_plan(run_state))


def _load_resources_log(raw, event_index):
    """The saved per-event resources, cleaned. Anything that is not exactly one finite number per event
    already resolved (an older save, a hand-edited one) gives [] and the run simply has no ghost comparison."""
    if not isinstance(raw, list) or event_index < 1 or len(raw) != event_index:
        return []
    cleaned = [ghost_lib.clean_number(v) for v in raw]
    return [] if any(v is None for v in cleaned) else cleaned


def ghost_entry(run_state):
    """The stored best run for this run's schedule as {"run", "score", "trace"}, or None."""
    key = ghost_mode_key(run_state.scenario, run_state.extended)
    raw = runstate.meta.get("ghosts", {}).get(key)
    return _sanitize_ghosts({key: raw}).get(key) if raw is not None else None   # re-checked on every read


def file_run_ghost(run_state):
    """Keep a just-finished run's trace as the schedule's ghost when it scores at least as well as the one it
    replaces (the latest wins a tie). Returns True when it was filed."""
    if not ghost_run_eligible(run_state) or len(run_state.resources_log) != len(run_state.schedule):
        return False
    recorder = ghost_lib.Recorder()
    for value in run_state.resources_log:
        recorder.record(value)
    trace = recorder.trace(f"Run {run_state.run_number}")
    score = ghost_lib.clean_number(run_state.run_score())
    if trace is None or score is None:
        return False
    key = ghost_mode_key(run_state.scenario, run_state.extended)
    previous = runstate.meta.get("ghosts", {}).get(key)
    if previous is not None and score < previous["score"]:
        return False
    runstate.meta.setdefault("ghosts", {})[key] = {"run": run_state.run_number, "score": score, "trace": trace}
    save_meta()
    return True


def ghost_enabled():
    try:
        return localStorage.getItem(GHOST_STORAGE_KEY) != "0"
    except Exception:
        return True


def ghost_note_text(run_state=None):
    """The sentence under the damage preview: where this run stands against the best run on the same schedule,
    in the shared ghost wording. "" when this run cannot be compared."""
    run_state = run_state or runstate.run
    if not ghost_run_eligible(run_state):
        return ""
    entry = ghost_entry(run_state)
    if entry is None:
        return "Ghost: finish a run on this schedule and your best one is kept here to race, one number after each event."
    trace, score = entry["trace"], ghost_lib.format_number(entry["score"])
    if run_state.is_complete() and entry["run"] == run_state.run_number:
        return f"Ghost: this run is your best on this schedule ({score} resources left). It will be the ghost for your next one."
    if run_state.event_index == 0:
        return (f"Ghost: your best run on this schedule ({trace['label'] or 'earlier run'}) ended with {score} resources. "
                "It is compared with this run after every event.")
    if len(run_state.resources_log) != run_state.event_index:
        return "Ghost: this run was saved before ghosts were kept, so it cannot be compared. The next run can."
    result = ghost_lib.compare(run_state.resources_log, trace)
    if result is not None and result["status"] in ("ahead", "behind"):   # resources are read in whole numbers, like everywhere else
        lead = int(round(result["lead"]))
        result = dict(result, status="level", lead=0) if lead == 0 else dict(result, lead=lead)
    who = f"your best run ({trace['label']})" if trace["label"] else "your best run"
    return ghost_lib.summary(result, label=who, unit=" resources").replace("ghost: ", "Ghost: ", 1) + "."


def render_ghost():
    note, wrap, toggle = _el("ghost-note"), _el("ghost-toggle-wrap"), _el("ghost-toggle")
    eligible = ghost_run_eligible(runstate.run)
    if wrap is not None:
        wrap.hidden = not eligible
    if toggle is not None:
        toggle.checked = ghost_enabled()
    if note is not None:
        text = ghost_note_text() if eligible and ghost_enabled() else ""
        note.innerText = text
        note.hidden = not text


# ---- E-4: shareable run codes (shared/run_code.py) and challenge runs -------------------------------
# A run code carries: a seed (5 characters), a mode word (a-z0-9, up to 8), a score and two numbers.
# Aftermath uses them like this:
#   mode   the scenario word ("classic", "coastal", ..., "heatsea"), plus a trailing "x" for an
#          Extended Run, or "custom" for a player-built schedule;
#   seed   the severity DRAW (a whole number written in the seed alphabet; the sender's run number,
#          because severity is a fixed pattern per run number), or, for "custom", the schedule itself
#          (up to 7 events, 3 bits each, with a leading 1 so the length is kept);
#   score  the sender's resources left; stats: their adjusted score (E-9) and the damage they took.
# A friend who pastes the code can PLAY the same schedule as a challenge run: the same events in the
# same order struck by the same draw pattern at the plain severity band, with their own skill tree,
# starting bonuses and society memory switched off, so both of you start from a fresh settlement.
# Challenge runs earn no knowledge and write nothing to the run history; they count toward a visible
# "challenge runs finished" tally and a best score per code.
RUN_CODE_GAME = "aftermath"
SCENARIO_CODE_WORD = {
    "classic": "classic", "coastal": "coastal", "inland": "inland", "urban": "urban",
    "san_francisco": "sanfran", "houston": "houston", "phoenix": "phoenix", "chicago": "chicago",
    "heat_season": "heatsea",
}
CODE_WORD_SCENARIO = {word: scenario for scenario, word in SCENARIO_CODE_WORD.items()}
CUSTOM_CODE_WORD = "custom"
# The position of an event type in a custom schedule's seed. Only ever APPEND here (and the digit
# base of 8 leaves room for exactly one more), because shared codes would otherwise change meaning.
EVENT_CODE_ORDER = (
    "flood", "heatwave", "storm", "supply_chain", "infrastructure_failure", "civil_unrest", "heat_mortality",
)


def run_code_mode_names():
    """Mode word -> display name, for the page's 'Their run: ...' line (read through pyodide)."""
    names = {}
    for word, scenario in CODE_WORD_SCENARIO.items():
        label = SCENARIOS[scenario]["label"]
        names[word] = label
        names[word + "x"] = f"{label}, extended"
    names[CUSTOM_CODE_WORD] = "Custom schedule"
    return names


def seed_text_for_int(number):
    """The 5-character seed for a whole number (base 31, the seed alphabet), as AFTERMATH-XXXXX."""
    base = len(shared_seed.ALPHABET)
    if not isinstance(number, int) or number < 0 or number >= base ** shared_seed.CODE_LEN:
        return None
    chars = []
    for _ in range(shared_seed.CODE_LEN):
        number, remainder = divmod(number, base)
        chars.append(shared_seed.ALPHABET[remainder])
    return f"{shared_seed.prefix_for(RUN_CODE_GAME)}-{''.join(reversed(chars))}"


def int_from_seed_text(text):
    code = str(text).split("-")[-1]
    number = 0
    for ch in code:
        number = number * len(shared_seed.ALPHABET) + shared_seed.ALPHABET.index(ch)
    return number


def custom_schedule_number(events):
    """A custom schedule as one whole number: a leading 1 then each event's position in base 8."""
    if not events or len(events) > CUSTOM_MAX_EVENTS or any(e not in EVENT_CODE_ORDER for e in events):
        return None
    number = 1
    for event_type in events:
        number = number * 8 + EVENT_CODE_ORDER.index(event_type)
    return number


def custom_schedule_from_number(number):
    """The inverse; None unless it is a well-formed schedule of CUSTOM_MIN_EVENTS..CUSTOM_MAX_EVENTS."""
    digits = []
    while number > 1:
        number, digit = divmod(number, 8)
        if digit >= len(EVENT_CODE_ORDER):
            return None
        digits.append(EVENT_CODE_ORDER[digit])
    if number != 1 or not CUSTOM_MIN_EVENTS <= len(digits) <= CUSTOM_MAX_EVENTS:
        return None
    return list(reversed(digits))


def run_code_mode(run_state):
    if run_state.custom_events:
        return CUSTOM_CODE_WORD
    return SCENARIO_CODE_WORD[run_state.scenario] + ("x" if run_state.extended else "")


def run_code_seed_number(run_state):
    if run_state.custom_events:
        return custom_schedule_number(run_state.custom_events)
    return run_state.draw if run_state.normalised else run_state.run_number


def run_code_fields(run_state=None):
    """The fields for shared/run-code.js's copy box (the page reads this through pyodide): a FINISHED
    run only, else None. The score is the resources left; the two stats are the adjusted score and
    the damage taken."""
    run_state = run_state or runstate.run
    if not run_state.is_complete():
        return None
    if run_state.aid_given:  # R-31: a run with neighbour aid is not on equal terms, so it has no code
        return None
    seed_text = seed_text_for_int(run_code_seed_number(run_state))
    if seed_text is None:
        return None
    return {
        "seed": seed_text,
        "mode": run_code_mode(run_state),
        "score": int(round(max(0.0, run_state.run_score()))),
        "stats": [
            int(round(adjusted_score(run_state.run_score(), run_state.event_log))),
            int(round(max(0.0, run_state.damage_taken))),
        ],
    }


def make_run_code(run_state=None):
    fields = run_code_fields(run_state)
    if fields is None:
        return None
    return shared_run_code.encode({"game": RUN_CODE_GAME, **fields})


def schedule_code(events):
    """A code for a schedule alone (no result), to hand a friend before anyone has played it."""
    number = custom_schedule_number(events)
    seed_text = seed_text_for_int(number) if number is not None else None
    if seed_text is None:
        return None
    return shared_run_code.encode({"game": RUN_CODE_GAME, "seed": seed_text, "mode": CUSTOM_CODE_WORD})


def challenge_spec(decoded):
    """(spec, error) from a decoded run code: what to play. spec has scenario, extended, draw and
    custom_events."""
    if not decoded.get("ok"):
        return None, decoded.get("message") or "That is not a run code."
    mode, seed_text = decoded.get("mode", ""), decoded.get("seed", "")
    if not seed_text:
        return None, "That code has no schedule to play. Ask for a code from a finished run or a saved schedule."
    number = int_from_seed_text(seed_text)
    if mode == CUSTOM_CODE_WORD:
        events = custom_schedule_from_number(number)
        if events is None:
            return None, "That custom schedule code is not valid."
        return {"scenario": DEFAULT_SCENARIO, "extended": False, "draw": 1, "custom_events": events}, ""
    extended = False
    word = mode
    if word not in CODE_WORD_SCENARIO and word.endswith("x") and word[:-1] in CODE_WORD_SCENARIO:
        word, extended = word[:-1], True
    if word not in CODE_WORD_SCENARIO:
        return None, "That code is for a mode this version of Aftermath does not know."
    return {"scenario": CODE_WORD_SCENARIO[word], "extended": extended, "draw": number, "custom_events": None}, ""


def _challenge_info(decoded):
    stats = decoded.get("stats") or []
    return {
        "code": decoded["code"],
        "their_score": decoded.get("score"),
        "their_adjusted": stats[0] if len(stats) > 0 else None,
        "their_damage": stats[1] if len(stats) > 1 else None,
    }


def _reset_run_ui_state():
    """What starting or swapping a run clears (shared by new runs, challenges and built schedules)."""
    runstate.callout_message = ""
    runstate.last_knowledge_preview = None
    document.getElementById("copy-run-summary-status").innerText = ""
    document.getElementById("copy-run-summary-area").hidden = True
    announce("")


DAILY_CODE_MODE = "classic"  # Z-5c: Today's run is the classic schedule for everyone, so the day is the same for all


def daily_run_code(seed_text):
    """Z-5c: the run code that Today's run plays: the classic schedule at the day's shared seed (the severity draw), the same
    route a friend's code takes. (code, error)."""
    result = shared_seed.validate(seed_text, RUN_CODE_GAME)
    if not result["ok"]:
        return None, result["message"]
    try:
        return shared_run_code.encode({"game": RUN_CODE_GAME, "seed": result["seed"], "mode": DAILY_CODE_MODE}), ""
    except Exception:  # noqa: BLE001 -- an unreadable seed is a message, never a crash
        return None, "That seed could not be turned into a run."


def daily_seed_of_code(code):
    """Z-5c: the seed of a Today's-run code (classic mode, no custom schedule), else ''."""
    decoded = shared_run_code.decode(code, RUN_CODE_GAME) if isinstance(code, str) else {}
    if not decoded.get("ok") or decoded.get("mode") != DAILY_CODE_MODE:
        return ""
    return decoded.get("seed", "")


def run_is_untouched(run_state=None):
    """Z-5c: a run that nothing has been done in: no event faced and no resources moved into resilience or growth."""
    run_state = run_state or runstate.run
    return run_state.event_index == 0 and run_state.resources == run_state.starting_resources and not run_state.allocation_history


def _record_shared_daily(run_state):
    """Z-5c: a finished Today's run whose seed is TODAY's shared seed counts once for the day in the record the hub's Today
    strip reads (`localStorage["noyvj-daily-v1"]`, written by `NoyvjSeed.daily.markCompleted`). The page decides what today
    is (`isDaily`), so a run begun on an older day's seed, a friend's challenge or an ordinary run records nothing. Fails
    soft: no shared script (pytest, an old page) or any error means nothing, and the run's own result is never affected."""
    seed_text = (run_state.challenge or {}).get("daily_seed")
    if not seed_text:
        return
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        daily = getattr(getattr(js.window, "NoyvjSeed", None), "daily", None)
        if daily is None or not daily.isDaily(RUN_CODE_GAME, seed_text):
            return
        info = js.Object.new()
        info.text = f"Ended with {int(round(max(0.0, run_state.run_score())))} resources"
        daily.markCompleted(RUN_CODE_GAME, info)
    except Exception:  # noqa: BLE001 -- a courtesy record must never break finishing a run
        pass


def _note_challenge_result(run_state):
    """A finished challenge counts toward the visible tally and keeps the best score per code."""
    runstate.meta["challenge_runs"] += 1
    info = run_state.challenge or {}
    code = info.get("code")
    if code:
        score = int(round(max(0.0, run_state.run_score())))
        best = runstate.meta["challenge_best"]
        best[code] = max(score, best.get(code, 0))
        while len(best) > CHALLENGE_BEST_MAX:
            best.pop(next(iter(best)))
    save_meta()


def challenge_result_text(run_state):
    info = run_state.challenge or {}
    mine = int(round(run_state.run_score()))
    if info.get("daily_seed"):  # Z-5c
        return (
            f"Today's run finished: you ended with {mine} resources ({adjusted_text(run_state.run_score(), run_state.event_log)}). "
            "Everyone who plays it faces the same events and the same severity pattern. "
            "It earns no knowledge and leaves your history alone."
        )
    text = (
        f"Challenge finished: you ended with {mine} resources ({adjusted_text(run_state.run_score(), run_state.event_log)}). "
    )
    theirs = info.get("their_score")
    if theirs is not None:
        extra = f", {info['their_adjusted']} adjusted" if info.get("their_adjusted") is not None else ""
        text += (
            f"Their run ended with {theirs}{extra}. They played with their own skill tree and you started fresh, "
            "so read it as a friendly note, not a ranking. "
        )
    return text + "Challenge runs earn no knowledge and leave your history alone."


def challenge_stats_text():
    played = runstate.meta["challenge_runs"]
    text = f"Challenge runs finished: {played}."
    if runstate.run.normalised and runstate.run.challenge:
        best = runstate.meta["challenge_best"].get(runstate.run.challenge.get("code"))
        if best is not None:
            text += f" Your best on this code: {best}."
    return text


def challenge_banner_text(run_state=None):
    run_state = run_state or runstate.run
    if not run_state.normalised:
        return ""
    info = run_state.challenge or {}
    if info.get("daily_seed"):  # Z-5c
        return (
            f"Today's run: the day's shared schedule, {len(run_state.schedule)} events, with your skill tree and "
            "memory switched off, so everyone faces the same draw. No knowledge is earned."
        )
    theirs = f" Their run ended with {info['their_score']}." if info.get("their_score") is not None else ""
    return (
        f"Challenge run: a friend's schedule, {len(run_state.schedule)} events, with your skill tree and "
        f"memory switched off. No knowledge is earned.{theirs}"
    )


def render_challenge():
    banner = _el("challenge-banner")
    if banner is not None:
        banner.innerText = challenge_banner_text()
        banner.hidden = not runstate.run.normalised
    leave = _el("challenge-leave-button")
    if leave is not None:
        leave.hidden = not (runstate.run.normalised and not runstate.run.is_complete())
    stats = _el("challenge-stats")
    if stats is not None:
        stats.innerText = challenge_stats_text()
    status = _el("challenge-status")
    if status is not None:
        status.innerText = runstate.challenge_status_text
    wrap = _el("run-end-code-wrap")
    if wrap is not None:
        wrap.hidden = not runstate.run.is_complete() or bool(runstate.run.aid_given)  # R-31: an aided run has no code to copy
    note = _el("run-end-code-note")
    if note is not None:
        note.innerText = (
            "This run had help from neighbouring towns, so it has no run code (codes compare runs on equal terms)."
            if runstate.run.is_complete() and runstate.run.aid_given
            else "" if runstate.run.is_complete() else "Finish a run to get its run code, then copy it for a friend."
        )
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    update = getattr(window, "aftermathRunCodeUpdate", None)
    if update is not None:
        try:
            update()
        except Exception:
            pass


# ---- E-13: schedule builder --------------------------------------------------------------------------
builder_draft = []


def builder_total_damage(events=None):
    return sum(EVENT_BASE_DAMAGE[e] for e in (builder_draft if events is None else events))


def builder_knowledge_share(events=None):
    events = builder_draft if events is None else events
    reference = sum(EVENT_BASE_DAMAGE[e] for e in EVENT_SCHEDULE)
    return min(1.0, builder_total_damage(events) / reference) if events else 0.0


def builder_summary_text():
    count = len(builder_draft)
    if not count:
        return f"Empty. Add {CUSTOM_MIN_EVENTS} to {CUSTOM_MAX_EVENTS} events from the library."
    return (
        f"{count} of {CUSTOM_MAX_EVENTS} events, {builder_total_damage():.0f} base damage "
        f"(Classic mix: {sum(EVENT_BASE_DAMAGE[e] for e in EVENT_SCHEDULE):.0f}). "
        f"A run on it earns {builder_knowledge_share() * 100:.0f}% of the usual knowledge."
    )


def builder_add(event_type):
    if event_type not in EVENT_LABEL or len(builder_draft) >= CUSTOM_MAX_EVENTS:
        return False
    builder_draft.append(event_type)
    return True


def builder_remove(index):
    if 0 <= index < len(builder_draft):
        builder_draft.pop(index)
        return True
    return False


def builder_move(index, delta):
    target = index + delta
    if 0 <= index < len(builder_draft) and 0 <= target < len(builder_draft):
        builder_draft[index], builder_draft[target] = builder_draft[target], builder_draft[index]
        return True
    return False


def _custom_named(name):
    key = _clean_name(name, CUSTOM_NAME_MAX).casefold()
    for entry in runstate.meta["custom_schedules"]:
        if entry["name"].casefold() == key:
            return entry
    return None


def save_custom_schedule(name, events=None):
    """Saves the draft (or `events`) under a name; the same name (any case) is replaced."""
    events = list(builder_draft if events is None else events)
    name = _clean_name(name, CUSTOM_NAME_MAX)
    if not name:
        return False, "Give the schedule a name."
    if not CUSTOM_MIN_EVENTS <= len(events) <= CUSTOM_MAX_EVENTS:
        return False, f"A schedule needs {CUSTOM_MIN_EVENTS} to {CUSTOM_MAX_EVENTS} events."
    existing = _custom_named(name)
    if existing is None and len(runstate.meta["custom_schedules"]) >= CUSTOM_SCHEDULES_MAX:
        return False, f"You can keep up to {CUSTOM_SCHEDULES_MAX} saved schedules. Delete one first."
    entry = {"name": name, "events": events}
    if existing is None:
        runstate.meta["custom_schedules"].append(entry)
    else:
        runstate.meta["custom_schedules"][runstate.meta["custom_schedules"].index(existing)] = entry
    save_meta()
    return True, f"{'Updated' if existing else 'Saved'} schedule {name} ({len(events)} events)."


def delete_custom_schedule(name):
    existing = _custom_named(name)
    if existing is None:
        return False
    runstate.meta["custom_schedules"].remove(existing)
    save_meta()
    return True


def _builder_message(message):
    runstate.builder_status_text = message
    render()
    announce(message)


def _make_library_handler(event_type):
    def handler(event=None):
        if builder_add(event_type):
            _builder_message(f"Added {EVENT_LABEL[event_type]}. {len(builder_draft)} of {CUSTOM_MAX_EVENTS} events.")
        else:
            _builder_message(f"The schedule is full: {CUSTOM_MAX_EVENTS} events at most.")
    return handler


def build_library_buttons():
    holder = _el("builder-library")
    if holder is None:
        return
    holder.innerHTML = ""
    for event_type in EVENT_CODE_ORDER:
        button = document.createElement("button")
        button.className = f"secondary builder-library-button event-category--{EVENT_CATEGORY[event_type]}"
        button.setAttribute("type", "button")
        button.setAttribute("data-event", event_type)
        button.innerText = f"+ {EVENT_ICON[event_type]} {EVENT_LABEL[event_type]}"
        button.addEventListener("click", create_proxy(_make_library_handler(event_type)))
        holder.appendChild(button)


def render_builder():
    holder = _el("builder-library")
    full = len(builder_draft) >= CUSTOM_MAX_EVENTS
    if holder is not None:
        for button in holder.children:
            button.disabled = full
    draft = _el("builder-draft")
    if draft is not None:
        draft.innerHTML = ""
        for index, event_type in enumerate(builder_draft):
            item = document.createElement("li")
            item.className = f"builder-item event-category--{EVENT_CATEGORY[event_type]}"
            label = document.createElement("span")
            label.className = "builder-item-label"
            label.innerText = f"{EVENT_ICON[event_type]} {EVENT_LABEL[event_type]} ({EVENT_BASE_DAMAGE[event_type]:.0f})"
            item.appendChild(label)
            for action, text, aria in (("up", "↑", "Move up"), ("down", "↓", "Move down"), ("remove", "✕", "Remove")):
                button = document.createElement("button")
                button.className = "secondary builder-item-button"
                button.setAttribute("type", "button")
                button.setAttribute("data-action", action)
                button.setAttribute("data-index", str(index))
                button.setAttribute("aria-label", f"{aria} event {index + 1}, {EVENT_LABEL[event_type]}")
                button.innerText = text
                button.disabled = (action == "up" and index == 0) or (action == "down" and index == len(builder_draft) - 1)
                item.appendChild(button)
            draft.appendChild(item)
    summary = _el("builder-summary")
    if summary is not None:
        summary.innerText = builder_summary_text()
    save = _el("builder-save-button")
    if save is not None:
        save.disabled = len(builder_draft) < CUSTOM_MIN_EVENTS
    clear = _el("builder-clear-button")
    if clear is not None:
        clear.disabled = not builder_draft
    saved = _el("builder-saved-list")
    if saved is not None:
        saved.innerHTML = ""
        if not runstate.meta["custom_schedules"]:
            empty = document.createElement("li")
            empty.innerText = "No saved schedules yet."
            saved.appendChild(empty)
        can_run = runstate.run.is_complete() or runstate.run.event_index == 0
        for entry in runstate.meta["custom_schedules"]:
            item = document.createElement("li")
            item.className = "builder-saved-item"
            label = document.createElement("span")
            label.className = "builder-item-label"
            label.innerText = f"{entry['name']}: " + " → ".join(EVENT_LABEL[e] for e in entry["events"])
            item.appendChild(label)
            for action, text in (("run", "Run it"), ("load", "Edit"), ("share", "Code"), ("delete", "Delete")):
                button = document.createElement("button")
                button.className = "secondary builder-item-button"
                button.setAttribute("type", "button")
                button.setAttribute("data-action", action)
                button.setAttribute("data-name", entry["name"])
                button.setAttribute("aria-label", f"{text}: {entry['name']}")
                button.innerText = text
                button.disabled = action == "run" and not can_run
                item.appendChild(button)
            saved.appendChild(item)
    status = _el("builder-status")
    if status is not None:
        status.innerText = runstate.builder_status_text
