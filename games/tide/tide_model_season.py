"""SettlementState, part 3 of 3 (SettlementSeasonMixin) and the assembled SettlementState: Harbor Ledger, snapshots and scrubber, descriptions, ticker messages and advance_season(). Creates the live settlement."""

import tide_runstate as runstate
from tide_coasts import _is_seawall_row, flooded_row_count, heritage_sites, tile_row_state
from tide_model_economy import SettlementEconomyMixin
from tide_model_town import SettlementTownMixin
from tide_rules import (
    ACIDITY_FALL_PER_REDUCTION, ACIDITY_RISE_PER_OUTPUT, ADAPTATION_TIERS, ADVANCE_BATCH,
    BALANCE_MULTIPLIERS, CATEGORIES, CHESS_RUNOFF_LAG, CHESS_RUNOFF_SHARE, COASTLINE_ROWS, CREW_WAGE,
    DOMINO_DISCOUNT, DOMINO_DISCOUNT_SEASONS, DOMINO_MIN_ROWS, FISH_CRASH_LEVEL, FISH_RECOVERED_LEVEL,
    FISH_YIELD_WARNING_THRESHOLD, FLOODED, HERITAGE_CODES, HERITAGE_COL, HERITAGE_RISK_SEASONS,
    HERITAGE_UNPROTECTED, IRONMAN_SEASONS, LEDGER_COLUMNS, LEDGER_KEYS, LEDGER_LIMIT, MARKET_DIP_FACTOR,
    MONITOR_COOLDOWN_SEASONS, OUTPUT_INCOME_PER_UNIT, OUTPUT_MIX, POP_START, SNAPSHOT_LIMIT, STARTING_FUNDS,
    TICKER_FULL_HISTORY_LIMIT, TICKER_LOG_LIMIT, TIER_BADGES,
)


