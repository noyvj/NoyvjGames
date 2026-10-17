"""SettlementState, part 1 of 3 (SettlementTownMixin): starting values, retreat, population, diversification, checkpoint, heritage, citizen science, storms and bracing, naming, tides."""

import math

from tide_coasts import (
    coast_storm_interval, flooded_row_count, heritage_sites, row_flood_threshold, tile_row_state,
)
from tide_rules import (
    AQUACULTURE_ACIDITY_SCALE, AQUACULTURE_INCOME_PER_LEVEL, AQUACULTURE_MIN_MULTIPLIER,
    BARRIER_FUNDS_PER_SURGE, BRACE_STEP, BRACE_WINDOW, CATEGORIES, CHECKPOINT_DROP_KEYS, CHRONICLE_LIMIT,
    CITIZEN_SCIENCE_FACTS, COASTLINES, COASTLINE_ROWS, DEFAULT_COASTLINE, DEFAULT_OUTPUT_MIX,
    DEFAULT_SEA_SCENARIO, DIVERSIFY_COST, DIVERSIFY_MAX_LEVEL, EVACUATE_COST, FISH_DAMAGE_SCALE, FLOODED,
    HERITAGE_LOST, HERITAGE_PROTECTED, HERITAGE_UNPROTECTED, HERITAGE_UPKEEP, MIN_FISH_MULTIPLIER,
    MONITOR_COOLDOWN_SEASONS, MONITOR_COST, POP_GROWTH_MIN_FISH_YIELD, POP_GROWTH_RATE, POP_PER_ROW,
    POP_PER_ROW_PER_TIER, POP_START, RESCUE_WITHIN_SEASONS, RETREAT_COST, RETREAT_DAMAGE_CUT,
    RETREAT_EARLY_MAX_FLOODED, RETREAT_MAX_STEPS, SEA_SCENARIOS, SETTLEMENT_NAME_MAX, STARTING_FUNDS,
    STORM_BASE_SURGE, STORM_FUNDS_PER_DAMAGE, STORM_RESULT_TIERS, STORM_SURGE_GROWTH, TIDE_AMPLITUDE,
    TIDE_HIGH_CUTOFF, TIDE_PERIOD_FACTOR, TOURISM_HERITAGE_BONUS, TOURISM_INCOME_PER_LEVEL,
    WORKSHOP_DEFAULTS,
)


# get_state() is defined in tide_savestate, which comes later in the module list; that module puts it here when it
# loads (see the end of tide_savestate.py). Calls below find it at run time.
get_state = None


