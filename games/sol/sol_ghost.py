"""The Ghost Run (personal-best and daily recordings, the pace sentence) and the splits panel."""

import json
import re

import challenges
import ghost as ghost_lib
from js import document

import sol_runstate as runstate
from sol_headless import parse_blueprint
from sol_rhythm import SPLIT_KEYS, pb_splits, run_splits
from sol_rules import (
    GHOST_DAILY_KEEP, GHOST_DAILY_KEY, GHOST_LIVE_KEY, GHOST_ON_KEY, GHOST_PB_KEY, GHOST_SAVE_EVERY,
    PLANETS, planet_state,
)
from sol_runmods import _run_ticks
from sol_scarcity import _scarcity_refs
from sol_scarcity_run import _scarcity_headless, scarcity_spec
from sol_util import (
    _make_button, _make_text, _read_json_item, _read_local_storage_item, _split_delta, _split_time,
    _today_utc, _write_local_storage_item, split_label,
)


def update_splits_display(force=False):
    """The panel is built once (and again when the Ghost Run switch or the best recording changes) and its rows are then
    updated in place, so the ghost button is never swallowed by a rebuild."""
    toggle = document.getElementById("splits-toggle-button")
    panel = document.getElementById("splits-panel")
    toggle.innerText = "Hide Splits" if runstate.splits_open else "⏱️ Splits"
    panel.hidden = not runstate.splits_open
    if not runstate.splits_open:
        runstate._splits_signature = None
        return
    signature = (ghost_enabled(), runstate._pb_ghost is not None, tuple(sorted(run_splits)), tuple(sorted(pb_splits)))
    if force or signature != runstate._splits_signature:
        _build_splits_panel()
        runstate._splits_signature = signature
    for key, row in _splits_refs.get("rows", {}).items():
        mine = run_splits.get(key)
        best = pb_splits.get(key)
        if mine is None:
            text = f"{split_label(key)}: not yet"
            if best is not None:
                text += f" (best {_split_time(best)})"
        elif best is None:
            text = f"{split_label(key)}: {_split_time(mine)} (no personal best yet)"
        else:
            text = f"{split_label(key)}: {_split_time(mine)} (best {_split_time(best)}, {_split_delta(mine, best)})"
        row.innerText = text


def _build_splits_panel():
    panel = document.getElementById("splits-panel")
    panel.innerHTML = ""
    _splits_refs.clear()
    heading = document.createElement("h2")
    heading.className = "stats-panel-heading"
    heading.innerText = "Speedrun splits"
    panel.appendChild(heading)
    intro = document.createElement("p")
    intro.className = "splits-intro"
    intro.innerText = (
        "Time into this run when each world was unlocked, in game time. Your personal best is the "
        "run with the fastest full playthrough; each row says how far ahead (-) or behind (+) it you are."
    )
    panel.appendChild(intro)
    rows = {}
    for key in SPLIT_KEYS:
        row = document.createElement("p")
        row.className = "splits-row"
        panel.appendChild(row)
        rows[key] = row
    _splits_refs["rows"] = rows
    panel.appendChild(_make_text("stats-panel-heading", "Ghost Run", tag="h2"))
    panel.appendChild(_make_text(
        "splits-intro",
        "Race a recording of your fastest full playthrough. It is made automatically while you play, kept in this browser only "
        "(never in your save code) and replaced only when you finish faster. Every 25 ticks the split track shows how many "
        "terraform points ahead (+) or behind (-) you are."))
    if runstate._pb_ghost is None:
        panel.appendChild(_make_text("splits-row", "No personal-best recording yet: finish a full playthrough to make one."))
    else:
        panel.appendChild(_make_text("splits-row", f"Your best recording: {_split_time(runstate._pb_ghost['ticks'])}."))
    panel.appendChild(_make_button(
        "Ghost run: On" if ghost_enabled() else "Ghost run: Off", {"data-action": "ghost-toggle"}, None,
        selected=ghost_enabled(), disabled=runstate._pb_ghost is None and not ghost_enabled()))
    track = document.createElement("div")
    track.className = "ghost-track"
    panel.appendChild(track)
    _splits_refs["track"] = track
    _render_ghost_track(track, runstate._live_ghost, runstate._pb_ghost if ghost_enabled() else None, "your best run")


