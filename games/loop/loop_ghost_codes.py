"""Run codes and the ghost (GH-28/H-7): build, decode, store, compare, draw."""

import base64
import html
import json
import re
import zlib

from js import document

import loop_runstate as runstate
from loop_bridge import _window
from loop_planner import plan_buys_text
from loop_rules import ALL_GOODS, BUY_KINDS
from loop_summaries import summary_blocks


# ---- GH-28 ghost run codes and H-7 comparison cards --------------------------------------------------------------------
GHOST_PREFIX = "LOOPRUN1"
GHOST_MAX_CYCLES = 60  # a code carries the first 60 cycles
GHOST_MAX_INPUT = 6000  # longer pasted text is refused without being read
GHOST_MAX_JSON = 20000  # the unpacked size limit (a zip-bomb guard)
GHOST_STORAGE_KEY = "loop-ghost-v1"
_GHOST_PATTERN = re.compile(r"^LOOPRUN1-([A-Za-z0-9_-]+)\.([0-9a-f]{8})$")
ghost_message = ["", False]  # text, is-a-problem


def _ghost_check(payload):
    return format(zlib.crc32(("loop-ghost-v1|" + payload).encode("ascii")) & 0xFFFFFFFF, "08x")


def build_run_code():
    """(code, error) for the chain in play: its goods, cycles, extraction, score, the circular share of each of the
    first 60 cycles and (when known) what was bought in each. Holds nothing a player typed and nothing personal."""
    cycles = runstate.chain.cycle_number - 1
    if cycles < 1:
        return "", "Run at least one cycle first: a code needs a run to share."
    shown = min(cycles, GHOST_MAX_CYCLES)
    buys = [list(row) for row in runstate.chain.buy_log[:shown]] if len(runstate.chain.buy_log) == cycles else []
    data = {
        "v": 1, "g": runstate.chain.picked_category, "n": cycles, "x": round(runstate.chain.total_extracted),
        "s": round(runstate.chain.score()), "k": runstate.chain.first_loop_closed_cycle or 0,
        "f": [round(f * 100) for f in runstate.chain.circular_fraction_log[:shown]], "b": buys,
    }
    raw = json.dumps(data, separators=(",", ":")).encode("ascii")
    payload = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")
    return f"{GHOST_PREFIX}-{payload}.{_ghost_check(payload)}", ""


