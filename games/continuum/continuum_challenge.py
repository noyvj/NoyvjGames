"""Daily challenge and scenario editor with share codes (K-10/K-11): ledger, controls, runs and the panel."""

import json
import time

from js import document

import challengerun
import sim

import continuum_runstate as runstate
from continuum_achievements import _display_toast, _seed_achievement_toast_baseline
from continuum_base import _js_window
from continuum_founders import sync_name_input

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# K-10 daily challenge and K-11 scenario editor with share codes. The rules, the
# par autopilot, the mod-code format and the ledger live in challengerun.py; this
# is the DOM half. A "challenge run" is a fixed start, an optional modifier, Hard
# Mode on or off and a length in seasons; it needs a fresh settlement.
# ===========================================================================
_challenge_utc_today_override = None                # tests set a date here


def _utc_today():
    """Today's date in UTC as YYYY-MM-DD (the daily changes at 00:00 UTC for everybody)."""
    if _challenge_utc_today_override:
        return _challenge_utc_today_override
    window = _js_window()
    try:
        seed_js = getattr(window, "NoyvjSeed", None) if window is not None else None
        text = str(seed_js.daily.today()) if seed_js is not None else ""
        if len(text) == 10:
            return text
    except Exception:  # noqa: BLE001 -- the page helper is optional
        pass
    return time.strftime("%Y-%m-%d", time.gmtime())


def challenge_ledger_load():
    window = _js_window()
    if window is None:
        return []
    try:
        raw = window.localStorage.getItem(challengerun.LEDGER_KEY)
    except Exception:  # noqa: BLE001
        return []
    return challengerun.clean_ledger(raw) if isinstance(raw, str) else []


def challenge_ledger_store(entries):
    window = _js_window()
    if window is None or runstate.sandbox_active:  # Z-18: the sandbox writes no browser storage
        return False
    try:
        window.localStorage.setItem(challengerun.LEDGER_KEY, challengerun.serialize_ledger(entries))
        return True
    except Exception:  # noqa: BLE001
        return False


def _challenge_read_inputs():
    """Reads the editor's controls into `_challenge_editor` (always a valid config)."""
    raw = {}
    for name in challengerun.RANGES:
        raw[name] = document.getElementById(f"challenge-dial-{name}").value
    raw["modifier"] = document.getElementById("challenge-modifier-select").value
    raw["hard"] = bool(getattr(document.getElementById("challenge-hard-checkbox"), "checked", False))
    runstate._challenge_editor = challengerun.clean_config(raw)
    return runstate._challenge_editor


def _challenge_write_inputs(cfg):
    for name in challengerun.RANGES:
        document.getElementById(f"challenge-dial-{name}").value = str(cfg[name])
    document.getElementById("challenge-modifier-select").value = cfg["modifier"]
    document.getElementById("challenge-hard-checkbox").checked = cfg["hard"]


def _build_challenge_controls():
    select = document.getElementById("challenge-modifier-select")
    select.innerHTML = ""
    for modifier_id in challengerun.MODIFIER_IDS:
        option = document.createElement("option")
        option.value = modifier_id
        option.innerText = challengerun.modifier_label(modifier_id)
        select.appendChild(option)
    _challenge_write_inputs(runstate._challenge_editor)


def on_toggle_challenge(event=None):
    runstate.challenge_panel_open = not runstate.challenge_panel_open
    update_challenge_panel()


def on_challenge_input(event=None):
    runstate._challenge_code_message = ""
    _challenge_read_inputs()
    update_challenge_panel()


def _begin_challenge(kind, config, seed_text="", date_text=""):
    """Starts a run on the fresh settlement. Returns True when it began."""
    if not challengerun.can_start(runstate.campaign):
        runstate._challenge_start_message = (
            "A challenge run needs a fresh settlement: before the first season, not a consulting case."
        )
        update_challenge_panel()
        return False
    if not challengerun.start(runstate.campaign, runstate.chronicle, kind, config, seed_text, date_text):
        runstate._challenge_start_message = "That run could not be started."
        update_challenge_panel()
        return False
    runstate._challenge_start_message = ""
    cfg = challengerun.clean_config(config)
    label = f"the daily challenge for {date_text}" if kind == "daily" else f"mod code {challengerun.encode(cfg)}"
    runstate.chronicle.log_challenge(
        runstate.state.season, runstate.state.era, f"Challenge run begins: {label}, {cfg['goal']} seasons."
    )
    sync_name_input()
    render()
    _seed_achievement_toast_baseline()
    return True


