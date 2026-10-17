"""The small multipliers that feed a plot's growth, recovery and payout: carbon slump, legacy bonus, weather, perfect streak, clear-cut dip, Seed Vault perks and Expedition perks (with their trees)."""

import skill_tree

import canopy_runstate as runstate
from canopy_rules import (
    CARBON_SLUMP_MULTIPLIER, CLEAR_CUT_DIP, CLEAR_CUT_HEAL_TICKS, DEGRADE_PER_CLEAR,
    DEGRADE_PER_CLEAR_BY_DIFFICULTY, carbon, lab,
)
from canopy_weather import weather_multiplier_at
from canopy_worldvars import (
    CHALLENGE_NONE, PERFECT_STREAK_BONUS_PER_SEASON, PERFECT_STREAK_MAX_BONUS_SEASONS, TEND_COOLDOWN_TICKS,
)


def current_degrade_per_clear():
    return DEGRADE_PER_CLEAR_BY_DIFFICULTY.get(runstate.current_difficulty, DEGRADE_PER_CLEAR) * vault_soil_factor() * expedition_soil_factor() * lab["soil"]  # GB-10: Soil perks; GB-3: Expedition soil upgrade; B-5: Forest Lab


def carbon_slump_multiplier():
    return CARBON_SLUMP_MULTIPLIER if carbon["slump"] > 0 else 1.0


def current_legacy_multiplier():
    return runstate.legacy_multiplier


def current_weather_multiplier():
    return weather_multiplier_at(runstate.forest_tick)


def current_perfect_streak_multiplier():
    return 1.0 + PERFECT_STREAK_BONUS_PER_SEASON * min(runstate.perfect_streak, PERFECT_STREAK_MAX_BONUS_SEASONS)


def clear_cut_dip_fraction(plot):
    """How many points of growth the plot's soil is down from its clear-cut right now (0 when none)."""
    ticks = getattr(plot, "soil_dip_ticks", 0)
    if ticks <= 0:
        return 0.0
    return CLEAR_CUT_DIP * min(ticks, CLEAR_CUT_HEAL_TICKS) / CLEAR_CUT_HEAL_TICKS


VAULT_GROWTH_BONUS = {"growth_1": 0.03, "growth_2": 0.04, "growth_3": 0.05}
VAULT_SOIL_FACTOR = 0.9  # each soil perk multiplies the soil lost per clear by this
VAULT_RECOVERY_TICKS_SAVED = 2
VAULT_TREE = {
    "id": "seed_vault",
    "title": "Seed Vault",
    "currency": "seed points",
    "branches": [
        {"id": "roots", "title": "Roots", "blurb": "Standing plots grow faster."},
        {"id": "soil", "title": "Soil", "blurb": "Clearing hurts less and replanted plots heal sooner."},
        {"id": "crews", "title": "Ranger crews", "blurb": "Idle crews do small jobs for you as the forest runs."},
    ],
    "nodes": [
        {"id": "deep_roots", "branch": "roots", "cost": 1, "label": "Deep Roots",
         "description": "Standing plots grow 3% faster.", "effect": "growth_1"},
        {"id": "canopy_cover", "branch": "roots", "cost": 2, "label": "Canopy Cover",
         "description": "Another 4% faster growth.", "requires": ["deep_roots"], "effect": "growth_2"},
        {"id": "old_growth_memory", "branch": "roots", "cost": 3, "label": "Old-Growth Memory",
         "description": "Another 5% faster growth.", "requires": ["canopy_cover"], "effect": "growth_3"},
        {"id": "mulch_bed", "branch": "soil", "cost": 1, "label": "Mulch Bed",
         "description": "Each clear costs a plot's soil 10% less.", "effect": "soil_1"},
        {"id": "leaf_litter", "branch": "soil", "cost": 2, "label": "Leaf Litter",
         "description": "Another 10% less soil lost per clear.", "requires": ["mulch_bed"], "effect": "soil_2"},
        {"id": "fast_sprouts", "branch": "soil", "cost": 2, "label": "Fast Sprouts",
         "description": "Replanted plots recover 2 ticks sooner.", "requires": ["mulch_bed"], "effect": "recovery_1"},
        {"id": "tending_crew", "branch": "crews", "cost": 2, "label": "Tending Crew",
         "description": "When Tend has been ready for 3 ticks, a crew tends your youngest plot for you.", "effect": "crew_tend"},
        {"id": "seedling_watch", "branch": "crews", "cost": 3, "label": "Seedling Watch",
         "description": "A crew catches a golden seedling in its last tick if you have not.", "effect": "crew_seedling"},
        {"id": "replant_crew", "branch": "crews", "cost": 3, "label": "Replant Crew",
         "description": "Every 20 ticks a crew replants the first bare plot.", "requires": ["tending_crew"], "effect": "crew_replant"},
        {"id": "crew_lead", "branch": "crews", "cost": 4, "label": "Crew Lead",
         "description": "The replant crew works every 12 ticks instead of 20.",
         "requires": ["tending_crew", "replant_crew"], "effect": "crew_lead"},
    ],
}

vault_owned = []

_vault_effect_cache = {}


def vault_perks_active():
    """Perks and crews rest during a challenge run so those stay comparable."""
    return runstate.current_challenge == CHALLENGE_NONE and runstate.current_expedition is None  # GB-3: an Expedition has its own tree


