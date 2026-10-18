"""The career that survives Start New Chain: founder rank, name plates, secret goods, speed flags, ring themes."""

from js import document

import loop_runstate as runstate
from loop_bridge import _window
from loop_rules import (
    ALL_GOODS, GOODS_CATEGORIES, LEAN_CLOSE_EXTRACTION, PLATES, PLATE_DOMINANT_SHARE, PLATE_FOR_SOURCE,
    RING_THEME_UNLOCKS, SPEED_CLOSE_CYCLE,
)


# GH-14/GH-15/GH-20 + H-9: the career, which like the two counters above survives
# "Start New Chain". Everything here is a pure record of what happened (never an input
# to the sums), and rides get_state()/load_state() as one "career" key.
career_closed_categories = set()  # picked categories that ran a fully closed cycle
career_plates = set()  # PLATES keys earned
career_speed = set()  # {"cycle12", "lean", "no_trade"}: speed-loop flags (GH-20)
career_best = {}  # picked category -> {"fastest_close", "lowest_extraction", "best_score", "best_streak"}
# H-12: lifetime counts from FINISHED chains (the chain in play is added live, so a rewind can never
# double count). Part of the career: survives Start New Chain, saved with it.
career_counts = {"cycles": 0, "chains_closed": 0}
FOUNDER_POINTS_PER_CLOSED_CHAIN = 15
FOUNDER_POINTS_PER_CATEGORY = 30
FOUNDER_RANKS = (
    ("Apprentice", 0), ("Fitter", 15), ("Technician", 40), ("Engineer", 80), ("Lead Engineer", 140),
    ("Director", 220), ("Chief Circularity Officer", 330), ("Founder", 480),
)
CAREER_SPEED_FLAGS = ("cycle12", "lean", "no_trade")
CAREER_BEST_FIELDS = ("fastest_close", "lowest_extraction", "best_score", "best_streak")


def founder_stats():
    """H-12: (cycles run, chains closed, goods mastered) across the whole career, including the chain in play."""
    cycles = career_counts["cycles"] + len(runstate.chain.circular_fraction_log)
    closed = career_counts["chains_closed"] + (1 if runstate.chain.first_loop_closed_cycle is not None else 0)
    mastered = len(career_closed_categories & set(ALL_GOODS))
    return cycles, closed, mastered


def founder_points():
    cycles, closed, mastered = founder_stats()
    return cycles + FOUNDER_POINTS_PER_CLOSED_CHAIN * closed + FOUNDER_POINTS_PER_CATEGORY * mastered


def founder_rank():
    """H-12: (index, name, points, next_name or None, next_threshold or None). Purely a badge:
    nothing in the game reads it."""
    points = founder_points()
    index = 0
    for i, (_name, needed) in enumerate(FOUNDER_RANKS):
        if points >= needed:
            index = i
    name = FOUNDER_RANKS[index][0]
    if index + 1 < len(FOUNDER_RANKS):
        return index, name, points, FOUNDER_RANKS[index + 1][0], FOUNDER_RANKS[index + 1][1]
    return index, name, points, None, None


def founder_text():
    _index, name, points, next_name, next_at = founder_rank()
    cycles, closed, mastered = founder_stats()
    line = (
        f"Founder rank: {name}. {cycles} cycle{'' if cycles == 1 else 's'} run, {closed} chain{'' if closed == 1 else 's'} "
        f"closed, {mastered} of {len(ALL_GOODS)} goods mastered: {points} points."
    )
    if next_name is None:
        return line + " That is the top rank."
    return line + f" Next rank: {next_name} at {next_at} points ({next_at - points} to go)."


def ring_theme_unlocked(theme):
    """GH-23: 'standard' is always open; the other three open through the career."""
    if theme == "standard":
        return True
    if theme == "neon":
        return bool(career_closed_categories)
    if theme == "blueprint":
        return secret_unlocked()
    if theme == "paper":
        return len(career_plates) >= 3
    return False


def ring_theme_count():
    return sum(1 for theme in RING_THEME_UNLOCKS if ring_theme_unlocked(theme))


def secret_unlocked():
    """GH-14: the secret category opens once every ordinary category has had a fully
    closed cycle."""
    return set(GOODS_CATEGORIES) <= career_closed_categories


def secret_progress():
    return len(career_closed_categories & set(GOODS_CATEGORIES)), len(GOODS_CATEGORIES)


def plate_for_mix(shares):
    """GH-15: which plate a supply mix earns, or None when nothing is supplied."""
    if not shares:
        return None
    source, share = max(shares.items(), key=lambda kv: kv[1])
    if share >= PLATE_DOMINANT_SHARE:
        return PLATE_FOR_SOURCE.get(source, "allrounder")
    return "allrounder"


