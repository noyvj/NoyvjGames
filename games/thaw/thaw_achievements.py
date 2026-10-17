"""Achievements (catalog, checks, progress, panel, toast) and the map skins they unlock."""

import json

from js import document, setTimeout
from pyodide.ffi import create_proxy

import thaw_runstate as runstate
from thaw_bridge import _escape, _read_local_storage_item, _write_local_storage_item
from thaw_model import region, region_b, region_c, region_d
from thaw_rules import CATEGORIES, MAX_FEEDBACK_DAMPENING


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration, as also built out for Canopy/Grid/Continuum. Every
# achievement's earned status is a pure function of state that already
# exists elsewhere in this module, recomputed fresh every call — never a
# separately hand-maintained "earned" flag. A handful of achievements
# genuinely needed new tracked state (dampening_at_melt_start on
# RegionState, and the module-level preset_used_ever/
# worst_case_region_revealed flags above) because "was this true at some
# specific past moment" or "has the player ever done X" can't be derived
# from state that only remembers the present.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's/Grid's `_read_achievements_json()`:
    the boot script fetches achievements.json and hands it to Python as a
    window global before this file runs; the pytest harness's fake `js`
    module has no such attribute, so this falls through to reading the
    file straight off disk, keeping the module importable outside a real
    browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Thaw's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

EARLY_INVESTOR_MIN_DAMPENING = 0.25
SLOW_BURN_ROUNDS_AFTER_MELT = 15
SLOW_BURN_MAX_ACCELERATION = 1.5
WELL_FUNDED_TARGET = 500
LONG_HAUL_ROUND_TARGET = 25
BEAT_BOTH_REGIONS_MIN_ROUND = 15
SNOW_LEOPARD_MIN_ROUND = 20   # GG-14: a full session (about 20 minutes) in
SNOW_LEOPARD_GAP = 8.0        # GG-14: degrees cooler than the unmanaged Region D


def _all_categories_invested():
    return all(region.capacity[c] >= 1 for c in CATEGORIES)


def _invested_count():
    return sum(1 for c in CATEGORIES if region.capacity[c] >= 1)


def _both_secondary_regions_invested():
    return sum(region_b.capacity.values()) >= 1 and sum(region_c.capacity.values()) >= 1


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_output": lambda: region.capacity["output"] >= 1,
    "first_intervention": lambda: region.capacity["preserve"] >= 1 or region.capacity["monitor"] >= 1,
    "triple_threat": _all_categories_invested,
    "quarter_dampening": lambda: region.feedback_dampening_fraction() >= 0.25,
    "half_dampening": lambda: region.feedback_dampening_fraction() >= 0.5,
    "max_dampening": lambda: region.feedback_dampening_fraction() >= MAX_FEEDBACK_DAMPENING - 1e-9,
    "tipping_point_witnessed": lambda: region.melt_started_round is not None,
    "early_investor": lambda: (
        region.dampening_at_melt_start is not None
        and region.dampening_at_melt_start >= EARLY_INVESTOR_MIN_DAMPENING
    ),
    "degree_saved_5": lambda: region.temperature_saved() >= 5,
    "degree_saved_10": lambda: region.temperature_saved() >= 10,
    "degree_saved_20": lambda: region.temperature_saved() >= 20,
    "slow_burn": lambda: (
        region.melt_started_round is not None
        and (region.round_number - region.melt_started_round) >= SLOW_BURN_ROUNDS_AFTER_MELT
        and region.acceleration_factor() < SLOW_BURN_MAX_ACCELERATION
    ),
    "well_funded": lambda: region.funds >= WELL_FUNDED_TARGET,
    "long_haul": lambda: region.round_number >= LONG_HAUL_ROUND_TARGET,
    "beat_both_regions": lambda: (
        region.round_number >= BEAT_BOTH_REGIONS_MIN_ROUND
        and region.temperature < region_b.temperature
        and region.temperature < region_c.temperature
    ),
    "comparison_engaged": _both_secondary_regions_invested,
    "preset_strategist": lambda: runstate.preset_used_ever,
    "worst_case_witnessed": lambda: runstate.worst_case_region_revealed,
    # GG-14: secret; a quiet predator that keeps well ahead of pure neglect for a whole session.
    "snow_leopard": lambda: (
        region.round_number >= SNOW_LEOPARD_MIN_ROUND
        and region_d.temperature - region.temperature >= SNOW_LEOPARD_GAP
    ),
}

