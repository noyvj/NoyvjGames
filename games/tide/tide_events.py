"""Postcards, the Acid Tide boss, bracing for storms and the chess mode panel."""

import html
import json

from js import document, setTimeout
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_bridge import _read_local_storage_item, _write_local_storage_item
from tide_coasts import heritage_sites, tile_row_state
from tide_rules import (
    ACID_BOSS_SEASON, ACID_BOSS_SPIKE, ACID_BOSS_WARN_SEASONS, ACID_BRACE_COST, ACID_BRACE_MIN_REDUCTION,
    BRACE_STEP, CHESS_RUNOFF_LAG, COASTLINE_ROWS, EVACUATE_COST, FLOODED, HERITAGE_PROTECTED, POP_START,
)
from tide_seasonflow import _reduced_motion


# GD-9 Postcard ending ----------------------------------------------------------------------------------------------
POSTCARD_KEY = "tide_postcards_v1"
POSTCARD_GRADES = ("S", "A", "B", "C", "D", "E")
POSTCARD_NICKNAMES = (
    "The Unflooded", "The Drowned Quay", "The Quiet Nets", "Keeper of Lights", "The Anchor That Held",
    "The Busy Harbour", "The Stubborn Harbour",
)
POSTCARD_MIN_SEASONS = 3


def postcard_score():
    """0..1 from what actually happened: dry rows, fish yield, population kept and damage the defences saved."""
    s = runstate.state
    dry = s.rows_dry_count() / COASTLINE_ROWS
    fish = s.fish_yield_multiplier()
    population = min(1.0, s.population / max(1, s.peak_population or POP_START))
    saved = (s.damage_saved() / s.undampened_damage_total) if s.undampened_damage_total > 0 else 1.0
    return max(0.0, min(1.0, 0.35 * dry + 0.25 * fish + 0.20 * population + 0.20 * max(0.0, min(1.0, saved))))


def postcard_grade(score=None):
    score = postcard_score() if score is None else score
    for grade, floor in zip(POSTCARD_GRADES, (0.9, 0.75, 0.6, 0.45, 0.3, 0.0)):
        if score >= floor:
            return grade
    return "E"


def postcard_nickname():
    s = runstate.state
    if s.ironman_earned:
        return "The Anchor That Held"
    if s.rows_dry_count() == COASTLINE_ROWS and s.current_tier_index() >= 3:
        return "The Unflooded"
    if s.rows_dry_count() <= 1:
        return "The Drowned Quay"
    if s.fish_yield_multiplier() < 0.6:
        return "The Quiet Nets"
    if s.protected_heritage_count() == len(heritage_sites()):
        return "Keeper of Lights"
    if len(s.crew) >= 2:
        return "The Busy Harbour"
    return "The Stubborn Harbour"


