"""Shareable run codes (shared/run_code.py): packing, decoding, replay and the friend-run ghosts."""

import re

import run_code as shared_run_code
from js import document

import tide_runstate as runstate
from tide_library import _ghosts
from tide_model_season import SettlementState
from tide_rules import (
    ADAPTATION_TIERS, CATEGORIES, COASTLINES, COASTLINE_IDS, COASTLINE_ROWS, FISH_DAMAGE_SCALE,
    LIBRARY_CURRENT, OUTPUT_MIX, SEA_SCENARIOS,
)


# ---- D-3 shareable run codes (shared/run_code.py) --------------------------------------------------------------
# A finished run becomes a short text a friend pastes in the Session Library to view it as a "ghost": a read-only
# overlay (and a per-season crosshair read-out) against their own run. A ghost is replayed from the choices into the
# same record shape the library uses; it is never a playable state and never touches the viewer's run or save.
#
# The shared format carries a mode word (8 symbols), a score and two numbers. Tide packs a bit stream into them:
#   header (39 bits): coastline 3, sea scenario 2, harder lag 1, storm seasons 1, output mix 2, seasons played 6,
#                     seasons in the code 6, damage avoided 12, rows dry 3, tier 3
#   then per season, three Elias-gamma numbers: Output, Reduction and Adaptation purchases that season.
# Mode word = the first 40 bits (8 symbols of 5 bits), then score, stat 1 and stat 2 = 48 bits each: 184 bits in all.
# When a long run does not fit, the code holds its first seasons (the header says how many of how many).
RUN_CODE_GAME = "tide"
RUN_CODE_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"  # 32 symbols, 5 bits each (lower-case a-z0-9 as the mode word allows)
RUN_CODE_BITS = 40 + 48 * 3
RUN_CODE_HEADER_BITS = 39
RUN_CODE_MIN_SEASONS = 3
RUN_CODE_MAX_INPUT = 400
RUN_CODE_BUY_CAP = 63  # purchases per category per season held in a code
RUN_CODE_NOTE = ("Run codes are not checked against a server: anyone can write one with any result, so treat it as a "
                 "friendly look at their run, not proof.")
GHOST_LIMIT = 6
_ghost_seq = [0]
_run_code_message = ["", False]  # text, is-a-problem


def _bits_of(value, width):
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def _gamma_bits(value):
    n = value + 1
    return [0] * (n.bit_length() - 1) + _bits_of(n, n.bit_length())


def _take(bits, pos, width):
    if pos + width > len(bits):
        return None, pos
    value = 0
    for b in bits[pos:pos + width]:
        value = (value << 1) | b
    return value, pos + width


def _take_gamma(bits, pos):
    zeros = 0
    while True:
        if pos >= len(bits) or zeros > 7:
            return None, pos
        if bits[pos]:
            break
        zeros += 1
        pos += 1
    value, pos = _take(bits, pos, zeros + 1)
    if value is None:
        return None, pos
    return value - 1, pos


def run_code_blocker():
    """"" when this run can be shared, else the plain reason it cannot."""
    if runstate.state.workshop_active() or runstate.state.acid_boss_mode:
        return "Runs with custom Workshop rules, Tidal Chess or the Acid Tide boss are not shared as codes."
    if runstate.state.daily:
        return "Daily Tide results are shared with the Copy result button instead."
    seasons = runstate.state.season - 1
    if seasons < RUN_CODE_MIN_SEASONS:
        return f"Play at least {RUN_CODE_MIN_SEASONS} seasons to make a run code."
    if len(runstate.state.season_buys) < seasons or seasons > 63:
        return ("This run began before purchases were logged (or is longer than 63 seasons), so it cannot be shared. "
                "A new run can.")
    return ""


def _pack_run(params):
    """params -> the 184-bit list, or None. `buys` is a list of [output, reduction, adaptation] counts."""
    buys = params["buys"]
    shown = len(buys)
    while True:
        bits = []
        for value, width in (
            (COASTLINE_IDS.index(params["coast"]), 3), (list(SEA_SCENARIOS).index(params["scenario"]), 2),
            (1 if params["lag"] == "hard" else 0, 1), (1 if params["storms"] else 0, 1),
            (list(OUTPUT_MIX).index(params["mix"]), 2), (params["played"], 6), (shown, 6),
            (min(4095, max(0, int(round(params["score"])))), 12), (params["rows_dry"], 3), (params["tier"], 3),
        ):
            bits += _bits_of(value, width)
        for row in buys[:shown]:
            for count in row:
                bits += _gamma_bits(min(RUN_CODE_BUY_CAP, count))
        if len(bits) <= RUN_CODE_BITS:
            return bits + [0] * (RUN_CODE_BITS - len(bits)), shown
        shown -= 1
        if shown < 1:
            return None, 0