def on_challenge_daily_start(event=None):
    today = _utc_today()
    day = challengerun.daily(today)
    if day is None:
        return
    if _begin_challenge("daily", day["config"], day["seed"], day["date"]):
        window = _js_window()
        try:
            if window is not None and getattr(window, "NoyvjSeed", None) is not None:
                window.NoyvjSeed.set(day["seed"])
        except Exception:  # noqa: BLE001 -- the footer seed is a nicety
            pass


def on_challenge_custom_start(event=None):
    _begin_challenge("custom", _challenge_read_inputs())


def on_challenge_abandon(event=None):
    if challengerun.abandon(runstate.campaign):
        render()


def on_challenge_copy_code(event=None):
    window = _js_window()
    code = challengerun.encode(runstate._challenge_editor)
    copied = False
    try:
        if window is not None and getattr(window, "navigator", None) is not None:
            window.navigator.clipboard.writeText(code)
            copied = True
    except Exception:  # noqa: BLE001
        copied = False
    runstate._challenge_code_message = (
        f"Copied {code}." if copied else f"Select the code above and press Ctrl+C: {code}"
    )
    update_challenge_panel()


def on_challenge_load_code(event=None):
    cfg, error = challengerun.decode(document.getElementById("challenge-code-input").value)
    if cfg is None:
        runstate._challenge_code_message = error
    else:
        _challenge_write_inputs(cfg)
        _challenge_read_inputs()
        runstate._challenge_code_message = "Code loaded into the editor. Press Play this setup to try it."
    update_challenge_panel()


def _finish_challenge_run(result):
    """Called on the season the run ends: books the par, the ledger, the daily mark and a log line."""
    run = challengerun.get(runstate.campaign.ui)
    if run is None:
        return
    par_points = challengerun.par_for(run["config"])
    run["par"] = par_points
    runstate.campaign.ui[challengerun.KEY] = run
    challenge_ledger_store(challengerun.ledger_add(challenge_ledger_load(), run))
    runstate.chronicle.log_challenge(
        runstate.state.season,
        runstate.state.era,
        f"Challenge run complete: {result['points']} points over {result['seasons']} seasons. "
        + challengerun.verdict(result["points"], par_points),
    )
    if run["kind"] == "daily" and run["date"] == _utc_today() and not runstate.sandbox_active:  # Z-18: never posted from the sandbox
        window = _js_window()
        try:
            if window is not None and getattr(window, "NoyvjSeed", None) is not None:
                info = window.JSON.parse(
                    json.dumps({"score": result["points"], "text": f"{result['points']} points"})
                )
                window.NoyvjSeed.daily.markCompleted("continuum", info)
        except Exception:  # noqa: BLE001 -- the hub's Today strip is a nicety
            pass
        try:  # K-10: offered to the opt-in daily board (the widget only posts for a signed-in, opted-in player)
            board = getattr(window, "NoyvjLeaderboard", None) if window is not None else None
            if board is not None:
                board.report("continuum", "daily_challenge", int(result["points"]), "")
        except Exception:  # noqa: BLE001 -- a board is a nicety
            pass
    _display_toast(f"🎯 Challenge run complete: {result['points']} points")


def challenge_share_result():
    """The finished run as JSON for the shared Copy result button ({} when none is finished)."""
    fields = challengerun.share_fields(challengerun.get(runstate.campaign.ui))
    return json.dumps(fields or {})


def _daily_done_today():
    window = _js_window()
    try:
        seed_js = getattr(window, "NoyvjSeed", None) if window is not None else None
        if seed_js is None:
            return None
        data = seed_js.daily.read()
        runs = getattr(data, "runs", None)
        entry = getattr(runs, "continuum", None) if runs is not None else None
        if entry is None:
            return None
        score = getattr(entry, "score", None)
        return int(score) if score is not None else 0
    except Exception:  # noqa: BLE001
        return None