def postcard_svg():
    """The postcard as an SVG: every coastline row is a band (dry sand, flooded water, retreat marked), with the seawall tier, heritage and boats."""
    s = runstate.state
    width, height, band = 200, 150, 16
    tier = s.current_tier_index()
    parts = [f'<svg viewBox="0 0 {width} {height}" class="postcard-svg" xmlns="http://www.w3.org/2000/svg" role="img" '
             f'aria-label="Postcard of {html.escape(s.display_name())}: grade {postcard_grade()}, {s.rows_dry_count()} of {COASTLINE_ROWS} rows dry">',
             f'<rect width="{width}" height="{height}" fill="#cfeaf5"/>',
             '<rect y="0" width="200" height="22" fill="#e8f6fb"/>']
    for row in range(COASTLINE_ROWS):
        y = 24 + row * band
        lost = tile_row_state(row, s.sea_level) == FLOODED
        retreated = row in s.retreat_rows
        fill = "#2f7f9e" if lost else "#8d6e4a" if retreated else "#e6cf9a"
        parts.append(f'<rect x="10" y="{y}" width="180" height="{band - 1}" fill="{fill}"/>')
        if lost:
            for col in range(8):  # sunken roofs: a small triangle just under the surface
                parts.append(f'<path d="M{16 + col * 22},{y + 12} l5,-6 l5,6 z" fill="#1a5876"/>')
        else:
            for col in range(0, 8, 2):
                parts.append(f'<rect x="{18 + col * 22}" y="{y + 5}" width="8" height="6" fill="#b5651d"/>')
    if tier:
        parts.append(f'<rect x="8" y="24" width="{2 + tier * 2}" height="{COASTLINE_ROWS * band}" fill="#6b6b6b"/>')
    for site in heritage_sites():
        if s.heritage.get(site["id"]) == HERITAGE_PROTECTED:
            parts.append(f'<text x="168" y="{24 + site["row"] * band + 12}" font-size="12">{site["emoji"]}</text>')
    boats = min(4, max(0, int(s.population / 60))) if s.fish_yield_multiplier() > 0.3 else 0
    for i in range(boats):
        parts.append(f'<path d="M{30 + i * 40},20 l8,0 l-4,-7 z" fill="#fff" stroke="#555" stroke-width="0.5"/>')
    if s.population > 0 and boats == 0 and s.fish_yield_multiplier() <= 0.3:
        parts.append('<path d="M60,20 l10,0 l-2,3 l-6,0 z" fill="#555"/>')  # one abandoned hull
    parts.append(f'<text x="100" y="{height - 6}" font-size="9" text-anchor="middle" fill="#13354a">Greetings from {html.escape(s.display_name())} · {postcard_grade()} · {html.escape(postcard_nickname())}</text>')
    parts.append("</svg>")
    return "".join(parts)


def load_postcards():
    raw = _read_local_storage_item(POSTCARD_KEY)
    try:
        data = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict) and item.get("grade") in POSTCARD_GRADES and item.get("nickname") in POSTCARD_NICKNAMES:
            out.append({"grade": item["grade"], "nickname": item["nickname"], "name": str(item.get("name", ""))[:24], "season": int(item["season"]) if isinstance(item.get("season"), int) and not isinstance(item.get("season"), bool) else 0})
    return out[:len(POSTCARD_GRADES) * len(POSTCARD_NICKNAMES)]


def collect_postcard():
    """Files the current postcard in the gallery (one per grade and nickname variant). Returns 'new', 'seen' or 'early'."""
    if runstate.state.season - 1 < POSTCARD_MIN_SEASONS or runstate.state.workshop_active():
        return "early"
    entry = {"grade": postcard_grade(), "nickname": postcard_nickname(), "name": runstate.state.display_name()[:24], "season": runstate.state.season - 1}
    cards = load_postcards()
    if any(c["grade"] == entry["grade"] and c["nickname"] == entry["nickname"] for c in cards):
        return "seen"
    cards.append(entry)
    _write_local_storage_item(POSTCARD_KEY, json.dumps(cards))
    return "new"


def gallery_text():
    cards = load_postcards()
    total = len(POSTCARD_GRADES) * len(POSTCARD_NICKNAMES)
    if not cards:
        return f"Postcard gallery: 0 of {total} variants collected."
    shown = ", ".join(f"{c['grade']} {c['nickname']}" for c in cards[-6:])
    return f"Postcard gallery: {len(cards)} of {total} variants collected. Latest: {shown}."


_postcard_status = {"text": ""}


def render_postcard():
    box = document.getElementById("postcard-view")
    if box is not None:
        box.innerHTML = postcard_svg() if runstate.session_summary_open else ""
    for element_id, text in (("postcard-gallery", gallery_text()), ("postcard-status", _postcard_status["text"])):
        element = document.getElementById(element_id)
        if element is not None:
            element.innerText = text