def _bits_to_fields(bits):
    mode = "".join(RUN_CODE_ALPHABET[int("".join(map(str, bits[i:i + 5])), 2)] for i in range(0, 40, 5))
    parts = [int("".join(map(str, bits[40 + 48 * i:88 + 48 * i])), 2) for i in range(3)]
    return mode, parts


def _fields_to_bits(mode, parts):
    bits = []
    for ch in mode:
        bits += _bits_of(RUN_CODE_ALPHABET.index(ch), 5)
    for value in parts:
        bits += _bits_of(value, 48)
    return bits


def _current_run_params():
    return {
        "coast": runstate.state.coastline, "scenario": runstate.state.sea_scenario, "lag": "hard" if runstate.state.hard_lag_mode else "standard",
        "storms": bool(runstate.state.storm_mode), "mix": runstate.state.output_mix, "played": runstate.state.season - 1,
        "score": runstate.state.damage_saved(), "rows_dry": runstate.state.rows_dry_count(), "tier": runstate.state.current_tier_index(),
        "buys": [list(row) for row in runstate.state.season_buys[:runstate.state.season - 1]],
    }


def build_run_code():
    """(code, "") for the running session, or ("", why not)."""
    why = run_code_blocker()
    if why:
        return "", why
    bits, shown = _pack_run(_current_run_params())
    if bits is None:
        return "", "This run is too large to fit in a code."
    mode, parts = _bits_to_fields(bits)
    try:
        return shared_run_code.encode({"game": RUN_CODE_GAME, "mode": mode, "score": parts[0], "stats": parts[1:]}), ""
    except ValueError as error:  # RunCodeError is a ValueError
        return "", f"This run could not be turned into a code ({error})."


def run_code_preview(params, shown=None):
    seasons = params["played"]
    coast = COASTLINES[params["coast"]]["label"]
    lag = "harder lag" if params["lag"] == "hard" else "standard lag"
    tier = ADAPTATION_TIERS[params["tier"]]["name"]
    text = (f"{coast}, {params['scenario']} sea, {lag}{', storm seasons on' if params['storms'] else ''}: {seasons} seasons, "
            f"{params['score']:.0f} damage avoided, {params['rows_dry']} of {COASTLINE_ROWS} rows dry, {tier}.")
    if shown is not None and shown < seasons:
        text += f" The code holds the first {shown} seasons of choices."
    return text


def decode_run_code(text):
    """Reads a pasted code. Returns {"ok", "message", "params"}; never raises, never changes any game state."""
    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "message": "Paste a run code first.", "params": None}
    if len(text) > RUN_CODE_MAX_INPUT:
        return {"ok": False, "message": f"That is too long to be a run code (over {RUN_CODE_MAX_INPUT} characters). Nothing was read.", "params": None}
    decoded = shared_run_code.decode(text, RUN_CODE_GAME)
    if not decoded.get("ok") and decoded.get("error") == "format":
        match = re.search(r"RUN-TIDE(?:-[A-Z0-9]+)+", text.upper())  # "Tide run code, RUN-TIDE-..." as copied
        if match:
            decoded = shared_run_code.decode(match.group(0), RUN_CODE_GAME)
    if not decoded.get("ok"):
        message = decoded.get("message") or "That does not look like a Tide run code."
        if decoded.get("error") == "checksum":
            message = "That code has a typing mistake or was cut off or changed, so it was not loaded. Check it against the original."
        return {"ok": False, "message": message, "params": None}
    stats = decoded.get("stats") or []
    mode = decoded.get("mode") or ""
    if len(stats) != 2 or len(mode) != 8 or any(ch not in RUN_CODE_ALPHABET for ch in mode) or decoded.get("seed"):
        return {"ok": False, "message": "That is a run code, but not from this version of Tide's run codes, so it was not loaded.", "params": None}
    bits = _fields_to_bits(mode, [decoded["score"], stats[0], stats[1]])
    problem = "The contents of that code do not look like a real Tide run, so it was not loaded."
    pos = 0
    values = []
    for width in (3, 2, 1, 1, 2, 6, 6, 12, 3, 3):
        value, pos = _take(bits, pos, width)
        values.append(value)
    coast_i, scen_i, lag, storms, mix_i, played, shown, score, rows_dry, tier = values
    if (coast_i >= len(COASTLINE_IDS) or scen_i >= len(SEA_SCENARIOS) or mix_i >= len(OUTPUT_MIX) or not 1 <= shown <= played <= 63
            or shown > played or rows_dry > COASTLINE_ROWS or tier >= len(ADAPTATION_TIERS) or played < RUN_CODE_MIN_SEASONS):
        return {"ok": False, "message": problem, "params": None}
    buys = []
    for _season in range(shown):
        row = []
        for _cat in range(3):
            count, pos = _take_gamma(bits, pos)
            if count is None or count > RUN_CODE_BUY_CAP:
                return {"ok": False, "message": problem, "params": None}
            row.append(count)
        buys.append(row)
    if any(bits[pos:]) or sum(sum(r) for r in buys) > 600:
        return {"ok": False, "message": problem, "params": None}
    params = {
        "coast": COASTLINE_IDS[coast_i], "scenario": list(SEA_SCENARIOS)[scen_i], "lag": "hard" if lag else "standard",
        "storms": bool(storms), "mix": list(OUTPUT_MIX)[mix_i], "played": played, "shown": shown, "score": float(score),
        "rows_dry": rows_dry, "tier": tier, "buys": buys,
    }
    return {"ok": True, "message": "", "params": params}


