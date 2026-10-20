"""Small shared helpers: tile ids and coordinate labels, localStorage reads and writes, SVG text and sparklines, the forest log entry, the screen-reader announcer queue, timed callbacks, number formatting and display preferences."""

import json
import os

from js import document, setTimeout
from pyodide.ffi import create_proxy

import canopy_runstate as runstate
from canopy_rules import (
    ACCRUING_STATES, BIODIVERSITY_ACCRUAL_PER_TICK, DIFFICULTY_RANGER, DIFFICULTY_RIVAL,
    DIFFICULTY_WILDFIRE, REPLANTING, SPECIALIST_BIODIVERSITY_MULTIPLIER, SPECIALIZATION_BIODIVERSITY,
    lab_active,
)
from canopy_worldvars import (
    CHALLENGE_NONE, CHALLENGE_SPECS, FOREST_LOG_MAX_ENTRIES, FOREST_PULSE_MS, NUMBER_FORMATS,
    NUMBER_FORMAT_COMPACT, NUMBER_FORMAT_GROUPED, NUMBER_FORMAT_PRECISE, NUMBER_FORMAT_STANDARD,
    PACE_NORMAL, REQUEST_PACE_LABEL, SOIL_BANDS, UI_PREF_NUMBER_FORMAT, _announce_queue, _gb_toast_queue,
)


def _plot_tile_id(index):
    return f"plot-{index}"


# B4 (planning/TODO.md "Per-game: Canopy"): coordinate-style plot labels
# ("A1".."F6") so stakeholder-request messages and plot detail text read as
# a real place on the grid instead of an opaque array index. Columns are
# letters (A..F for GRID_COLS==6), rows are 1-based numbers — the same
# spreadsheet-style convention the TODO's own "C3" example uses. Pure
# presentation over the existing `index = row * GRID_COLS + col` layout;
# no stored state, so it's safe to compute anywhere without touching
# get_state()/load_state().
def plot_coordinate_label(index):
    row, col = divmod(index, runstate.GRID_COLS)
    return f"{chr(ord('A') + col)}{row + 1}"


# Z6 (planning/TODO.md "Z. Games"): how long the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css)
# stays on before self-removing -- matches the CSS animation's own
# duration so the class is gone right as the pulse finishes.
PERSONAL_BEST_BADGE_MS = 1800


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json()) so
    this file stays importable outside a real browser. Broad except on
    the actual read/write below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, not core gameplay,
    so it degrades to "no personal best recorded" rather than crashing
    the module import the way _read_achievements_json()'s own docstring
    describes for that feature."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 — see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 — see _read_local_storage_item's docstring
        pass


# B6: a small inline SVG sparkline built directly as a markup string
# (assigned via innerHTML) rather than a chain of createElement calls --
# simplest way to draw two polylines from `_value_history`, and this
# element is replaced wholesale on every summary render anyway (same
# rebuild-from-scratch approach render_grid() already uses for its tiles).
SPARKLINE_WIDTH = 260
SPARKLINE_HEIGHT = 60
SPARKLINE_INCOME_COLOR = "#e8a33d"
SPARKLINE_STANDING_COLOR = "#4caf50"