def _update_career():
    """Idempotent: folds the current chain into the career records. Called after every
    action, so it must only ever add or improve."""
    category = runstate.chain.picked_category
    if runstate.chain.last_cycle_mix is not None:  # the last cycle ran fully closed
        career_closed_categories.add(category)
        plate = plate_for_mix(runstate.chain.last_cycle_mix)
        if plate:
            career_plates.add(plate)
    if runstate.chain.assist_used:
        return  # H-8: an assisted chain adds to what you have tried, never to speed flags or mastery records
    if runstate.chain.first_loop_closed_cycle is not None:
        if runstate.chain.first_loop_closed_cycle <= SPEED_CLOSE_CYCLE:
            career_speed.add("cycle12")
        if runstate.chain.first_close_extracted is not None and runstate.chain.first_close_extracted < LEAN_CLOSE_EXTRACTION:
            career_speed.add("lean")
        if runstate.chain.first_close_trade_free:
            career_speed.add("no_trade")
    if runstate.chain.total_produced > 0:
        best = career_best.setdefault(category, {})
        score = runstate.chain.score()
        if score > best.get("best_score", float("-inf")):
            best["best_score"] = score
        if runstate.chain.best_closed_loop_streak > best.get("best_streak", 0):
            best["best_streak"] = runstate.chain.best_closed_loop_streak
        if runstate.chain.first_loop_closed_cycle is not None:
            fastest = best.get("fastest_close")
            if fastest is None or runstate.chain.first_loop_closed_cycle < fastest:
                best["fastest_close"] = runstate.chain.first_loop_closed_cycle
            if runstate.chain.first_close_extracted is not None:
                lowest = best.get("lowest_extraction")
                if lowest is None or runstate.chain.first_close_extracted < lowest:
                    best["lowest_extraction"] = runstate.chain.first_close_extracted


def career_state():
    """JSON-safe copy of the career (empty dict when there is nothing to save)."""
    if not (career_closed_categories or career_plates or career_speed or career_best or any(career_counts.values())):
        return {}
    state = {
        "closed": sorted(career_closed_categories),
        "plates": sorted(career_plates),
        "speed": sorted(career_speed),
        "best": {cat: dict(rec) for cat, rec in sorted(career_best.items())},
    }
    if any(career_counts.values()):
        state["counts"] = dict(career_counts)
    return state


def _finite_number(value, low=0.0, high=1e9):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and value == value and low <= value <= high
    )


def load_career(data):
    """Validates a saved career key by key; anything unknown or malformed is dropped."""
    career_closed_categories.clear()
    career_plates.clear()
    career_speed.clear()
    career_best.clear()
    career_counts.update({"cycles": 0, "chains_closed": 0})
    if not isinstance(data, dict):
        return
    counts = data.get("counts")
    if isinstance(counts, dict):
        for field in career_counts:
            value = counts.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10_000_000:
                career_counts[field] = value
    valid_categories = set(ALL_GOODS)
    closed = data.get("closed")
    if isinstance(closed, list):
        career_closed_categories.update(c for c in closed if isinstance(c, str) and c in valid_categories)
    plates = data.get("plates")
    if isinstance(plates, list):
        career_plates.update(p for p in plates if isinstance(p, str) and p in PLATES)
    speed = data.get("speed")
    if isinstance(speed, list):
        career_speed.update(f for f in speed if isinstance(f, str) and f in CAREER_SPEED_FLAGS)
    best = data.get("best")
    if isinstance(best, dict):
        for category, record in best.items():
            if not (isinstance(category, str) and category in valid_categories and isinstance(record, dict)):
                continue
            clean = {}
            for field in CAREER_BEST_FIELDS:
                value = record.get(field)
                if field in ("fastest_close", "best_streak"):
                    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100000:
                        clean[field] = value
                elif _finite_number(value, -1e9, 1e9):
                    clean[field] = float(value)
            if clean:
                career_best[category] = clean


def career_reset():
    load_career(None)


RING_THEME_LABELS = {"standard": "Standard", "neon": "Neon", "blueprint": "Blueprint", "paper": "Paper cut-out"}


def render_ring_themes():
    """GH-23: unlock state of the three themes in Settings, and a fall back to Standard if the chosen one
    is not open on this save (settings.js owns the choice itself)."""
    for theme, label in RING_THEME_LABELS.items():
        option = document.getElementById(f"ring-theme-{theme}")
        open_now = ring_theme_unlocked(theme)
        option.disabled = not open_now
        option.innerText = label if open_now else f"{label} (locked: {RING_THEME_UNLOCKS[theme]})"
    document.getElementById("ring-theme-status").innerText = (
        f"{ring_theme_count()} of {len(RING_THEME_UNLOCKS)} themes unlocked. Cosmetic only: it changes how the ring looks."
    )
    window = _window()
    settings = getattr(window, "LoopSettings", None) if window is not None else None
    chosen = getattr(settings, "ringTheme", None)
    if chosen is not None:
        try:
            current = str(chosen())
            if current in RING_THEME_LABELS and not ring_theme_unlocked(current):
                settings.applyRingTheme("standard")
        except Exception:  # noqa: BLE001 -- a cosmetic bridge must never break rendering
            pass