def acid_boss_text():
    if not runstate.state.acid_boss_mode:
        return "The Acid Tide boss is off. Turn it on for one optional mega acid surge in Season 15 that you can brace against."
    if runstate.state.acid_boss_result == "survived":
        return "The Acid Tide has been faced down. Your buffer held."
    if runstate.state.acid_boss_result == "hit":
        return "The Acid Tide struck. Watch the fish: the lag means the full damage arrives in a few seasons."
    wait = runstate.state.seasons_until_acid_boss()
    if wait is not None and wait <= ACID_BOSS_WARN_SEASONS * 2:
        brace = ("Braced." if runstate.state.acid_braced else
                 f"Brace for it: {ACID_BRACE_COST} funds and {ACID_BRACE_MIN_REDUCTION} Reduction capacity (you have {runstate.state.capacity['reduction']}).")
        return f"Acid Tide forecast: a +{ACID_BOSS_SPIKE:.0f} acidity surge in {wait} season{'s' if wait != 1 else ''}. {brace}"
    return f"Acid Tide boss on: a surge is coming around Season {ACID_BOSS_SEASON}. A warning will appear {ACID_BOSS_WARN_SEASONS * 2} seasons ahead."


def render_acid_boss():
    toggle, text, brace = (document.getElementById(i) for i in ("acid-boss-toggle-button", "acid-boss-text", "acid-boss-brace-button"))
    if toggle is not None:
        toggle.innerText = "Acid Tide boss: On (turn off)" if runstate.state.acid_boss_mode else "Acid Tide boss: Off (turn on)"
        toggle.disabled = bool(runstate.state.acid_boss_result)
    if text is not None:
        text.innerText = acid_boss_text()
    if brace is not None:
        brace.hidden = not runstate.state.acid_boss_pending()
        brace.disabled = not runstate.state.can_brace()


def render_brace():
    panel, text, result = (document.getElementById(i) for i in ("brace-panel", "brace-text", "storm-result"))
    if panel is not None:
        panel.hidden = not runstate.state.can_brace_storm()
    if text is not None:
        text.innerText = runstate.state.brace_text()
    for kind in ("barriers", "stockpile", "evacuate"):
        button = document.getElementById(f"brace-{kind}-button")
        if button is not None:
            cost = EVACUATE_COST if kind == "evacuate" else BRACE_STEP
            button.disabled = not runstate.state.can_brace_storm() or runstate.state.funds < cost or (kind == "evacuate" and runstate.state.brace["evacuate"])
    if result is not None:
        result.innerText = f"Last storm: {runstate.state.last_storm_result}." if runstate.state.last_storm_result else ""
    root = document.getElementById("coastline-grid")
    if root is not None and runstate.state.last_storm_result and _storm_crash["season"] != runstate.state.season and runstate.state.storm_log:
        _storm_crash["season"] = runstate.state.season
        if not _reduced_motion():
            root.classList.add("storm-crash")
            _remove_class_later(root, "storm-crash", 1400)


_storm_crash = {"season": 0}


def _remove_class_later(element, class_name, delay_ms):
    holder = []

    def remove():
        element.classList.remove(class_name)
        if holder:
            holder[0].destroy()

    holder.append(create_proxy(remove))
    setTimeout(holder[0], delay_ms)


def chess_text():
    if not runstate.state.chess_mode:
        return "Tidal Chess is off. Turn it on before the first season for a runoff delay on top of the fish lag, with the acidity readouts hidden."
    return (f"Tidal Chess: runoff reaches the water {CHESS_RUNOFF_LAG} seasons late and only the fish warning is shown. "
            f"Seasons with the fish at the warning level: {runstate.state.chess_dips} (fewer is better).")


def render_chess():
    toggle, text = document.getElementById("chess-toggle-button"), document.getElementById("chess-text")
    if toggle is not None:
        toggle.innerText = "Tidal Chess: On (turn off)" if runstate.state.chess_mode else "Tidal Chess: Off (turn on)"
        toggle.disabled = runstate.state.season > 1
    if text is not None:
        text.innerText = chess_text()
    root = getattr(document, "documentElement", None)
    if root is not None and hasattr(root, "setAttribute"):
        root.setAttribute("data-tidal-chess", "on" if runstate.state.chess_mode else "off")