def _sparkline_points(series, max_value):
    """Maps a list of values onto SVG viewport coordinates -- x spread
    evenly left-to-right, y scaled so 0 sits on the baseline and
    `max_value` sits at the top. A flat (all-zero, or single-point)
    series still renders as a flat line along the baseline rather than
    dividing by zero."""
    if not series:
        return ""
    denominator = max(max_value, 1e-9)
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    points = []
    for i, value in enumerate(series):
        x = i * step
        y = SPARKLINE_HEIGHT - (value / denominator) * SPARKLINE_HEIGHT
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _svg_text(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _log_event(kind, text, plot_index=None):
    runstate.forest_log.append({"tick": runstate.forest_tick, "kind": kind, "plot": plot_index, "text": text})
    del runstate.forest_log[:-FOREST_LOG_MAX_ENTRIES]
    if kind not in ("wildlife", "mature"):  # B-7: everything else is worth saying aloud
        _announce(text)


# ===========================================================================
# GB batch 1 -- behaviour (constants/state are declared near the top of the
# file, above reset_session()). See planning/IMPROVEMENT-IDEAS-ROUND-3.md
# section GB for the wording of each idea.
# ===========================================================================


def _el(element_id):
    """getElementById that tolerates a page/test DOM without the element (a
    real browser returns None, the fake test DOM raises KeyError)."""
    try:
        return document.getElementById(element_id)
    except KeyError:
        return None


def _gb_hash(*parts):
    """A small deterministic integer hash, standing in for randomness (this
    game deliberately has no RNG, so runs and tests are repeatable)."""
    h = 2166136261
    for part in parts:
        h = ((h ^ (int(part) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return h


def _gb_toast(message):
    """Queues a GB toast; the next render shows it (joined with any achievement
    toast that lands in the same render, so neither hides the other)."""
    _gb_toast_queue.append(message)


def _timed_callback(callback, delay_ms):
    """setTimeout for a one-shot callback whose proxy destroys itself after
    firing (never destroy a still-pending proxy, see show_achievement_toast)."""
    holder = []

    def _run():
        try:
            callback()
        finally:
            holder[0].destroy()

    holder.append(create_proxy(_run))
    setTimeout(holder[0], delay_ms)


def _plot_ref(index):
    """How the log and readouts name a main-forest plot: its coordinate, or
    the adopted plot's nickname (GB-14) with the coordinate in brackets."""
    label = plot_coordinate_label(index)
    if index == runstate.adopted_plot_index and runstate.adopted_plot_nickname:
        return f"{runstate.adopted_plot_nickname} ({label})"
    return label


def _forest_display_name():
    return runstate.forest_name or "The forest"


def _ordinal_word(n):
    return {1: "a first", 2: "a second", 3: "a third"}.get(n, f"{n}th")


def _neighbour_indices(index):
    """The up-to-8 main-forest plots touching `index` (sides and corners)."""
    row, col = divmod(index, runstate.GRID_COLS)
    found = []
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            r, c = row + d_row, col + d_col
            if 0 <= r < runstate.GRID_ROWS and 0 <= c < runstate.GRID_COLS:
                found.append(r * runstate.GRID_COLS + c)
    return found


def _flash_element(element_id):
    """Reuses the shared .just-improved pulse (personal-best flash pattern)."""
    element = _el(element_id)
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = _el(element_id)
        if el is not None:
            el.classList.remove("just-improved")

    _timed_callback(_unflash, PERSONAL_BEST_BADGE_MS)


def _flash_forest_pulse():
    """The brief light pulse: the forest backdrop flushes and the title flashes
    (the shared personal-best .just-improved pattern)."""
    visual = _el("forest-visual")
    if visual is not None:
        visual.classList.add("forest-pulse")
        runstate._forest_pulse_gen += 1
        gen = runstate._forest_pulse_gen

        def _unpulse():
            el = _el("forest-visual")
            if el is not None and gen == runstate._forest_pulse_gen:
                el.classList.remove("forest-pulse")

        _timed_callback(_unpulse, FOREST_PULSE_MS)
    _flash_element("forest-title-display")


# ===========================================================================
# GB batch 2 -- behaviour (constants and state are above reset_session()).
# ===========================================================================

# --- display options read from localStorage (B-8, B-10, B-26) ------------------------------------------------

def ui_pref(key, default=""):
    """A per-browser display option written by settings.js (never saved with a game)."""
    value = _read_local_storage_item(key)
    return default if value is None else str(value)


def number_format_mode():
    mode = ui_pref(UI_PREF_NUMBER_FORMAT, NUMBER_FORMAT_STANDARD)
    return mode if mode in NUMBER_FORMATS else NUMBER_FORMAT_STANDARD


def _compact_number(value):
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    suffixes = ((1e9, "B"), (1e6, "M"), (1e3, "k"))
    for position, (limit, suffix) in enumerate(suffixes):
        if magnitude >= limit:
            scaled = round(magnitude / limit, 1)
            if scaled >= 1000 and position > 0:  # 999.96k is "1M", not "1000k"
                limit, suffix = suffixes[position - 1]
                scaled = round(magnitude / limit, 1)
            text = f"{scaled:.1f}"
            if text.endswith(".0"):
                text = text[:-2]
            return f"{sign}{text}{suffix}"
    return f"{sign}{magnitude:.1f}"


def fmt_num(value, decimals=1):
    """B-26: a number for the HUD and mobile dock in the player's chosen format."""
    mode = number_format_mode()
    if mode == NUMBER_FORMAT_GROUPED:
        return f"{value:,.{decimals}f}"
    if mode == NUMBER_FORMAT_COMPACT:
        return _compact_number(value)
    if mode == NUMBER_FORMAT_PRECISE:
        return f"{value:.{max(decimals, 2)}f}"
    return f"{value:.{decimals}f}"


def soil_band(plot):
    """B-10: (percent, band name) for a plot's soil quality."""
    pct = round(plot.productivity_multiplier() * 100)
    for floor, name in SOIL_BANDS:
        if pct >= floor:
            return pct, name
    return pct, SOIL_BANDS[-1][1]


def _plot_tooltip_detail(plot):
    """B-16: the second line of the plot card: age, biodiversity rate, clear count."""
    if plot.state in ACCRUING_STATES:
        age = f"standing {plot.ticks_intact} ticks"
        rate = BIODIVERSITY_ACCRUAL_PER_TICK
        if plot.specialization == SPECIALIZATION_BIODIVERSITY:
            rate *= SPECIALIST_BIODIVERSITY_MULTIPLIER
    elif plot.state == REPLANTING:
        age = f"replanting, {plot.replant_ticks_remaining} ticks to go"
        rate = 0.0
    else:
        age = "bare"
        rate = 0.0
    if plot.clear_count == 0:
        cleared = "never cleared"
    else:
        cleared = f"cleared {plot.clear_count} time{'s' if plot.clear_count != 1 else ''}"
    return f"Age: {age} · biodiversity +{rate:.2f}/tick · {cleared}"


ANNOUNCE_MAX_QUEUED = 6


def _announce(message):
    """Queues a sentence for the polite live region; the next render speaks it."""
    if message:
        _announce_queue.append(str(message))
        del _announce_queue[:-ANNOUNCE_MAX_QUEUED]


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


def session_tag_text():
    """Names every non-default setting that changes how a run plays, so shared results stay honest."""
    parts = []
    if runstate.current_difficulty == DIFFICULTY_RANGER:
        parts.append("Forest ranger")
    if runstate.current_pace != PACE_NORMAL:
        parts.append(REQUEST_PACE_LABEL[runstate.current_pace].lower())
    if runstate.current_challenge != CHALLENGE_NONE:
        parts.append(f"{CHALLENGE_SPECS[runstate.current_challenge]['label']} challenge")
    if runstate.current_difficulty == DIFFICULTY_WILDFIRE:
        parts.append("Wildfire season")
    if runstate.current_difficulty == DIFFICULTY_RIVAL:
        parts.append("Rival logging company")
    if lab_active():
        parts.append("Forest Lab sandbox")
    return ", ".join(parts)


def _number_or(value, default, low=0.0, high=None):
    """A finite non-bool number clamped into [low, high], else `default`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    if value in (float("inf"), float("-inf")):
        return default
    value = max(low, value)
    return value if high is None else min(high, value)


def _index_or_none(value, size):
    """`value` when it is an int index into a list of `size` things, else None (bools and floats do not count)."""
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < size:
        return value
    return None


def read_data_json(window_name, filename):
    """Read a JSON data file from the window global (boot script) or disk (pytest)."""
    try:
        import js as _js  # noqa: PLC0415
    except ImportError:
        _js = None

    raw = getattr(_js, window_name, None) if _js is not None else None
    if raw is None:
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", filename)
        try:
            with open(data_path, encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            return None

    try:
        return json.loads(str(raw))
    except (ValueError, OSError):
        return None
