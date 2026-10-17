"""The farm itself: FarmState (herd, methane, income, pressure, welfare, satellite farm, poultry, purchase log) plus the
ranch-rule accessors it reads (rule(), pressure_scale(), season_for_round() ...). Ask for this file to change how the simulation works.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import copy

import herd_runstate as runstate
from herd_rules import (
    AUDIT_EVERY, AUDIT_FINE_INCOME_ROUNDS, AUDIT_GOODWILL_BONUS, AUDIT_LOG_MAX, AUDIT_PERKS,
    AUDIT_PERK_REPEAT_FUNDS, AUDIT_TRUST_PENALTY, AUDIT_TRUST_ROUNDS, BASE_COUPLING_RATIO,
    BIOGAS_SALE_PER_UNIT, BULK_MAX_UNITS, CAPTURE_SELF_USE_UNITS, CERTIFICATION_PRICE_PREMIUM,
    CERTIFICATION_RATIO_THRESHOLD, CERTIFICATION_ROUNDS_REQUIRED, DECOUPLING_MEASURES,
    DEMAND_SURGE_PLANT_INCOME_MULTIPLIER, GENETICS_COST, GENETICS_MATURE_ROUNDS, GENETICS_RATIO_REDUCTION,
    HALF_DECOUPLED_CALLOUT_THRESHOLD, HERD_GROWTH_COST, HERD_INCOME_PER_UNIT, LEVER_LOG_MAX,
    MAX_PLANT_BASED_FRACTION, MAX_PRESSURE, METHANE_PENALTY_NUDGE_THRESHOLD, METHANE_PENALTY_WEIGHT,
    MIN_COUPLING_RATIO, MIN_POULTRY_RATIO, MIN_SATELLITE_RATIO, MIXER_BONUS_FRACTION, MIXER_BONUS_MAX,
    MIXER_PERFECT_QUALITY, PERFECT_STREAK_BONUSES, PLANT_BASED_EMISSIONS_MULTIPLIER,
    PLANT_BASED_INCOME_MULTIPLIER, PLANT_PIVOT_COST, PLANT_PIVOT_FRACTION_PER_UNIT, POLICY_CARBON_BASE,
    POLICY_CARBON_PER_DECOUPLED, POLICY_CASH_BONUS, POLICY_EVENT_INTERVAL, POLICY_HEDGE_DISCOUNT,
    POLICY_HEDGE_ROUNDS, POLICY_HISTORY_MAX, POLICY_LABEL_BONUS, POLICY_LABEL_ROUNDS, POLICY_ORDER,
    POLICY_SUBSIDY_DISCOUNT, POLICY_SUBSIDY_ROUNDS, POLICY_WELFARE_BASE, POLICY_WELFARE_PER_POINT,
    POULTRY_BASE_RATIO, POULTRY_GROW_COST, POULTRY_GROW_SLOPE, POULTRY_INCOME_PER_UNIT, POULTRY_MEASURES,
    POULTRY_UPKEEP_PER_UNIT, PRESSURE_CALLOUT_THRESHOLD, PRESSURE_SCALE, REGIONAL_CAP, RULE_SPECS,
    SATELLITE_BASE_RATIO, SATELLITE_GROW_COST, SATELLITE_GROW_SLOPE, SATELLITE_INCOME_PER_UNIT,
    SATELLITE_MAX_OFFSET, SATELLITE_MAX_RETROFITS, SATELLITE_MAX_SIZE, SATELLITE_MIN_MAIN_HERD,
    SATELLITE_OFFSET_FLOOR, SATELLITE_OFFSET_RATE, SATELLITE_OPEN_COST, SATELLITE_RETROFIT_COST,
    SATELLITE_RETROFIT_REDUCTION, SEASONS, SUPPLY_CHAIN_BONUS_PER_UNIT, SUPPLY_CHAIN_COST,
    SUPPLY_CHAIN_MAX_UNITS, WELFARE_CAPS, WELFARE_FEED, WELFARE_GENETICS, WELFARE_INCOME_BONUS_MAX,
    WELFARE_MAX, WELFARE_START,
)
from herd_util import _is_finite_number


def rule(name):
    return runstate.ranch_rules[name]


def clean_rule_value(name, value):
    """A usable value for this rule (a number inside its range, on its step), or None."""
    spec = RULE_SPECS.get(name)
    if spec is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or abs(value) == float("inf"):
        return None
    clamped = max(spec["min"], min(spec["max"], float(value)))
    snapped = spec["min"] + round((clamped - spec["min"]) / spec["step"]) * spec["step"]
    return max(spec["min"], min(spec["max"], snapped))


def rules_are_custom():
    return any(abs(runstate.ranch_rules[n] - spec["default"]) > 1e-9 for n, spec in RULE_SPECS.items())


def rules_unranked():
    """True for a run that started or ran under non-standard Ranch Rules (it stays unranked for good)."""
    return runstate.sandbox_active or runstate.farm.custom_rules_used or rules_are_custom() or runstate.farm.loadout != "standard"


def pressure_scale():
    """Methane at which pressure would reach 100% income loss; the strength rule shrinks or stretches it."""
    return PRESSURE_SCALE * 100.0 / runstate.ranch_rules["pressure_strength"]


def season_for_round(round_number):
    """Deterministic pseudo-random season (same on every load/replay)."""
    return SEASONS[(round_number * 7 + 3) % len(SEASONS)]


def demand_surge_active(round_number):
    return round_number % 6 in (4, 5)


def audit_coupling_target(number):
    return max(0.6, round(0.9 - 0.1 * (number - 1), 2))


def audit_welfare_target(number):
    return float(min(60, 50 + 5 * number))


class FarmState:
    sandbox = False  # GF-24: true only on the practice sandbox's farm (SandboxFarmState)

    def __init__(self):
        self.round_number = 1
        self.funds = rule("starting_funds")
        self.herd_size = 0
        self.methane = 0.0
        self.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}
        self.plant_pivot_investment = 0

        # F1/F3/F13 — a parallel "pure-growth" counterfactual: the exact
        # same herd-growth path (same herd_size every round), but zero
        # decoupling/plant-pivot investment ever applied. Same technique
        # as Grid's bau_emissions / Thaw's counterfactual_temperature —
        # accumulated round-by-round in advance_round(), never
        # recalculated from scratch, so it survives save/load like any
        # other cumulative field. It does NOT mirror decoupling spend, so
        # it isolates whether decoupling investment paid for itself net
        # of its own cost, not just "what if you'd grown the same herd."
        self.counterfactual_funds = rule("starting_funds")
        self.counterfactual_methane = 0.0

        # F5/F11/F17 — one-time nudge callouts. seen_* flags persist (so a
        # reload doesn't replay a nudge already shown); just_* flags are
        # one-tick, consumed by the very next render(), same shape as
        # Thaw's just_started_melting / Grid's seen_retire_callout pair.
        self.seen_half_decoupled_callout = False
        self.seen_pressure_callout = False
        self.seen_methane_penalty_nudge = False
        self.just_hit_callout = None  # None, or one of "half_decoupled"/"pressure"/"methane_penalty"

        # Achievements — clean_operator needs the worst pressure fraction
        # seen so far, since pressure_fraction() alone only reads the
        # *current* value and a player could spike pressure then invest
        # their way back down before checking achievements.
        self.max_pressure_fraction_seen = 0.0

        # F7 — methane-over-rounds trend history, same shape as Thaw's
        # per-region temperature_history / Grid's emissions_history.
        self.methane_history = [0.0]

        # F11 — sustainable certification progress. Both persist.
        self.certification_streak = 0
        self.certified = False

        # F16 — one-tick flag (not saved): the round's added methane just
        # dropped below the previous round's, i.e. the curve flattened.
        self.just_flattened = False

        # F23 poultry (unlocked by certification), F5 genetics, F13 supply
        # chain, F9/F3 variation toggle, F19 cap toggle, F27 policy event.
        self.poultry_size = 0
        self.poultry_investment = {m: 0 for m in POULTRY_MEASURES}
        self.genetics_active = 0
        self.genetics_pending = []  # rounds-remaining for each in-progress unit
        self.supply_chain_investment = 0
        self.variation_enabled = False
        self.regional_cap_enabled = False
        self.policy_offer_pending = False
        self.subsidy_rounds_left = 0
        # F-9: the two options on the table, those already offered this cycle, a short history
        # of what was taken, and the two new timed effects.
        self.policy_offer = []
        self.policy_seen = []
        self.policy_history = []  # [round, taken id, other id]
        self.hedge_rounds_left = 0
        self.label_rounds_left = 0
        # GF-25: the mixer's visible tally (blends, perfect blends, funds earned) and the round last blended.
        self.mixer_blends = 0
        self.mixer_perfects = 0
        self.mixer_bonus_total = 0.0
        self.mixer_round = 0
        # GF-10: the choices made so far in "The Family Farm" story (narrative only, no effect on the sim).
        self.story_choices = []

        # F1 satellite farm.
        self.satellite_open = False
        self.satellite_size = 0
        self.satellite_retrofits = 0

        # GF-29/F-17/GF-15: per-round funds record (aligned with methane_history,
        # None where an older save never recorded it), the purchase log and the
        # perfect-round streak.
        self.funds_history = [rule("starting_funds")]
        # F-1: true once any round (or the farm's start) happened under non-standard Ranch Rules.
        self.custom_rules_used = rules_are_custom()
        self.lever_log = []
        self.perfect_streak = 0
        self.best_perfect_streak = 0
        self.last_round_perfect = False  # one-tick, not saved
        self.just_streak_bonus = None  # one-tick (streak, bonus), not saved

        # GF-3: audits resolved, their log ([audit number, round, passed 0/1]), perks earned and the
        # rounds of shaken market trust left. just_audit is a one-tick result for the toast (not saved).
        self.audits_done = 0
        self.audit_log = []
        self.audit_perks = []
        self.trust_rounds_left = 0
        self.just_audit = None

        # GF-23: the starting loadout this farm began with ("standard" = none).
        self.loadout = "standard"

        # GF-28: an opt-in blind run hides the baseline comparison until it is revealed.
        self.blind_run = False
        self.blind_revealed = False

        # GF-21: golden cows welcomed on this farm and the funds they brought (a visible tally).
        self.golden_claimed = 0
        self.golden_funds = 0.0

        # GF-18: one rewind per game. undo_snapshot (the state just before the last
        # Advance Round) is never saved; undo_used is, once it is true.
        self.undo_used = False
        self.undo_snapshot = None

    # ---- F-19 bulk buying ----
    def bulk_plan(self, key, mode):
        """(units, total cost) for buying `mode` (1, 5 or "max") units of Grow Herd ("herd")
        or one decoupling lever, worked out on a scratch copy so nothing changes here.
        It stops at whatever the funds or the regional cap allow. For 5 and max it also
        stops once the lever's efficiency ratio is at its floor, so a bulk click never buys
        units that save nothing (a single unit is always allowed, as before)."""
        want = mode if mode in (1, 5) else BULK_MAX_UNITS
        scratch = copy.copy(self)
        scratch.decoupling_investment = dict(self.decoupling_investment)
        scratch.lever_log = []
        units = 0
        while units < want:
            if (
                want > 1 and key in DECOUPLING_MEASURES
                and scratch._efficiency_coupling_ratio() <= MIN_COUPLING_RATIO + 1e-9
            ):
                break
            bought = scratch.grow_herd() if key == "herd" else scratch.invest_decoupling(key)
            if not bought:
                break
            units += 1
        return units, self.funds - scratch.funds

    def buy_bulk(self, key, mode):
        """Buys what bulk_plan() promised, one real purchase at a time (so every unit is
        logged and priced exactly as a single click would be). Returns units bought."""
        units, _total = self.bulk_plan(key, mode)
        bought = 0
        for _ in range(units):
            ok = self.grow_herd() if key == "herd" else self.invest_decoupling(key)
            if not ok:
                break
            bought += 1
        return bought

    # ---- GF-13 named cows ----
    def herd_unit_rounds(self):
        """The round each herd unit was bought, oldest first. Units the purchase log no
        longer holds (an old save, or a log that hit its cap) are counted as bought in round 1."""
        rounds = [r for r, k, _c in self.lever_log if k == "herd"]
        rounds = rounds[-self.herd_size:] if self.herd_size > 0 else []
        return [1] * (self.herd_size - len(rounds)) + rounds

    # ---- F-17 lever history ----
    def log_purchase(self, key, cost):
        self.lever_log.append([self.round_number, key, round(float(cost), 2)])
        extra = len(self.lever_log) - LEVER_LOG_MAX
        if extra > 0:
            del self.lever_log[:extra]

    # ---- F-13 funds per methane saved ----
    def methane_saved_by(self, key):
        """Methane per round that ONE more unit of this lever would remove at the
        current herd, found by trying the unit and putting it back (no lasting
        change). Uses the same ratio formulas as the real purchase, so the
        satellite network offset and the plant-pivot cap are included."""
        before = self.methane_this_round()
        if key in DECOUPLING_MEASURES:
            self.decoupling_investment[key] += 1
            after = self.methane_this_round()
            self.decoupling_investment[key] -= 1
        elif key == "pivot":
            self.plant_pivot_investment += 1
            after = self.methane_this_round()
            self.plant_pivot_investment -= 1
        elif key in POULTRY_MEASURES:
            self.poultry_investment[key] += 1
            after = self.methane_this_round()
            self.poultry_investment[key] -= 1
        elif key == "genetics":
            self.genetics_active += 1
            after = self.methane_this_round()
            self.genetics_active -= 1
        elif key == "satellite_retrofit":
            self.satellite_retrofits += 1
            after = self.methane_this_round()
            self.satellite_retrofits -= 1
        else:
            return 0.0
        return max(0.0, before - after)

    # ---- F-24 cap headroom ----
    def cap_headroom(self):
        """Free methane per round under the regional cap, never below zero."""
        return max(0.0, REGIONAL_CAP - self.methane_this_round())

    def growth_pace(self):
        """Herd units added per round so far, averaged over the rounds played."""
        return self.herd_size / max(1, self.round_number - 1)

    def rounds_until_cap(self):
        """Rounds until the cap blocks growth if the herd keeps growing at its pace so
        far and nothing is decoupled. None when the herd is not growing; 0 when the
        next animal is already blocked."""
        pace = self.growth_pace()
        ratio = self.coupling_ratio()
        if self.cap_blocks_growth(herd=1):
            return 0
        if pace <= 0 or ratio <= 0:
            return None
        return int(self.cap_headroom() / (pace * ratio))

    # ---- F1 satellite farm ----
    def satellite_available(self):
        return self.satellite_open or self.herd_size >= SATELLITE_MIN_MAIN_HERD

    def satellite_own_ratio(self):
        """The satellite's ratio from its own retrofits alone."""
        reduction = self.satellite_retrofits * SATELLITE_RETROFIT_REDUCTION
        return max(MIN_SATELLITE_RATIO, SATELLITE_BASE_RATIO - reduction)

    def satellite_offset_fraction(self):
        """Share of the satellite's emissions the main farm's surplus
        decoupling cancels out: zero until the main farm is decoupled past
        SATELLITE_OFFSET_FLOOR, then growing with the surplus up to
        SATELLITE_MAX_OFFSET."""
        surplus = max(0.0, self.decoupled_fraction() - SATELLITE_OFFSET_FLOOR)
        return min(SATELLITE_MAX_OFFSET, surplus * SATELLITE_OFFSET_RATE)

    def satellite_coupling_ratio(self):
        return max(MIN_SATELLITE_RATIO, self.satellite_own_ratio() * (1 - self.satellite_offset_fraction()))

    def satellite_grow_cost(self):
        return SATELLITE_GROW_COST + self.satellite_size * SATELLITE_GROW_SLOPE

    def open_satellite(self):
        if self.satellite_open or self.herd_size < SATELLITE_MIN_MAIN_HERD or self.funds < SATELLITE_OPEN_COST:
            return False
        self.funds -= SATELLITE_OPEN_COST
        self.satellite_open = True
        self.log_purchase("satellite_open", SATELLITE_OPEN_COST)
        return True

    def grow_satellite(self):
        cost = self.satellite_grow_cost()
        if (
            not self.satellite_open or self.satellite_size >= SATELLITE_MAX_SIZE
            or self.funds < cost or self.cap_blocks_growth(satellite=1)
        ):
            return False
        self.funds -= cost
        self.satellite_size += 1
        self.log_purchase("satellite_grow", cost)
        return True

    def retrofit_satellite(self):
        if (
            not self.satellite_open or self.satellite_retrofits >= SATELLITE_MAX_RETROFITS
            or self.funds < SATELLITE_RETROFIT_COST
        ):
            return False
        self.funds -= SATELLITE_RETROFIT_COST
        self.satellite_retrofits += 1
        self.log_purchase("satellite_retrofit", SATELLITE_RETROFIT_COST)
        return True

    def satellite_net_income(self):
        return self.satellite_size * SATELLITE_INCOME_PER_UNIT

    # ---- F27 policy advisor ----
    def decoupling_cost(self, measure):
        cost = DECOUPLING_MEASURES[measure]["cost"]
        if "green_loan" in self.audit_perks:
            cost = max(1, cost - 1)  # GF-3: an audit perk
        if self.subsidy_rounds_left > 0:
            cost *= 1 - POLICY_SUBSIDY_DISCOUNT
        if measure == "feed" and self.hedge_rounds_left > 0:
            cost *= 1 - POLICY_HEDGE_DISCOUNT
        return cost

    def mixer_available(self):
        return self.decoupling_investment["feed"] >= 1 and self.mixer_round != self.round_number

    def mixer_bonus_for(self, quality):
        """Funds a blend of this quality (0 to 1) pays right now: a share of the funds in hand, capped."""
        quality = max(0.0, min(1.0, quality))
        return round(quality * min(MIXER_BONUS_MAX, MIXER_BONUS_FRACTION * max(0.0, self.funds)), 1)

    def blend(self, quality):
        """One mixer blend. Returns the bonus paid, or None when no blend is allowed right now."""
        if not self.mixer_available() or not _is_finite_number(quality):
            return None
        bonus = self.mixer_bonus_for(quality)
        self.funds += bonus
        self.mixer_blends += 1
        if quality >= MIXER_PERFECT_QUALITY:
            self.mixer_perfects += 1
        self.mixer_bonus_total += bonus
        self.mixer_round = self.round_number
        return bonus

    # ---- GF-3 regulator audits ----
    def next_audit_round(self):
        """The round at whose end the next audit happens (this round, when it is a multiple of AUDIT_EVERY)."""
        return -(-self.round_number // AUDIT_EVERY) * AUDIT_EVERY

    def audit_multiplier(self):
        multiplier = 1.0
        if "goodwill" in self.audit_perks:
            multiplier *= 1 + AUDIT_GOODWILL_BONUS
        if self.trust_rounds_left > 0:
            penalty = AUDIT_TRUST_PENALTY * (0.5 if "friendly_inspector" in self.audit_perks else 1.0)
            multiplier *= 1 - penalty
        return multiplier

    def audit_passes(self, number=None):
        number = self.audits_done + 1 if number is None else number
        return (
            self.coupling_ratio() <= audit_coupling_target(number) + 1e-9
            and self.welfare() >= audit_welfare_target(number) - 1e-9
        )

    def _run_audit(self):
        """The audit at the end of the round just played. Sets just_audit for the toast."""
        number = self.audits_done + 1
        passed = self.audit_passes(number)
        self.audits_done = number
        perk, fine = None, 0.0
        if passed:
            for entry in AUDIT_PERKS:
                if entry["id"] not in self.audit_perks:
                    perk = entry["id"]
                    self.audit_perks.append(perk)
                    break
            if perk is None:
                self.funds += AUDIT_PERK_REPEAT_FUNDS
        else:
            share = AUDIT_FINE_INCOME_ROUNDS * (0.5 if "friendly_inspector" in self.audit_perks else 1.0)
            fine = float(min(max(0.0, self.funds), round(self.income_breakdown()["total"] * share)))
            self.funds -= fine
            self.trust_rounds_left = AUDIT_TRUST_ROUNDS
        if self.funds_history and self.funds_history[-1] is not None:
            self.funds_history[-1] = self.funds
        self.audit_log.append([number, self.round_number - 1, 1 if passed else 0])
        del self.audit_log[:-AUDIT_LOG_MAX]
        self.just_audit = (number, passed, fine, perk)

    def label_multiplier(self):
        return 1 + POLICY_LABEL_BONUS if self.label_rounds_left > 0 else 1.0

    def current_policy_offer(self):
        """The two option ids on the table (the original pair when an older save has none stored)."""
        if len(self.policy_offer) == 2:
            return list(self.policy_offer)
        return ["subsidy", "cash"]

    def draw_policy_offer(self):
        """Two options from the pool, in the fixed order, none repeated until the pool is used up."""
        unseen = [o for o in POLICY_ORDER if o not in self.policy_seen]
        if len(unseen) < 2:
            self.policy_seen = []
            unseen = list(POLICY_ORDER)
        first = unseen[0]
        second = unseen[1 + len(self.policy_history) % (len(unseen) - 1)]
        self.policy_seen += [first, second]
        return [first, second]

    def carbon_credit_value(self):
        return round(POLICY_CARBON_BASE + POLICY_CARBON_PER_DECOUPLED * max(0.0, self.decoupled_fraction()))

    def welfare_grant_value(self):
        return round(POLICY_WELFARE_BASE + POLICY_WELFARE_PER_POINT * max(0.0, self.welfare() - WELFARE_START))

    def choose_policy(self, choice):
        if not self.policy_offer_pending or choice not in self.current_policy_offer():
            return False
        if choice == "subsidy":
            self.subsidy_rounds_left = POLICY_SUBSIDY_ROUNDS
        elif choice == "cash":
            self.funds += POLICY_CASH_BONUS
        elif choice == "carbon_credit":
            self.funds += self.carbon_credit_value()
        elif choice == "feed_hedge":
            self.hedge_rounds_left = POLICY_HEDGE_ROUNDS
        elif choice == "organic_trial":
            self.label_rounds_left = POLICY_LABEL_ROUNDS
        elif choice == "welfare_grant":
            self.funds += self.welfare_grant_value()
        else:
            return False
        other = [o for o in self.current_policy_offer() if o != choice][0]
        self.policy_history.append([self.round_number, choice, other])
        del self.policy_history[:-POLICY_HISTORY_MAX]
        self.policy_offer_pending = False
        self.policy_offer = []
        return True

    # ---- F23 poultry ----
    def poultry_unlocked(self):
        # F25: a heritage flock (legacy perk) carries the unlock to every
        # later generation without needing to re-earn certification.
        return self.certified or runstate.legacy_perks.get("heritage_flock", 0) > 0 or self.loadout == "poultry_start" or self.sandbox

    def poultry_coupling_ratio(self):
        reduction = sum(
            self.poultry_investment[m] * POULTRY_MEASURES[m]["ratio_reduction"] for m in POULTRY_MEASURES
        )
        return max(MIN_POULTRY_RATIO, POULTRY_BASE_RATIO - reduction)

    def poultry_grow_cost(self):
        return POULTRY_GROW_COST + self.poultry_size * POULTRY_GROW_SLOPE

    def grow_poultry(self):
        cost = self.poultry_grow_cost()
        if not self.poultry_unlocked() or self.funds < cost or self.cap_blocks_growth(poultry=1):
            return False
        self.funds -= cost
        self.poultry_size += 1
        self.log_purchase("poultry", cost)
        return True

    def invest_poultry(self, measure):
        if not self.poultry_unlocked():
            return False
        cost = POULTRY_MEASURES[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.poultry_investment[measure] += 1
        self.log_purchase(measure, cost)
        return True

    def poultry_net_income(self):
        return self.poultry_size * (POULTRY_INCOME_PER_UNIT - POULTRY_UPKEEP_PER_UNIT)

    # ---- F5 genetics ----
    def invest_genetics(self):
        if self.funds < GENETICS_COST:
            return False
        self.funds -= GENETICS_COST
        self.genetics_pending.append(GENETICS_MATURE_ROUNDS)
        self.log_purchase("genetics", GENETICS_COST)
        return True

    # ---- F13 supply chain ----
    def invest_supply_chain(self):
        if self.funds < SUPPLY_CHAIN_COST or self.supply_chain_investment >= SUPPLY_CHAIN_MAX_UNITS:
            return False
        self.funds -= SUPPLY_CHAIN_COST
        self.supply_chain_investment += 1
        self.log_purchase("supply", SUPPLY_CHAIN_COST)
        return True

    def supply_chain_multiplier(self):
        return 1 + self.supply_chain_investment * SUPPLY_CHAIN_BONUS_PER_UNIT

    # ---- F15 welfare ----
    def welfare(self):
        score = (
            WELFARE_START
            + self.decoupling_investment["feed"] * WELFARE_FEED
            + self.decoupling_investment["caps"] * WELFARE_CAPS
            + self.genetics_active * WELFARE_GENETICS
        )
        return min(WELFARE_MAX, score)

    def welfare_multiplier(self):
        return 1 + WELFARE_INCOME_BONUS_MAX * (self.welfare() - WELFARE_START) / (WELFARE_MAX - WELFARE_START)

    # ---- F9/F3 variation ----
    def season_modifier(self, round_number=None):
        if not self.variation_enabled:
            return 0.0
        raw = season_for_round(self.round_number if round_number is None else round_number)[1]
        return raw * runstate.ranch_rules["season_swing"] / 100.0

    def plant_income_multiplier(self, round_number=None):
        r = self.round_number if round_number is None else round_number
        if self.variation_enabled and demand_surge_active(r):
            return DEMAND_SURGE_PLANT_INCOME_MULTIPLIER
        return PLANT_BASED_INCOME_MULTIPLIER

    # ---- F29 biogas ----
    def biogas_sales(self):
        surplus = max(0, self.decoupling_investment["capture"] - CAPTURE_SELF_USE_UNITS)
        return self.herd_size * surplus * BIOGAS_SALE_PER_UNIT

    # ---- F19 regional cap ----
    def cap_blocks_growth(self, herd=0, poultry=0, satellite=0):
        if not self.regional_cap_enabled:
            return False
        projected = (
            (self.herd_size + herd) * self.coupling_ratio()
            + (self.poultry_size + poultry) * self.poultry_coupling_ratio()
            + (self.satellite_size + satellite) * self.satellite_coupling_ratio()
        )
        return projected > REGIONAL_CAP + 1e-9

    def certification_multiplier(self):
        return 1 + CERTIFICATION_PRICE_PREMIUM if self.certified else 1.0

    def _efficiency_coupling_ratio(self):
        """Methane produced per herd unit, per round, from the feed/caps/
        capture efficiency measures alone — floored so it never hits zero."""
        reduction = sum(
            self.decoupling_investment[m] * DECOUPLING_MEASURES[m]["ratio_reduction"]
            for m in DECOUPLING_MEASURES
        ) + self.genetics_active * GENETICS_RATIO_REDUCTION
        return max(MIN_COUPLING_RATIO, BASE_COUPLING_RATIO - reduction)

    def plant_based_fraction(self):
        return min(MAX_PLANT_BASED_FRACTION, self.plant_pivot_investment * PLANT_PIVOT_FRACTION_PER_UNIT)

    def coupling_ratio(self):
        """The efficiency-measure ratio, further blended down by however
        much of the herd's output has pivoted to (near-zero-methane)
        plant-based production. Same public method every other Pass 1
        mechanic already reads from, so the gauge shows one unified
        number regardless of which lever moved it."""
        base = self._efficiency_coupling_ratio()
        fraction = self.plant_based_fraction()
        blended_multiplier = (1 - fraction) + fraction * PLANT_BASED_EMISSIONS_MULTIPLIER
        return max(MIN_COUPLING_RATIO, base * blended_multiplier)

    def invest_plant_pivot(self):
        if self.funds < PLANT_PIVOT_COST:
            return False
        self.funds -= PLANT_PIVOT_COST
        self.plant_pivot_investment += 1
        self.log_purchase("pivot", PLANT_PIVOT_COST)
        return True

    def decoupled_fraction(self):
        """How far below baseline the current coupling ratio sits, 0..1.
        Shared by the decoupling-summary display, the real-world-42%
        comparison (F15), and the decoupling-threshold achievements/
        callout — one function, not four copies of the same subtraction."""
        return 1 - (self.coupling_ratio() / BASE_COUPLING_RATIO)

    def methane_this_round(self):
        return (
            self.herd_size * self.coupling_ratio()
            + self.poultry_size * self.poultry_coupling_ratio()
            + self.satellite_size * self.satellite_coupling_ratio()
        )

    def grow_herd_cost(self):
        """F6 — a rising growth-cost curve: the very first unit still
        costs exactly HERD_GROWTH_COST (herd_size == 0), and each unit
        after that costs marginally more, reflecting real land/logistics
        constraints on scaling a herd rather than a flat per-unit price
        forever."""
        return HERD_GROWTH_COST + self.herd_size * runstate.ranch_rules["growth_slope"]

    def grow_herd(self):
        cost = self.grow_herd_cost()
        if self.funds < cost or self.cap_blocks_growth(herd=1):
            return False
        self.funds -= cost
        self.herd_size += 1
        self.log_purchase("herd", cost)
        return True

    def invest_decoupling(self, measure):
        cost = self.decoupling_cost(measure)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.decoupling_investment[measure] += 1
        self.log_purchase(measure, cost)
        return True

    def pressure_fraction(self):
        """Fraction of income lost to market/regulatory pressure and
        degraded yields, scaling with sustained methane. Capped so income
        never fully vanishes — a bad strategy gets worse, not impossible."""
        return min(MAX_PRESSURE, self.methane / pressure_scale())

    def counterfactual_pressure_fraction(self):
        return min(MAX_PRESSURE, self.counterfactual_methane / pressure_scale())

    def counterfactual_score(self):
        """F1/F3/F13 — the pure-growth counterfactual's own score, using
        the exact same formula as score() so the two numbers are directly
        comparable."""
        return self.counterfactual_funds - self.counterfactual_methane * METHANE_PENALTY_WEIGHT

    def income_breakdown(self):
        """Every piece of one round's income, in the order the game applies them. advance_round()
        banks exactly breakdown["total"], so the F-6 inspector can never disagree with the game."""
        fraction = self.plant_based_fraction()
        plant_blend = (1 - fraction) + fraction * self.plant_income_multiplier()
        certification = self.certification_multiplier()
        welfare = self.welfare_multiplier()
        supply = self.supply_chain_multiplier()
        season = 1 + self.season_modifier()
        herd_base = self.herd_size * HERD_INCOME_PER_UNIT
        herd_income = self.herd_size * HERD_INCOME_PER_UNIT * plant_blend * certification * welfare
        poultry = self.poultry_net_income()
        satellite = self.satellite_net_income()
        label = self.label_multiplier()
        audit = self.audit_multiplier()
        raw_income = (herd_income + poultry + satellite) * supply * season * label * audit
        pressure = self.pressure_fraction()
        biogas = self.biogas_sales()
        return {
            "herd_base": herd_base, "plant_fraction": fraction, "plant_blend": plant_blend,
            "certification": certification, "welfare": welfare, "herd_income": herd_income,
            "poultry": poultry, "satellite": satellite, "supply": supply, "season": season, "label": label,
            "audit": audit, "raw": raw_income, "pressure": pressure, "after_pressure": raw_income * (1 - pressure),
            "biogas": biogas, "total": raw_income * (1 - pressure) + biogas,
        }

    def advance_round(self):
        pressure = self.pressure_fraction()
        season = 1 + self.season_modifier()
        self.funds += self.income_breakdown()["total"]
        self.methane += self.methane_this_round()
        self.max_pressure_fraction_seen = max(self.max_pressure_fraction_seen, pressure)

        # Counterfactual: same herd_size, but baseline (fully-coupled)
        # emissions and no plant-pivot income multiplier — never mirrors
        # decoupling/pivot spend, so the comparison isolates whether that
        # spend paid for itself.
        counterfactual_pressure = self.counterfactual_pressure_fraction()
        counterfactual_raw_income = (
            self.herd_size * HERD_INCOME_PER_UNIT + self.poultry_net_income() + self.satellite_net_income()
        ) * season
        self.counterfactual_funds += counterfactual_raw_income * (1 - counterfactual_pressure)
        self.counterfactual_methane += (
            self.herd_size * BASE_COUPLING_RATIO + self.poultry_size * POULTRY_BASE_RATIO
            + self.satellite_size * SATELLITE_BASE_RATIO
        )

        # F5 -- breeding matures; F27 -- subsidy runs down and a new offer
        # arrives every POLICY_EVENT_INTERVAL rounds.
        self.genetics_pending = [r - 1 for r in self.genetics_pending]
        matured = sum(1 for r in self.genetics_pending if r <= 0)
        self.genetics_active += matured
        self.genetics_pending = [r for r in self.genetics_pending if r > 0]
        if self.subsidy_rounds_left > 0:
            self.subsidy_rounds_left -= 1
        if self.hedge_rounds_left > 0:
            self.hedge_rounds_left -= 1
        if self.label_rounds_left > 0:
            self.label_rounds_left -= 1
        if self.trust_rounds_left > 0:
            self.trust_rounds_left -= 1
        if (self.round_number + 1) % POLICY_EVENT_INTERVAL == 0:
            self.policy_offer_pending = True
            self.policy_offer = self.draw_policy_offer()

        self.round_number += 1
        prev_increment = (
            self.methane_history[-1] - self.methane_history[-2] if len(self.methane_history) >= 2 else 0.0
        )
        self.methane_history.append(self.methane)
        # F16 — curve flattening: this round added less than the last.
        self.just_flattened = (
            prev_increment > 0 and (self.methane_history[-1] - self.methane_history[-2]) < prev_increment - 1e-9
        )

        # GF-15 -- perfect round: this round's methane fell below the last one's AND
        # funds ended higher than they ended the previous round. Funds history is
        # kept for the highlights reel too (GF-29).
        prev_funds = self.funds_history[-1] if self.funds_history else None
        self.funds_history.append(self.funds)
        self.last_round_perfect = bool(
            self.just_flattened and prev_funds is not None and self.funds > prev_funds
        )
        self.just_streak_bonus = None
        if self.last_round_perfect:
            self.perfect_streak += 1
            self.best_perfect_streak = max(self.best_perfect_streak, self.perfect_streak)
            bonus = PERFECT_STREAK_BONUSES.get(self.perfect_streak)
            if bonus:
                self.funds += bonus
                self.funds_history[-1] = self.funds
                self.just_streak_bonus = (self.perfect_streak, bonus)
        else:
            self.perfect_streak = 0

        # F11 — certification streak, counted on the ratio held this round.
        if self.coupling_ratio() <= CERTIFICATION_RATIO_THRESHOLD:
            self.certification_streak += 1
        else:
            self.certification_streak = 0
        if not self.certified and self.certification_streak >= CERTIFICATION_ROUNDS_REQUIRED:
            self.certified = True

        # F5/F11/F17 — one-time nudge callouts, checked in a fixed
        # priority order so at most one fires per round (the shared
        # milestone-toast can only show one message at a time anyway).
        if not self.seen_half_decoupled_callout and self.decoupled_fraction() >= HALF_DECOUPLED_CALLOUT_THRESHOLD:
            self.seen_half_decoupled_callout = True
            self.just_hit_callout = "half_decoupled"
        elif not self.seen_pressure_callout and pressure >= PRESSURE_CALLOUT_THRESHOLD:
            self.seen_pressure_callout = True
            self.just_hit_callout = "pressure"
        elif (
            not self.seen_methane_penalty_nudge
            and self.methane * METHANE_PENALTY_WEIGHT >= METHANE_PENALTY_NUDGE_THRESHOLD
        ):
            self.seen_methane_penalty_nudge = True
            self.just_hit_callout = "methane_penalty"

        # GF-3: the regulator audit at the end of every AUDIT_EVERY-th round.
        self.just_audit = None
        if (self.round_number - 1) % AUDIT_EVERY == 0:
            self._run_audit()

    def score(self):
        """Profitability weighted against sustained emissions — rewards
        decoupling specifically, not just growth or just restraint."""
        return self.funds - self.methane * METHANE_PENALTY_WEIGHT


def clone_farm(source):
    """A scratch copy of a farm: every list and dict is copied, so playing the copy cannot change the original."""
    twin = copy.copy(source)
    twin.decoupling_investment = dict(source.decoupling_investment)
    twin.poultry_investment = dict(source.poultry_investment)
    for name in ("genetics_pending", "methane_history", "funds_history", "policy_offer", "policy_seen", "audit_perks"):
        setattr(twin, name, list(getattr(source, name)))
    twin.lever_log = [list(entry) for entry in source.lever_log]
    twin.audit_log = [list(entry) for entry in source.audit_log]
    twin.policy_history = [list(entry) for entry in source.policy_history]
    twin.undo_snapshot = None
    return twin