# Progress readouts, only for achievements with a genuine numeric scale-up
# — a one-shot milestone (e.g. "witness the tipping point") gets no
# progress row at all, the honest shape for it per the design doc.
ACHIEVEMENT_PROGRESS = {
    "triple_threat": lambda: (_invested_count(), len(CATEGORIES)),
    "quarter_dampening": lambda: (min(100, round(region.feedback_dampening_fraction() * 100)), 25),
    "half_dampening": lambda: (min(100, round(region.feedback_dampening_fraction() * 100)), 50),
    "max_dampening": lambda: (
        min(100, round(region.feedback_dampening_fraction() * 100)),
        round(MAX_FEEDBACK_DAMPENING * 100),
    ),
    "degree_saved_5": lambda: (max(0, min(5, round(region.temperature_saved()))), 5),
    "degree_saved_10": lambda: (max(0, min(10, round(region.temperature_saved()))), 10),
    "degree_saved_20": lambda: (max(0, min(20, round(region.temperature_saved()))), 20),
    "well_funded": lambda: (max(0, min(WELL_FUNDED_TARGET, round(region.funds))), WELL_FUNDED_TARGET),
    "long_haul": lambda: (min(region.round_number, LONG_HAUL_ROUND_TARGET), LONG_HAUL_ROUND_TARGET),
    # G-27: three more with a real numeric scale.
    "slow_burn": lambda: (
        0 if region.melt_started_round is None
        else max(0, min(SLOW_BURN_ROUNDS_AFTER_MELT, region.round_number - region.melt_started_round)),
        SLOW_BURN_ROUNDS_AFTER_MELT,
    ),
    "beat_both_regions": lambda: (min(region.round_number, BEAT_BOTH_REGIONS_MIN_ROUND), BEAT_BOTH_REGIONS_MIN_ROUND),
    "comparison_engaged": lambda: (
        (1 if sum(region_b.capacity.values()) >= 1 else 0) + (1 if sum(region_c.capacity.values()) >= 1 else 0),
        2,
    ),
}

# G-27 / G-31: what the progress number counts, so the remaining-amount line and the hover detail can
# say "12 more per cent of dampening" instead of a bare number. (singular unit, plural unit)
ACHIEVEMENT_UNITS = {
    "triple_threat": ("category left to invest in", "categories left to invest in"),
    "quarter_dampening": ("more per cent of dampening", "more per cent of dampening"),
    "half_dampening": ("more per cent of dampening", "more per cent of dampening"),
    "max_dampening": ("more per cent of dampening", "more per cent of dampening"),
    "degree_saved_5": ("more degree saved", "more degrees saved"),
    "degree_saved_10": ("more degree saved", "more degrees saved"),
    "degree_saved_20": ("more degree saved", "more degrees saved"),
    "well_funded": ("more fund", "more funds"),
    "long_haul": ("more round", "more rounds"),
    "slow_burn": ("more round of holding the loop down", "more rounds of holding the loop down"),
    "beat_both_regions": ("more round before the comparison counts", "more rounds before the comparison counts"),
    "comparison_engaged": ("region left to invest in", "regions left to invest in"),
}