class SettlementSeasonMixin:
    """SettlementState, part 3 of 3: Harbor Ledger, snapshots and scrubber, quiet seasons, descriptions, ticker messages
    and advance_season()."""

    # ---- D-1 Harbor Ledger -------------------------------------------
    def rows_dry_count(self):
        return sum(1 for row in range(COASTLINE_ROWS) if not self.row_lost(row))

    def _record_ledger_entry(self, resolved_season, damage, fish_yield):
        """Appends the just-resolved season to the ledger (rounded, so a
        saved ledger stays small)."""
        self.season_ledger.append(
            {
                "season": resolved_season,
                "funds": round(self.funds, 1),
                "acidity": round(self.acidity, 2),
                "fish_yield": round(fish_yield, 3),
                "damage": round(damage, 2),
                "rows_dry": self.rows_dry_count(),
                "population": int(self.population),
                "tier": self.current_tier_index(),
                "invested": int(sum(self.capacity.values())),
            }
        )
        self.season_ledger = self.season_ledger[-LEDGER_LIMIT:]

    def sorted_ledger(self, key="season", descending=False):
        """The ledger sorted by one column (stable, so ties keep season order)."""
        if key not in LEDGER_KEYS:
            key = "season"
        return sorted(self.season_ledger, key=lambda entry: entry[key], reverse=bool(descending))

    def ledger_series(self, key):
        """One column's values in season order, for its small chart."""
        return [entry[key] for entry in self.season_ledger if key in entry]

    def ledger_summary_text(self, key="season", descending=True):
        if not self.season_ledger:
            return "No seasons recorded yet. Advance a season and its row appears here."
        first, last = self.season_ledger[0]["season"], self.season_ledger[-1]["season"]
        label = dict(LEDGER_COLUMNS)[key if key in LEDGER_KEYS else "season"]
        peak = max(self.season_ledger, key=lambda e: e["funds"])
        low = min(self.season_ledger, key=lambda e: e["fish_yield"])
        text = (
            f"{len(self.season_ledger)} season(s) recorded (Season {first} to {last}), "
            f"sorted by {label.lower()}, {'highest first' if descending else 'lowest first'}. "
            f"Peak funds {peak['funds']:.0f} in Season {peak['season']}; "
            f"lowest fish yield {low['fish_yield'] * 100:.0f}% in Season {low['season']}."
        )
        if self.season - 1 > len(self.season_ledger) and len(self.season_ledger) < LEDGER_LIMIT:
            text += " Seasons played before the ledger existed (older saves) are not listed."
        return text

    # ---- D-4 season scrubber ------------------------------------------
    def _record_snapshot(self, resolved_season):
        """What the ledger cannot rebuild: the sea level, which heritage
        sites were safe, and which rows had been given up, as of the end of
        the season just resolved."""
        code = "".join(HERITAGE_CODES.get(self.heritage.get(site["id"]), "u") for site in heritage_sites(self.coastline))
        self.season_snapshots.append(
            [resolved_season, round(self.sea_level, 1), code, list(self.retreat_rows)]
        )
        self.season_snapshots = self.season_snapshots[-SNAPSHOT_LIMIT:]

    def scrub_snapshot(self, position):
        """A read-only picture of the start of season `position` (what the
        player saw before investing in it), or None for the live season, a
        future one or one this save has no record of. Position 1 is the
        fixed starting state."""
        if not isinstance(position, int) or position < 1 or position >= self.season:
            return None
        heritage = {site["id"]: HERITAGE_UNPROTECTED for site in heritage_sites(self.coastline)}
        if position == 1:
            return {
                "season": 1, "funds": float(STARTING_FUNDS), "acidity": 0.0, "fish_yield": 1.0,
                "damage_total": 0.0, "sea_level": 0.0, "tier": 0, "rows_dry": COASTLINE_ROWS,
                "population": POP_START, "heritage": heritage, "retreat_rows": [],
            }
        resolved = position - 1
        entry = next((e for e in self.season_ledger if e["season"] == resolved), None)
        snap = next((x for x in self.season_snapshots if x[0] == resolved), None)
        if entry is None or snap is None or len(self.damage_log) < resolved:
            return None
        for site, letter in zip(heritage_sites(self.coastline), snap[2]):
            heritage[site["id"]] = next((k for k, v in HERITAGE_CODES.items() if v == letter), HERITAGE_UNPROTECTED)
        return {
            "season": position, "funds": entry["funds"], "acidity": entry["acidity"],
            "fish_yield": entry["fish_yield"], "damage_total": sum(self.damage_log[:resolved]),
            "sea_level": snap[1], "tier": entry["tier"], "rows_dry": entry["rows_dry"],
            "population": entry["population"], "heritage": heritage, "retreat_rows": list(snap[3]),
        }

    def scrub_positions(self):
        """Every season start the scrubber can show (ascending)."""
        return [n for n in range(1, self.season) if self.scrub_snapshot(n) is not None]

    def scrub_text(self, snap):
        tier = ADAPTATION_TIERS[snap["tier"]]
        sites = "; ".join(
            f"{site['name'].lower()} {snap['heritage'][site['id']]}" for site in heritage_sites(self.coastline)
        )
        return (
            f"Start of Season {snap['season']} (read-only, your live run is untouched): "
            f"funds {snap['funds']:.0f}, acidity {snap['acidity']:.1f}, fishing yield "
            f"{snap['fish_yield'] * 100:.0f}%, damage so far {snap['damage_total']:.0f}, "
            f"{snap['rows_dry']} of {COASTLINE_ROWS} rows dry, population {snap['population']}, "
            f"tier {TIER_BADGES[snap['tier']]} {tier['name']}. Heritage: {sites}."
        )

    # ---- D-15 Advance x5 ---------------------------------------------
    def fish_warning_active(self):
        """True while the fish-yield early warning (D14) is showing."""
        preview = self.next_season_fish_yield_preview()
        current = self.fish_yield_multiplier()
        return (
            preview is not None
            and preview < current - 1e-6
            and preview <= FISH_YIELD_WARNING_THRESHOLD
        )

    def heritage_at_risk(self):
        """Unprotected, still-dry heritage sites close to flooding that the
        player can afford to protect right now."""
        return [
            site
            for site in heritage_sites(self.coastline)
            if self.heritage.get(site["id"]) == HERITAGE_UNPROTECTED
            and not self.row_lost(site["row"])
            and self.funds >= site["cost"]
            and self.seasons_until_flood(site["row"]) <= HERITAGE_RISK_SEASONS
        ]

    def monitoring_ready_again(self):
        """True the first season a monitoring crew is available again, for a
        player who has used monitoring before (so it never nags anyone else)."""
        return (
            self.monitoring_reports > 0
            and self.monitoring_last_season > 0
            and self.can_monitor()
            and self.season - self.monitoring_last_season == MONITOR_COOLDOWN_SEASONS
        )

    def attention_reasons(self):
        """Things that deserve a decision before another season passes, as
        (kind, plain-language text). Advance x5 only runs while this is empty."""
        reasons = []
        wait = self.seasons_until_storm()
        if wait is not None and wait <= 1:
            when = "this season" if wait == 0 else "next season"
            reasons.append(("storm", f"a storm surge is forecast for {when}"))
        if self.fish_warning_active():
            reasons.append(("fish", "a fish-yield warning is showing"))
        for site in self.heritage_at_risk():
            reasons.append(("heritage", f"the {site['name'].lower()} is at risk and can be protected"))
        if self.monitoring_ready_again():
            reasons.append(("monitor", "a monitoring crew is available again"))
        return reasons

    def advance_quiet_seasons(self, count=ADVANCE_BATCH):
        """Runs up to `count` seasons, stopping BEFORE any season that has
        something needing attention. Returns (seasons_run, stop_text); stop_text
        is None when all `count` seasons ran quietly."""
        run = 0
        for _ in range(max(0, int(count))):
            reasons = self.attention_reasons()
            if reasons:
                return run, "; ".join(text for _kind, text in reasons)
            self.advance_season()
            run += 1
        return run, None

    # ---- D-7 screen-reader text --------------------------------------
    def coast_view(self):
        """The live coastline as a plain dict, the same shape scrub_snapshot()
        returns, so one renderer and one description can draw either."""
        return {
            "sea_level": self.sea_level, "tier": self.current_tier_index(),
            "heritage": self.heritage, "retreat_rows": self.retreat_rows,
            "tidal": self.tidal_rows(),
        }

    def coastline_row_description(self, row, view=None, col=None):
        """e.g. "Row 5: dry, seawall tier 2" -- the text twin of one grid row. With `col`
        it names one tile ("Row 5, column 3: dry, ..."); only the heritage column mentions
        the heritage site. `view` describes a scrubbed past season instead of the live one."""
        view = view or self.coast_view()
        if row in view["retreat_rows"]:
            status = "cleared by managed retreat"
        elif tile_row_state(row, view["sea_level"], self.coastline) == FLOODED:
            status = "flooded"
        else:
            status = "dry"
        parts = [status]
        tier_index = view["tier"]
        if tier_index and _is_seawall_row(row, tier_index):
            parts.append(f"seawall tier {tier_index}")
        site = next((x for x in heritage_sites(self.coastline) if x["row"] == row), None)
        if site is not None and (col is None or col == HERITAGE_COL):
            heritage = view["heritage"].get(site["id"])
            parts.append(f"{site['name'].lower()} {heritage}")
        if row in view.get("tidal", ()):
            parts.append("washed by this season's tide")
        where = f"Row {row + 1}" + (f", column {col + 1}" if col is not None else "")
        return f"{where}: " + ", ".join(parts)

    def coastline_description(self):
        lines = [self.coastline_row_description(r) for r in range(COASTLINE_ROWS)]
        return (
            f"Coastline, {COASTLINE_ROWS} rows from row 1 (highest ground) to row {COASTLINE_ROWS} "
            f"(at the shore). {self.rows_dry_count()} dry. " + ". ".join(lines) + "."
        )

    def season_result_text(self):
        """What a screen reader announces after a season resolves."""
        if not self.season_ledger:
            return f"Season {self.season}."
        last = self.season_ledger[-1]
        text = (
            f"Season {last['season']} resolved. Now Season {self.season}. "
            f"Funds {self.funds:.0f}. Ocean acidity {self.acidity:.1f}. "
            f"Fishing yield {self.fish_yield_multiplier() * 100:.0f} percent. "
            f"Damage this season {last['damage']:.0f}. "
            f"{self.rows_dry_count()} of {COASTLINE_ROWS} coastline rows dry."
        )
        if self.ticker_log:
            text += " Latest: " + self.ticker_log[-1]
        return text

    # ---- D-18 copy as text -------------------------------------------
    def share_text(self):
        lines = [
            f"{self.display_name()} — a Tide settlement",
            self.session_summary_text(),
            f"Population {self.population} (peak {self.peak_population}); "
            f"{self.rows_dry_count()} of {COASTLINE_ROWS} coastline rows dry; "
            f"sea scenario: {self.sea_scenario}.",
        ]
        chronicle = self.chronicle_lines()
        if chronicle:
            lines.append("")
            lines.append("Chronicle:")
            lines.extend(chronicle)
        return "\n".join(lines)

    def _log_ticker(self, message):
        """Every ticker-producing method routes through here so the short
        live ticker (ticker_log, capped at TICKER_LOG_LIMIT) and D5's
        long-form history (ticker_full_history, capped much higher) never
        drift out of sync with each other."""
        self.ticker_log.append(message)
        self.ticker_log = self.ticker_log[-TICKER_LOG_LIMIT:]
        self.ticker_full_history.append(message)
        self.ticker_full_history = self.ticker_full_history[-TICKER_FULL_HISTORY_LIMIT:]

    def _record_ticker_message(self, acidity_change, old_fish_yield, new_fish_yield):
        """Delayed-effect ticker: narrates the lag as it builds and
        lands, so cause stays traceable in hindsight without spelling
        out the mechanic outright. Iteration-pass addition."""
        lag = self._effective_fish_lag()
        message = None
        if new_fish_yield < old_fish_yield - 1e-6:
            message = (
                f"Fish stocks quietly declining — acidity from {lag} "
                f"seasons ago is catching up."
            )
        elif new_fish_yield > old_fish_yield + 1e-6:
            message = "Fish stocks recovering as past acidity spikes fade from the lag window."
        elif acidity_change > 0 and len(self.acidity_history) <= lag:
            message = "Acidity is rising — the effect on fish stocks won't show for a few more seasons."

        if message:
            self._log_ticker(message)

    def _record_tier_unlock_message(self, tier_index):
        """Iteration Pass 3 — immediate, visible payoff at the moment an
        adaptation tier unlocks, logged into the same ticker the player
        is already reading for decline/recovery. Without this, a tier
        upgrade was only a passive label change the player might not
        notice; this makes "you just made things better" as legible as
        the ticker already makes decline."""
        tier = ADAPTATION_TIERS[tier_index]
        message = (
            f"Adaptation upgraded to {tier['name']} — sea-level damage is now "
            f"dampened {tier['dampening'] * 100:.0f}%, effective immediately."
        )
        self._log_ticker(message)
        self._chronicle_event(f"{tier['name']} completed along the shore.")

    def _record_trend_message(self):
        """Iteration Pass 3 — recovery narration for the delayed damage
        trend: fires once, the first season the damage curve visibly
        flattens (mirrors the existing damage_trend() comparison used
        for the static display), so the player gets the same kind of
        clear, in-the-moment feedback for "adaptation is working" that
        the ticker already gives for fish-stock decline."""
        if self.trend_flattening_announced:
            return
        trend = self.damage_trend()
        if trend is None:
            return
        first_half_avg, second_half_avg = trend
        if second_half_avg < first_half_avg - 1e-6:
            self.trend_flattening_announced = True
            message = (
                f"Damage curve flattening ({first_half_avg:.1f}/season -> "
                f"{second_half_avg:.1f}/season) — your adaptation spending is visibly working."
            )
            self._log_ticker(message)

    def _record_first_flood_message(self):
        """D17: a one-time callout the first season any coastline row
        actually floods -- distinct from the ongoing decline/recovery/
        tier-unlock narration above, this one only ever fires once per
        settlement, ever."""
        if self.first_flood_announced:
            return
        if flooded_row_count(self.sea_level, self.coastline) >= 1:
            self.first_flood_announced = True
            self._log_ticker(
                "The first coastline tile has flooded — the sea has arrived."
            )
            self._chronicle_event("The first stretch of coast went under.")

    def advance_season(self):
        self.season_buys.append(list(self.buys_now))  # D-3: what was bought in the season now resolving
        self.season_buys = self.season_buys[-LEDGER_LIMIT:]
        self.buys_now = [0, 0, 0]
        old_fish_yield = self.fish_yield_multiplier()
        mix = OUTPUT_MIX[self.output_mix]
        fishing_share = mix["fishing_share"]
        income = self.capacity["output"] * OUTPUT_INCOME_PER_UNIT * (
            fishing_share * old_fish_yield + (1 - fishing_share)
        )
        if self.coast_weight("output") != 1.0:  # D-8
            income *= self.coast_weight("output")
        tourism_income, aquaculture_income = self.diversified_income()
        funds_start = self.funds  # D-28
        # GD-14: investing in all three categories this season extends the balanced streak; skipping one breaks it.
        balanced = set(CATEGORIES) <= self.season_invested
        self.balance_streak = self.balance_streak + 1 if balanced else 0
        multiplier = BALANCE_MULTIPLIERS[min(self.balance_streak, len(BALANCE_MULTIPLIERS) - 1)]
        self.season_invested = set()
        if self.income_dip_seasons > 0:  # GD-8: the price of an accepted deal
            multiplier *= MARKET_DIP_FACTOR
            self.income_dip_seasons -= 1
        bonus = (income + tourism_income + aquaculture_income) * (multiplier - 1.0)
        if bonus > 0 and multiplier > 1.0:
            self._log_ticker(f"Balanced seasons x{multiplier:.1f}: +{bonus:.0f} income from investing in all three.")
        self.funds += (income + tourism_income + aquaculture_income) * multiplier
        if self.domino_seasons_left > 0:  # GD-28: the comeback discount runs down one season at a time
            self.domino_seasons_left -= 1
        rows_flooded_before = flooded_row_count(self.sea_level, self.coastline)
        self.max_funds_ever = max(self.max_funds_ever, self.funds)

        output_rise = self.capacity["output"] * ACIDITY_RISE_PER_OUTPUT * mix["acidity_multiplier"]
        if self.chess_mode:  # GD-4: half the output acidity arrives CHESS_RUNOFF_LAG seasons late
            late = output_rise * CHESS_RUNOFF_SHARE
            self.runoff_queue.append(late)
            arriving = self.runoff_queue.pop(0) if len(self.runoff_queue) > CHESS_RUNOFF_LAG else 0.0
            output_rise = output_rise - late + arriving
        acidity_change = (
            output_rise
            - self.capacity["reduction"] * ACIDITY_FALL_PER_REDUCTION
        )
        acidity_start = self.acidity  # D-28
        self.acidity = max(0.0, self.acidity + acidity_change)
        self._resolve_acid_boss()  # GD-12: the spike lands before this season's acidity is recorded
        self.acidity_history.append(self.acidity)
        self.max_acidity_ever = max(self.max_acidity_ever, self.acidity)

        rise = self.sea_rise_per_season()
        self.sea_level += rise
        newly_flooded = flooded_row_count(self.sea_level, self.coastline) - rows_flooded_before
        if newly_flooded >= DOMINO_MIN_ROWS:  # GD-28: a disaster that becomes a pivot
            self.domino_seasons_left = DOMINO_DISCOUNT_SEASONS
            self.domino_count += 1
            self._log_ticker(f"Domino season: {newly_flooded} rows flooded at once. Emergency funds make adaptation "
                             f"{round(DOMINO_DISCOUNT * 100)}% cheaper for {DOMINO_DISCOUNT_SEASONS} seasons.")
            self._chronicle_event(f"{newly_flooded} rows went under in one season; the town rallied behind the walls.")
        damage_this_season = rise * (1 - self.dampening_fraction())
        self.cumulative_damage += damage_this_season
        self.undampened_damage_total += rise
        self.damage_log.append(damage_this_season)
        self.tier_log.append(self.current_tier_index())
        self._advance_sister(rise)

        funds_before_upkeep = self.funds  # D-28
        self._update_heritage()
        upkeep_paid = funds_before_upkeep - self.funds
        wages_before = self.funds
        self.funds = max(0.0, self.funds - CREW_WAGE * len(self.crew))  # GD-11
        wages_paid = wages_before - self.funds
        self._update_population()
        funds_before_storm = self.funds
        if self.storm_this_season():
            self._resolve_storm()
            if self.last_storm_result != "Breached":  # D-10
                self.storms_weathered += 1
                if newly_flooded == 0:
                    self.storms_clean += 1
        storm_cost = funds_before_storm - self.funds
        self.last_breakdown = {  # D-28
            "acidity": {
                "from": acidity_start, "to": self.acidity,
                "parts": [
                    ("Output pushing acidity up", output_rise),
                    ("Reduction pulling it down", -self.capacity["reduction"] * ACIDITY_FALL_PER_REDUCTION),
                ],
            },
            "funds": {
                "from": funds_start, "to": self.funds,
                "parts": [
                    ("Output income", income * multiplier),
                    ("Tourism", tourism_income * multiplier),
                    ("Aquaculture", aquaculture_income * multiplier),
                    ("Heritage upkeep", -upkeep_paid),
                    ("Crew wages", -wages_paid),
                    ("Storm repairs", -storm_cost),
                ],
            },
        }

        self.season += 1
        if not self.hard_lag_mode:  # GD-24: the badge needs hard lag for the whole run
            self.hard_lag_all_run = False
        if (not self.ironman_earned and self.hard_lag_all_run and self.season - 1 >= IRONMAN_SEASONS
                and not self.rewind_used and self.replay_count == 0):
            self.ironman_earned = True
            self._log_ticker(f"\u2693 Ironman: {IRONMAN_SEASONS} seasons in Hard Lag with no Rewind and no checkpoint replay.")
            self._chronicle_event(f"The harbour held for {IRONMAN_SEASONS} seasons of hard lag without turning back the clock.")

        self._update_market()  # GD-8
        new_fish_yield = self.fish_yield_multiplier()
        self.fish_yield_history.append(new_fish_yield)
        self.min_fish_yield_ever = min(self.min_fish_yield_ever, new_fish_yield)
        if self.chess_mode and new_fish_yield <= FISH_YIELD_WARNING_THRESHOLD:  # GD-4
            self.chess_dips += 1
        self._record_ledger_entry(self.season - 1, damage_this_season, new_fish_yield)
        self._record_snapshot(self.season - 1)

        self._record_ticker_message(acidity_change, old_fish_yield, new_fish_yield)
        self._record_trend_message()
        self._record_first_flood_message()
        self._record_recovery_message(new_fish_yield)

    def _record_recovery_message(self, fish_yield):
        """D23: a celebratory callout, equal in weight to the decline
        narration, once a crashed stock rebuilds."""
        if fish_yield <= FISH_CRASH_LEVEL:
            if not self.fish_crash_open:
                self._chronicle_event("The fish stocks crashed; boats came back near-empty.")
            self.fish_crash_open = True
        elif self.fish_crash_open and fish_yield >= FISH_RECOVERED_LEVEL:
            self.fish_crash_open = False
            self.recovery_celebrated_season = self.season
            self._chronicle_event("The fish stocks rebuilt after the lean years.")
            self._log_ticker(
                f"🎉 The fish stock has rebuilt to {fish_yield * 100:.0f}% — the "
                "consequence of past acidity has finally faded. Cleaner choices paid off."
            )

    def damage_saved(self):
        """The hope-angle payoff, as a direct number: how much less
        cumulative damage the settlement has taken than it would have
        with zero adaptation investment, ever."""
        return self.undampened_damage_total - self.cumulative_damage

    def damage_trend(self):
        """Compares the first half of seasons played to the second half —
        a visibly flattening damage curve is the direct, legible reward
        for early adaptation investment, not just a good final number."""
        n = len(self.damage_log)
        if n < 4:
            return None
        half = n // 2
        first_half_avg = sum(self.damage_log[:half]) / half
        second_half_avg = sum(self.damage_log[half:]) / (n - half)
        return first_half_avg, second_half_avg


class SettlementState(SettlementTownMixin, SettlementEconomyMixin, SettlementSeasonMixin):
    """One settlement: the three mixins above hold the methods (split so no file is too big for the small local AI);
    __init__ is in SettlementTownMixin."""


runstate.state = SettlementState()
