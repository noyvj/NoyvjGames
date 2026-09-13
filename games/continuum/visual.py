"""Continuum — Phase 5's state -> visual data contract.

Pure Python, zero DOM code, zero knowledge that Three.js exists on the
other end of this. This module is the ONE seam between the already-tested
Python simulation (sim.py / sustainability.py) and the untested Three.js
rendering layer (render3d.js): `visual_state(state, effects)` reduces the
full CityState/effects picture down to a small, plain, JSON-serialisable
dict that a JS render loop can read after every render() without needing
to understand sim.py's internals at all.

Kept deliberately small and stable, per CLAUDE.md's own Phase 5 brief:
"Keep this data contract minimal and well-documented; it's the seam
between your two languages and needs to stay stable as the JS side gets
built out." Every value here is a plain int/float/str/bool/None/dict of
those — nothing here is ever a live Python object, the same JSON-safety
discipline save.py's get_state() already holds itself to (see save.py's
own module docstring).

This function is a pure function of (state, effects), exactly like every
function in sustainability.py — no mutation, no hidden history, safe to
call as often as the render loop likes (including mid-revisit, where it
correctly describes whatever era snapshot is currently loaded into
`state`, without needing to know revisiting is happening at all).
"""

import sim
import sustainability


def visual_state(state, effects):
    """One plain dict describing the settlement for the Three.js layer.

    Field-by-field:
      - era / era_index / era_label: which era's scene to draw. era_index
        is included so a future scene picker can do range checks
        ("industrial or later") without re-importing sim.ERA_ORDER on the
        JS side.
      - season, population, housing_capacity: settlement scale — the brief
        example this contract exists to satisfy ("hut count scales with
        population/shelter count").
      - buildings: counts for every building unlocked by this era or an
        earlier one (sim.buildings_for_era), keyed by the same building
        ids sim.py and the Build panel already use — a later era's scene
        can read `buildings["farmland"]`, `buildings["habitat_rings"]`,
        etc. without this module needing an era-specific branch for each.
      - land_health: 0..1, the same land-health fraction the 2D UI's meter
        already shows — useful for tinting a scene's ground/foliage.
      - pollution / sprawl: the two lagged 0..1 growth-side stocks
        Industrial (Milestone 11) and Digital (Milestone 12) introduced.
        Always present and always 0.0 before their era, since CityState
        initialises both fields unconditionally (see sim.py) — no era
        guard needed here, matching how the season loop itself is already
        guarded at the source.
      - habitat_layout_ratio / public_works_coverage_ratio: the two
        existing per-capita coverage ratios game.py's season narration
        already computes inline (see season_report_message()) for Space
        Age and Medieval+ respectively — None before their era (rather
        than 0.0) so a scene builder can tell "not applicable yet" apart
        from "applicable and currently zero coverage".
      - score / score_label / weakest_component: the sustainability
        headline, for a scene that wants to tint lighting/mood by how the
        settlement is actually doing, not just how big it is.
    """
    reading = sustainability.evaluate(state, effects)
    score_value = reading["score"]

    building_ids = sim.buildings_for_era(state.era)
    building_counts = {building: state.buildings[building] for building in building_ids}

    era_at_least = lambda era: sim.era_index(state.era) >= sim.era_index(era)  # noqa: E731

    habitat_layout_ratio = None
    if era_at_least("space") and state.population > 0:
        habitat_layout_ratio = min(1.0, state.habitat_capacity(effects) / state.population)

    public_works_coverage_ratio = None
    if era_at_least("medieval") and state.population > 0:
        public_works_coverage_ratio = min(
            1.0, state.public_works_coverage(effects) / state.population
        )

    return {
        "era": state.era,
        "era_index": sim.era_index(state.era),
        "era_label": sim.ERA_LABEL[state.era],
        "season": state.season,
        "population": state.population,
        "housing_capacity": state.housing_capacity(effects),
        "buildings": building_counts,
        "land_health": state.land_health,
        "pollution": state.pollution,
        "sprawl": state.sprawl,
        "habitat_layout_ratio": habitat_layout_ratio,
        "public_works_coverage_ratio": public_works_coverage_ratio,
        "score": score_value,
        "score_label": sustainability.score_label(score_value),
        "weakest_component": sustainability.weakest_component(state, effects),
    }