def replay_run(params):
    """The curves of a decoded run, replayed through the game's own season rules on a scratch settlement (the
    running state is swapped out only for the length of the call). Returns the library-shaped acidity and fish series."""
    real = runstate.state
    scratch = SettlementState()
    scratch.sea_scenario = params["scenario"]
    scratch.set_coastline(params["coast"])
    scratch.hard_lag_mode = params["lag"] == "hard"
    scratch.output_mix = params["mix"]
    runstate.state = scratch
    try:
        for row in params["buys"]:
            for index, count in enumerate(row):
                scratch.capacity[CATEGORIES[index]] += count
            scratch.advance_season()
    finally:
        runstate.state = real
    return (
        [round(min(1.0, a / FISH_DAMAGE_SCALE), 3) for a in scratch.acidity_history],
        [round(v, 3) for v in scratch.fish_yield_history],
    )


def load_ghost(text):
    """Pastes a code: on success adds a ghost, shows it as the dashed overlay and in the comparison; on any problem
    says so in plain words and changes nothing."""
    result = decode_run_code(text)
    if not result["ok"]:
        _run_code_message[:] = [result["message"], True]
        return False
    params = result["params"]
    try:
        acidity, fish = replay_run(params)
    except Exception:  # noqa: BLE001 -- a code that cannot be replayed is refused, not half-loaded
        _run_code_message[:] = ["That code could not be replayed, so it was not loaded.", True]
        return False
    _ghost_seq[0] += 1
    ghost_id = f"g{_ghost_seq[0]}"
    _ghosts[ghost_id] = {
        "id": ghost_id, "name": f"Friend's run {_ghost_seq[0]}", "seasons": params["shown"], "scenario": params["scenario"],
        "lag": params["lag"], "coast": params["coast"], "storms": params["storms"], "score": round(params["score"], 1),
        "rows_dry": params["rows_dry"], "tier": params["tier"], "acidity": acidity, "fish": fish, "ghost": True,
        "played": params["played"],
    }
    while len(_ghosts) > GHOST_LIMIT:
        del _ghosts[next(iter(_ghosts))]
    runstate.library_b = ghost_id
    runstate.library_overlay_id = ghost_id
    _run_code_message[:] = [
        f"Loaded {_ghosts[ghost_id]['name']}: {run_code_preview(params, params['shown'])} It is shown as dashed lines on the "
        "graphs and as session B; your own run is untouched.", False,
    ]
    return True


def clear_ghosts():
    _ghosts.clear()
    for name in ("library_a", "library_b", "library_overlay_id"):
        if vars(runstate)[name].startswith("g"):
            vars(runstate)[name] = LIBRARY_CURRENT if name == "library_a" else ""
    _run_code_message[:] = ["Removed the loaded friend runs.", False]


def run_code_copy_fields():
    """For the shared Copy result button: "Tide run code, RUN-TIDE-..." (empty when this run cannot be shared)."""
    code, _why = build_run_code()
    return {"game": "Tide run code", "stats": [code]} if code else {}


def render_run_code_box():
    out = document.getElementById("run-code-output")
    if out is None:
        return
    code, why = build_run_code()
    out.value = code
    status = document.getElementById("run-code-status")
    if status is not None:
        if code:
            decoded = decode_run_code(code)
            status.innerText = ("A friend will see: " + run_code_preview(decoded["params"], decoded["params"]["shown"])
                                + " " + RUN_CODE_NOTE) if decoded["ok"] else ""
        else:
            status.innerText = why
    copy_host = document.getElementById("run-code-copy")
    if copy_host is not None:
        copy_host.hidden = not code
    message = document.getElementById("run-code-message")
    if message is not None:
        message.innerText = ("! " if _run_code_message[1] else "") + _run_code_message[0]
        message.setAttribute("role", "alert" if _run_code_message[1] else "status")
    field = document.getElementById("run-code-input")
    if field is not None:
        field.setAttribute("aria-invalid", "true" if _run_code_message[1] else "false")
    clear = document.getElementById("run-code-clear-button")
    if clear is not None:
        clear.hidden = not _ghosts
