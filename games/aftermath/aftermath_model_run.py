"""RunState (one run: resources, events, damage, payout, scoring) and the creation of the first live run."""

import copy
import math

import aftermath_runstate as runstate
from aftermath_achievements import _note_achievement_progress, _season_run_finished
from aftermath_bonuses import (
    DEFAULT_LOOK, TIMER_MAX_STEP, adaptive_growth_bonus, category_memory_bonus, category_mitigation_bonus,
    category_skill_bonus, early_warning_mitigation_bonus, entry_aid, founding_owned,
    founding_star_resources, look_for_skill_count, mutual_aid_mitigation_bonus, neighbour_aid_due,
    record_societal_memory, run_timer_enabled, starting_resilience_bonus, starting_resources_bonus,
)
from aftermath_challenges import _note_challenge_result, _record_shared_daily, file_run_ghost
from aftermath_chronicle import _chronicle_payout_notes
from aftermath_pastruns import _report_hardest_schedule
from aftermath_persist import (
    _now, note_curriculum_run, run_log_history, save_highest_awarded_run, save_legacy_event_counts,
    save_legacy_events, save_run_history, save_run_log_history, skill_tree_strength, societal_memory,
)
from aftermath_rules import (
    DEFAULT_SCENARIO, EVENT_BASE_DAMAGE, EVENT_LABEL, EVENT_SCHEDULE, FLAWLESS_BONUS_KNOWLEDGE, GROWTH_COST,
    GROWTH_INCOME_PER_UNIT, MAX_MITIGATION, RESILIENCE_COST, RESILIENCE_MITIGATION_PER_UNIT, SCENARIOS,
    STARTING_RESOURCES, entry_is_flawless, event_severity, flawless_count, severity_label,
)
from aftermath_skillmap import record_skill_progress


