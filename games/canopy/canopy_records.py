"""Personal best and the legacy bonus (both kept in localStorage, never in the save)."""

import json

from js import document, setTimeout
from pyodide.ffi import create_proxy

import canopy_runstate as runstate
from canopy_helpers import (
    PERSONAL_BEST_BADGE_MS, _read_local_storage_item, _write_local_storage_item, fmt_num,
)
from canopy_rules import lab_active
from canopy_valuation import layout_active, standing_forest_value


# B14 (planning/TODO.md "Per-game: Canopy"): a per-browser "personal
# best" for both of the game's own two axes (standing value, harvested
# income), persisted via localStorage. Deliberately NOT part of
# get_state()/the save-code system -- this tracks the best this *browser*
# has ever seen across every session/save on this device, not one save's
# snapshot, the same distinction B14's other quartet-game equivalents
# (Tide's D13, Thaw's G19) draw.
PERSONAL_BEST_STORAGE_KEY = "canopy_personal_best_v1"


def load_personal_best():
    """Reads the stored best (standing_value, income) pair, defaulting to
    zeros if nothing is stored yet, storage is unavailable, or the stored
    value is malformed (e.g. hand-edited or from a future incompatible
    format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"standing_value": 0.0, "income": 0.0}
    try:
        data = json.loads(raw)
        return {
            "standing_value": float(data.get("standing_value", 0.0)),
            "income": float(data.get("income", 0.0)),
        }
    except (ValueError, TypeError, AttributeError):
        return {"standing_value": 0.0, "income": 0.0}


personal_best = load_personal_best()

# Z6: one-shot-per-session guard so _maybe_update_personal_best() flashes
# the badge exactly once per axis per session, not on every tick after the
# stored best is first beaten -- see that function's docstring.
_personal_best_flashed = {"standing_value": False, "income": False}

# B15 (planning/TODO.md "Per-game: Canopy"): "legacy forest" -- a fresh
# session starts with a small permanent economic-growth bonus based on
# the standing forest value the *previous* session ended with, banked to
# localStorage the moment reset_session() wipes state for a new one --
# same per-browser pattern as personal_best above. A first-ever session
# has nothing banked yet, so it starts at the neutral 1.0 multiplier
# (this is what makes it "opt-in" in practice: nothing changes until a
# real session has actually ended once). Built independently of any
# shared cross-game meta-progression module, per planning/TODO.md's Z3
# resolution ("better to let each game build its own").
LEGACY_STORAGE_KEY = "canopy_legacy_forest_v1"
LEGACY_BONUS_PER_BANKED_VALUE = 0.0002  # +0.02% growth per 1 banked value point
LEGACY_MAX_BONUS = 0.25  # capped so legacy can never dwarf the base game


def _read_banked_legacy_value():
    """The banked standing value from the previous session (0.0 when nothing is banked, storage is
    unavailable or the stored value is malformed)."""
    raw = _read_local_storage_item(LEGACY_STORAGE_KEY)
    banked = 0.0
    if raw:
        try:
            banked = max(0.0, float(json.loads(raw).get("banked_value", 0.0)))
        except (ValueError, TypeError, AttributeError):
            banked = 0.0
    return banked


def legacy_bonus_for(banked):
    """The growth multiplier a banked standing value earns (1.0 means no bonus), capped at LEGACY_MAX_BONUS."""
    return 1.0 + min(LEGACY_MAX_BONUS, max(0.0, banked) * LEGACY_BONUS_PER_BANKED_VALUE)


def load_legacy_bonus():
    """Reads the banked standing value from the previous session and
    converts it into a growth multiplier, defaulting to 1.0 (no bonus) if
    nothing is banked yet, storage is unavailable, or the stored value is
    malformed."""
    return legacy_bonus_for(_read_banked_legacy_value())


def legacy_chip_text():
    """B-2: the chip's short label."""
    if runstate.legacy_multiplier <= 1.0:
        return "Legacy: none yet"
    return f"Legacy +{(runstate.legacy_multiplier - 1) * 100:.0f}% from your last forest"


def legacy_chip_tooltip():
    """B-2: what the bonus comes from and how close it is to the cap."""
    cap_pct = LEGACY_MAX_BONUS * 100
    if runstate.legacy_multiplier <= 1.0:
        return (
            "Legacy bonus: none yet. When a session ends, its final standing forest value is banked, and the next "
            f"session grows faster by 0.02% for every banked point, up to +{cap_pct:.0f}%."
        )
    bonus_pct = (runstate.legacy_multiplier - 1) * 100
    banked = _read_banked_legacy_value()
    share = min(100.0, bonus_pct / cap_pct * 100)
    return (
        f"Legacy bonus: +{bonus_pct:.1f}% growth, from the {banked:.0f} standing forest value your last session ended "
        f"with (0.02% per point). The cap is +{cap_pct:.0f}%; you are at {share:.0f}% of it."
        + (" The cap is reached, so extra standing value no longer adds growth." if bonus_pct >= cap_pct - 1e-9 else "")
    )


def _bank_legacy_value():
    """Called from reset_session() just before state is wiped -- banks
    this session's final standing value for the *next* session's legacy
    bonus. Replaces whatever was banked before (this session's own most
    recent result, not a lifetime max, matching B15's own "based on a
    previous session's final standing value" wording)."""
    if lab_active():  # B-5: a sandbox forest leaves the stored legacy value alone
        return
    _write_local_storage_item(
        LEGACY_STORAGE_KEY, json.dumps({"banked_value": standing_forest_value()})
    )


runstate.legacy_multiplier = load_legacy_bonus()


def render_legacy_bonus():
    element = document.getElementById("legacy-bonus-display")
    if element is None:
        return
    element.innerText = legacy_chip_text()
    tooltip = legacy_chip_tooltip()
    element.title = tooltip
    element.setAttribute("aria-label", tooltip)


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it on either axis. Two independent bests, not
    one combined score -- income vs. standing value is the game's own
    central two-axis comparison, and collapsing them into one number
    would lose exactly the distinction the rest of the game is built
    around.

    Both axes climb every tick during ordinary preserved-plot accrual, so
    once a session has beaten a stored best it would otherwise keep
    re-beating its own just-bumped record on every following tick --
    the flash would spam constantly instead of marking one felt moment.
    `_personal_best_flashed` makes each axis's flash fire at most once per
    session (still comparing against the true stored best, so a session
    that beats it on both axes in the same tick still only flashes once)."""
    if lab_active() or layout_active():  # B-5, B-29: sandbox and custom-shape forests never set the standard personal best
        return
    standing_value = standing_forest_value()
    persist = False
    flash = False
    if standing_value > personal_best["standing_value"]:
        personal_best["standing_value"] = standing_value
        persist = True
        if not _personal_best_flashed["standing_value"]:
            _personal_best_flashed["standing_value"] = True
            flash = True
    if runstate.total_income > personal_best["income"]:
        personal_best["income"] = runstate.total_income
        persist = True
        if not _personal_best_flashed["income"]:
            _personal_best_flashed["income"] = True
            flash = True
    if persist:
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
    if flash:
        _flash_personal_best_badge()


def _flash_personal_best_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a session beats its stored best,
    then removes it after PERSONAL_BEST_BADGE_MS -- the actual "badge"
    moment, distinct from render_personal_best()'s always-on label text.
    Same setTimeout+create_proxy shape as the achievement toast below."""
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("personal-best-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), PERSONAL_BEST_BADGE_MS)


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.innerText = (
        f"Personal best: standing {fmt_num(personal_best['standing_value'])} "
        f"· income {fmt_num(personal_best['income'])}"
    )
