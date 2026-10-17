"""load_state() and _apply_state(): putting a saved game back, then redrawing.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import herd_runstate as runstate
from herd_rules import (
    DECOUPLING_MEASURES, POULTRY_MEASURES, SATELLITE_MAX_RETROFITS, SATELLITE_MAX_SIZE,
    SUPPLY_CHAIN_MAX_UNITS,
)
from herd_util import _safe_int
from herd_achievements import _seed_achievement_toast_baseline
from herd_sandbox import _sandbox_notify_page, _sandbox_restore_real
from herd_rules_ui import _load_rules_from_save
from herd_succession import LEGACY_PERKS
from herd_collection import _sync_collection
from herd_savegame import (
    _load_policy_fields, _load_progress_fields, _offer_recovery, check_save, get_state, render_save_recovery,
)
from herd_renderer import render


def load_state(data):
    """Validates first, so a broken save never leaves the farm half-loaded. A problem save raises
    ValueError (the save widget then says "Load failed") after the recovery panel explains why.
    If something unforeseen goes wrong while applying a save that passed the checks, the farm is put
    back exactly as it was and the same panel is shown."""
    problems = check_save(data)
    if problems:
        _offer_recovery(data, problems)
        if not isinstance(data, dict):
            return False
        raise ValueError("Save not loaded: " + " ".join(reason for _key, reason in problems[:3]))
    if runstate.sandbox_active:  # GF-24: loading a save always lands in the real game
        _sandbox_restore_real()
    backup = get_state()
    try:
        result = _apply_state(data)
    except Exception:
        _apply_state(backup)
        _offer_recovery(None, [("", "Something in this save could not be read, so it was not loaded.")])
        raise
    if runstate.pending_recovery is not None:
        runstate.pending_recovery = None
        render_save_recovery()
    _sandbox_notify_page()
    return result


def _apply_state(data):
    # Every top-level field uses a .get() fallback (to the farm's current
    # live value) rather than bare data["key"] indexing -- a save missing
    # any single field (an older save predating that field, e.g. one from
    # before the Pass 2 plant-based pivot added plant_pivot_investment to
    # the state dict, or a hand-edited/corrupted payload) must not crash
    # load_state() outright and abort every field after the missing one,
    # the same bare-indexing bug already fixed in Tide's load_state() --
    # see BCM114-DEV-LOG.md 2026-09-02.
    _load_rules_from_save(data)
    runstate.farm.round_number = data.get("round_number", runstate.farm.round_number)
    runstate.farm.funds = data.get("funds", runstate.farm.funds)
    runstate.farm.herd_size = data.get("herd_size", runstate.farm.herd_size)
    runstate.farm.methane = data.get("methane", runstate.farm.methane)
    # Merge key-by-key rather than replacing the dict outright: a save
    # missing a measure (an older save format from before that measure
    # existed, or a hand-edited/corrupted payload) must not wipe that
    # measure's key out of the live dict entirely -- render() and
    # _efficiency_coupling_ratio() both do decoupling_investment[measure]
    # for every measure in DECOUPLING_MEASURES unconditionally, so a
    # missing key would crash the game on the very next render/round.
    runstate.farm.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}
    saved_decoupling_investment = data.get("decoupling_investment")
    if isinstance(saved_decoupling_investment, dict):
        runstate.farm.decoupling_investment.update(saved_decoupling_investment)
    runstate.farm.plant_pivot_investment = data.get("plant_pivot_investment", runstate.farm.plant_pivot_investment)
    runstate.farm.counterfactual_funds = data.get("counterfactual_funds", runstate.farm.counterfactual_funds)
    runstate.farm.counterfactual_methane = data.get("counterfactual_methane", runstate.farm.counterfactual_methane)
    saved_methane_history = data.get("methane_history")
    if isinstance(saved_methane_history, list) and saved_methane_history:
        runstate.farm.methane_history = list(saved_methane_history)
    runstate.farm.max_pressure_fraction_seen = data.get(
        "max_pressure_fraction_seen", runstate.farm.max_pressure_fraction_seen
    )
    runstate.farm.seen_half_decoupled_callout = data.get(
        "seen_half_decoupled_callout", runstate.farm.seen_half_decoupled_callout
    )
    runstate.farm.seen_pressure_callout = data.get("seen_pressure_callout", runstate.farm.seen_pressure_callout)
    runstate.farm.seen_methane_penalty_nudge = data.get(
        "seen_methane_penalty_nudge", runstate.farm.seen_methane_penalty_nudge
    )
    runstate.farm.certification_streak = data.get("certification_streak", 0)
    runstate.farm.certified = bool(data.get("certified", False))
    # F25: succession state, validated (ints only; perk names must exist and
    # levels are clamped to each perk's own maximum).
    runstate.generation = max(1, _safe_int(data.get("generation"), 1))
    runstate.legacy_points = _safe_int(data.get("legacy_points"), 0)
    runstate.legacy_perks = {}
    saved_perks = data.get("legacy_perks")
    if isinstance(saved_perks, dict):
        for name, spec in LEGACY_PERKS.items():
            level = min(spec["max"], _safe_int(saved_perks.get(name), 0))
            if level > 0:
                runstate.legacy_perks[name] = level
    # Round-3 fields: every one validated and defaulted (older saves lack them).
    runstate.farm.poultry_size = _safe_int(data.get("poultry_size"), 0)
    runstate.farm.poultry_investment = {m: 0 for m in POULTRY_MEASURES}
    saved_poultry = data.get("poultry_investment")
    if isinstance(saved_poultry, dict):
        for m in POULTRY_MEASURES:
            runstate.farm.poultry_investment[m] = _safe_int(saved_poultry.get(m), 0)
    runstate.farm.satellite_open = data.get("satellite_open") is True
    runstate.farm.satellite_size = min(SATELLITE_MAX_SIZE, _safe_int(data.get("satellite_size"), 0)) if runstate.farm.satellite_open else 0
    runstate.farm.satellite_retrofits = (
        min(SATELLITE_MAX_RETROFITS, _safe_int(data.get("satellite_retrofits"), 0)) if runstate.farm.satellite_open else 0
    )
    runstate.farm.genetics_active = _safe_int(data.get("genetics_active"), 0)
    pending = data.get("genetics_pending")
    runstate.farm.genetics_pending = (
        [_safe_int(r, 1) for r in pending if isinstance(r, (int, float)) and not isinstance(r, bool)]
        if isinstance(pending, list) else []
    )
    runstate.farm.supply_chain_investment = min(SUPPLY_CHAIN_MAX_UNITS, _safe_int(data.get("supply_chain_investment"), 0))
    _load_progress_fields(data)
    runstate.farm.variation_enabled = data.get("variation_enabled") is True
    runstate.farm.regional_cap_enabled = data.get("regional_cap_enabled") is True
    runstate.farm.policy_offer_pending = data.get("policy_offer_pending") is True
    runstate.farm.subsidy_rounds_left = _safe_int(data.get("subsidy_rounds_left"), 0)
    _load_policy_fields(data)
    # achievements_earned is deliberately never read back here -- it's a
    # write-only projection recomputed fresh by get_state() every save,
    # per ACHIEVEMENTS-SYSTEM-DESIGN.md.
    _sync_collection(award=False)  # a load records what the farm qualifies for but never pays
    render()
    _seed_achievement_toast_baseline()
    return True
