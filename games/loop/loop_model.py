"""ChainState: the supply chain itself (one run): money, circularity, extraction, scoring, saving of one chain."""

import copy

from loop_rules import (
    ASSIST_MODES, BUY_KINDS, CHALLENGE_MODE_SUPPLY_MULTIPLIER, CIRCULARITY_BONUS_WEIGHT,
    CIRCULARITY_INVESTMENTS, COMBO_BONUS_PER_LEVEL, COMBO_CAP, CULTURE_BASE_COST, CULTURE_DEMAND_REDUCTION,
    CULTURE_MAX_LEVEL, DEFAULT_GOODS_CATEGORY, ENVIRONMENTAL_DAMAGE_SCALE, EXPORT_PRICE_PER_UNIT,
    EXTRACTION_COST_PER_UNIT, IMPORT_SUPPLY_PER_UNIT, INSURANCE_COST, LEDGER_MAX, MAX_COST_MULTIPLIER,
    OVERSEAS_IMPORT_SUPPLY_PER_UNIT, OVERSEAS_TRADE_COST, PARTNER_COSTS, PASSPORT_MAX_ENTRIES,
    PASSPORT_SOURCES, PRODUCTION_TARGET, REDESIGN_BASE_COST, REDESIGN_MAX_LEVEL, REDESIGN_SUPPLY_BONUS,
    REGIONAL_IMPORT_SUPPLY_PER_UNIT, REGIONAL_TRADE_COST, SALE_PRICE_PER_UNIT, SHOCK_DEMAND_MULTIPLIER,
    SHOCK_PRICE_MULTIPLIER, STARTING_FUNDS, TRADE_LINK_COST, WASTE_STREAM_SPECIALIZATION_BONUS,
    ZERO_WASTE_EXTRACTION_CAP, _GOLDEN, clean_note, rival_funds_after, shock_for_cycle,
)


