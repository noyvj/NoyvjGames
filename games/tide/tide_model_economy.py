"""SettlementState, part 2 of 3 (SettlementEconomyMixin): Trade Winds market, investing, output mix, hard lag, Acid Tide boss, crew, fish yield, the sister settlement, tiers and flood readouts."""

import math

from tide_coasts import coast_meter_max, flooded_row_count, row_flood_threshold
from tide_rules import (
    ACIDITY_FALL_PER_REDUCTION, ACIDITY_RISE_PER_OUTPUT, ACID_BOSS_SEASON, ACID_BOSS_SPIKE, ACID_BRACE_COST,
    ACID_BRACE_MIN_REDUCTION, ADAPTATION_TIERS, BALANCE_MULTIPLIERS, BROKER_GAIN_BONUS, CATEGORIES,
    COASTLINE_ROWS, CREW, CREW_HIRE_COST, CREW_MAX, CREW_WAGE, DOMINO_DISCOUNT, ENGINEER_DISCOUNT,
    FISH_DAMAGE_SCALE, FISH_LAG_SEASONS, FISH_LAG_SEASONS_HARD, INVEST_COST, MARKET_EVERY, MARKET_KINDS,
    MIN_FISH_MULTIPLIER, OUTPUT_INCOME_PER_UNIT, OUTPUT_MIX, RETREAT_DAMAGE_CUT, SISTER_EXPOSURE,
    SISTER_FUNDS_PER_DAMAGE, SISTER_INCOME, SISTER_LEVEL_OFFSET,
)