# G-31: an arctic glyph per achievement, shown in place of the old trophy on earned cards and as a
# dimmed outline on locked ones. Plain emoji, no images.
ACHIEVEMENT_GLYPHS = {
    "first_output": "\U0001F3ED",
    "first_intervention": "\U0001F332",
    "triple_threat": "\u2744\uFE0F",
    "quarter_dampening": "\U0001F6E1\uFE0F",
    "half_dampening": "\U0001F6E1\uFE0F",
    "max_dampening": "\U0001F3F0",
    "tipping_point_witnessed": "\U0001F4A7",
    "early_investor": "\U0001F9CA",
    "degree_saved_5": "\U0001F321\uFE0F",
    "degree_saved_10": "\u2744\uFE0F",
    "degree_saved_20": "\U0001F3D4\uFE0F",
    "slow_burn": "\U0001F525",
    "well_funded": "\U0001F4B0",
    "long_haul": "\u23F3",
    "beat_both_regions": "\U0001F947",
    "comparison_engaged": "\u2696\uFE0F",
    "preset_strategist": "\U0001F39B\uFE0F",
    "worst_case_witnessed": "\U0001F480",
    "snow_leopard": "\U0001F406",
}
DEFAULT_ACHIEVEMENT_GLYPH = "\u2744\uFE0F"


def achievement_glyph(achievement_id):
    return ACHIEVEMENT_GLYPHS.get(achievement_id, DEFAULT_ACHIEVEMENT_GLYPH)


def achievement_remaining_text(achievement_id, progress):
    """G-27: "12 more per cent of dampening to go", or "" when there is no scale or it is met."""
    if progress is None:
        return ""
    current, target = progress
    left = max(0, target - current)
    if left <= 0:
        return ""
    singular, plural = ACHIEVEMENT_UNITS.get(achievement_id, ("more", "more"))
    return f"{left} {singular if left == 1 else plural} to go"


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