class RunState:
    def __init__(self, run_number=1, extended=False, scenario=DEFAULT_SCENARIO,
                 normalised=False, draw=None, custom_events=None, custom_name=None, challenge=None):
        """Reads current skill-tree bonuses at creation time — a new run
        starts a little more capable than the last, per unlocked skills.

        `extended` (E18: optional extended-run mode) picks a per-instance
        `schedule` — the same fixed EVENT_SCHEDULE repeated twice for a
        longer, harder-fought run, or the plain schedule otherwise. Every
        schedule-length-dependent method below reads self.schedule rather
        than the module-level EVENT_SCHEDULE directly, so a normal run's
        behavior (and every test pinned to it) is completely unchanged —
        only a run explicitly started as `extended` ever sees the longer
        list."""
        self.run_number = run_number
        self.extended = extended
        # E17a: which scenario's schedule this run follows (unknown names
        # fall back to the classic mix).
        self.scenario = scenario if isinstance(scenario, str) and scenario in SCENARIOS else DEFAULT_SCENARIO
        base_schedule = SCENARIOS[self.scenario]["schedule"]
        self.schedule = base_schedule * 2 if extended else base_schedule
        # E-13: a player-built schedule replaces the scenario's (never extended).
        self.custom_events = None
        self.custom_name = None
        if custom_events and all(e in EVENT_LABEL for e in custom_events):
            self.custom_events = list(custom_events)
            self.custom_name = custom_name if isinstance(custom_name, str) and custom_name else None
            self.schedule = list(custom_events)
            self.extended = False
        # E-4: a challenge run (a friend's run code) ignores the player's own tree: no starting
        # bonuses, no skill or memory mitigation, severity from the code's draw at the
        # un-widened band. `challenge` keeps the code and the sender's result for comparison.
        self.normalised = bool(normalised)
        self.draw = int(draw) if draw is not None else run_number
        self.challenge = challenge if self.normalised and isinstance(challenge, dict) else None
        self.event_index = 0
        # GE-25: the settlement's look, fixed when the run starts (a friend's challenge run ignores the tree).
        self.look = DEFAULT_LOOK if self.normalised else look_for_skill_count(skill_tree_strength())
        self.resources = (
            STARTING_RESOURCES + starting_resources_bonus(self._unlocked())
            + (0 if self.normalised else founding_star_resources())  # GE-10: the Founding stars' perk
        )
        self.resilience_capacity = starting_resilience_bonus(self._unlocked())
        self.growth_capacity = adaptive_growth_bonus(self._unlocked())
        self.damage_taken = 0.0
        self.event_log = []
        # Z-3d: the resources left after each event so far (one number per event), the live side of the ghost.
        # Saved only when the run can be compared with a ghost; a save from before it has none.
        self.resources_log = []
        # Achievements ("profitable_run") need to compare a run's *final*
        # resources against what it actually started with -- which varies
        # run to run once skill-tree bonuses affect starting resources, so
        # this is captured once here rather than re-deriving it later from
        # STARTING_RESOURCES + starting_resources_bonus() (the latter would
        # silently drift if more skills unlock mid-run... they can't, but
        # capturing it explicitly avoids relying on that being true).
        self.starting_resources = self.resources
        # GE-18: one entry per allocation click this between-event phase, as
        # (kind, units). Not part of get_state(): after a load, or once an
        # event resolves, there is nothing to undo.
        self.allocation_history = []
        # GE-23: the optional run timer. `timed` is None until the run's first action, then True (counted from
        # that action with the timer on) or False (the timer was off, or was switched off, so this run has no time).
        self.timed = None
        self.elapsed = 0.0
        self._timer_last = None
        # E-18: how the most recent event's damage was worked out. In memory
        # only (never saved): after a load there is no breakdown to show.
        self.last_breakdown = None

    @property
    def aid_given(self):
        """R-31: resources received from neighbouring towns this run (0 for almost every run). Read from
        the event log, so it survives a save and load with no extra field."""
        return sum(entry_aid(e) for e in self.event_log)

    def _unlocked(self):
        return frozenset() if self.normalised else (runstate.skill_tree.unlocked | founding_owned())

    def _memory(self):
        return frozenset() if self.normalised else societal_memory

    def category_bonus(self, event_type):
        return category_mitigation_bonus(event_type, self._unlocked(), self._memory())

    def severity_at(self, index):
        """The severity multiplier for event `index` of this run: the player's own pattern
        (widened by their tree and career), or, in a challenge run, the code's fixed draw at the
        plain band so both players face the same numbers."""
        if self.normalised:
            return event_severity(self.draw, index, 0, 0)
        return event_severity(self.run_number, index, skill_tree_strength())

    def is_complete(self):
        return self.event_index >= len(self.schedule)

    def next_event_type(self):
        if self.is_complete():
            return None
        return self.schedule[self.event_index]

    def invest_resilience(self, record=True):
        if self.resources < RESILIENCE_COST:
            return False
        self.resources -= RESILIENCE_COST
        self.resilience_capacity += 1
        if record:
            self._record_allocation("resilience", 1)
        _note_achievement_progress(ever_invested_resilience=True)
        if self.mitigation_fraction() >= MAX_MITIGATION:
            _note_achievement_progress(ever_maxed_mitigation=True)
        return True

    def invest_growth(self, record=True):
        if self.resources < GROWTH_COST:
            return False
        self.resources -= GROWTH_COST
        self.growth_capacity += 1
        if record:
            self._record_allocation("growth", 1)
        _note_achievement_progress(ever_invested_growth=True)
        return True

    # GE-18: undo of allocation clicks before Resolve.
    def _record_allocation(self, kind, units):
        self._timer_touch()  # GE-23
        self.allocation_history.append((kind, units))

    def _timer_touch(self):
        """GE-23: called at every action. Starts the timer at the run's first action (when the switch is on),
        otherwise adds the time since the last touch, at most TIMER_MAX_STEP seconds at once so a tab left open
        overnight cannot make a run look slow. A timer switched off mid-run ends timing for that run."""
        enabled = run_timer_enabled()
        if self.timed is None:
            self.timed = bool(enabled and not self.normalised)
            self._timer_last = _now() if self.timed else None
            return
        if self.timed and not enabled:
            self.timed = False
            self._timer_last = None
            return
        if self.timed:
            self.tick_timer(_now())

    def tick_timer(self, now):
        if not self.timed or self.is_complete():
            return
        if self._timer_last is not None:
            self.elapsed += min(max(0.0, now - self._timer_last), TIMER_MAX_STEP)
        self._timer_last = now

    def undo_count(self):
        return len(self.allocation_history)

    def undo_last_allocation(self):
        """Gives back the last allocation click's units and resources. Only
        possible before the next Resolve (resolving clears the history)."""
        if not self.allocation_history or self.is_complete():
            return False
        kind, units = self.allocation_history.pop()
        if kind == "resilience":
            self.resilience_capacity -= units
            self.resources += RESILIENCE_COST * units
        elif kind == "preset":  # E-25: one click bought resilience and growth together
            self.resilience_capacity -= units[0]
            self.resources += RESILIENCE_COST * units[0]
            self.growth_capacity -= units[1]
            self.resources += GROWTH_COST * units[1]
        else:
            self.growth_capacity -= units
            self.resources += GROWTH_COST * units
        return True

    # E-15: x1 / x5 / Max steps.
    def _raw_mitigation(self):
        return (
            self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
            + early_warning_mitigation_bonus(self._unlocked())
            + mutual_aid_mitigation_bonus(self._unlocked())
        )

    def resilience_units_to_cap(self):
        """How many more resilience units fit before general mitigation
        reaches MAX_MITIGATION (more would be wasted)."""
        gap = MAX_MITIGATION - self._raw_mitigation()
        if gap <= 1e-9:
            return 0
        return int(math.ceil(gap / RESILIENCE_MITIGATION_PER_UNIT - 1e-9))

    def step_units(self, kind, step):
        """Units one click buys at this step size: 1, 5 or "max". x1 keeps
        the original rule (one unit whenever it is affordable); x5 and Max
        stop at the resource limit and, for resilience, at the 85% cap."""
        cost = RESILIENCE_COST if kind == "resilience" else GROWTH_COST
        affordable = int(self.resources // cost)
        if step == 1:
            return 1 if affordable >= 1 else 0
        if kind == "resilience":
            affordable = min(affordable, self.resilience_units_to_cap())
        if step == "max":
            return affordable
        return min(int(step), affordable)

    def invest_steps(self, kind, step):
        """Buys step_units() units as ONE undoable click. Returns the
        number bought (0 when nothing was affordable)."""
        if self.is_complete():
            return 0
        units = self.step_units(kind, step)
        bought = 0
        for _ in range(units):
            ok = self.invest_resilience(record=False) if kind == "resilience" else self.invest_growth(record=False)
            if not ok:
                break
            bought += 1
        if bought:
            self._record_allocation(kind, bought)
        return bought

    def invest_preset(self, resilience, growth):
        """E-25: buys up to `resilience` then `growth` units as ONE undoable click, limited by the
        resources in hand (and, for resilience, by the 85% cap, like x5 and Max). Returns the units
        actually bought as (resilience, growth)."""
        if self.is_complete():
            return 0, 0
        bought_r = bought_g = 0
        for _ in range(min(resilience, self.resilience_units_to_cap())):
            if not self.invest_resilience(record=False):
                break
            bought_r += 1
        for _ in range(growth):
            if not self.invest_growth(record=False):
                break
            bought_g += 1
        if bought_r or bought_g:
            self._record_allocation("preset", (bought_r, bought_g))
        return bought_r, bought_g

    def mitigation_fraction(self):
        from_resilience = self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
        return min(
            MAX_MITIGATION,
            from_resilience + early_warning_mitigation_bonus(self._unlocked()) + mutual_aid_mitigation_bonus(self._unlocked()),
        )

    def mitigation_for(self, event_type):
        """Total damage reduction for one event: the general mitigation
        plus any category-specific specialization bonus, still capped at
        MAX_MITIGATION so nothing ever reaches full immunity."""
        return min(MAX_MITIGATION, self.mitigation_fraction() + self.category_bonus(event_type))

    def damage_breakdown(self, event_type, severity):
        """E-18: base damage, the severity change, each mitigation source (in
        damage points) and the final damage, in the order the rules apply
        them. general = resilience + early warning + mutual aid is capped at
        MAX_MITIGATION, then the category bonus is added and the total capped
        again; `cap_added_back` is whatever those caps gave back."""
        base = EVENT_BASE_DAMAGE[event_type]
        unmitigated = base * severity
        sources = [
            ("Resilience investment", self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT),
            ("Early Warning Systems", early_warning_mitigation_bonus(self._unlocked())),
            ("Mutual Aid Network", mutual_aid_mitigation_bonus(self._unlocked())),
            ("Category skill", category_skill_bonus(event_type, self._unlocked())),
            ("Societal memory", category_memory_bonus(event_type, self._memory())),
        ]
        general_raw = sources[0][1] + sources[1][1] + sources[2][1]
        general = min(MAX_MITIGATION, general_raw)
        total = min(MAX_MITIGATION, general + sources[3][1] + sources[4][1])
        raw_total = sum(amount for _, amount in sources)
        return {
            "type": event_type,
            "base": base,
            "severity": severity,
            "unmitigated": unmitigated,
            "sources": [
                {"label": label, "fraction": amount, "damage": unmitigated * amount}
                for label, amount in sources
                if amount > 0
            ],
            "cap_added_back": unmitigated * (raw_total - total),
            "mitigation": total,
            "final": unmitigated * (1 - total),
        }

    def resolve_next_event(self):
        """Applies growth income, then resolves the next scheduled event's
        damage (reduced by resilience mitigation). No-op once the run is
        complete."""
        if self.is_complete():
            return False

        self._timer_touch()  # GE-23
        self.resources += self.growth_capacity * GROWTH_INCOME_PER_UNIT
        aid = neighbour_aid_due(self)  # R-31: planned, shown beforehand, a fixed function of the run number
        self.resources += aid

        event_type = self.schedule[self.event_index]
        severity = self.severity_at(self.event_index)
        damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - self.mitigation_for(event_type))
        self.last_breakdown = self.damage_breakdown(event_type, severity)  # E-18
        self.resources = max(0.0, self.resources - damage)
        self.damage_taken += damage
        self.event_log.append({"type": event_type, "damage": damage, "severity": severity, **({"aid": aid} if aid else {})})
        self.event_index += 1
        self.resources_log.append(self.resources)  # Z-3d
        self.allocation_history = []  # GE-18: nothing to undo after Resolve
        if entry_is_flawless(self.event_log[-1]):
            _note_achievement_progress(ever_flawless_defense=True)  # GE-15

        _note_achievement_progress(ever_faced_event=True)
        if severity_label(severity) == "severe" and self.resources > 0:
            _note_achievement_progress(ever_survived_severe_event=True)

        if self.is_complete() and self.normalised:
            _note_challenge_result(self)  # E-4: a friend's challenge earns nothing for the tree
            _record_shared_daily(self)  # Z-5c: Today's run on today's seed counts once in the shared daily record
        elif self.is_complete():
            if self.run_number > runstate.highest_awarded_run:
                runstate.skill_tree.add_knowledge(self.knowledge_points_earned())
                runstate.skill_tree.save()
                runstate.run_history.append(self.run_score())
                save_run_history(runstate.run_history)
                runstate.memory_just_formed = record_societal_memory(self.event_log, self.run_score())  # E29
                runstate.curriculum_just_completed = None if self.custom_events else note_curriculum_run(self)  # E19
                runstate.legacy_events.update(entry["type"] for entry in self.event_log)
                save_legacy_events(runstate.legacy_events)
                # E4: build out the legacy system beyond its original
                # single-flavor-text-line shape -- a per-event-type
                # *count* of how many times this settlement has weathered
                # each kind of event, alongside the pre-existing
                # ever-weathered set above (which legacy_message() still
                # uses unchanged).
                for entry in self.event_log:
                    runstate.legacy_event_counts[entry["type"]] = runstate.legacy_event_counts.get(entry["type"], 0) + 1
                save_legacy_event_counts(runstate.legacy_event_counts)
                # E7: persist this run's full event-by-event breakdown
                # (not just its final score, which run_history already
                # tracks) so players can review a specific past run later.
                run_log_history.append(
                    {
                        "run_number": self.run_number,
                        "score": self.run_score(),
                        "resilience_capacity": self.resilience_capacity,
                        "growth_capacity": self.growth_capacity,
                        "damage_taken": self.damage_taken,
                        "knowledge_earned": self.knowledge_points_earned(),
                        # E-1: the skill-tree strength this run was played at
                        # (older logs lack it and are left out of the band stat).
                        "skill_strength": skill_tree_strength(),
                        "event_log": copy.deepcopy(self.event_log),
                        # E-13: runs on a player-built schedule are tagged (older logs lack the field).
                        **({"custom_schedule": self.custom_name or "Unnamed"} if self.custom_events else {}),
                        # R-31: a run that received neighbour aid is tagged and kept off every comparison.
                        **({"neighbour_aid": self.aid_given} if self.aid_given else {}),
                        # GE-25: the settlement's look this run, only written when it is not the default.
                        **({"look": self.look} if self.look != DEFAULT_LOOK else {}),
                        # GE-23: the run's time, only when the timer was on for the whole run. Never affects a score.
                        **({"seconds": int(self.elapsed)} if self.timed and self.elapsed >= 1 else {}),
                    }
                )
                save_run_log_history(run_log_history)
                runstate.highest_awarded_run = self.run_number
                save_highest_awarded_run(runstate.highest_awarded_run)
                file_run_ghost(self)  # Z-3d
                _chronicle_payout_notes(self)  # E-7: a memory that formed and a lesson that was finished
                record_skill_progress(self)  # E-11: proven use of the skills owned, once per paid-out run
                _season_run_finished(self.resources)
                if not self.custom_events:  # E-13: a hand-built schedule never competes on the board
                    _report_hardest_schedule(self)  # E23

                # Playstyle achievements -- only recorded the first time a
                # given run_number genuinely completes (same guard as the
                # knowledge/history/legacy payout above), so reloading a
                # stale pre-completion save and re-resolving it can't
                # re-trigger these either.
                if self.resources > self.starting_resources:
                    _note_achievement_progress(ever_profitable_run=True)
                if self.growth_capacity >= 3 and self.growth_capacity > self.resilience_capacity:
                    _note_achievement_progress(ever_growth_heavy_run=True)
                if self.resilience_capacity >= 3 and self.resilience_capacity > self.growth_capacity:
                    _note_achievement_progress(ever_resilience_heavy_run=True)
                if self.growth_capacity >= 2 and self.growth_capacity == self.resilience_capacity:
                    _note_achievement_progress(ever_balanced_run=True)
                # E15: a narrow deep-investment run (5+ in one track, none
                # in the other) and a broad run (3+ in both) are both
                # rewarded; a third achievement needs both.
                if max(self.growth_capacity, self.resilience_capacity) >= 5 and min(
                    self.growth_capacity, self.resilience_capacity
                ) == 0:
                    _note_achievement_progress(ever_deep_specialist_run=True)
                if self.growth_capacity >= 3 and self.resilience_capacity >= 3:
                    _note_achievement_progress(ever_broad_generalist_run=True)

        return True

    def run_score(self):
        """How well the settlement weathered the run — just the resources
        it has left. Reflects both good mitigation (less damage) and good
        growth (more income to absorb it)."""
        return self.resources

    def knowledge_points_earned(self):
        """Currency for the skill tree. Floored at 1 — per the hope angle,
        even a rough run always contributes some permanent capability,
        never zero. GE-15: each Flawless Defense adds a bonus point."""
        return self.knowledge_breakdown()["total"]

    def knowledge_breakdown(self):
        """E-23: where the run's knowledge points come from."""
        raw = round(self.run_score() / 20)
        base = max(1, raw)
        factor = self.custom_knowledge_factor()
        if factor < 1.0:
            base = max(1, round(base * factor))
        flawless = flawless_count(self.event_log)
        bonus = flawless * FLAWLESS_BONUS_KNOWLEDGE
        return {
            "resources": self.run_score(),
            "raw": raw,
            "base": base,
            "floor_applied": raw < 1,
            "flawless": flawless,
            "flawless_bonus": bonus,
            "total": base + bonus,
            "schedule_factor": factor,
        }

    def custom_knowledge_factor(self):
        """E-13: a hand-built schedule earns knowledge in proportion to how much damage it throws
        compared with the Classic mix (at most the full amount), so a short, gentle schedule
        cannot be farmed for knowledge. Every built-in scenario and the extended run are
        untouched (factor 1.0)."""
        if not self.custom_events:
            return 1.0
        total = sum(EVENT_BASE_DAMAGE[e] for e in self.custom_events)
        reference = sum(EVENT_BASE_DAMAGE[e] for e in EVENT_SCHEDULE)
        return min(1.0, total / reference)


runstate.run = RunState()
