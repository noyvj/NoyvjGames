"""The Plot class (one forest plot: state, value, growth, degradation) and the plot grids built from it."""

import canopy_runstate as runstate
from canopy_clearcut import CLEAR_CUT_BONUS
from canopy_effects import (
    carbon_slump_multiplier, clear_cut_dip_fraction, current_degrade_per_clear, current_legacy_multiplier,
    current_perfect_streak_multiplier, current_weather_multiplier, expedition_growth_multiplier,
    expedition_recovery_ticks_saved, vault_growth_multiplier, vault_recovery_ticks_saved,
)
from canopy_rules import (
    ACCRUING_STATES, BARE, BASE_ACCRUAL, BIODIVERSITY_ACCRUAL_PER_TICK, BIODIVERSITY_WILDLIFE_THRESHOLD,
    CLEAR_CUT_HEAL_TICKS, MATURITY_TICKS, MIN_PRODUCTIVITY_MULTIPLIER, PARTNER_RECOVERY_TICKS,
    PARTNER_SHARE_RATIO, PRESERVED, RECOVERED, RECOVERY_TICKS, REPLANTING,
    SPECIALIST_BIODIVERSITY_MULTIPLIER, SPECIALIST_ECONOMIC_VALUE_MULTIPLIER, SPECIALIST_MIN_TICKS_INTACT,
    SPECIALIZATION_BIODIVERSITY, SPECIALIZATION_ECONOMIC, SPECIES, SPECIES_STANDARD, SYNERGY_REPLANT_FACTOR,
    VALID_ACTIONS, VETERAN_REQUESTS_SURVIVED, current_season_multiplier, growth_per_tick,
    mature_neighbour_count, species_recovery_ticks, synergy_multiplier,
)
from canopy_worldvars import (
    HIGHLAND_COLS, HIGHLAND_DEGRADE_MULTIPLIER, HIGHLAND_GROWTH_MULTIPLIER, HIGHLAND_ROWS,
    TEND_GROWTH_MULTIPLIER, WETLAND_COLS, WETLAND_GROWTH_MULTIPLIER, WETLAND_ROWS, rival_claims,
)