# --- A-29: the Ghost Run ----------------------------------------------------------------------
ghost_open_track = None

_splits_refs = {}


def ghost_enabled():
    return _read_local_storage_item(GHOST_ON_KEY) == "on"


def _load_pb_ghost():
    runstate._pb_ghost = challenges.clean_recording(_read_json_item(GHOST_PB_KEY))


def _load_daily_ghosts():
    raw = _read_json_item(GHOST_DAILY_KEY)
    out = {}
    if isinstance(raw, dict):
        for date_text, rec in raw.items():
            clean = challenges.clean_recording(rec)
            if clean is not None and challenges.valid_date(date_text):
                out[date_text] = clean
    return out


def _keep_daily_ghost(date_text, ticks, samples):
    """Keeps this run's recording for the date only if it is faster than the one kept (or none is kept)."""
    recording = challenges.clean_recording({"ticks": ticks, "pct": list(samples) + ([1000] if samples and samples[-1] < 1000 else [])})
    if recording is None:
        return False
    kept = _load_daily_ghosts()
    old = kept.get(date_text)
    if old is not None and old["ticks"] <= ticks:
        return False
    kept[date_text] = recording
    for stale in sorted(kept)[:-GHOST_DAILY_KEEP]:
        del kept[stale]
    _write_local_storage_item(GHOST_DAILY_KEY, json.dumps(kept))
    return True


def _resolve_scarcity_ghost(spec):
    choice = runstate._scarcity_ghost_choice
    if choice == "best":
        rec = _load_daily_ghosts().get(spec["date"])
        return rec, "your best for this day"
    if choice == "par":
        return spec["par_recording"], "the Governor alone"
    if choice == "friend" and runstate._scarcity_friend is not None and runstate._scarcity_friend["date"] == spec["date"]:
        return runstate._scarcity_friend["rec"], runstate._scarcity_friend["label"]
    return None, ""


def make_friend_ghost(code, date_text):
    """A friend's blueprint played by the Governor on one day. Returns (ok, message). Needs no network."""
    ok, result = parse_blueprint(code)
    if not ok:
        return False, result
    if not (result["rules"] or result["mutators"]):
        return False, "That blueprint has no Doctrines or rule twists for a ghost to play; it only has build-plan steps."
    today = _today_utc()
    if today is None or not challenges.playable(date_text, today):
        return False, "That day is not open yet."
    spec = scarcity_spec(date_text)
    ticks, recording = _scarcity_headless(spec, rules=result["rules"], mutators=result["mutators"])
    label = ("a friend's blueprint, " + (f"done in {_split_time(ticks)}" if ticks is not None else "did not finish within the bound"))
    runstate._scarcity_friend = {"date": date_text, "rec": recording, "label": label}
    return True, f"Ghost ready: {label}. Choose it, then start the day."


def _campaign_mean_progress():
    return sum(planet_state[p]["terraform_progress"] for p in PLANETS) / len(PLANETS)


def _ghost_reload_live():
    """Picks the in-progress recording up again after a page load or a save load, if it belongs to this run."""
    raw = _read_json_item(GHOST_LIVE_KEY)
    run_ticks = _run_ticks()
    expected = run_ticks // challenges.GHOST_STEP + 1
    runstate._live_ghost_run = runstate.run_start_tick
    samples = []
    if isinstance(raw, dict) and raw.get("run") == runstate.run_start_tick and isinstance(raw.get("pct"), list):
        samples = [v for v in raw["pct"] if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 1000]
        if len(samples) != len(raw["pct"]):
            samples = []
    runstate._live_ghost = samples[:expected]
    if not runstate._live_ghost and run_ticks <= 1:
        runstate._live_ghost = [round(_campaign_mean_progress() * 10)]  # a run that has only just begun: sample 0 is "now"
    runstate._live_ghost_partial = len(runstate._live_ghost) < expected - 1 or (not runstate._live_ghost and run_ticks > 0)