def vault_effects():
    if not vault_perks_active() or not vault_owned:
        return frozenset()
    key = tuple(vault_owned)
    cached = _vault_effect_cache.get(key)
    if cached is None:
        cached = frozenset(skill_tree.effects(VAULT_TREE, vault_owned))
        _vault_effect_cache.clear()
        _vault_effect_cache[key] = cached
    return cached


def vault_growth_multiplier():
    effects = vault_effects()
    return 1.0 + sum(bonus for effect, bonus in VAULT_GROWTH_BONUS.items() if effect in effects)


def vault_soil_factor():
    effects = vault_effects()
    return VAULT_SOIL_FACTOR ** sum(1 for effect in ("soil_1", "soil_2") if effect in effects)


def vault_recovery_ticks_saved():
    return VAULT_RECOVERY_TICKS_SAVED if "recovery_1" in vault_effects() else 0


EXPEDITION_RICH_GROWTH = 1.25
EXPEDITION_THIN_GROWTH = 0.80
EXPEDITION_GROWTH_BONUS = {"exp_growth_1": 0.06, "exp_growth_2": 0.08, "exp_growth_3": 0.10}
EXPEDITION_SOIL_FACTOR = 0.75  # soil lost per clear
EXPEDITION_NURSERY_TICKS_SAVED = 3

EXPEDITION_TEND_COOLDOWN = 10

EXPEDITION_TREE = {
    "id": "expedition",
    "title": "Expedition upgrades",
    "currency": "upgrade points",
    "branches": [
        {"id": "growth", "title": "Growth", "blurb": "Standing plots grow faster."},
        {"id": "soil", "title": "Soil and recovery", "blurb": "Clearing hurts less, replanting is quicker, clear-cuts heal sooner."},
        {"id": "trade", "title": "Trade and tending", "blurb": "Harvest for more, tend more often."},
    ],
    "nodes": [
        {"id": "sun_terraces", "branch": "growth", "cost": 1, "label": "Sun Terraces",
         "description": "Standing plots grow 6% faster.", "effect": "exp_growth_1"},
        {"id": "mycelium_net", "branch": "growth", "cost": 2, "label": "Mycelium Net",
         "description": "Another 8% faster growth.", "requires": ["sun_terraces"], "effect": "exp_growth_2"},
        {"id": "old_roots", "branch": "growth", "cost": 3, "label": "Old Roots",
         "description": "Another 10% faster growth.", "requires": ["mycelium_net"], "effect": "exp_growth_3"},
        {"id": "terraced_soil", "branch": "soil", "cost": 1, "label": "Terraced Soil",
         "description": "Each clear costs a plot's soil 25% less.", "effect": "exp_soil"},
        {"id": "quick_nursery", "branch": "soil", "cost": 2, "label": "Quick Nursery",
         "description": "Replanted plots recover 3 ticks sooner.", "requires": ["terraced_soil"], "effect": "exp_nursery"},
        {"id": "soil_salve", "branch": "soil", "cost": 2, "label": "Soil Salve",
         "description": "The soil dip left by a clear-cut heals twice as fast.", "requires": ["terraced_soil"], "effect": "exp_salve"},
        {"id": "trade_route", "branch": "trade", "cost": 2, "label": "Trade Route",
         "description": "Clears and clear-cuts you make pay 15% more.", "effect": "exp_trade"},
        {"id": "tend_rhythm", "branch": "trade", "cost": 2, "label": "Tend Rhythm",
         "description": "Tend is ready again after 10 ticks instead of 20.", "effect": "exp_tend"},
    ],
}

expedition_terrain = {}  # plot index -> "rich" | "thin" (main forest, derived from the seed, never saved)

_expedition_effect_cache = {}


def expedition_effects():
    if runstate.current_expedition is None or not runstate.current_expedition["owned"]:
        return frozenset()
    key = tuple(runstate.current_expedition["owned"])
    cached = _expedition_effect_cache.get(key)
    if cached is None:
        cached = frozenset(skill_tree.effects(EXPEDITION_TREE, runstate.current_expedition["owned"]))
        _expedition_effect_cache.clear()
        _expedition_effect_cache[key] = cached
    return cached


def expedition_growth_multiplier(plot):
    """Terrain (main forest only) times the Growth upgrades; exactly 1.0 outside an Expedition."""
    if runstate.current_expedition is None:
        return 1.0
    effects = expedition_effects()
    multiplier = 1.0 + sum(bonus for effect, bonus in EXPEDITION_GROWTH_BONUS.items() if effect in effects)
    if plot.region == "main":
        kind = expedition_terrain.get(plot.index)
        if kind == "rich":
            multiplier *= EXPEDITION_RICH_GROWTH
        elif kind == "thin":
            multiplier *= EXPEDITION_THIN_GROWTH
    return multiplier


def expedition_soil_factor():
    return EXPEDITION_SOIL_FACTOR if "exp_soil" in expedition_effects() else 1.0


def expedition_recovery_ticks_saved():
    return EXPEDITION_NURSERY_TICKS_SAVED if "exp_nursery" in expedition_effects() else 0


def expedition_extra_heal():
    return 1 if "exp_salve" in expedition_effects() else 0


def expedition_tend_cooldown():
    return EXPEDITION_TEND_COOLDOWN if "exp_tend" in expedition_effects() else TEND_COOLDOWN_TICKS