class Plot:
    def __init__(self, index, region="main"):
        self.species = None  # GB-6: None means the standard seedling
        self.replant_ticks_total = RECOVERY_TICKS
        self.blocked = False  # B-29: a cell a custom layout leaves out (open ground: no plot, never counted)
        self.index = index
        # V-CD-5 (planning/TODO.md section N): which grid this plot belongs
        # to -- "main" (the default) or "highland". Structural, not saved
        # state: it's fixed for a plot's whole lifetime by which list it was
        # constructed into (see highland_plots' construction sites), so
        # _plot_to_dict()/_apply_plot_dict() never need to persist it --
        # reconstructing highland_plots always passes region="highland"
        # again. Drives productivity_multiplier()/accrue_tick()'s region-
        # specific rate multipliers below.
        self.region = region
        self.state = PRESERVED
        self.value = 0.0
        self.ticks_intact = 0
        self.clear_count = 0
        self.replant_ticks_remaining = 0
        self.just_recovered = False
        self.biodiversity = 0.0
        # B4: True once this plot has ever hit "fully mature" (so the leaf
        # burst celebrates that moment exactly once per plot, ever).
        self.mature_celebrated = False
        # B22: how many clear-requests aimed at this plot the player has
        # declined. A plot with 3+ of these and no clears is a "veteran".
        self.requests_survived = 0
        # B21: one-time permanent specialization (None until chosen).
        self.specialization = None
        # B11: 0.0 normally; PARTNER_SHARE_RATIO while this planting was
        # done with a reforestation partner (cleared back to 0.0 on the
        # next clear() -- see that method).
        self.partner_share = 0.0
        # GB-4: ticks of Tend growth boost left (0 = not tended). Only one
        # plot is tended at a time; saved as the top-level "tend" key, never
        # per plot, so the plot dict shape stays unchanged.
        self.tend_ticks_left = 0
        # GB-21: ticks left of the clear-cut soil dip (0 = none). Healing, not permanent: see CLEAR_CUT_* below.
        self.soil_dip_ticks = 0

    def can_specialize(self):
        return (
            self.state in ACCRUING_STATES
            and self.specialization is None
            and self.ticks_intact >= SPECIALIST_MIN_TICKS_INTACT
        )

    def is_veteran(self):
        return self.requests_survived >= VETERAN_REQUESTS_SURVIVED and self.clear_count == 0

    def productivity_multiplier(self):
        """Soil quality factor from past clearing — 1.0 for a never-cleared
        plot, stepping down permanently with each clear, floored so a plot
        never stops producing entirely.

        V-CD-5: a Highland Grove plot's soil degrades HIGHLAND_DEGRADE_
        MULTIPLIER times faster per clear than the main forest's (thin,
        fragile alpine soil erodes faster once disturbed) — main-forest
        plots (region == "main") are completely untouched by this, since
        the multiplier is exactly 1.0 for them."""
        region_degrade_multiplier = HIGHLAND_DEGRADE_MULTIPLIER if self.region == "highland" else 1.0
        # B1: Wetland Forest keeps the main forest's soil rate (its tension
        # is flooding, not erosion) -- so it multiplies by 1.0 here.
        return max(
            MIN_PRODUCTIVITY_MULTIPLIER,
            1 - current_degrade_per_clear() * region_degrade_multiplier * self.clear_count - clear_cut_dip_fraction(self),  # GB-21
        )

    def accrue_tick(self):
        """Advances one tick of passive value growth. No-op outside
        PRESERVED/RECOVERED — bare and replanting plots hold no standing
        value to grow. Returns the value actually added this tick (0.0 on
        the no-op path) so callers (B17's floating "+X" pop) can react to
        a real increase without re-deriving it from before/after value."""
        if self.state not in ACCRUING_STATES:
            return 0.0
        self.ticks_intact += 1
        spec = SPECIES.get(self.species or SPECIES_STANDARD, SPECIES[SPECIES_STANDARD])  # GB-6
        compounding = self.ticks_intact if spec["steady_after"] is None else min(self.ticks_intact, spec["steady_after"])
        growth_multiplier = 1 + compounding * growth_per_tick()  # B-5
        delta = BASE_ACCRUAL * self.productivity_multiplier() * growth_multiplier * spec["value"] * runstate._mixed_bonus * synergy_multiplier(self)  # GB-5
        # V-CD-5: Highland Grove compounds HIGHLAND_GROWTH_MULTIPLIER times
        # slower than the main forest (a harsher, shorter high-altitude
        # growing season) — 1.0 (a no-op) for main-forest plots.
        if self.region == "highland":
            delta *= HIGHLAND_GROWTH_MULTIPLIER
        elif self.region == "wetland":  # B1: lush, fast-growing, but floods
            delta *= WETLAND_GROWTH_MULTIPLIER
        delta *= current_season_multiplier()  # B17
        delta *= current_legacy_multiplier()  # B15
        delta *= current_weather_multiplier()  # GB-23: rain / drought episodes
        delta *= current_perfect_streak_multiplier()  # GB-30: Perfect Season flame
        delta *= carbon_slump_multiplier()  # GB-29: the dip after selling credits
        delta *= vault_growth_multiplier()  # GB-10: Seed Vault Roots perks (1.0 with none)
        delta *= expedition_growth_multiplier(self)  # GB-3: the Expedition's map terrain and Growth upgrades (1.0 outside one)
        if self.tend_ticks_left > 0:  # GB-4: a Tended plot grows faster for a few ticks
            delta *= TEND_GROWTH_MULTIPLIER
        if self.specialization == SPECIALIZATION_ECONOMIC:
            delta *= SPECIALIST_ECONOMIC_VALUE_MULTIPLIER
        if self.partner_share:  # B11: partner's cut comes off the top, permanently
            delta *= 1 - self.partner_share
        self.value += delta
        biodiversity_gain = BIODIVERSITY_ACCRUAL_PER_TICK * spec["bio"]
        if self.specialization == SPECIALIZATION_BIODIVERSITY:
            biodiversity_gain *= SPECIALIST_BIODIVERSITY_MULTIPLIER
        self.biodiversity += biodiversity_gain
        return delta

    def has_wildlife(self):
        return self.biodiversity >= BIODIVERSITY_WILDLIFE_THRESHOLD

    def clear(self):
        """Harvests this plot's standing value and returns it as a payout
        (None if clearing isn't valid from the current state). Clearing
        also permanently degrades the plot's future productivity."""
        if self.blocked or "clear" not in VALID_ACTIONS[self.state]:
            return None
        payout = self.value
        self.clear_count += 1
        self.state = BARE
        self.value = 0.0
        self.ticks_intact = 0
        self.biodiversity = 0.0
        self.specialization = None
        self.partner_share = 0.0  # B11: a partnership is only good for one planting
        self.tend_ticks_left = 0  # GB-4: a cleared plot is no longer being tended
        self.species = None  # GB-6: the next planting chooses afresh
        return payout

    def clear_cut(self):
        """GB-21: a clear that pays CLEAR_CUT_BONUS more now and leaves a soil dip that heals over
        CLEAR_CUT_HEAL_TICKS (about three seasons). No dice. Counts as a clear for every purpose (soil
        degradation, the playstyle badge, contracts). Returns the payout, or None if clearing is not valid."""
        payout = self.clear()
        if payout is None:
            return None
        self.soil_dip_ticks = CLEAR_CUT_HEAL_TICKS
        return payout * (1 + CLEAR_CUT_BONUS)

    def blight(self):
        """GB-7: killed back to bare by blight. Unlike clear() nothing is harvested and the soil is not harmed."""
        if self.state not in ACCRUING_STATES:
            return False
        self.state = BARE
        self.value = 0.0
        self.ticks_intact = 0
        self.biodiversity = 0.0
        self.specialization = None
        self.partner_share = 0.0
        self.tend_ticks_left = 0
        self.species = None
        return True

    def replant(self, partner=False, species=None):
        """B11: `partner=True` uses a reforestation partner instead of a
        plain replant -- recovers in PARTNER_RECOVERY_TICKS (half the
        normal wait) but this planting's future economic value permanently
        shares PARTNER_SHARE_RATIO with the partner until the plot is next
        cleared."""
        if self.blocked or "replant" not in VALID_ACTIONS[self.state]:
            return False
        if self.region == "main" and self.index in rival_claims:  # GB-12: a mining claim cannot be planted
            return False
        self.state = REPLANTING
        base_ticks = PARTNER_RECOVERY_TICKS if partner else max(1, RECOVERY_TICKS - vault_recovery_ticks_saved() - expedition_recovery_ticks_saved())  # GB-10: Fast Sprouts; GB-3: Nursery
        self.species = species if species in SPECIES and species != SPECIES_STANDARD else None  # GB-6
        if self.region == "main" and mature_neighbour_count(self):  # GB-5: a mature neighbour shelters the seedling
            base_ticks = max(1, int(round(base_ticks * SYNERGY_REPLANT_FACTOR)))
        self.replant_ticks_remaining = species_recovery_ticks(self.species or SPECIES_STANDARD, base_ticks)
        self.replant_ticks_total = max(RECOVERY_TICKS, self.replant_ticks_remaining)
        self.partner_share = PARTNER_SHARE_RATIO if partner else 0.0
        return True

    def finish_recovery(self):
        """Transitions a REPLANTING plot to RECOVERED."""
        if self.state != REPLANTING:
            return False
        self.state = RECOVERED
        self.replant_ticks_remaining = 0
        self.just_recovered = True
        return True

    def maturity_fraction(self):
        """0..1 — how far this plot is toward "mature" for gradient
        purposes: ticks-intact progress for standing plots, recovery
        countdown progress for replanting ones, zero for bare."""
        if self.state in ACCRUING_STATES:
            return min(1.0, self.ticks_intact / MATURITY_TICKS)
        if self.state == REPLANTING:
            return 1 - (self.replant_ticks_remaining / max(1, self.replant_ticks_total))
        return 0.0

    def advance_recovery(self):
        """Counts down one tick of the replanting timer, auto-completing
        recovery once it reaches zero. No-op outside REPLANTING. Returns
        True exactly when this call caused a REPLANTING -> RECOVERED
        transition, so callers (achievements' `total_recoveries` counter)
        can react to the real event without polling state every tick."""
        if self.state != REPLANTING:
            return False
        self.replant_ticks_remaining -= 1
        if self.replant_ticks_remaining <= 0:
            return self.finish_recovery()
        return False


runstate.plots = [Plot(i) for i in range(runstate.GRID_ROWS * runstate.GRID_COLS)]

runstate.highland_plots = [Plot(i, region="highland") for i in range(HIGHLAND_ROWS * HIGHLAND_COLS)]

runstate.wetland_plots = [Plot(i, region="wetland") for i in range(WETLAND_ROWS * WETLAND_COLS)]
