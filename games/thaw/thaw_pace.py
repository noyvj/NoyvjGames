"""The pace line and ghost sentence (Z-3e3): best-run record, trace and text."""

import json
import re

import ghost as ghost_lib
from js import document

import thaw_runstate as runstate
from thaw_bridge import _num, _read_local_storage_item, _write_local_storage_item
from thaw_model import deg, region


# ===========================================================================
# G-21: a faint pace line from your best Region A run. The run with the most degrees saved on this
# device keeps its temperature path (up to PACE_MAX_ROUNDS rounds) in localStorage; the NEXT session
# draws it as a dashed line behind Region A's graph and says in words whether you are ahead of it. The
# line shown is the best run from before this session started, so it never chases your own current
# line. Per-browser (not in the save). The setting "Hide the best-run pace line" turns it off.
# ===========================================================================
PACE_KEY = "thaw_best_pace_v1"
PACE_MAX_ROUNDS = 120

# Z-3e3: the line now runs through the shared ghost (shared/ghost.py). Measure: Region A's temperature after every round
# (lower is ahead), one number per round, recorded by ghost.Recorder when a new best is stored. The stored record keeps its
# old shape ({saved, temps}, so every record already on a device loads unchanged); only a run longer than the shared cap of
# 120 numbers adds "rounds" (its true length), because its temps were then thinned evenly instead of cut off, and the
# trace reads a round by spreading it over the stored length. The shared sentence is drawn into the graph's accessible
# name and into #ghost-sentence (visually hidden, a polite status); "Hide the best-run pace line" switches line, label,
# both sentences and the pace words off together. Nothing new is saved and nothing enters the save.
GHOST_SENTENCE_LABEL = "your best run"


def _clean_pace(raw):
    """A stored best run ({saved, temps[, rounds]}) or None if it is missing or anything in it is unreadable."""
    if not isinstance(raw, dict):
        return None
    saved, temps = raw.get("saved"), raw.get("temps")
    if not _num(saved, 0, 1000000000) or not isinstance(temps, list):
        return None
    if not 2 <= len(temps) <= PACE_MAX_ROUNDS or not all(_num(t, -1000, 1000000) for t in temps):
        return None
    record = {"saved": float(saved), "temps": [float(t) for t in temps]}
    rounds = raw.get("rounds")
    if isinstance(rounds, int) and not isinstance(rounds, bool) and len(temps) < rounds <= ghost_lib.MAX_TURNS:
        record["rounds"] = rounds
    return record


def load_best_pace():
    raw = _read_local_storage_item(PACE_KEY)
    if not raw:
        return None
    try:
        return _clean_pace(json.loads(raw))
    except (ValueError, TypeError):
        return None


runstate.pace_best = load_best_pace()      # the stored record, raised during play
pace_baseline = runstate.pace_best         # what this session compares against (fixed at page load)

_pace_trace_cache = {"record": None, "trace": None}
_ghost_sentence_cache = {"key": None, "text": ""}


def pace_trace(record=None):
    """The shared ghost trace for a stored best run (the session's baseline by default), or None."""
    record = pace_baseline if record is None else record
    if not record:
        return None
    if _pace_trace_cache["record"] is record:
        return _pace_trace_cache["trace"]
    trace = ghost_lib.load({"v": ghost_lib.TRACE_VERSION, "turns": record.get("rounds", len(record["temps"])),
                            "values": record["temps"], "label": "best run"})
    _pace_trace_cache["record"], _pace_trace_cache["trace"] = record, trace
    return trace


def pace_values(rounds):
    """The ghost's temperature for rounds 1..rounds (as many as it has), for the graph's dashed line."""
    trace = pace_trace()
    if trace is None:
        return None
    return [ghost_lib.value_at(trace, i) for i in range(1, min(int(rounds), trace["turns"]) + 1)]


def _maybe_update_pace():
    """Called every render(): when Region A has saved more degrees than the stored best run, store this
    run's path as the new best (the baseline line on screen does not change until next time)."""
    saved = region.temperature_saved()
    history = region.temperature_history
    if saved <= 0 or len(history) < 2:
        return
    if runstate.pace_best is not None and saved <= runstate.pace_best["saved"]:
        return
    recorder = ghost_lib.Recorder(PACE_MAX_ROUNDS)   # one number per round; a longer run is thinned evenly
    for temperature in history:
        recorder.record(temperature)
    trace = recorder.trace("best run")
    if trace is None:
        return
    record = {"saved": float(saved), "temps": [float(t) for t in trace["values"]]}
    if trace["turns"] > len(trace["values"]):
        record["rounds"] = trace["turns"]
    runstate.pace_best = record
    _write_local_storage_item(PACE_KEY, json.dumps(runstate.pace_best))


def pace_text():
    """One sentence on where Region A stands against the best run from an earlier session ('' if none)."""
    trace = pace_trace()
    if trace is None:
        return ""
    history = region.temperature_history
    turns = trace["turns"]
    best = deg(pace_baseline["saved"])
    if not history:
        return f"Your best earlier run saved {best}; its path will show as a faint dashed line on the graph."
    index = len(history) - 1
    if index >= turns:
        return (
            f"You are past the {turns} rounds your best earlier run recorded (it saved {best} by then). "
            "Everything from here is new ground."
        )
    diff = history[index] - ghost_lib.value_at(trace, index + 1)
    if abs(diff) < 0.05:
        return f"Level with your best earlier run at this round (it saved {best} in all)."
    if diff < 0:
        return f"{deg(-diff)} cooler than your best earlier run was at this round: ahead of your best pace."
    return (
        f"{deg(diff)} warmer than your best earlier run was at this round; its path is the dashed line on the "
        "graph (it saved " + best + " in all)."
    )


def ghost_sentence():
    """The shared ghost's one-line sentence for Region A against the best earlier run ('Ghost: you are 0.4° ahead of your
    best run at round 7'; lower temperature is ahead), in the chosen temperature unit. '' with no ghost, no rounds yet or
    more rounds than the shared cap allows. Cached per round so render() stays cheap."""
    trace = pace_trace()
    history = region.temperature_history
    if trace is None or not history:
        return ""
    key = (tuple(trace["values"]), trace["turns"], len(history), history[-1], runstate.temp_unit)
    if _ghost_sentence_cache["key"] == key:
        return _ghost_sentence_cache["text"]
    result = ghost_lib.compare(history, trace, higher_is_better=False)
    text = ""
    if result is not None:
        scale = 1.8 if runstate.temp_unit == "f" else 1.0
        unit = {"f": "\u00b0F", "k": " K"}.get(runstate.temp_unit, "\u00b0")
        if result["status"] in ("ahead", "behind"):
            lead = round(result["lead"] * scale, 1)
            result = dict(result, status="level", lead=0) if lead == 0 else dict(result, lead=lead)
        text = ghost_lib.summary(result, label=GHOST_SENTENCE_LABEL, unit=unit)
        text = "Ghost: " + text[len("ghost: "):] + "."
        text = re.sub(r"\bturn (\d+)", r"round \1", text)
    _ghost_sentence_cache["key"], _ghost_sentence_cache["text"] = key, text
    return text


def render_pace():
    document.getElementById("pace-display").innerText = pace_text()
    document.getElementById("pace-display").hidden = pace_baseline is None
    note = document.getElementById("ghost-sentence")   # Z-3e3
    if note is not None:
        note.innerText = ghost_sentence()
        note.hidden = not note.innerText