class ChainState:
    def __init__(self):
        self.cycle_number = 1
        self.funds = STARTING_FUNDS
        self.total_extracted = 0.0
        self.total_produced = 0.0
        self.circularity_investment = {c: 0 for c in CIRCULARITY_INVESTMENTS}
        self.circular_fraction_log = []
        self.trade_link_investment = 0
        self.regional_trade_investment = 0
        self.overseas_trade_investment = 0
        # H16: the cycle number the loop first closed on (None until then).
        self.first_loop_closed_cycle = None
        self.goods_category = DEFAULT_GOODS_CATEGORY
        # Lifetime tallies + streak tracking added for the achievements
        # rollout and H19's closed-loop-streak tracker — all reset with a
        # fresh chain, same as every other field here (only
        # chains_completed_count/goods_categories_tried, module-level
        # below, are meant to survive a "Start New Chain" reset, since
        # their entire point is to measure things *across* resets).
        self.lifetime_investment_spend = 0.0
        self.lifetime_export_revenue = 0.0
        # H11: opt-in donation of the cycle's surplus to the shared regional
        # recycling pool instead of selling it. `last_donation` is the units
        # given in the most recent cycle (transient, never saved).
        self.donate_surplus = False
        self.lifetime_pool_donated = 0.0
        self.last_donation = 0.0
        self.closed_loop_streak = 0
        self.best_closed_loop_streak = 0
        # H13/H23: opt-in start-of-chain modes (see can_choose_mode()).
        self.challenge_mode = False
        self.zero_waste = False
        # H9: the one circularity measure currently carrying the specialization
        # bonus (None = no emphasis).
        self.waste_focus = None
        # H3: redesign level per measure (0..REDESIGN_MAX_LEVEL).
        self.redesign_level = {m: 0 for m in CIRCULARITY_INVESTMENTS}
        # H17: demand-side campaign level (0..CULTURE_MAX_LEVEL).
        self.culture_level = 0
        # H21: [{"cycle": int, "source": one of PASSPORT_SOURCES}], oldest first.
        self.passport = []
        # GH-14: the goods category PICKED at chain start (the relabel panel only changes
        # goods_category, so it cannot be used to unlock or record anything), and the
        # secret category's built-in scrap supply (units per cycle, 0 for the others).
        self.picked_category = DEFAULT_GOODS_CATEGORY
        self.head_start = 0.0
        # GH-12 / GH-24: banked combo score, and the once-per-chain streak insurance.
        self.perfect_bonus = 0.0
        self.insurance_used = False
        self.insurance_armed = False
        # Transient notes about the cycle that just ran (never saved).
        self.last_cycle_mix = None  # shares by source when that cycle needed no extraction
        self.last_combo_gain = 0.0
        self.last_insurance_saved = False
        # GH-20: the chain's first close, for the speed achievements (saved when set).
        self.first_close_extracted = None
        self.first_close_trade_free = None
        # GH-3 / FY-37: the opt-in market-shock mode (saved when on), and how many closed
        # cycles landed on a shock (saved when above zero).
        self.market_shocks = False
        self.shocks_shrugged = 0
        # H-10 / H-28: one dict per completed cycle (see LEDGER_COLUMNS), capped at LEDGER_MAX.
        self.ledger = []
        # GH-5 / FY-38: the opt-in Rival Corporation race, and the completed-cycle count at which the
        # player first pulled ahead of it (saved when on / when set).
        self.rival_on = False
        self.rival_crossover_cycle = None
        # GH-18 / FY-39: one rewind per chain. The undo point is a transient copy of the whole chain
        # taken just before each Advance Cycle (never saved); only the spent token is saved.
        self.rewind_used = False
        self.rewind_snapshot = None
        # H-26 / GH-28: purchases per completed cycle (a row of BUY_KINDS counts each), plus the
        # cycle in progress. Saved when anything was bought.
        self.buy_log = []
        self.buys_now = [0] * len(BUY_KINDS)
        # H-8: Assist mode, and the chain's tag once assistance has been on at any point.
        self.assist = "off"
        self.assist_used = False

    def can_choose_mode(self):
        """H13/H23: the modes change the rules of the whole chain, so they
        can only be picked before anything has been produced."""
        return self.total_produced == 0 and self.cycle_number == 1

    def set_assist(self, mode):
        """H-8: Off / Hints / Guided. Switching it on at any point tags the chain as assisted for good
        (switching it off again does not untag it); unknown values are refused."""
        if not (isinstance(mode, str) and mode in ASSIST_MODES):
            return False
        self.assist = mode
        if mode != "off":
            self.assist_used = True
        return True

    def set_challenge_mode(self, on):
        if not self.can_choose_mode():
            return False
        self.challenge_mode = bool(on)
        return True

    def set_zero_waste(self, on):
        if not self.can_choose_mode():
            return False
        self.zero_waste = bool(on)
        return True

    def supply_multiplier(self):
        return CHALLENGE_MODE_SUPPLY_MULTIPLIER if self.challenge_mode else 1.0

    def zero_waste_holding(self):
        """H23: still within the extraction cap. Soft by design: going over
        ends the challenge's own bragging rights, never blocks play."""
        return self.total_extracted <= ZERO_WASTE_EXTRACTION_CAP

    def measure_multiplier(self, measure):
        """H9: the focused measure's supply counts WASTE_STREAM_SPECIALIZATION_BONUS
        higher; the other two stay at their base rate."""
        focus = WASTE_STREAM_SPECIALIZATION_BONUS if self.waste_focus == measure else 0.0
        return 1.0 + focus + REDESIGN_SUPPLY_BONUS * self.redesign_level.get(measure, 0)

    def passport_source(self):
        """Where the traced unit comes from THIS cycle, drawn from the current
        supply mix (call before the cycle counter advances)."""
        need = self.material_need()
        extraction = self.new_extraction_needed()
        if need <= 0:
            return "extraction"
        shares = {"extraction": extraction / need}
        circular = 1.0 - shares["extraction"]
        parts = {m: self.measure_supply(m) for m in CIRCULARITY_INVESTMENTS}
        parts["trade"] = self.imported_supply()
        total = sum(parts.values())
        for name in ("repair", "reuse", "recycle", "trade"):
            shares[name] = circular * (parts[name] / total) if total > 0 else 0.0
        point = (self.cycle_number * _GOLDEN) % 1.0
        running = 0.0
        for name in PASSPORT_SOURCES:
            running += shares.get(name, 0.0)
            if point < running:
                return name
        return "extraction" if shares["extraction"] > 0 else max(PASSPORT_SOURCES[1:], key=lambda n: shares.get(n, 0.0))

    def passport_summary(self):
        """Counts over the recorded journey: (mined, recovered, longest run of recoveries)."""
        mined = sum(1 for e in self.passport if e["source"] == "extraction")
        recovered = len(self.passport) - mined
        longest = run = 0
        for e in self.passport:
            run = run + 1 if e["source"] != "extraction" else 0
            longest = max(longest, run)
        return mined, recovered, longest

    def material_need(self):
        """H17: units of material one cycle's production actually needs, after
        any demand-side culture campaign. Equals PRODUCTION_TARGET with none."""
        need = PRODUCTION_TARGET * (1.0 - CULTURE_DEMAND_REDUCTION * self.culture_level)
        shock = self.active_shock()
        if shock is not None and shock["kind"] == "demand_surge":
            need *= SHOCK_DEMAND_MULTIPLIER
        return need

    def active_shock(self):
        """GH-3: this cycle's shock, or None (always None with the mode off)."""
        return shock_for_cycle(self.cycle_number) if self.market_shocks else None

    def next_shock(self):
        """GH-3: a NEW shock that starts next cycle (the early warning), else None."""
        if not self.market_shocks:
            return None
        coming = shock_for_cycle(self.cycle_number + 1)
        return coming if coming is not None and coming["step"] == 1 else None

    def blocked_partner(self):
        """GH-3: the trade partner a port strike has shut this cycle, or None."""
        shock = self.active_shock()
        return shock["partner"] if shock is not None and shock["kind"] == "port_strike" else None

    def shock_price_multiplier(self):
        shock = self.active_shock()
        return SHOCK_PRICE_MULTIPLIER if shock is not None and shock["kind"] == "price_spike" else 1.0

    def price_multiplier(self):
        """What a unit of new extraction actually costs this cycle: the damage multiplier times
        any price spike."""
        return self.extraction_cost_multiplier() * self.shock_price_multiplier()

    def partner_supply(self, kind):
        """Units one trade partner imports per cycle (0 while a port strike shuts it)."""
        if kind == self.blocked_partner():
            return 0.0
        owned, per_unit = {
            "trade": (self.trade_link_investment, IMPORT_SUPPLY_PER_UNIT),
            "regional": (self.regional_trade_investment, REGIONAL_IMPORT_SUPPLY_PER_UNIT),
            "overseas": (self.overseas_trade_investment, OVERSEAS_IMPORT_SUPPLY_PER_UNIT),
        }[kind]
        return self.supply_multiplier() * owned * per_unit

    def culture_cost(self):
        return CULTURE_BASE_COST * (self.culture_level + 1)

    def invest_culture(self):
        if self.culture_level >= CULTURE_MAX_LEVEL:
            return False
        cost = self.culture_cost()
        if self.funds < cost:
            return False
        self.funds -= cost
        self.culture_level += 1
        self.lifetime_investment_spend += cost
        return True

    def redesign_unlocked(self):
        """H3: opens once the loop has closed at least once."""
        return self.first_loop_closed_cycle is not None

    def redesign_cost(self, measure):
        return REDESIGN_BASE_COST * (self.redesign_level[measure] + 1)

    def redesign(self, measure):
        if measure not in self.redesign_level or not self.redesign_unlocked():
            return False
        if self.redesign_level[measure] >= REDESIGN_MAX_LEVEL:
            return False
        cost = self.redesign_cost(measure)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.redesign_level[measure] += 1
        self.lifetime_investment_spend += cost
        return True

    def set_waste_focus(self, measure):
        """Freely switchable and free (the trade-off is structural: only one
        measure can carry the bonus at a time). None clears it."""
        if measure is not None and not (isinstance(measure, str) and measure in CIRCULARITY_INVESTMENTS):
            return False
        self.waste_focus = measure
        return True

    def measure_supply(self, measure):
        """Units one measure supplies per cycle, after every multiplier. The secret
        yard's built-in scrap line (GH-14) counts as recycling, so every view of the
        supply (maps, passport, contribution lines) keeps summing to the same total."""
        base = (
            self.circularity_investment[measure] * CIRCULARITY_INVESTMENTS[measure]["supply_per_unit"]
            * self.measure_multiplier(measure)
        )
        if measure == "recycle":
            base += self.head_start
        return self.supply_multiplier() * base

    def internal_circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction — the chain's own capacity,
        before anything crossing in from the trade network."""
        return sum(self.measure_supply(c) for c in CIRCULARITY_INVESTMENTS)

    def supply_mix(self):
        """GH-15: each source's share (0..1) of the circular supply right now, over
        repair, reuse, recycle and trade; empty when nothing is supplied."""
        units = {m: self.measure_supply(m) for m in CIRCULARITY_INVESTMENTS}
        units["trade"] = self.imported_supply()
        total = sum(units.values())
        if total <= 0:
            return {}
        return {name: value / total for name, value in units.items()}

    def combo_level(self):
        """GH-12: the Perfect Cycle combo, the closed-loop streak counted up to COMBO_CAP."""
        return min(self.closed_loop_streak, COMBO_CAP)

    def next_combo_gain(self):
        """Bonus the NEXT perfect cycle would bank (0 for the first of a run)."""
        level = min(self.closed_loop_streak + 1, COMBO_CAP)
        return COMBO_BONUS_PER_LEVEL * max(0, level - 1)

    def can_buy_insurance(self):
        """GH-24: once per chain, and only with a streak worth protecting."""
        return (
            not self.insurance_used and self.closed_loop_streak >= 1 and self.funds >= INSURANCE_COST
        )

    def buy_insurance(self):
        if not self.can_buy_insurance():
            return False
        self.funds -= INSURANCE_COST
        self.insurance_used = True
        self.insurance_armed = True
        return True

    def note_loop_closed(self):
        """Records the chain's FIRST close (called by the closing action)."""
        if self.first_loop_closed_cycle is not None:
            return False
        self.first_loop_closed_cycle = self.cycle_number
        self.first_close_extracted = self.total_extracted
        self.first_close_trade_free = (
            self.trade_link_investment == 0
            and self.regional_trade_investment == 0
            and self.overseas_trade_investment == 0
        )
        return True

    def imported_supply(self):
        return sum(self.partner_supply(kind) for kind in PARTNER_COSTS)

    def circular_supply(self):
        """Total supply toward closing the loop: internal circularity
        plus whatever the trade link imports from the neighboring
        system(s)."""
        return self.internal_circular_supply() + self.imported_supply()

    def exportable_surplus(self):
        """H1 fix — the import/export asymmetry: this used to read
        `max(0.0, self.internal_circular_supply() - PRODUCTION_TARGET)`,
        so only excess *internal* circularity supply was ever sold
        outward for revenue. Excess *imported* supply (from either trade
        partner) simply evaporated — no revenue, no carry-over — even
        though the player paid real funds for that import capacity.
        That was an unjustified, wasteful asymmetry: internal overshoot
        was monetized every single cycle it persisted, imported
        overshoot never was. Fixed by looking at total circular_supply()
        (internal + imported) beyond the production target instead, so
        any supply this chain doesn't need this cycle — regardless of
        source — is sold outward rather than silently discarded."""
        return max(0.0, self.circular_supply() - self.material_need())

    def new_extraction_needed(self):
        """The straight-line default: whatever circular supply doesn't
        cover has to come from newly extracted raw material. Floored at
        zero — enough circularity investment closes the loop entirely."""
        return max(0.0, self.material_need() - self.circular_supply())

    def invest_trade_link(self):
        if self.funds < TRADE_LINK_COST:
            return False
        self.funds -= TRADE_LINK_COST
        self.trade_link_investment += 1
        self.lifetime_investment_spend += TRADE_LINK_COST
        self.buys_now[BUY_KINDS.index("trade")] += 1
        return True

    def invest_regional_trade(self):
        """H8: the second trading partner — costs more per investment
        than the Local Trade Link but supplies more import capacity per
        unit (see REGIONAL_TRADE_COST/REGIONAL_IMPORT_SUPPLY_PER_UNIT
        above for the exact trade-off)."""
        if self.funds < REGIONAL_TRADE_COST:
            return False
        self.funds -= REGIONAL_TRADE_COST
        self.regional_trade_investment += 1
        self.lifetime_investment_spend += REGIONAL_TRADE_COST
        self.buys_now[BUY_KINDS.index("regional")] += 1
        return True

    def invest_overseas_trade(self):
        """H1: the third trading partner (see OVERSEAS_TRADE_COST)."""
        if self.funds < OVERSEAS_TRADE_COST:
            return False
        self.funds -= OVERSEAS_TRADE_COST
        self.overseas_trade_investment += 1
        self.lifetime_investment_spend += OVERSEAS_TRADE_COST
        self.buys_now[BUY_KINDS.index("overseas")] += 1
        return True

    def unit_cost(self, kind):
        """H-14: the price of ONE purchase of `kind` (a circularity measure or a trade partner)."""
        if kind in CIRCULARITY_INVESTMENTS:
            return CIRCULARITY_INVESTMENTS[kind]["cost"]
        return PARTNER_COSTS[kind]

    def affordable_count(self, kind, wanted):
        """H-14: how many of `wanted` purchases of `kind` the funds cover right now."""
        cost = self.unit_cost(kind)
        return max(0, min(int(wanted), int(self.funds // cost)))

    def invest_many(self, kind, count):
        """H-14: buys up to `count` of `kind`, one after the other, stopping when the funds run
        out. Returns how many were bought. Every purchase is the ordinary single purchase, so
        the lifetime tallies and the rules are exactly the same as clicking `count` times."""
        step = {
            "trade": self.invest_trade_link,
            "regional": self.invest_regional_trade,
            "overseas": self.invest_overseas_trade,
        }.get(kind)
        bought = 0
        for _ in range(max(0, int(count))):
            ok = step() if step else self.invest_circularity(kind)
            if not ok:
                break
            bought += 1
        return bought

    def extraction_cost_trend(self):
        """H8: 'rising' if last cycle's extraction pushed the per-unit
        extraction cost multiplier up, else 'steady' (also before any
        cycle has run). Damage never decays, so it can never get cheaper
        -- the honest options are pricier or unchanged."""
        if not self.circular_fraction_log:
            return "steady"
        last_extraction = PRODUCTION_TARGET * (1.0 - self.circular_fraction_log[-1])
        prev_damage = min(1.0, max(0.0, self.total_extracted - last_extraction) / ENVIRONMENTAL_DAMAGE_SCALE)
        prev_mult = 1.0 + prev_damage * (MAX_COST_MULTIPLIER - 1.0)
        return "rising" if self.extraction_cost_multiplier() > prev_mult + 1e-9 else "steady"

    def is_loop_closed(self):
        return self.new_extraction_needed() <= 0.0

    def circular_fraction_this_cycle(self):
        """0..1 — the share of *this* cycle's production target that
        circularity investment covers, capped at 1 (fully closed)."""
        # Floored at zero: a demand surge can need more than the target in new material.
        return max(0.0, (PRODUCTION_TARGET - self.new_extraction_needed()) / PRODUCTION_TARGET)

    def lifetime_circular_fraction(self):
        """0..1 — the share of all production ever run through the chain
        that came from circular supply rather than new extraction."""
        if self.total_produced == 0:
            return 0.0
        circular_total = self.total_produced - self.total_extracted
        return max(0.0, circular_total / self.total_produced)

    def invest_circularity(self, measure):
        cost = CIRCULARITY_INVESTMENTS[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.circularity_investment[measure] += 1
        self.lifetime_investment_spend += cost
        self.buys_now[BUY_KINDS.index(measure)] += 1
        return True

    def damage_fraction(self):
        """0..1 — cumulative land/emissions damage from lifetime new
        extraction, capped so extraction never becomes literally
        impossible, just steadily more expensive."""
        return min(1.0, self.total_extracted / ENVIRONMENTAL_DAMAGE_SCALE)

    def extraction_cost_multiplier(self):
        return 1.0 + self.damage_fraction() * (MAX_COST_MULTIPLIER - 1.0)

    def _snapshot(self):
        """A deep copy of every chain field except the undo point itself."""
        return copy.deepcopy({k: v for k, v in self.__dict__.items() if k != "rewind_snapshot"})

    def rewind_block_reason(self):
        """GH-18: None when a rewind is possible, else a short plain reason."""
        if self.rewind_used:
            return "used"
        if self.rewind_snapshot is None:
            return "no_point"
        if self.last_donation > 0:
            return "donated"
        return None

    def can_rewind(self):
        return self.rewind_block_reason() is None

    def rewind(self):
        """GH-18 / FY-39: one per chain. Puts the chain back exactly as it was before the last
        Advance Cycle (purchases made since are undone too) and spends the token. The career
        records, name plates and goods tried are NOT taken back: they record what happened."""
        if not self.can_rewind():
            return False
        saved = self.rewind_snapshot
        self.__dict__.clear()
        self.__dict__.update(copy.deepcopy(saved))
        self.rewind_used = True
        self.rewind_snapshot = None
        return True

    def advance_cycle(self, note=""):
        self.rewind_snapshot = self._snapshot()
        funds_before = self.funds
        # H-10: what the cycle looked like going in (the supply mix, the partners that delivered, the price).
        ledger_units = {m: self.measure_supply(m) for m in CIRCULARITY_INVESTMENTS}
        ledger_trade = self.imported_supply()
        ledger_partners = "".join(
            letter for kind, letter in (("trade", "T"), ("regional", "R"), ("overseas", "O"))
            if self.partner_supply(kind) > 0
        )
        ledger_damage = self.damage_fraction() * 100.0
        ledger_multiplier = self.price_multiplier()
        extraction = self.new_extraction_needed()
        cost = extraction * EXTRACTION_COST_PER_UNIT * self.price_multiplier()
        if extraction <= 0.0 and self.active_shock() is not None:
            self.shocks_shrugged += 1  # GH-3: a closed cycle that landed on a shock
        revenue = PRODUCTION_TARGET * SALE_PRICE_PER_UNIT
        surplus = self.exportable_surplus()
        if self.donate_surplus and surplus > 0:
            # H11: the surplus goes to the regional pool, not to market.
            export_revenue = 0.0
            self.last_donation = surplus
            self.lifetime_pool_donated += surplus
        else:
            export_revenue = surplus * EXPORT_PRICE_PER_UNIT
            self.last_donation = 0.0
        # A bad cycle (high damage plus a price spike or a demand surge) can wipe out the cycle's profit but
        # never takes funds the chain already holds.
        self.funds += max(0.0, revenue - cost + export_revenue)
        self.lifetime_export_revenue += export_revenue
        previous_after = self.ledger[-1]["funds_after"] if self.ledger else (STARTING_FUNDS if self.cycle_number == 1 else None)
        self.ledger.append({
            "cycle": self.cycle_number,
            "spent": None if previous_after is None else round(max(0.0, previous_after - funds_before), 1),
            "revenue": round(revenue, 1), "export": round(export_revenue, 1), "extraction_cost": round(cost, 1),
            "repair": round(ledger_units["repair"], 1), "reuse": round(ledger_units["reuse"], 1),
            "recycle": round(ledger_units["recycle"], 1), "trade": round(ledger_trade, 1),
            "extraction": round(extraction, 1), "damage": round(ledger_damage, 1),
            "multiplier": round(ledger_multiplier, 2), "partners": ledger_partners,
            "funds_after": round(self.funds, 1), "note": clean_note(note),
        })
        del self.ledger[:-LEDGER_MAX]
        # H19: closed-loop streak -- sticky best-ever value, same shape as
        # Grid's best_clean_streak. A cycle only counts toward the streak
        # if it needed zero new extraction (fully closed), matching
        # is_loop_closed()'s own definition.
        self.last_combo_gain = 0.0
        self.last_insurance_saved = False
        self.last_cycle_mix = None
        if extraction <= 0.0:
            # GH-12: the combo bonus uses the streak INCLUDING this cycle.
            self.last_cycle_mix = self.supply_mix()
            self.closed_loop_streak += 1
            self.best_closed_loop_streak = max(self.best_closed_loop_streak, self.closed_loop_streak)
            self.last_combo_gain = COMBO_BONUS_PER_LEVEL * max(0, min(self.closed_loop_streak, COMBO_CAP) - 1)
            self.perfect_bonus += self.last_combo_gain
        elif self.insurance_armed:
            # GH-24: the armed insurance freezes the streak through this one bad cycle.
            self.insurance_armed = False
            self.last_insurance_saved = True
        else:
            self.closed_loop_streak = 0
        self.buy_log.append(list(self.buys_now))  # H-26 / GH-28: this cycle's purchases, filed with the cycle
        del self.buy_log[:-LEDGER_MAX]
        self.buys_now = [0] * len(BUY_KINDS)
        self.passport.append({"cycle": self.cycle_number, "source": self.passport_source()})
        del self.passport[:-PASSPORT_MAX_ENTRIES]
        self.circular_fraction_log.append(self.circular_fraction_this_cycle())
        self.total_extracted += extraction
        self.total_produced += PRODUCTION_TARGET
        self.cycle_number += 1
        done = self.cycle_number - 1
        if self.rival_on and self.rival_crossover_cycle is None and self.funds > rival_funds_after(done):
            self.rival_crossover_cycle = done

    def score(self):
        """Profitability plus a direct reward for lifetime circular
        share — a fully closed, sustained loop earns the maximum bonus
        on top of whatever funds it generated."""
        return self.funds + self.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT + self.perfect_bonus

    def circular_trend(self):
        """Compares the first half of cycles run to the second half —
        the hope-angle payoff: a visibly rising circular share is the
        direct reward for early circularity investment, not just a good
        final number."""
        n = len(self.circular_fraction_log)
        if n < 4:
            return None
        half = n // 2
        first_half_avg = sum(self.circular_fraction_log[:half]) / half
        second_half_avg = sum(self.circular_fraction_log[half:]) / (n - half)
        return first_half_avg, second_half_avg