_flourished_achievements = set()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        # G-31: the unlock flourish plays once per card per page load, not on every re-render.
        if entry["earned"] and entry["id"] not in _flourished_achievements:
            _flourished_achievements.add(entry["id"])
            card.className += " achievement-card--new"
        card.dataset.achievementId = entry["id"]

        glyph = document.createElement("span")
        glyph.className = "achievement-card-glyph"
        glyph.innerText = achievement_glyph(entry["id"])
        glyph.setAttribute("aria-hidden", "true")
        card.appendChild(glyph)

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"Earned: {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            remaining = achievement_remaining_text(entry["id"], entry["progress"])
            progress.innerText = f"{current} of {target}" + (f" \u2014 {remaining}" if remaining else "")
            card.appendChild(progress)
            # G-27: a bar under the numbers (the numbers carry the meaning; the bar is a shape cue),
            # and the same detail on hover for the whole card.
            bar = document.createElement("div")
            bar.className = "achievement-card-bar"
            fill = document.createElement("div")
            fill.className = "achievement-card-bar-fill"
            fill.style.width = f"{min(100, max(0, current / target * 100)):.0f}%" if target else "0%"
            bar.appendChild(fill)
            card.appendChild(bar)
            card.title = f"{entry['label']}: {current} of {target}" + (f", {remaining}" if remaining else "")

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard
    # (ACHIEVEMENTS-SYSTEM-DESIGN.md §5), same convention as every other
    # game's reference retrofit. Relative path, no leading "/" (site-level
    # milestone 7's GitHub Pages subpath fix). The hub-side script.js
    # registration that makes Thaw's save data actually show up on that
    # dashboard is a root-file change, out of scope for this
    # games/thaw/-only dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())
    del _skin_announcements[:]


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest/preset/advance round/reveal worst-case region) — never from
    render() itself, since load_state() also calls render() and a loaded
    save with several achievements already earned must not flood the
    player with toasts for all of them at once."""
    earned_now = set(achievement_ids_earned())
    newly = earned_now - runstate._achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        suffix = skin_unlock_suffix()  # GG-18
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}{suffix}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels) + suffix)
    del _skin_announcements[:]
    runstate._achievements_seen_ids = earned_now


# ===========================================================================
# GG-18 / GG-14: map skins. The permafrost picture at the top of the page can wear one of four extra
# looks, each unlocked by a named achievement and kept for good on this device once unlocked (a
# collection, not a streak: nothing is lost if the run is restarted). Pure CSS keyed on
# #game[data-skin]; the chosen skin and the unlocked list live in localStorage, outside the save.
# ===========================================================================
SKINS = (  # (id, name, achievement that unlocks it; None = always available)
    ("default", "Default frost", None),
    ("aurora", "Aurora borealis", "half_dampening"),
    ("dusk", "Tundra at dusk", "long_haul"),
    ("pixel", "8-bit tundra", "well_funded"),
    ("leopard", "Snow Leopard station", "snow_leopard"),
)
SKIN_KEY = "thaw_skin_v1"
SKIN_UNLOCKS_KEY = "thaw_skin_unlocks_v1"

_skin_announcements = []


def _skin_entry(skin_id):
    for entry in SKINS:
        if entry[0] == skin_id:
            return entry
    return None


def _achievement_label(achievement_id):
    for entry in ACHIEVEMENTS:
        if entry["id"] == achievement_id:
            return entry["label"]
    return achievement_id


def skin_available(skin_id):
    entry = _skin_entry(skin_id)
    return entry is not None and (entry[2] is None or skin_id in runstate.skins_unlocked)


def load_skins():
    """Reads the stored choice and unlock list, forcing both into known values."""
    runstate.skins_unlocked = set()
    raw = _read_local_storage_item(SKIN_UNLOCKS_KEY)
    if raw:
        try:
            listed = json.loads(raw)
        except (ValueError, TypeError):
            listed = []
        if isinstance(listed, list):
            runstate.skins_unlocked = {i for i in listed if isinstance(i, str) and _skin_entry(i) and _skin_entry(i)[2]}
    choice = _read_local_storage_item(SKIN_KEY)
    runstate.current_skin = choice if isinstance(choice, str) and skin_available(choice) else "default"


def record_skin_unlocks():
    """Adds every skin whose achievement is currently earned to the stored list. Returns the ids that
    are new this time (for the unlock message)."""
    earned = set(achievement_ids_earned())
    fresh = [sid for sid, _name, ach in SKINS if ach and ach in earned and sid not in runstate.skins_unlocked]
    if fresh:
        runstate.skins_unlocked.update(fresh)
        _write_local_storage_item(SKIN_UNLOCKS_KEY, json.dumps(sorted(runstate.skins_unlocked)))
        _skin_announcements.extend(fresh)
    return fresh


def set_skin(skin_id):
    """Picks a skin; only an unlocked one can be chosen. Returns True when it took."""
    if not skin_available(skin_id):
        return False
    runstate.current_skin = skin_id
    _write_local_storage_item(SKIN_KEY, skin_id)
    return True


def skin_note_text():
    unlocked = sum(1 for sid, _n, _a in SKINS if skin_available(sid))
    locked = [(name, ach) for sid, name, ach in SKINS if not skin_available(sid)]
    text = f"{unlocked} of {len(SKINS)} map skins unlocked."
    if locked:
        text += " Locked: " + "; ".join(f"{name} (earn {_achievement_label(ach)})" for name, ach in locked) + "."
    else:
        text += " Every skin is yours."
    return text


def render_skins():
    select = document.getElementById("skin-select")
    options = ""
    for sid, name, ach in SKINS:
        if skin_available(sid):
            options += f'<option value="{sid}">{_escape(name)}</option>'
        else:
            options += f'<option value="{sid}" disabled>{_escape(name)} (locked: {_escape(_achievement_label(ach))})</option>'
    select.innerHTML = options
    select.value = runstate.current_skin
    document.getElementById("skin-note").innerText = skin_note_text()
    document.getElementById("game").setAttribute("data-skin", runstate.current_skin)


def skin_unlock_suffix():
    """Words added to the achievement toast when it also opened a skin; clears the pending list."""
    names = [_skin_entry(sid)[1] for sid in _skin_announcements if _skin_entry(sid)]
    del _skin_announcements[:]
    if not names:
        return ""
    return " \u2014 opens the " + " and ".join(names) + " map skin in Settings"