class SettlementEconomyMixin:
    """SettlementState, part 2 of 3: Trade Winds market, investing, output mix, hard lag, Acid Tide boss, crew, fish
    yield, the sister settlement, adaptation tiers, damage and flood readouts."""

    # ---- GD-8 Trade Winds ----------------------------------------------
    def market_offer_text(self):
        event = self.market_event
        if not event:
            return ""
        broker = "broker" in self.crew  # GD-11: the Broker's better terms are shown before you decide
        gain = event["gain"] * (1 + BROKER_GAIN_BONUS) if broker else event["gain"]
        if event["kind"] == "export":
            return f"Trade Winds: a fish-export contract pays {gain:.0f} funds now, but the extra boats push acidity up by 0.6."
        if event["kind"] == "tourism":
            dip = "and your Broker keeps hosts from being overstretched, so there is no income dip." if broker else "but overstretched hosts cut next season's income by 10%."
            return f"Trade Winds: a tourism boom pays {gain:.0f} funds now, {dip}"
        dip = "the premium cuts next season's income by 10%." if broker else "the premium cuts the next two seasons' income by 10%."
        return f"Trade Winds: an insurance payout of {gain:.0f} funds is on offer, but {dip}"

    def market_telegraph_text(self):
        if self.market_event is None and self.season % MARKET_EVERY == MARKET_EVERY - 1:
            return "Trade Winds: a trader is expected next season. Plan for a deal."
        return ""

    def _market_kind_for(self, season):
        kinds = [k for k in MARKET_KINDS if k != "insurance" or flooded_row_count(self.sea_level, self.coastline) > 0]
        return kinds[(season * 7 + season // MARKET_EVERY * 3) % len(kinds)]

    def _market_gain(self, kind):
        if kind == "export":
            return round((30 + 10 * self.diversification["aquaculture"]) * self.fish_yield_multiplier(), 1)
        if kind == "tourism":
            return float(25 + 25 * self.diversification["tourism"])
        return float(10 * max(1, flooded_row_count(self.sea_level, self.coastline)) + 5 * (self.diversification["tourism"] + self.diversification["aquaculture"]))

    def _update_market(self):
        """Called at the end of a resolved season: expire an unanswered deal, then offer the next one when due."""
        if self.market_event is not None:
            self._log_ticker("Trade Winds: the trader sailed on; the deal lapsed.")
            self.market_event = None
        if self.season % MARKET_EVERY == 0:
            kind = self._market_kind_for(self.season)
            self.market_event = {"kind": kind, "gain": self._market_gain(kind), "season": self.season}
            self._log_ticker(self.market_offer_text())

    def answer_market(self, accept):
        event = self.market_event
        if event is None:
            return False
        self.market_event = None
        if not accept:
            self._log_ticker("Trade Winds: you declined the deal.")
            return True
        if "broker" in self.crew:  # GD-11: better terms
            event = dict(event, gain=round(event["gain"] * (1 + BROKER_GAIN_BONUS), 1))
        self.funds += event["gain"]
        self.max_funds_ever = max(self.max_funds_ever, self.funds)
        self.market_accepted += 1
        if event["kind"] == "export":
            self.acidity += 0.6
            self.max_acidity_ever = max(self.max_acidity_ever, self.acidity)
        elif event["kind"] == "tourism":
            self.income_dip_seasons = max(self.income_dip_seasons, 0 if "broker" in self.crew else 1)
        else:
            self.income_dip_seasons = max(self.income_dip_seasons, 1 if "broker" in self.crew else 2)
        self._log_ticker(f"Trade Winds: you took the {event['kind']} deal (+{event['gain']:.0f} funds).")
        self._chronicle_event(f"A trader's {event['kind']} deal was accepted.")
        return True

    def invest_cost(self, category):
        """The price now: the base cost, with the adaptation discount while a domino comeback is running."""
        base = INVEST_COST[category]
        factor = 1.0
        if category == "adaptation" and self.domino_seasons_left > 0:
            factor *= 1 - DOMINO_DISCOUNT
        if category == "adaptation" and "engineer" in self.crew:  # GD-11
            factor *= 1 - ENGINEER_DISCOUNT
        return int(math.ceil(base * factor)) if factor != 1.0 else base

    def balance_multiplier(self):
        """The income multiplier the next Advance Season will use, given this season's investments so far."""
        streak = self.balance_streak + (1 if set(CATEGORIES) <= self.season_invested else 0)
        return BALANCE_MULTIPLIERS[min(streak, len(BALANCE_MULTIPLIERS) - 1)]

    def invest(self, category):
        cost = self.invest_cost(category)
        if self.funds < cost:
            return False
        old_tier_index = self.current_tier_index() if category == "adaptation" else None
        self.funds -= cost
        self.capacity[category] += 1
        self.buys_now[CATEGORIES.index(category)] += 1  # D-3
        self.season_invested.add(category)  # GD-14
        if category == "adaptation":
            new_tier_index = self.current_tier_index()
            if new_tier_index > old_tier_index:
                self._record_tier_unlock_message(new_tier_index)
                if new_tier_index == len(ADAPTATION_TIERS) - 1 and self.maxtier_actions is None:
                    self.maxtier_actions = self.actions_count  # GD-23
                    self.maxtier_seconds = round(self.active_seconds, 1)
                if (
                    new_tier_index == len(ADAPTATION_TIERS) - 1
                    and flooded_row_count(self.sea_level, self.coastline) == 0
                ):
                    self.fortified_in_time_earned = True
        return True

    def set_output_mix(self, mix):
        """D16: switches which income/acidity mix Output investment uses
        going forward. Invalid mix names are ignored (no crash, no
        partial state change) -- the same "degrade quietly" posture as
        set_hard_lag_mode()."""
        if mix in OUTPUT_MIX:
            self.output_mix = mix
            return True
        return False

    def set_hard_lag_mode(self, enabled):
        """D9: toggles the delayed-consequence lag length. Safe to flip
        mid-session -- it only changes which index _effective_fish_lag()
        reads out of acidity_history on the next call, nothing is
        recomputed retroactively."""
        enabled = bool(enabled)
        first_time = enabled != self.hard_lag_mode and not self.hard_lag_note_seen
        self.hard_lag_mode = enabled
        if first_time:
            # D30: one-time confirmation, via the same ticker the player
            # already reads.
            self.hard_lag_note_seen = True
            self._log_ticker(
                "Lag mode changed — the new lag takes effect from next season's fish yield."
            )

    def set_comparison_baseline(self):
        """D18: lets the player re-anchor the "then vs. now" comparison
        (both the coastline grids and then_vs_now_text()) to right now,
        instead of the literal Season 1 start -- useful for comparing
        "since I changed my strategy" rather than only "since the very
        beginning"."""
        self.baseline_season = self.season
        self.baseline_sea_level = self.sea_level
        self.baseline_damage = self.cumulative_damage

    def _effective_fish_lag(self):
        """D9: which lag length is currently live -- the hard-mode toggle
        only ever changes this lookup, never acidity_history itself. GD-11: a Marine Biologist shortens it by one season."""
        lag = FISH_LAG_SEASONS_HARD if self.hard_lag_mode else FISH_LAG_SEASONS
        if self.workshop["lag"]:  # D-5: a chosen lag replaces both presets
            lag = self.workshop["lag"]
        return max(1, lag - 1) if "biologist" in self.crew else lag

    # ---- GD-12 Acid Tide boss ---------------------------------------------
    def acid_boss_pending(self):
        return self.acid_boss_mode and not self.acid_boss_result and self.season <= ACID_BOSS_SEASON

    def seasons_until_acid_boss(self):
        return ACID_BOSS_SEASON - self.season if self.acid_boss_pending() else None

    def can_brace(self):
        return (self.acid_boss_pending() and not self.acid_braced and self.funds >= ACID_BRACE_COST
                and self.capacity["reduction"] >= ACID_BRACE_MIN_REDUCTION)

    def brace_for_acid_tide(self):
        if not self.can_brace():
            return False
        self.funds -= ACID_BRACE_COST
        self.acid_braced = True
        self._log_ticker(f"Braced for the Acid Tide: {ACID_BRACE_COST} funds set aside as a buffer.")
        return True

    def _resolve_acid_boss(self):
        """Called while the boss season resolves."""
        if not self.acid_boss_mode or self.acid_boss_result or self.season != ACID_BOSS_SEASON:
            return
        if self.acid_braced:
            self.acid_boss_result = "survived"
            self._log_ticker("\U0001F30A The Acid Tide broke against your buffer. The harbour held.")
            self._chronicle_event("The great Acid Tide came and went; the buffer held.")
        else:
            self.acid_boss_result = "hit"
            self.acidity += ACID_BOSS_SPIKE
            self.max_acidity_ever = max(self.max_acidity_ever, self.acidity)
            self._log_ticker(f"\U0001F30A The Acid Tide struck: acidity jumped by {ACID_BOSS_SPIKE:.0f}. The fish will feel it in a few seasons.")
            self._chronicle_event("The Acid Tide struck an unprepared harbour.")

    # ---- GD-11 crew ------------------------------------------------------
    def hire(self, crew_id):
        if crew_id not in CREW or crew_id in self.crew or len(self.crew) >= CREW_MAX or self.funds < CREW_HIRE_COST:
            return False
        self.funds -= CREW_HIRE_COST
        self.crew.append(crew_id)
        self._log_ticker(f"Hired a {CREW[crew_id]['name']}: {CREW[crew_id]['effect']} (wage {CREW_WAGE} a season).")
        self._chronicle_event(f"A {CREW[crew_id]['name'].lower()} joined the harbour crew.")
        return True

    def dismiss(self, crew_id):
        if crew_id not in self.crew:
            return False
        self.crew.remove(crew_id)
        self._log_ticker(f"The {CREW[crew_id]['name']} was let go.")
        return True

    def fish_yield_multiplier(self):
        """1.0 (full yield) until enough seasons have passed for the lag
        to "arrive" — then reflects acidity from _effective_fish_lag()
        seasons ago."""
        lag = self._effective_fish_lag()
        if len(self.acidity_history) < lag:
            return 1.0
        lagged_acidity = self.acidity_history[-lag]
        return max(MIN_FISH_MULTIPLIER, 1 - lagged_acidity * self.workshop["fish"] / FISH_DAMAGE_SCALE)

    def next_season_fish_yield_preview(self):
        """D14: what fish_yield_multiplier() will read out *next* season,
        computed from acidity already banked in acidity_history -- the
        lag means this is always knowable one season ahead of time.
        Returns None once there isn't yet enough history to preview (the
        same "hasn't arrived yet" case fish_yield_multiplier() itself
        handles by returning a flat 1.0)."""
        lag = self._effective_fish_lag()
        if lag <= 1:
            return None
        if len(self.acidity_history) < lag - 1:
            return None
        lagged_acidity = self.acidity_history[-(lag - 1)]
        return max(MIN_FISH_MULTIPLIER, 1 - lagged_acidity / FISH_DAMAGE_SCALE)

    def enable_sister(self):
        """D3: switches the sister settlement on (once; it cannot be turned off,
        since its history is part of the run)."""
        if self.sister_enabled:
            return False
        self.sister_enabled = True
        return True

    def sister_sea_level(self):
        return self.sea_level + SISTER_LEVEL_OFFSET

    def sister_rows_flooded(self):
        """How many of the sister's COASTLINE_ROWS rows the sea has reached."""
        return sum(1 for row in range(COASTLINE_ROWS) if self.sister_sea_level() >= row_flood_threshold(row, self.coastline))

    def _advance_sister(self, rise):
        """D3: this season's effect of the sister on the shared funds. Called
        right after the main coastline's own rise, with that same `rise`."""
        if not self.sister_enabled:
            return
        damage = rise * SISTER_EXPOSURE * (1 - self.dampening_fraction())
        self.sister_cumulative_damage += damage
        net = SISTER_INCOME - damage * SISTER_FUNDS_PER_DAMAGE
        self.sister_net_funds += net
        self.funds += net

    def sister_text(self):
        if not self.sister_enabled:
            return ""
        return (
            f"Sister settlement (low-lying, shares your funds and seawall tier): "
            f"{self.sister_rows_flooded()} of {COASTLINE_ROWS} rows flooded, "
            f"{self.sister_cumulative_damage:.0f} damage so far, "
            f"{self.sister_net_funds:+.0f} funds net for you."
        )

    def current_tier_index(self):
        """Index into ADAPTATION_TIERS of the highest tier this
        settlement's cumulative adaptation investment has reached."""
        index = 0
        for i, tier in enumerate(ADAPTATION_TIERS):
            if self.capacity["adaptation"] >= tier["threshold"]:
                index = i
        return index

    def current_tier(self):
        return ADAPTATION_TIERS[self.current_tier_index()]

    def dampening_fraction(self):
        """Tier dampening, plus D1's permanent per-step cut from managed
        retreat (compounded, so it can never reach 100%)."""
        tier = self.current_tier()["dampening"]
        if not self.retreat_rows:
            return tier
        return 1 - (1 - tier) * (1 - RETREAT_DAMAGE_CUT * len(self.retreat_rows))

    def next_tier_progress_text(self):
        tier_index = self.current_tier_index()
        if tier_index == len(ADAPTATION_TIERS) - 1:
            return f"{self.current_tier()['name']} — maximum adaptation tier reached."
        next_tier = ADAPTATION_TIERS[tier_index + 1]
        return (
            f"{self.capacity['adaptation']}/{next_tier['threshold']} invested toward "
            f"{next_tier['name']} (next tier)."
        )

    def sea_level_fraction(self):
        """0..1 — sea level relative to the point where even the highest
        coastline row would flood. Iteration-pass addition, giving the
        sea-level indicator its own meter distinct from acidity/fish."""
        return min(1.0, self.sea_level / coast_meter_max(self.coastline))

    def next_flood_estimate(self):
        """D3: seasons remaining (rounded up) until the next currently-
        unflooded row crosses its threshold, reading rows bottom-up since
        that's the order they actually flood in. Returns 0 once every row
        is already flooded -- "estimate" bottoms out at "already
        happened" rather than returning a nonsensical negative or None."""
        for row in range(COASTLINE_ROWS - 1, -1, -1):
            threshold = row_flood_threshold(row, self.coastline)
            if self.sea_level < threshold:
                remaining = threshold - self.sea_level
                return math.ceil(remaining / self.sea_rise_per_season())
        return 0

    def worst_season(self):
        """D12: the single highest-damage season played so far, as
        (season_number, damage) -- damage_log[i] was recorded during the
        season the settlement was in *before* advance_season()'s own
        self.season += 1, i.e. season i+1. None before any season has
        been played."""
        if not self.damage_log:
            return None
        worst_index = max(range(len(self.damage_log)), key=lambda i: self.damage_log[i])
        return worst_index + 1, self.damage_log[worst_index]

    def seasons_until_flood(self, row):
        """D26: seasons left at the current pace before `row` floods (0
        once it already has)."""
        remaining = row_flood_threshold(row, self.coastline) - self.sea_level
        if remaining <= 0:
            return 0
        return math.ceil(remaining / self.sea_rise_per_season())

    def worst_season_cause(self):
        """D2: names what was (or wasn't) protecting the coast during the
        worst season. Returns None with no data; for a save that predates
        tier_log, falls back to no explanation."""
        worst = self.worst_season()
        if worst is None:
            return None
        index = worst[0] - 1
        if index >= len(self.tier_log):
            return None
        tier = ADAPTATION_TIERS[self.tier_log[index]]
        if self.tier_log[index] == 0:
            return "no adaptation investment had reached a tier yet"
        return f"only {tier['name']} ({tier['dampening'] * 100:.0f}% dampening) was in place"

    def then_vs_now_damage_series(self):
        """D14: per-season damage since the baseline, for a sparkline."""
        return list(self.damage_log[max(0, self.baseline_season - 1):])

    def output_mix_preview(self, mix):
        """D22: per-season (income, acidity change) at current capacity
        for a given mix, using the live fish-yield lag -- what the
        dropdown would do if chosen now."""
        cfg = OUTPUT_MIX[mix]
        share = cfg["fishing_share"]
        income = self.capacity["output"] * OUTPUT_INCOME_PER_UNIT * (
            share * self.fish_yield_multiplier() + (1 - share)
        )
        if self.coast_weight("output") != 1.0:  # D-8
            income *= self.coast_weight("output")
        acidity = (
            self.capacity["output"] * ACIDITY_RISE_PER_OUTPUT * cfg["acidity_multiplier"]
            - self.capacity["reduction"] * ACIDITY_FALL_PER_REDUCTION
        )
        return income, acidity

    def then_vs_now_text(self):
        """D4: a numeric companion to the visual coastline-comparison
        grids -- rows flooded and damage taken, measured against whatever
        baseline_* currently points at (Season 1 by default, or a
        player-chosen checkpoint via set_comparison_baseline())."""
        then_flooded = flooded_row_count(self.baseline_sea_level, self.coastline)
        now_flooded = flooded_row_count(self.sea_level, self.coastline)
        damage_since_baseline = self.cumulative_damage - self.baseline_damage
        return (
            f"Then (Season {self.baseline_season}): {then_flooded}/{COASTLINE_ROWS} rows flooded. "
            f"Now (Season {self.season}): {now_flooded}/{COASTLINE_ROWS} rows flooded — "
            f"{damage_since_baseline:.0f} damage taken since then."
        )

    def counterfactual_message(self):
        """D6: "what if you'd invested earlier" -- holds the *current*
        adaptation tier's dampening fixed across every season already
        played (instead of the tier actually ramping up over time the
        way it really did) and compares the resulting hypothetical
        cumulative damage to what actually happened. A positive
        difference is the hope-angle payoff made concrete: investing
        early (so the strong tier is active from season 1) beats reaching
        the same tier late."""
        seasons_played = len(self.damage_log)
        if seasons_played == 0:
            return "Play a few seasons to see what earlier adaptation investment could have saved."
        hypothetical_damage = (
            self.sea_rise_per_season() * (1 - self.dampening_fraction()) * seasons_played
        )
        difference = self.cumulative_damage - hypothetical_damage
        if difference <= 0.5:
            return (
                "Your current adaptation tier has been in place essentially the whole "
                "time — there's little counterfactual gap left to close."
            )
        return (
            f"If you'd had your current tier ({self.current_tier()['name']}) since Season 1, "
            f"you'd have taken about {hypothetical_damage:.0f} cumulative damage instead of your "
            f"actual {self.cumulative_damage:.0f} — investing early would have saved roughly "
            f"{difference:.0f} more."
        )

    def session_summary_text(self):
        """D7: a player-triggered end-of-session recap, not an auto
        pop-up (same "never forced mid-session" posture as the info
        page/achievements panels)."""
        worst = self.worst_season()
        worst_text = (
            f"Worst season: Season {worst[0]} ({worst[1]:.0f} damage)."
            if worst
            else "No seasons played yet."
        )
        tier = self.current_tier()
        extras = ""
        if self.rewind_used:
            extras += " \U0001FA96 Rewound once (a tin hat marks the run)."  # GD-20
        if self.ironman_earned:
            extras += " \u2693 Hard-lag ironman."  # GD-24
        if self.maxtier_actions is not None:
            extras += f" Top tier reached in {self.maxtier_actions} clicks and about {self.maxtier_seconds:.0f} seconds."  # GD-23
        return (
            f"Seasons played: {max(0, self.season - 1)}. Final funds: {self.funds:.0f}. "
            f"Cumulative damage: {self.cumulative_damage:.0f} (saved {self.damage_saved():.0f} "
            f"via adaptation). Adaptation tier reached: {tier['name']}. {worst_text}{extras}"
        )