def _ghost_save_live():
    _write_local_storage_item(GHOST_LIVE_KEY, json.dumps({"run": runstate._live_ghost_run, "pct": runstate._live_ghost}))


def _ghost_tick():
    """Campaign recording, once per GHOST_STEP ticks of the current run. Off inside a Scarcity Run."""
    if runstate._scarcity is not None or runstate.run_completed:
        return
    run_ticks = _run_ticks()
    if runstate._live_ghost_run != runstate.run_start_tick:  # a prestige began a new run
        runstate._live_ghost[:] = []
        runstate._live_ghost_run = runstate.run_start_tick
        runstate._live_ghost_partial = run_ticks > 1
        if not runstate._live_ghost_partial:
            runstate._live_ghost.append(round(_campaign_mean_progress() * 10))
    if run_ticks % challenges.GHOST_STEP:
        return
    index = run_ticks // challenges.GHOST_STEP
    value = round(_campaign_mean_progress() * 10)
    if len(runstate._live_ghost) > index:
        del runstate._live_ghost[index:]  # an earlier save was loaded: the future is rewritten
    while len(runstate._live_ghost) < index:
        runstate._live_ghost.append(runstate._live_ghost[-1] if runstate._live_ghost else 0)
        runstate._live_ghost_partial = True
    runstate._live_ghost.append(value)
    if len(runstate._live_ghost) > challenges.GHOST_MAX_SAMPLES:
        runstate._live_ghost_partial = True
        runstate._live_ghost.pop()
    if len(runstate._live_ghost) % GHOST_SAVE_EVERY == 0:
        _ghost_save_live()
    _refresh_ghost_strip()


def _ghost_run_finished(duration, is_best):
    """Called when the whole system is first terraformed in a run. Keeps the recording only for a new personal best."""
    if not is_best or runstate._live_ghost_partial or not runstate._live_ghost:
        return False
    recording = challenges.clean_recording({"ticks": max(1, duration), "pct": list(runstate._live_ghost) + [1000]})
    if recording is None:
        return False
    _write_local_storage_item(GHOST_PB_KEY, json.dumps(recording))
    runstate._pb_ghost = recording
    return True


def _ghost_lead_now():
    """(you, ghost, label) for the strip, or None when no ghost is being raced."""
    if runstate._scarcity is not None:
        run = runstate._scarcity
        if run["ghost"] is None or not run["samples"]:
            return None
        index = len(run["samples"]) - 1
        mine = run["samples"][-1] / 10.0
        return mine, challenges.ghost_value(run["ghost"], index), run["ghost_label"]
    if not ghost_enabled() or runstate._pb_ghost is None or runstate.run_completed or not runstate._live_ghost:
        return None
    return runstate._live_ghost[-1] / 10.0, challenges.ghost_value(runstate._pb_ghost, len(runstate._live_ghost) - 1), "your best run"


# Z-3d3: the same race, told through the shared ghost (shared/ghost.py). A recording's checkpoints (average terraform
# percent every GHOST_STEP ticks, one number per checkpoint, so a "turn" here is a 25-tick checkpoint) are run through
# ghost.Recorder into a shared trace; ghost.compare/summary then give the one-line sentence for screen readers
# (#ghost-sentence, a polite status). The recording above stays the stored form (full resolution for the split track,
# nothing new is saved), so every older recording gives a shared trace with no migration.
GHOST_SENTENCE_EVERY = 8  # checkpoints (200 ticks) between two refreshes of the sentence, so a screen reader is not chatty
_trace_cache = {"recording": None, "trace": None}
_ghost_sentence_state = {"n": -1, "text": ""}