def update_challenge_panel():
    toggle = document.getElementById("challenge-toggle-button")
    panel = document.getElementById("challenge-panel")
    toggle.innerText = "Hide Challenge Runs" if runstate.challenge_panel_open else "🎯 Challenge Runs"
    panel.hidden = not runstate.challenge_panel_open
    if not runstate.challenge_panel_open:
        return
    run = challengerun.get(runstate.campaign.ui)
    can_start = challengerun.can_start(runstate.campaign)
    status = document.getElementById("challenge-run-status-display")
    result_box = document.getElementById("challenge-result-display")
    abandon = document.getElementById("challenge-abandon-button")
    document.getElementById("challenge-copy-result").hidden = run is None or run["result"] is None
    if run is None:
        status.innerText = runstate._challenge_start_message or (
            "No challenge run in progress."
            if can_start
            else "Start a challenge run from a fresh settlement (before the first season)."
        )
        result_box.hidden = True
        abandon.hidden = True
    else:
        kind = "Daily challenge" if run["kind"] == "daily" else "Custom run"
        when = f" {run['date']}" if run["date"] else ""
        mod = challengerun.modifier_label(run["config"]["modifier"])
        status.innerText = (
            f"{kind}{when} (code {run['code']}). {challengerun.progress_text(run)} "
            f"Modifier: {mod}. Hard Mode: {'on' if run['config']['hard'] else 'off'}."
        )
        abandon.hidden = False
        if run["result"] is None:
            result_box.hidden = True
        else:
            result_box.hidden = False
            par_points = run["par"] if run["par"] is not None else challengerun.par_for(run["config"])
            res = run["result"]
            result_box.innerHTML = ""
            for line in (
                f"Result: {res['points']} points. {challengerun.verdict(res['points'], par_points)}",
                f"Average sustainability {res['avg_score']:.0f}, {res['population']} people, "
                f"{res['discoveries']} discoveries, {res['eras']} eras entered.",
            ):
                row = document.createElement("p")
                row.className = "status-line"
                row.innerText = line
                result_box.appendChild(row)

    # today's challenge
    today = _utc_today()
    day = challengerun.daily(today)
    info = document.getElementById("challenge-daily-info")
    daily_button = document.getElementById("challenge-daily-start-button")
    if day is None:
        info.innerText = "Today's challenge is not available."
        daily_button.disabled = True
    else:
        cfg = day["config"]
        par_points = challengerun.par_for(cfg)
        scenario = sim.SCENARIOS[day["scenario"]]["label"]
        mod = challengerun.MODIFIERS[cfg["modifier"]]
        done = _daily_done_today()
        text = (
            f"{today} (UTC), seed {day['seed']}: {scenario}, modifier {mod['label']} ({mod['blurb']}) "
            f"Hard Mode {'on' if cfg['hard'] else 'off'}, {cfg['goal']} seasons. Par {par_points} points. "
            "The same for everyone, changing at 00:00 UTC."
        )
        if done is not None:
            text += f" Done today: {done} points."
        info.innerText = text
        daily_button.disabled = not can_start
        daily_button.innerText = "Play today's challenge" if done is None else "Play today's challenge again"

    # the editor
    cfg = runstate._challenge_editor
    for name in challengerun.RANGES:
        document.getElementById(f"challenge-dial-{name}-value").innerText = str(cfg[name])
    par_points = challengerun.par_for(cfg)
    preview = " ".join(challengerun.summary_lines(cfg)) + f" Par: {par_points} points."
    document.getElementById("challenge-preview-display").innerText = preview
    document.getElementById("challenge-code-display").value = challengerun.encode(cfg)
    document.getElementById("challenge-custom-start-button").disabled = not can_start
    document.getElementById("challenge-code-message").innerText = runstate._challenge_code_message

    # finished runs
    holder = document.getElementById("challenge-ledger-list")
    holder.innerHTML = ""
    entries = challenge_ledger_load()
    if not entries:
        row = document.createElement("p")
        row.className = "row-blurb"
        row.innerText = "No finished runs yet. Each one you finish is listed here with its points and its par."
        holder.appendChild(row)
    for entry in reversed(entries):
        row = document.createElement("p")
        row.className = "status-line challenge-ledger-row"
        row.innerText = challengerun.ledger_line(entry)
        holder.appendChild(row)