def _plain_int(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def decode_run_code(text):
    """(ghost, error). A decoded code is DATA TO DISPLAY: never executed, never saved as your own progress, never
    a verified result (the check only catches typing mistakes; anyone can write a code with any numbers)."""
    if not isinstance(text, str):
        return None, "Paste a run code first."
    compact = "".join(text.split())
    if not compact:
        return None, "Paste a run code first."
    if len(compact) > GHOST_MAX_INPUT:
        return None, "That is too long to be a Loop run code."
    match = _GHOST_PATTERN.match(compact)
    if not match:
        return None, "That does not look like a Loop run code. They start with LOOPRUN1-."
    payload, check = match.groups()
    if _ghost_check(payload) != check:
        return None, "That run code has a typing mistake: check each character and try again."
    try:
        blob = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        unpacker = zlib.decompressobj()
        raw = unpacker.decompress(blob, GHOST_MAX_JSON)
        if unpacker.unconsumed_tail or not unpacker.eof:
            return None, "That run code could not be read."
        data = json.loads(raw.decode("ascii"))
    except (ValueError, zlib.error, UnicodeError):
        return None, "That run code could not be read."
    if not isinstance(data, dict) or data.get("v") != 1:
        return None, "That run code was made by a different version of the game."
    category, cycles, extracted, score, closed = (data.get(k) for k in ("g", "n", "x", "s", "k"))
    fractions, buys = data.get("f"), data.get("b")
    if not (isinstance(category, str) and category in ALL_GOODS and _plain_int(cycles, 1, 1_000_000)):
        return None, "That run code could not be read."
    if not (_plain_int(extracted, 0, 10**9) and _plain_int(score, -(10**9), 10**9) and _plain_int(closed, 0, 1_000_000)):
        return None, "That run code could not be read."
    shown = min(cycles, GHOST_MAX_CYCLES)
    if not (isinstance(fractions, list) and len(fractions) == shown and all(_plain_int(v, 0, 100) for v in fractions)):
        return None, "That run code could not be read."
    if not isinstance(buys, list) or (buys and len(buys) != shown):
        return None, "That run code could not be read."
    for row in buys:
        if not (isinstance(row, list) and len(row) == len(BUY_KINDS) and all(_plain_int(v, 0, 999) for v in row)):
            return None, "That run code could not be read."
    return {
        "category": category, "cycles": cycles, "extracted": extracted, "score": score,
        "closed": closed or None, "fractions": [v / 100.0 for v in fractions], "buys": [list(r) for r in buys],
    }, ""


def _storage_get(key):
    window = _window()
    if window is None:
        return None
    try:
        return window.localStorage.getItem(key)
    except Exception:  # noqa: BLE001 -- storage can be blocked
        return None


def _storage_set(key, value):
    window = _window()
    if window is None:
        return
    try:
        if value is None:
            window.localStorage.removeItem(key)
        else:
            window.localStorage.setItem(key, value)
    except Exception:  # noqa: BLE001 -- the ghost then simply lasts for this visit
        pass


def load_ghost(text):
    """Loads a friend's code as the ghost. Returns True on success; the message says what happened either way."""
    loaded, error = decode_run_code(text)
    if loaded is None:
        ghost_message[:] = [error, True]
        return False
    runstate.ghost = loaded
    _storage_set(GHOST_STORAGE_KEY, "".join(text.split()))
    name = ALL_GOODS[loaded["category"]].get("name") or ALL_GOODS[loaded["category"]]["label"].capitalize()
    ghost_message[:] = [f"Ghost loaded: {name} chain of {loaded['cycles']} cycles. It is drawn dotted on the Past chains graph.", False]
    return True


def clear_ghost():
    runstate.ghost = None
    _storage_set(GHOST_STORAGE_KEY, None)
    ghost_message[:] = ["Ghost removed.", False]


def restore_ghost():
    """On page load: brings back the ghost the player had loaded (silently drops one that no longer decodes)."""
    stored = _storage_get(GHOST_STORAGE_KEY)
    if not stored:
        return
    loaded, _error = decode_run_code(stored)
    if loaded is None:
        _storage_set(GHOST_STORAGE_KEY, None)
        return
    runstate.ghost = loaded


def ghost_buy_lines():
    """What the ghost bought in each cycle, so you can follow (or beat) it."""
    if runstate.ghost is None:
        return []
    lines = []
    for i, row in enumerate(runstate.ghost["buys"]):
        counts = {kind: row[j] for j, kind in enumerate(BUY_KINDS) if row[j]}
        lines.append(f"Cycle {i + 1}: {plan_buys_text(counts) if counts else 'bought nothing'}")
    return lines


def ghost_gap_text():
    if runstate.ghost is None:
        return ""
    done = runstate.chain.cycle_number - 1
    if done < 1:
        return "Run a cycle and the ghost's circular share can be compared with yours."
    n = min(done, len(runstate.ghost["fractions"]))
    mine, theirs = runstate.chain.circular_fraction_log[n - 1], runstate.ghost["fractions"][n - 1]
    diff = round((mine - theirs) * 100)
    if diff > 0:
        verdict = f"you are {diff} points ahead"
    elif diff < 0:
        verdict = f"you are {-diff} points behind"
    else:
        verdict = "you are level"
    return f"On cycle {n} the ghost was {theirs * 100:.0f}% circular and you were {mine * 100:.0f}%: {verdict}."


def ghost_compare_rows():
    """(label, yours, ghost's) rows for the comparison card."""
    if runstate.ghost is None:
        return []
    done = runstate.chain.cycle_number - 1
    label = lambda c: ALL_GOODS[c].get("name") or ALL_GOODS[c]["label"].capitalize()  # noqa: E731
    mine_closed = runstate.chain.first_loop_closed_cycle
    return [
        ("Goods", label(runstate.chain.picked_category), label(runstate.ghost["category"])),
        ("Cycles run", str(done), str(runstate.ghost["cycles"])),
        ("Closed the loop on cycle", str(mine_closed) if mine_closed else "not yet",
         str(runstate.ghost["closed"]) if runstate.ghost["closed"] else "never"),
        ("Units extracted", f"{runstate.chain.total_extracted:.0f}", str(runstate.ghost["extracted"])),
        ("Score", f"{runstate.chain.score():.0f}", str(runstate.ghost["score"])),
    ]


def ghost_table_html():
    rows = ghost_compare_rows()
    if not rows:
        return ""
    out = ['<table class="planner-table"><thead><tr><th></th><th>You</th><th>Ghost</th></tr></thead><tbody>']
    for label, mine, theirs in rows:
        out.append(f"<tr><th scope=\"row\">{html.escape(label)}</th><td>{html.escape(mine)}</td><td>{html.escape(theirs)}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


def render_ghost():
    present = runstate.ghost is not None
    document.getElementById("ghost-compare").hidden = not present
    document.getElementById("ghost-clear-button").hidden = not present
    message, problem = ghost_message
    message_el = document.getElementById("ghost-message")
    message_el.innerText = message
    message_el.setAttribute("role", "alert" if problem else "status")
    if not present:
        return
    document.getElementById("ghost-table").innerHTML = ghost_table_html()
    document.getElementById("ghost-gap").innerText = ghost_gap_text()
    document.getElementById("ghost-sparks").innerText = (
        "You    " + (summary_blocks(runstate.chain.circular_fraction_log) or "(no cycles yet)") + "\n"
        "Ghost  " + (summary_blocks(runstate.ghost["fractions"]) or "")
    )
    lines = ghost_buy_lines() or ["This code does not carry its purchases."]
    document.getElementById("ghost-buys").innerHTML = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