class SettlementTownMixin:
    """SettlementState, part 1 of 3: starting values, retreat, population, diversification, checkpoint, heritage,
    citizen science, storms and bracing, naming, tides, workshop and coastline settings."""

    def __init__(self):
        self.season = 1
        self.funds = STARTING_FUNDS
        self.capacity = {c: 0 for c in CATEGORIES}
        self.acidity = 0.0
        self.acidity_history = []
        self.sea_level = 0.0
        self.cumulative_damage = 0.0
        self.undampened_damage_total = 0.0
        self.damage_log = []
        self.ticker_log = []
        # Iteration Pass 3 — fires once, the first season the damage curve
        # visibly flattens, so the ticker confirms recovery instead of
        # only the static damage-trend text passively updating.
        self.trend_flattening_announced = False

        # D5: the same ticker messages as ticker_log, but never truncated
        # below TICKER_FULL_HISTORY_LIMIT -- backs the expandable "full
        # history" panel, ticker_log stays the short live-glance version.
        self.ticker_full_history = []
        # D9: optional harder delayed-consequence lag (see
        # FISH_LAG_SEASONS_HARD/_effective_fish_lag()).
        self.hard_lag_mode = False
        # D3: the optional sister settlement (see SISTER_* above).
        self.sister_enabled = False
        self.sister_cumulative_damage = 0.0
        self.sister_net_funds = 0.0
        # D16: which income/acidity mix Output investment currently uses.
        # "fishing" reproduces the original single-formula behavior.
        self.output_mix = DEFAULT_OUTPUT_MIX
        # D15: fish_yield_multiplier() sampled once per season, parallel
        # to acidity_history, so a mini-graph can chart both together.
        self.fish_yield_history = []
        # D17: fires once, the very first time any coastline row floods.
        self.first_flood_announced = False
        # D18: a player-chosen checkpoint the "then vs. now" comparison
        # (render_coastline_comparison()/then_vs_now_text()) measures
        # against, instead of always the literal Season 1 start. Defaults
        # to the real start, so an untouched game behaves exactly as
        # before this feature existed.
        self.baseline_season = 1
        self.baseline_sea_level = 0.0
        self.baseline_damage = 0.0

        # Achievements' new tracked state (ACHIEVEMENTS-SYSTEM-DESIGN.md
        # §4): each of these answers "did this ever happen / how far did
        # this ever go", which the current-moment fields above can't
        # answer on their own once the number moves back the other way
        # (funds get spent, fish yield recovers, acidity falls).
        self.min_fish_yield_ever = 1.0
        self.max_acidity_ever = 0.0
        self.max_funds_ever = STARTING_FUNDS
        # Set once, inside invest()'s own tier-unlock branch, the instant
        # the top adaptation tier is reached while zero coastline rows are
        # flooded yet -- a genuine "before" fact that flooded_row_count()
        # alone can't recover later once the sea catches up.
        self.fortified_in_time_earned = False
        # D-10: the ranked achievements need three more "did this ever happen" counters (the rest of their
        # numbers already exist: protected sites, retreat rows, diversification levels, reports, peak population).
        self.storms_weathered = 0   # storms that did not breach the defences
        self.storms_clean = 0       # of those, storms in a season when no coastline row flooded
        self.early_retreats = 0     # managed retreats taken while at most one row had flooded

        # D2: adaptation tier index active during each season, parallel
        # to damage_log, so the worst-season callout can name what was
        # (or wasn't) protecting the coast then.
        self.tier_log = []
        # D30: the one-time "takes effect next season" note for hard lag.
        self.hard_lag_note_seen = False
        # D23: a crash is "open" once yield dips to FISH_CRASH_LEVEL; the
        # recovery celebration fires once when it climbs back.
        self.fish_crash_open = False
        self.recovery_celebrated_season = 0
        # D19: sea-level-rise scenario (locked after the first season).
        self.sea_scenario = DEFAULT_SEA_SCENARIO
        # D-8: the named coastline (elevation, heritage, economy, storms); locked after the first season like the scenario.
        self.coastline = DEFAULT_COASTLINE
        # GD-5: a Daily Tide run ({"date", "seed", "storms", "done", ...}) or None for an ordinary run.
        self.daily = None
        # D-3: purchases per resolved season ([output, reduction, adaptation]) and the running season's counts, so a
        # finished run can be shared as a run code.
        self.season_buys = []
        self.buys_now = [0, 0, 0]
        # D29: a light diegetic layer -- an optional player-chosen name
        # plus a short chronicle of the settlement's notable moments.
        self.settlement_name = ""
        self.chronicle = []
        # D17: id -> HERITAGE_* status.
        self.heritage = {site["id"]: HERITAGE_UNPROTECTED for site in heritage_sites(self.coastline)}
        # D21: how many facts revealed, and the season of the last report.
        self.monitoring_reports = 0
        self.monitoring_last_season = 0
        # D13: opt-in storm seasons.
        self.storm_mode = False
        self.storm_log = []
        # D1: rows given up on purpose (row indices, lowest first).
        self.retreat_rows = []
        # D5 / D15: population and displacement counters.
        self.population = POP_START
        self.peak_population = POP_START
        self.displaced_total = 0
        self.relocated_total = 0
        # D11: level of each diversified income source.
        self.diversification = {"tourism": 0, "aquaculture": 0}
        # D27: a saved snapshot of the run, and the "foresight" record of
        # what happened after it the last time the player replayed from it.
        self.checkpoint = None
        self.foresight = []
        self.replay_count = 0
        # D-1: one dict per resolved season (see _record_ledger_entry()).
        self.season_ledger = []
        # D-4: one compact snapshot per resolved season (see _record_snapshot()).
        self.season_snapshots = []
        # GD-19: the one personal goal pinned under the header, and whether its ping already fired.
        self.pinned_goal = ""
        self.pinned_goal_reached = False
        # GD-14: categories invested in this season, and how many seasons in a row had all three.
        self.season_invested = set()
        self.balance_streak = 0
        # GD-28: seasons of cheaper adaptation left after a domino season.
        self.domino_seasons_left = 0
        self.domino_count = 0
        # GD-20: the single Rewind charge; GD-24: ironman bookkeeping; GD-23: clicks and active seconds so far,
        # and the totals at the moment the top adaptation tier was reached.
        self.rewind_used = False
        self.hard_lag_all_run = True
        self.ironman_earned = False
        self.actions_count = 0
        self.active_seconds = 0.0
        self.maxtier_actions = None
        self.maxtier_seconds = None
        # GD-18: ids of the critters the player has clicked into the Sightings list.
        self.sightings = []
        # GD-4: Tidal Chess mode, the runoff still on its way, and seasons the fish yield sat at the warning level.
        self.chess_mode = False
        self.runoff_queue = []
        self.chess_dips = 0
        # GD-3: funds committed to brace for the next storm, and how the last storm ended.
        self.brace = {"barriers": 0, "stockpile": 0, "evacuate": False}
        self.last_storm_result = ""
        # GD-12: the opt-in boss: mode, braced yes/no, and how it ended ("", "survived" or "hit").
        self.acid_boss_mode = False
        self.acid_braced = False
        self.acid_boss_result = ""
        # D-5: the Workshop dials for this run (see WORKSHOP_DEFAULTS).
        self.workshop = dict(WORKSHOP_DEFAULTS)
        # GD-11: the specialists on the payroll.
        self.crew = []
        # GD-8: the deal on the table right now ({"kind", "gain", "season"} or None), how many deals were accepted,
        # and the seasons of slower income an accepted deal can leave behind.
        self.market_event = None
        self.market_accepted = 0
        self.income_dip_seasons = 0
        # D-28: where the last season's acidity and funds changes came from (transient, never saved).
        self.last_breakdown = None
        # GD-27: the site most recently saved at the last second (transient, shown once, never saved).
        self.last_rescue = None

    # ---- GD-25 quiet seasons -----------------------------------------
    def quiet_seasons(self):
        """Seasons in a row (counting back from the latest) in which acidity did not rise."""
        history = self.acidity_history
        count = 0
        for i in range(len(history) - 1, -1, -1):
            previous = history[i - 1] if i > 0 else 0.0
            if history[i] > previous + 1e-9:
                break
            count += 1
        return count

    # ---- D1 managed retreat ------------------------------------------
    def row_lost(self, row):
        """True for a flooded row and for one given up by managed retreat."""
        return row in self.retreat_rows or tile_row_state(row, self.sea_level, self.coastline) == FLOODED

    def next_retreat_row(self):
        for row in range(COASTLINE_ROWS - 1, -1, -1):
            if not self.row_lost(row):
                return row
        return None

    def can_retreat(self):
        return (
            len(self.retreat_rows) < RETREAT_MAX_STEPS
            and self.funds >= RETREAT_COST
            and self.next_retreat_row() is not None
        )

    def managed_retreat(self):
        if not self.can_retreat():
            return False
        row = self.next_retreat_row()
        if flooded_row_count(self.sea_level, self.coastline) <= RETREAT_EARLY_MAX_FLOODED:  # D-10
            self.early_retreats += 1
        self.funds -= RETREAT_COST
        self.retreat_rows.append(row)
        self._log_ticker(
            f"Managed retreat: row {row + 1} was cleared and its people rehoused inland — "
            f"sea-level damage is now permanently {RETREAT_DAMAGE_CUT * 100:.0f}% lower per step."
        )
        self._chronicle_event(f"The council chose an orderly retreat from row {row + 1}.")
        self._update_heritage()
        self._update_population(orderly=True)
        return True

    # ---- D5 / D15 population -----------------------------------------
    def housing_capacity(self):
        land_rows = sum(1 for row in range(COASTLINE_ROWS) if not self.row_lost(row))
        return land_rows * (POP_PER_ROW + POP_PER_ROW_PER_TIER * self.current_tier_index())

    def _update_population(self, orderly=False):
        """Displaces the excess when housing shrinks below the population,
        otherwise grows toward capacity while fish yield is healthy."""
        capacity = self.housing_capacity()
        if self.population > capacity:
            displaced = self.population - capacity
            self.population = capacity
            if orderly or self.retreat_rows:
                relocated = displaced // 2 if not orderly else displaced
                self.relocated_total += relocated
                self.displaced_total += displaced - relocated
            else:
                self.displaced_total += displaced
            self._log_ticker(
                f"{displaced} people had to leave the flooded coast"
                + (" (many rehoused in an orderly retreat)." if orderly or self.retreat_rows else " — refugees moving inland.")
            )
            self._chronicle_event(f"{displaced} residents relocated inland.")
        elif (
            self.population < capacity
            and self.fish_yield_multiplier() >= POP_GROWTH_MIN_FISH_YIELD
        ):
            growth = max(1, round(self.population * POP_GROWTH_RATE))
            self.population = min(capacity, self.population + growth)
        self.peak_population = max(self.peak_population, self.population)

    def population_text(self):
        text = f"Population {self.population} of {self.housing_capacity()} housing (peak {self.peak_population})."
        if self.displaced_total or self.relocated_total:
            text += f" Displaced so far: {self.displaced_total}; rehoused in orderly retreat: {self.relocated_total}."
        return text

    # ---- D11 diversification -----------------------------------------
    def diversify(self, kind):
        if kind not in DIVERSIFY_COST or self.diversification[kind] >= DIVERSIFY_MAX_LEVEL:
            return False
        if self.funds < DIVERSIFY_COST[kind]:
            return False
        self.funds -= DIVERSIFY_COST[kind]
        self.diversification[kind] += 1
        self._log_ticker(f"Economy diversified: {kind} is now level {self.diversification[kind]}.")
        return True

    def diversified_income(self):
        """(tourism, aquaculture) income per season at the current state."""
        land_rows = sum(1 for row in range(COASTLINE_ROWS) if not self.row_lost(row))
        tourism = self.diversification["tourism"] * (
            TOURISM_INCOME_PER_LEVEL * land_rows / COASTLINE_ROWS
            + TOURISM_HERITAGE_BONUS * self.protected_heritage_count()
        )
        if self.coast_weight("tourism") != 1.0:  # D-8
            tourism *= self.coast_weight("tourism")
        multiplier = max(AQUACULTURE_MIN_MULTIPLIER, 1 - self.acidity / AQUACULTURE_ACIDITY_SCALE)
        aquaculture = self.diversification["aquaculture"] * AQUACULTURE_INCOME_PER_LEVEL * multiplier
        if self.coast_weight("aquaculture") != 1.0:  # D-8
            aquaculture *= self.coast_weight("aquaculture")
        return tourism, aquaculture

    # ---- D27 checkpoint replay ---------------------------------------
    def set_checkpoint(self):
        snapshot = get_state()
        for key in CHECKPOINT_DROP_KEYS:
            snapshot.pop(key, None)
        snapshot.pop("checkpoint", None)
        snapshot.pop("foresight", None)
        self.checkpoint = snapshot
        self._log_ticker(f"Checkpoint saved at Season {self.season}.")

    def can_replay(self):
        return self.checkpoint is not None and self.season > self.checkpoint["season"]

    def foresight_text(self):
        """What the earlier run did in the seasons ahead, for the season the
        replay is currently in."""
        if not self.foresight:
            return ""
        upcoming = [e for e in self.foresight if e["season"] >= self.season][:3]
        if not upcoming:
            return "You have passed everything the earlier run showed you."
        parts = [
            f"Season {e['season']}: fish yield {e['fish_yield'] * 100:.0f}%, "
            f"{e['damage']:.0f} damage, {e['flooded']} row(s) flooded"
            for e in upcoming
        ]
        return "Foresight from your earlier run — " + " | ".join(parts)

    # ---- D17 heritage ------------------------------------------------
    def protect_heritage(self, site_id):
        site = next((x for x in heritage_sites(self.coastline) if x["id"] == site_id), None)
        if site is None or self.heritage.get(site_id) != HERITAGE_UNPROTECTED:
            return False
        if self.funds < site["cost"] or self.row_lost(site["row"]):
            return False
        self.funds -= site["cost"]
        self.heritage[site_id] = HERITAGE_PROTECTED
        self._log_ticker(f"{site['name']} is now protected — it will outlast the flood, at a small upkeep each season.")
        self._chronicle_event(f"Townsfolk pooled funds to protect the {site['name'].lower()}.")
        if self.seasons_until_flood(site["row"]) <= RESCUE_WITHIN_SEASONS:  # GD-27: saved at the last second
            self.last_rescue = site_id
            self._log_ticker(f"\U0001F6DF SAVED! The {site['name'].lower()} was protected with its row about to flood.")
            self._chronicle_event(f"The {site['name'].lower()} was saved at the last second, just before its row flooded.")
        return True

    def protected_heritage_count(self):
        return sum(1 for v in self.heritage.values() if v == HERITAGE_PROTECTED)

    def _update_heritage(self):
        """Unprotected sites whose row has flooded are lost; protected ones
        cost upkeep (never below zero funds)."""
        for site in heritage_sites(self.coastline):
            if (
                self.heritage.get(site["id"]) == HERITAGE_UNPROTECTED
                and self.row_lost(site["row"])
            ):
                self.heritage[site["id"]] = HERITAGE_LOST
                self._log_ticker(f"The {site['name'].lower()} has been lost to the sea.")
                self._chronicle_event(f"The {site['name'].lower()} was swallowed by the sea.")
        self.funds = max(0.0, self.funds - HERITAGE_UPKEEP * self.protected_heritage_count())

    # ---- D21 citizen science -----------------------------------------
    def can_monitor(self):
        if self.monitoring_reports >= len(CITIZEN_SCIENCE_FACTS) or self.funds < MONITOR_COST:
            return False
        return (
            self.monitoring_last_season == 0
            or self.season - self.monitoring_last_season >= MONITOR_COOLDOWN_SEASONS
        )

    def fund_monitoring(self):
        if not self.can_monitor():
            return False
        self.funds -= MONITOR_COST
        self.monitoring_reports += 1
        self.monitoring_last_season = self.season
        self._log_ticker("Monitoring report in: " + CITIZEN_SCIENCE_FACTS[self.monitoring_reports - 1])
        return True

    def revealed_facts(self):
        return CITIZEN_SCIENCE_FACTS[: self.monitoring_reports]

    # ---- D13 storms --------------------------------------------------
    def set_storm_mode(self, enabled):
        self.storm_mode = bool(enabled) or bool(self.daily)  # GD-5: a daily's storms stay on

    def storm_this_season(self):
        if self.daily and self.daily.get("storms"):  # GD-5: the day's seeded storm seasons
            return self.storm_mode and self.season in self.daily["storms"]
        return self.storm_mode and self.season % coast_storm_interval(self.coastline) == 0

    def seasons_until_storm(self):
        """0 if the storm lands when this season resolves; None when off."""
        if not self.storm_mode:
            return None
        if self.daily and self.daily.get("storms"):
            ahead = [s - self.season for s in self.daily["storms"] if s >= self.season]
            return min(ahead) if ahead else None
        return (-self.season) % coast_storm_interval(self.coastline)

    def storm_surge_strength(self):
        base = (STORM_BASE_SURGE + STORM_SURGE_GROWTH * len(self.storm_log)) * self.workshop["surge"]
        weight = COASTLINES[self.coastline]["surge"]
        return base * weight if weight != 1.0 else base

    # ---- GD-3 bracing ------------------------------------------------------
    def can_brace_storm(self):
        wait = self.seasons_until_storm()
        return self.storm_mode and wait is not None and wait <= BRACE_WINDOW

    def add_brace(self, kind):
        if not self.can_brace_storm():
            return False
        if kind in ("barriers", "stockpile"):
            if self.funds < BRACE_STEP:
                return False
            self.funds -= BRACE_STEP
            self.brace[kind] += BRACE_STEP
            return True
        if kind == "evacuate":
            exposed = [x for x in heritage_sites(self.coastline) if self.heritage.get(x["id"]) == HERITAGE_UNPROTECTED]
            if self.brace["evacuate"] or not exposed or self.funds < EVACUATE_COST:
                return False
            self.funds -= EVACUATE_COST
            self.brace["evacuate"] = True
            return True
        return False

    def brace_text(self):
        if not self.can_brace_storm():
            return ""
        b = self.brace
        held = b["barriers"] / BARRIER_FUNDS_PER_SURGE
        return (f"Brace for the storm: barriers {b['barriers']} (holds back {held:.0f} more surge), stockpile {b['stockpile']}, "
                f"{'heritage evacuated' if b['evacuate'] else 'heritage not evacuated'}.")

    def _resolve_storm(self):
        """Called while advance_season() resolves a season. The surge is cut
        by the current dampening; what gets through costs funds. GD-3: committed brace funds cut it further."""
        surge = self.storm_surge_strength()
        extra_held = self.brace["barriers"] / BARRIER_FUNDS_PER_SURGE
        taken = max(0.0, surge * (1 - self.dampening_fraction()) - extra_held)
        funds_lost = min(self.funds + self.brace["stockpile"], taken * STORM_FUNDS_PER_DAMAGE)
        from_stockpile = min(self.brace["stockpile"], funds_lost)
        self.funds += self.brace["stockpile"] - from_stockpile  # the unused stockpile comes back
        funds_lost -= from_stockpile
        ratio = taken / surge if surge else 0.0
        self.last_storm_result = next(label for limit, label in STORM_RESULT_TIERS if ratio < limit)
        if self.last_storm_result == "Breached":
            for site in heritage_sites(self.coastline):
                if self.heritage.get(site["id"]) == HERITAGE_UNPROTECTED and not self.brace["evacuate"]:
                    self.heritage[site["id"]] = HERITAGE_LOST
                    self._log_ticker(f"The {site['name'].lower()} was lost when the storm breached the defences.")
        self.brace = {"barriers": 0, "stockpile": 0, "evacuate": False}
        self.funds -= funds_lost
        self.storm_log.append(
            {"season": self.season, "surge": surge, "taken": taken, "blocked": surge - taken}
        )
        self.storm_log = self.storm_log[-20:]
        self._log_ticker(
            f"⛈️ Storm surge in Season {self.season} ({self.last_storm_result}): {surge - taken:.0f} of {surge:.0f} held back "
            f"by your defences; the rest cost {funds_lost:.0f} funds."
        )
        self._chronicle_event(f"A storm surge struck; defences held back {surge - taken:.0f} of {surge:.0f}.")

    def set_settlement_name(self, name):
        """D29: trims, collapses whitespace and caps the length; anything
        that isn't a string is ignored (no crash, no partial change)."""
        if not isinstance(name, str):
            return False
        cleaned = " ".join(name.split())[:SETTLEMENT_NAME_MAX]
        self.settlement_name = cleaned
        return True

    def display_name(self):
        return self.settlement_name or "Your settlement"

    def _chronicle_event(self, text):
        """D29: appends one dated line to the settlement's history."""
        self.chronicle.append({"season": self.season, "text": text})
        self.chronicle = self.chronicle[-CHRONICLE_LIMIT:]

    def chronicle_lines(self):
        return [f"Season {e['season']}: {e['text']}" for e in self.chronicle]

    def tide_offset(self):
        """D8: this season's tide height relative to mean sea level, a
        deterministic function of the season number (so it needs no saved
        state and a loaded save shows the same tide)."""
        return round(TIDE_AMPLITUDE * math.sin(self.season * TIDE_PERIOD_FACTOR), 1)

    def tide_label(self):
        offset = self.tide_offset()
        if offset >= TIDE_HIGH_CUTOFF:
            return "High"
        if offset <= -TIDE_HIGH_CUTOFF:
            return "Low"
        return "Mid"

    def tidal_rows(self):
        """D8: rows that are dry at mean sea level but that this season's
        tide would wash over."""
        effective = self.sea_level + self.tide_offset()
        return [
            row
            for row in range(COASTLINE_ROWS)
            if self.sea_level < row_flood_threshold(row, self.coastline) <= effective
        ]

    def tide_text(self):
        offset = self.tide_offset()
        rows = self.tidal_rows()
        wash = (
            f" — the tide is washing over {len(rows)} otherwise-dry row(s)."
            if rows
            else " — no dry rows are reached."
        )
        return f"Tide this season: {self.tide_label()} ({offset:+.1f} vs. mean sea level){wash}"

    def delayed_consequence_rows(self):
        """D7: for each banked season, the acidity fraction it recorded
        and the fish yield it will cause `lag` seasons later, as
        (season, acidity_fraction, arrival_season, projected_yield)."""
        lag = self._effective_fish_lag()
        rows = []
        for i, acidity in enumerate(self.acidity_history):
            projected = max(MIN_FISH_MULTIPLIER, 1 - acidity / FISH_DAMAGE_SCALE)
            rows.append((i + 1, min(1.0, acidity / FISH_DAMAGE_SCALE), i + 1 + lag, projected))
        return rows

    def delayed_consequence_text(self):
        rows = self.delayed_consequence_rows()
        if not rows:
            return "Advance a season to see today's acidity choices lined up against their later fish-yield impact."
        season, _fraction, arrival, projected = rows[-1]
        return (
            f"Acidity banked in Season {season} reaches fish stocks in Season {arrival}: "
            f"yield of about {projected * 100:.0f}% from that season's acidity alone."
        )

    def workshop_active(self):
        """True for any run with non-standard rules: Workshop dials or the Tidal Chess challenge."""
        return self.chess_mode or any(self.workshop[k] != WORKSHOP_DEFAULTS[k] for k in WORKSHOP_DEFAULTS)

    def keeps_records_out(self):
        """Custom-rule runs and Daily Tide runs stay out of the Almanac, the personal best and the library."""
        return self.workshop_active() or bool(self.daily)

    def set_chess_mode(self, enabled):
        if self.season > 1 and enabled != self.chess_mode:
            return False  # only before the first season resolves, so the score is comparable
        self.chess_mode = bool(enabled)
        if not self.chess_mode:
            self.runoff_queue, self.chess_dips = [], 0
        return True

    def sea_rise_per_season(self):
        return SEA_SCENARIOS[self.sea_scenario]["rise"] * self.workshop["rise"]

    def set_sea_scenario(self, scenario):
        """D19: only while nothing has been played yet -- changing the
        trajectory mid-run would silently rewrite history."""
        if scenario not in SEA_SCENARIOS or self.damage_log or self.season != 1 or self.daily:
            return False
        self.sea_scenario = scenario
        return True

    def set_coastline(self, coastline_id):
        """D-8: like the sea scenario, only before anything has been played (the elevation, heritage and economy
        would otherwise rewrite history)."""
        if coastline_id not in COASTLINES or self.damage_log or self.season != 1 or self.daily:
            return False
        if coastline_id != self.coastline:
            self.coastline = coastline_id
            self.heritage = {site["id"]: HERITAGE_UNPROTECTED for site in heritage_sites(coastline_id)}
        return True

    def coast_weight(self, kind):
        """The economy weight of this coastline for "output", "tourism" or "aquaculture" (1.0 on the open coast)."""
        return COASTLINES[self.coastline][kind]