def ghost_trace(recording, label="best run"):
    """The shared ghost trace for a stored recording (percent, one number per checkpoint), or None."""
    if recording is None:
        return None
    if _trace_cache["recording"] is recording:
        return _trace_cache["trace"]
    recorder = ghost_lib.Recorder()
    for tenths in recording["pct"]:
        recorder.record(tenths / 10.0)
    trace = recorder.trace(label)
    _trace_cache["recording"], _trace_cache["trace"] = recording, trace
    return trace


def ghost_sentence(samples, recording, label):
    """ghost.summary for the live samples (tenths of a percent) against a recording: 'ghost: you are 2.5 points ahead of
    your best run at checkpoint 12'. '' when there is nothing to compare or the run is longer than the shared cap."""
    trace = ghost_trace(recording)
    if trace is None or not samples or len(samples) > ghost_lib.HARD_INPUT_LIMIT:
        return ""
    result = ghost_lib.compare([tenths / 10.0 for tenths in samples], trace)
    if result is None:
        return ""
    text = ghost_lib.summary(result, label=label, unit=" points")
    return re.sub(r"\bturn (\d+)", r"checkpoint \1", text)


def _ghost_racing():
    """(samples, recording, label) of the ghost being raced right now, or None."""
    if runstate._scarcity is not None:
        run = runstate._scarcity
        if run["ghost"] is None or not run["samples"]:
            return None
        return run["samples"], run["ghost"], run["ghost_label"]
    if not ghost_enabled() or runstate._pb_ghost is None or runstate.run_completed or not runstate._live_ghost:
        return None
    return runstate._live_ghost, runstate._pb_ghost, "your best run"


def _refresh_ghost_sentence():
    racing = _ghost_racing()
    box = document.getElementById("ghost-sentence")
    if racing is None:
        _ghost_sentence_state.update(n=-1, text="")
    else:
        samples = racing[0]
        stale = _ghost_sentence_state["n"] < 0 or len(samples) < _ghost_sentence_state["n"] \
            or len(samples) - _ghost_sentence_state["n"] >= GHOST_SENTENCE_EVERY
        if stale:
            _ghost_sentence_state.update(n=len(samples), text=ghost_sentence(*racing))
    if box is not None:
        box.innerText = _ghost_sentence_state["text"]
        box.hidden = not _ghost_sentence_state["text"]


def _refresh_ghost_strip():
    strip = document.getElementById("ghost-strip")
    lead = _ghost_lead_now()
    strip.hidden = lead is None
    if lead is None:
        strip.innerText = ""
    else:
        mine, ghost, label = lead
        strip.innerText = f"Ghost ({label}): you {mine:.1f}%, ghost {ghost:.1f}%, {challenges.lead_text(mine, ghost)}."
    _refresh_ghost_sentence()
    track = _scarcity_refs.get("track") if runstate._scarcity is not None else _splits_refs.get("track")
    if track is not None:
        if runstate._scarcity is not None:
            _render_ghost_track(track, runstate._scarcity["samples"], runstate._scarcity["ghost"], runstate._scarcity["ghost_label"])
        else:
            _render_ghost_track(track, runstate._live_ghost, runstate._pb_ghost if ghost_enabled() else None, "your best run")


def _render_ghost_track(container, samples, recording, label):
    """The split track: the latest checkpoints, each with both percents and a signed difference in text."""
    container.innerHTML = ""
    if recording is None or not samples:
        container.appendChild(_make_text("splits-row", "No ghost is racing right now."))
        return
    ahead, behind, level = challenges.ghost_summary(samples, recording)
    container.appendChild(_make_text(
        "splits-row", f"Split track vs {label}: ahead at {ahead} checkpoints, behind at {behind}, level at {level}."))
    for row in challenges.split_rows(samples, recording):
        words = "ahead" if row["diff"] > 0 else ("behind" if row["diff"] < 0 else "level")
        container.appendChild(_make_text(
            "splits-row ghost-row",
            f"{_split_time(row['tick'])}: you {row['mine']:.1f}%, ghost {row['ghost']:.1f}%, {row['text']} ({words})"))
