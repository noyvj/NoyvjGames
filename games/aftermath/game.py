"""Aftermath — Climate Adaptation & Resilience Game.

Runs in-browser via Pyodide. A repeated-short-run core loop: a fixed
schedule of extreme weather (and other resilience-relevant) events,
resource allocation between events (resilience vs. growth investment),
and damage resolution, feeding a persistent cross-run skill tree and
"how far you've come" run comparison. See CLAUDE.md for the full
milestone history.
"""

import copy
import json

import info_page
from js import document, localStorage, setTimeout
from pyodide.ffi import create_proxy

STARTING_RESOURCES = 200.0

RESILIENCE_COST = 25
GROWTH_COST = 20
GROWTH_INCOME_PER_UNIT = 8

RESILIENCE_MITIGATION_PER_UNIT = 0.05
MAX_MITIGATION = 0.85

# Fixed schedule — every run faces the same sequence of event types, so
# runs are comparable to each other (needed for Milestone 5's "how far
# you've come" comparison). Iteration Pass 2 extended this with two
# non-weather resilience shocks (supply-chain, infrastructure) so
# "resilience" reads as a broader societal capacity than storm-proofing
# alone — same scheduled-event structure, just more event variety.
EVENT_SCHEDULE = [
    "flood", "heatwave", "supply_chain", "storm", "infrastructure_failure", "flood", "storm",
]

EVENT_LABEL = {
    "flood": "Flood",
    "heatwave": "Heatwave",
    "storm": "Storm",
    "supply_chain": "Supply-Chain Disruption",
    "infrastructure_failure": "Infrastructure Failure",
}

EVENT_ICON = {
    # Each icon carries an explicit U+FE0F variation selector so every
    # entry renders as a colorful emoji glyph consistently across
    # platforms/fonts, rather than some (e.g. the high-voltage sign) risking
    # a plain monochrome text-style glyph without it. Purely cosmetic —
    # rendering-only, no functional effect.
    "flood": "\U0001F30A️",  # water wave
    "heatwave": "\U0001F525️",  # fire
    "storm": "\U0001F32A️",  # tornado
    "supply_chain": "\U0001F4E6️",  # package
    "infrastructure_failure": "⚡️",  # high voltage
}

EVENT_BASE_DAMAGE = {
    "flood": 40.0,
    "heatwave": 35.0,
    "storm": 50.0,
    "supply_chain": 30.0,
    "infrastructure_failure": 38.0,
}

# Iteration Pass 2 — event-type category, so weather and non-weather
# shocks get a distinct visual/audio signature (a CSS class here, since
# there's no audio system in the stack) rather than just a different
# label on the same event UI.
EVENT_CATEGORY = {
    "flood": "weather",
    "heatwave": "weather",
    "storm": "weather",
    "supply_chain": "non-weather",
    "infrastructure_failure": "non-weather",
}

# Iteration-pass addition: severity varies per event so repeated runs
# don't feel identical. Deterministic (a hash-based formula, not
# wall-clock random) rather than truly random, and off entirely for
# run 1 — this keeps the run-1-vs-latest-run comparison
# (progress_comparison) meaningful (same run number always faces the
# same challenge level) and keeps every single-run test's exact damage
# numbers unchanged.
SEVERITY_VARIATION_MIN = 0.85
SEVERITY_VARIATION_MAX = 1.15

# Iteration Pass 3 (fun/teaching-balance) — a skill tree that only makes
# the player stronger while events stay flat is the textbook
# flow-boredom failure mode, so the severity spread widens symmetrically
# around the same 1.0 center for each resilience skill the player has
# unlocked overall. Center stays fixed (this isn't "the game punishes
# you for upgrading" — the hope-angle comparison must stay meaningful),
# but the ceiling a stronger skill tree can face rises right along with
# the floor it can catch, so a fully-invested run still gets asked
# something a first run never sees, instead of becoming a rote replay
# of an already-solved strategy.
SEVERITY_VARIATION_RANGE_PER_SKILL = 0.05


def skill_tree_strength():
    """How many resilience skills are unlocked overall — the signal Pass
    3 uses to widen event-severity variation so a stronger skill tree
    keeps facing a wider spread of challenge, not a flat one."""
    return len(skill_tree.unlocked)


def event_severity(run_number, event_index, skill_strength=0):
    if run_number <= 1:
        return 1.0
    seed = (run_number * 97 + event_index * 31) % 100
    center = (SEVERITY_VARIATION_MIN + SEVERITY_VARIATION_MAX) / 2
    half_width = (SEVERITY_VARIATION_MAX - SEVERITY_VARIATION_MIN) / 2
    half_width += SEVERITY_VARIATION_RANGE_PER_SKILL * skill_strength
    variation_min = center - half_width
    variation_max = center + half_width
    return variation_min + (seed / 100) * (variation_max - variation_min)


def severity_label(severity):
    if severity < 0.95:
        return "mild"
    if severity > 1.05:
        return "severe"
    return "typical"

# Skill tree — lives outside the run loop entirely, persisting between
# runs (and between visits, via localStorage). Bonus application to new
# runs is Milestone 4's job; this milestone is just the structure.
SKILLS = {
    "reinforced_infrastructure": {
        "cost": 3,
        "label": "Reinforced Infrastructure",
        "description": "+2 starting resilience capacity",
        "real_practice": "Mirrors real building codes requiring flood-resistant foundations and reinforced structures in vulnerable regions.",
    },
    "community_reserves": {
        "cost": 3,
        "label": "Community Reserves",
        "description": "+50 starting resources",
        "real_practice": "Mirrors community emergency funds and mutual-aid reserves, letting a region self-fund early recovery instead of waiting on outside aid.",
    },
    "early_warning": {
        "cost": 5,
        "label": "Early Warning Systems",
        "description": "+10% mitigation on all events",
        "real_practice": "Mirrors real early-warning networks — alert systems for floods and storms have been shown to cut disaster damage and casualties dramatically for relatively low cost.",
    },
}

SKILL_TREE_STORAGE_KEY = "aftermath_skill_tree_v1"
RUN_HISTORY_STORAGE_KEY = "aftermath_run_history_v1"

# Iteration Pass 2 — legacy system (stretch goal, built after the
# diversified events were solid): each completed run leaves behind a
# small trace beyond the skill-tree currency — a persistent record of
# which event types this settlement has weathered before, referenced as
# flavor text in the next run rather than a mechanical bonus.
LEGACY_STORAGE_KEY = "aftermath_legacy_events_v1"

# The shared save widget can restore an *older* in-memory RunState over a
# newer one (that's the whole point of "load a save from earlier") --
# including one whose event_index has already advanced past a point that
# was, in a different RunState object, resolved all the way to completion
# and already awarded knowledge/history/legacy. Without a persistent
# record of which run_number has already paid out, re-resolving that
# reloaded run's remaining events to completion would trigger the
# completion payout a second time for the same run: free knowledge
# points and a duplicate run_history entry, just by reloading a save
# taken before the run's last event. This tracks the highest run_number
# that has already been awarded (independent of any one RunState
# instance) so a completion only pays out the first time a given
# run_number crosses the finish line, no matter how many stale snapshots
# of it get loaded and re-resolved afterward.
AWARDED_RUN_STORAGE_KEY = "aftermath_highest_awarded_run_v1"


def load_highest_awarded_run():
    raw = localStorage.getItem(AWARDED_RUN_STORAGE_KEY)
    if not raw:
        return 0
    try:
        return int(json.loads(raw))
    except (ValueError, TypeError):
        return 0


def save_highest_awarded_run(run_number):
    localStorage.setItem(AWARDED_RUN_STORAGE_KEY, json.dumps(run_number))


def load_legacy_events():
    raw = localStorage.getItem(LEGACY_STORAGE_KEY)
    if not raw:
        return set()
    try:
        return set(json.loads(raw))
    except ValueError:
        return set()


def save_legacy_events(events):
    localStorage.setItem(LEGACY_STORAGE_KEY, json.dumps(sorted(events)))


def load_run_history():
    raw = localStorage.getItem(RUN_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except ValueError:
        return []


def save_run_history(history):
    localStorage.setItem(RUN_HISTORY_STORAGE_KEY, json.dumps(history))


def starting_resources_bonus():
    return 50 if "community_reserves" in skill_tree.unlocked else 0


def starting_resilience_bonus():
    return 2 if "reinforced_infrastructure" in skill_tree.unlocked else 0


def early_warning_mitigation_bonus():
    return 0.10 if "early_warning" in skill_tree.unlocked else 0.0


class RunState:
    def __init__(self, run_number=1):
        """Reads current skill-tree bonuses at creation time — a new run
        starts a little more capable than the last, per unlocked skills."""
        self.run_number = run_number
        self.event_index = 0
        self.resources = STARTING_RESOURCES + starting_resources_bonus()
        self.resilience_capacity = starting_resilience_bonus()
        self.growth_capacity = 0
        self.damage_taken = 0.0
        self.event_log = []
        # Achievements ("profitable_run") need to compare a run's *final*
        # resources against what it actually started with -- which varies
        # run to run once skill-tree bonuses affect starting resources, so
        # this is captured once here rather than re-deriving it later from
        # STARTING_RESOURCES + starting_resources_bonus() (the latter would
        # silently drift if more skills unlock mid-run... they can't, but
        # capturing it explicitly avoids relying on that being true).
        self.starting_resources = self.resources

    def is_complete(self):
        return self.event_index >= len(EVENT_SCHEDULE)

    def next_event_type(self):
        if self.is_complete():
            return None
        return EVENT_SCHEDULE[self.event_index]

    def invest_resilience(self):
        if self.resources < RESILIENCE_COST:
            return False
        self.resources -= RESILIENCE_COST
        self.resilience_capacity += 1
        _note_achievement_progress(ever_invested_resilience=True)
        if self.mitigation_fraction() >= MAX_MITIGATION:
            _note_achievement_progress(ever_maxed_mitigation=True)
        return True

    def invest_growth(self):
        if self.resources < GROWTH_COST:
            return False
        self.resources -= GROWTH_COST
        self.growth_capacity += 1
        _note_achievement_progress(ever_invested_growth=True)
        return True

    def mitigation_fraction(self):
        from_resilience = self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
        return min(MAX_MITIGATION, from_resilience + early_warning_mitigation_bonus())

    def resolve_next_event(self):
        """Applies growth income, then resolves the next scheduled event's
        damage (reduced by resilience mitigation). No-op once the run is
        complete."""
        if self.is_complete():
            return False

        self.resources += self.growth_capacity * GROWTH_INCOME_PER_UNIT

        event_type = EVENT_SCHEDULE[self.event_index]
        severity = event_severity(self.run_number, self.event_index, skill_tree_strength())
        damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - self.mitigation_fraction())
        self.resources = max(0.0, self.resources - damage)
        self.damage_taken += damage
        self.event_log.append({"type": event_type, "damage": damage, "severity": severity})
        self.event_index += 1

        _note_achievement_progress(ever_faced_event=True)
        if severity_label(severity) == "severe" and self.resources > 0:
            _note_achievement_progress(ever_survived_severe_event=True)

        if self.is_complete():
            global highest_awarded_run
            if self.run_number > highest_awarded_run:
                skill_tree.add_knowledge(self.knowledge_points_earned())
                skill_tree.save()
                run_history.append(self.run_score())
                save_run_history(run_history)
                legacy_events.update(entry["type"] for entry in self.event_log)
                save_legacy_events(legacy_events)
                highest_awarded_run = self.run_number
                save_highest_awarded_run(highest_awarded_run)

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

        return True

    def run_score(self):
        """How well the settlement weathered the run — just the resources
        it has left. Reflects both good mitigation (less damage) and good
        growth (more income to absorb it)."""
        return self.resources

    def knowledge_points_earned(self):
        """Currency for the skill tree. Floored at 1 — per the hope angle,
        even a rough run always contributes some permanent capability,
        never zero."""
        return max(1, round(self.run_score() / 20))


class SkillTreeState:
    """Persistent, separate from RunState — survives across runs and, via
    localStorage, across visits (same browser)."""

    def __init__(self):
        self.knowledge_points = 0
        self.unlocked = set()
        # Lifetime total ever earned -- unlike knowledge_points (a spendable
        # balance that drops on unlock), this only ever grows, so it's the
        # correct signal for a "earn N knowledge points over your
        # settlement's lifetime" achievement (knowledge_25/knowledge_100).
        self.lifetime_knowledge = 0

    def can_unlock(self, skill_id):
        return skill_id not in self.unlocked and self.knowledge_points >= SKILLS[skill_id]["cost"]

    def unlock(self, skill_id):
        if not self.can_unlock(skill_id):
            return False
        self.knowledge_points -= SKILLS[skill_id]["cost"]
        self.unlocked.add(skill_id)
        self.save()
        return True

    def add_knowledge(self, amount):
        self.knowledge_points += amount
        self.lifetime_knowledge += amount

    def to_dict(self):
        return {
            "knowledge_points": self.knowledge_points,
            "unlocked": sorted(self.unlocked),
            "lifetime_knowledge": self.lifetime_knowledge,
        }

    def save(self):
        localStorage.setItem(SKILL_TREE_STORAGE_KEY, json.dumps(self.to_dict()))

    @classmethod
    def load(cls):
        instance = cls()
        raw = localStorage.getItem(SKILL_TREE_STORAGE_KEY)
        if not raw:
            return instance
        try:
            data = json.loads(raw)
        except ValueError:
            return instance
        instance.knowledge_points = data.get("knowledge_points", 0)
        instance.unlocked = set(data.get("unlocked", []))
        # Defensive fallback for a save made before this field existed
        # (ACHIEVEMENTS-SYSTEM-DESIGN.md §4's pattern): default to whatever
        # the current spendable balance is rather than 0, so an existing
        # player's lifetime total isn't understated the moment this field
        # ships -- an underestimate (missing already-spent knowledge) is
        # far less surprising than a stale save silently reporting fewer
        # lifetime points than the player can literally see they're holding.
        instance.lifetime_knowledge = data.get("lifetime_knowledge", instance.knowledge_points)
        return instance


skill_tree = SkillTreeState.load()
run_history = load_run_history()
legacy_events = load_legacy_events()
highest_awarded_run = load_highest_awarded_run()
run = RunState()


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL/Canopy/Grid's
# reference integrations. Every achievement's earned status is a pure
# function of state that already exists elsewhere in this module, recomputed
# fresh every call — never a separately hand-maintained "earned" flag.
#
# Several achievements here genuinely can't be derived from run_history/
# skill_tree/legacy_events alone: things like "ever invested in Resilience"
# or "ever finished a run in profit" are facts about a *specific run's*
# transient RunState, which resets every new run (§4's five-step pattern
# from the design doc — a persistent fact needs its own persistent tracked
# state, or it would flicker unearned the instant a new run starts). Those
# live in `achievement_progress`, a small persistent dict alongside the
# skill tree/run history/legacy events already in localStorage, mutated
# only where the real event happens (inside RunState's own methods, since
# that's where each of these facts actually becomes true) and otherwise
# read-only from every achievement checker below.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"
ACHIEVEMENT_PROGRESS_STORAGE_KEY = "aftermath_achievement_progress_v1"


def _read_achievements_json():
    """Same loading contract as SOL/Canopy/Grid's `_read_achievements_json()`:
    the boot script fetches achievements.json and hands it to Python as a
    window global before this file runs; the pytest harness's fake `js`
    module has no such attribute, so this falls through to reading the file
    straight off disk, keeping the module importable outside a real
    browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Aftermath's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

RUN_COMPLETE_TARGETS = {"run_complete_1": 1, "run_complete_5": 5, "run_complete_10": 10}
KNOWLEDGE_TARGETS = {"knowledge_25": 25, "knowledge_100": 100}
SKILL_ACHIEVEMENT_IDS = {
    "reinforced_infrastructure": "unlock_reinforced_infrastructure",
    "community_reserves": "unlock_community_reserves",
    "early_warning": "unlock_early_warning",
}


def _default_achievement_progress():
    return {
        "ever_faced_event": False,
        "ever_invested_resilience": False,
        "ever_invested_growth": False,
        "ever_maxed_mitigation": False,
        "ever_survived_severe_event": False,
        "ever_profitable_run": False,
        "ever_growth_heavy_run": False,
        "ever_resilience_heavy_run": False,
        "ever_balanced_run": False,
    }


def load_achievement_progress():
    progress = _default_achievement_progress()
    raw = localStorage.getItem(ACHIEVEMENT_PROGRESS_STORAGE_KEY)
    if not raw:
        return progress
    try:
        data = json.loads(raw)
    except ValueError:
        return progress
    if isinstance(data, dict):
        for key in progress:
            if key in data:
                progress[key] = bool(data[key])
    return progress


def save_achievement_progress():
    localStorage.setItem(ACHIEVEMENT_PROGRESS_STORAGE_KEY, json.dumps(achievement_progress))


achievement_progress = load_achievement_progress()


def _note_achievement_progress(**updates):
    """Sets one or more achievement_progress flags to True (only ever True
    — these are one-way "has this ever happened" facts, never unset) and
    persists if anything actually changed."""
    changed = False
    for key, value in updates.items():
        if value and not achievement_progress.get(key):
            achievement_progress[key] = True
            changed = True
    if changed:
        save_achievement_progress()


def _full_skill_tree_earned():
    return all(skill_id in skill_tree.unlocked for skill_id in SKILLS)


ACHIEVEMENT_CHECKS = {
    "first_event_faced": lambda: achievement_progress["ever_faced_event"],
    "first_resilience_investment": lambda: achievement_progress["ever_invested_resilience"],
    "first_growth_investment": lambda: achievement_progress["ever_invested_growth"],
    "run_complete_1": lambda: len(run_history) >= RUN_COMPLETE_TARGETS["run_complete_1"],
    "run_complete_5": lambda: len(run_history) >= RUN_COMPLETE_TARGETS["run_complete_5"],
    "run_complete_10": lambda: len(run_history) >= RUN_COMPLETE_TARGETS["run_complete_10"],
    "unlock_reinforced_infrastructure": lambda: "reinforced_infrastructure" in skill_tree.unlocked,
    "unlock_community_reserves": lambda: "community_reserves" in skill_tree.unlocked,
    "unlock_early_warning": lambda: "early_warning" in skill_tree.unlocked,
    "full_skill_tree": _full_skill_tree_earned,
    "knowledge_25": lambda: skill_tree.lifetime_knowledge >= KNOWLEDGE_TARGETS["knowledge_25"],
    "knowledge_100": lambda: skill_tree.lifetime_knowledge >= KNOWLEDGE_TARGETS["knowledge_100"],
    "iron_defenses": lambda: achievement_progress["ever_maxed_mitigation"],
    "severe_survivor": lambda: achievement_progress["ever_survived_severe_event"],
    "profitable_run": lambda: achievement_progress["ever_profitable_run"],
    "growth_focused": lambda: achievement_progress["ever_growth_heavy_run"],
    "resilience_focused": lambda: achievement_progress["ever_resilience_heavy_run"],
    "balanced_strategy": lambda: achievement_progress["ever_balanced_run"],
    "come_back_stronger": lambda: len(run_history) >= 2 and run_history[-1] > run_history[0],
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone.
ACHIEVEMENT_PROGRESS = {
    "run_complete_5": lambda: (min(len(run_history), 5), 5),
    "run_complete_10": lambda: (min(len(run_history), 10), 10),
    "full_skill_tree": lambda: (len(skill_tree.unlocked & set(SKILLS)), len(SKILLS)),
    "knowledge_25": lambda: (min(skill_tree.lifetime_knowledge, 25), 25),
    "knowledge_100": lambda: (min(skill_tree.lifetime_knowledge, 100), 100),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False


# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as SOL's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest resilience/growth, resolve an event, unlock a skill, start a
    new run) — never from render() itself, since load_state() also calls
    render() and a loaded save with several achievements already earned
    must not flood the player with toasts for all of them at once (see
    _seed_achievement_toast_baseline)."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub Pages
    # subpath fix). Rebuilt each open alongside the cards since the panel
    # is cleared first. Note: the hub-side script.js registration that
    # makes Aftermath's save data actually show up on that dashboard is a
    # root-file change, out of scope for this games/aftermath/-only
    # dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)


def legacy_message():
    if not legacy_events:
        return "No history yet — this is the settlement's first trial."
    labels = sorted(EVENT_LABEL[event_type] for event_type in legacy_events)
    return (
        f"This settlement has weathered {', '.join(labels)} before — every run's "
        f"damage becomes part of what the next one is built to withstand."
    )


def progress_comparison():
    """The hope-angle payoff: run 1 vs. the most recent run, same event
    schedule. None until at least two runs have been completed."""
    if len(run_history) < 2:
        return None
    return run_history[0], run_history[-1]


def progress_message(comparison):
    if comparison is None:
        return "Play more runs to see how far you've come."
    first, latest = comparison
    if latest > first:
        return (
            f"Look how far you've come — your first run scored {first:.0f}, "
            f"your most recent scored {latest:.0f}. Same events, handled better."
        )
    if latest < first:
        return f"Your most recent run ({latest:.0f}) scored lower than your first ({first:.0f})."
    return f"Your run performance has held steady at {latest:.0f}."


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Adaptation — building resilience to climate impacts already "
        "locked in — is treated by climate science and policy as its own "
        "necessary response, not a fallback for failed mitigation. Real "
        "communities that invested early in resilient infrastructure have "
        "documented, measurable payoffs. Aftermath's resource-allocation "
        "choices and its \"how far you've come\" comparison are modeled "
        "on that same idea."
    ),
    "mechanic_tie_in": (
        "The skill tree's resilience/growth split mirrors a real, "
        "documented tradeoff facing infrastructure investment: pay up "
        "front for resilience, or grow capacity and risk being caught "
        "underprepared."
    ),
    "sources": [
        {
            "label": "IPCC AR6 Working Group II — Climate Change 2022: Impacts, Adaptation and Vulnerability",
            "url": "https://www.ipcc.ch/report/ar6/wg2/",
            "note": "The authoritative global reference on adaptation as a distinct climate response, backing Aftermath's core framing.",
        },
        {
            "label": "World Resources Institute — Accelerating Climate-resilient Infrastructure Investment in China",
            "url": "https://www.wri.org/research/accelerating-climate-resilient-infrastructure-investment-china",
            "note": "A real resilience-infrastructure investment case study, grounding Aftermath's resource-allocation mechanic.",
        },
        {
            "label": "World Resources Institute — Driving System Shifts for Climate Resilience (Bhutan, Ethiopia, Costa Rica)",
            "url": "https://www.wri.org/research/driving-system-shifts-climate-resilience-case-studies-transformative-adaptation-bhutan",
            "note": "Real communities' documented adaptation journeys — strong backing for the \"look how far you've come\" hope angle.",
        },
        {
            "label": "EU Mission on Adaptation to Climate Change — Success Stories",
            "url": "https://mission-adaptation-portal.ec.europa.eu/stories-0_en",
            "note": "A running collection of real municipal adaptation wins — concrete \"this actually worked\" examples.",
        },
    ],
}
info_page_open = False


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


def render():
    render_info_page()
    update_achievements_display()
    document.getElementById("legacy-display").innerText = legacy_message()
    document.getElementById("resources-display").innerText = f"Resources: {run.resources:.0f}"
    document.getElementById("resilience-display").innerText = f"Resilience: {run.resilience_capacity}"
    document.getElementById("growth-display").innerText = f"Growth: {run.growth_capacity}"

    if run.is_complete():
        document.getElementById("progress-display").innerText = "Run complete"
        document.getElementById("next-event-display").innerText = "No more events this run."
        document.getElementById("run-summary-display").innerText = (
            f"Score: {run.run_score():.0f} — "
            f"earned {run.knowledge_points_earned()} resilience knowledge point"
            f"{'s' if run.knowledge_points_earned() != 1 else ''}."
        )
    else:
        document.getElementById("run-summary-display").innerText = ""
        document.getElementById("progress-display").innerText = (
            f"Event {run.event_index + 1} of {len(EVENT_SCHEDULE)}"
        )
        next_type = run.next_event_type()
        next_event_el = document.getElementById("next-event-display")
        next_event_el.innerText = f"Next: {EVENT_ICON[next_type]} {EVENT_LABEL[next_type]}"
        next_event_el.className = f"status-line event-category--{EVENT_CATEGORY[next_type]}"

    last_event_el = document.getElementById("last-event-display")
    if run.event_log:
        last = run.event_log[-1]
        last_event_el.innerText = (
            f"Last: {EVENT_ICON[last['type']]} {EVENT_LABEL[last['type']]} "
            f"— {last['damage']:.0f} damage ({severity_label(last['severity'])} intensity)"
        )
        last_event_el.className = f"status-line event-category--{EVENT_CATEGORY[last['type']]}"
    else:
        last_event_el.innerText = ""
        last_event_el.className = "status-line"

    document.getElementById("mitigation-bar").style.width = f"{run.mitigation_fraction() * 100:.0f}%"

    resilience_button = document.getElementById("resilience-invest-button")
    resilience_button.innerText = f"Invest in Resilience ({RESILIENCE_COST})"
    resilience_button.disabled = run.resources < RESILIENCE_COST or run.is_complete()

    growth_button = document.getElementById("growth-invest-button")
    growth_button.innerText = f"Invest in Growth ({GROWTH_COST})"
    growth_button.disabled = run.resources < GROWTH_COST or run.is_complete()

    resolve_button = document.getElementById("resolve-event-button")
    resolve_button.disabled = run.is_complete()

    document.getElementById("new-run-button").hidden = not run.is_complete()
    document.getElementById("progress-comparison-display").innerText = progress_message(
        progress_comparison()
    )

    document.getElementById("knowledge-points-display").innerText = (
        f"Resilience knowledge: {skill_tree.knowledge_points}"
    )
    for skill_id, skill in SKILLS.items():
        status_el = document.getElementById(f"skill-{skill_id}-status")
        practice_el = document.getElementById(f"skill-{skill_id}-practice")
        unlock_button = document.getElementById(f"skill-{skill_id}-unlock-button")
        practice_el.innerText = skill["real_practice"]
        if skill_id in skill_tree.unlocked:
            status_el.innerText = f"{skill['label']} — unlocked ({skill['description']})"
            unlock_button.hidden = True
        else:
            status_el.innerText = f"{skill['label']} — {skill['description']}"
            unlock_button.hidden = False
            unlock_button.innerText = f"Unlock ({skill['cost']})"
            unlock_button.disabled = not skill_tree.can_unlock(skill_id)


def on_invest_resilience(event=None):
    run.invest_resilience()
    render()
    _check_new_achievements_for_toast()


def on_invest_growth(event=None):
    run.invest_growth()
    render()
    _check_new_achievements_for_toast()


def on_resolve_event(event=None):
    run.resolve_next_event()
    render()
    _check_new_achievements_for_toast()


def start_new_run(event=None):
    """Starts a fresh run, reading current skill-tree bonuses — each run
    begins a little more capable than the last, per unlocked skills.

    Derives the new run_number from whichever is higher, the current run's
    own number or the persisted highest-awarded-run mark, not just the
    current run's number + 1. The current `run` can itself be a stale,
    reloaded snapshot (e.g. the player loaded an old still-in-progress save
    before starting anew) whose run_number sits behind runs that have
    since completed and been awarded elsewhere in the session -- basing
    the new number on it alone could hand out a run_number that's already
    in highest_awarded_run's past, silently blocking this genuinely new
    run's own completion payout later (see the double-award guard on
    resolve_next_event() above, and its dedicated test coverage in
    tests/test_save_system.py)."""
    global run
    run = RunState(run_number=max(run.run_number, highest_awarded_run) + 1)
    render()
    _check_new_achievements_for_toast()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state()/load_state() cover Aftermath's in-memory *per-run* state
# only — the current RunState (run_number, event_index, resources,
# resilience_capacity, growth_capacity, damage_taken, event_log) — which
# is what needs to round-trip so a saved-and-reloaded run resumes at the
# exact point it was saved. The persistent skill tree (SkillTreeState),
# run_history, and legacy_events are deliberately NOT part of this
# round trip: per CLAUDE.md's Tech notes, those are a distinct,
# already-working persistence mechanism keyed to localStorage (not to a
# save code) that survives across runs and browser visits on its own.
# Folding them into this save system would mean a loaded save code could
# silently overwrite a browser's separately-accumulated skill tree with
# whatever it looked like at save time — the wrong behavior for state
# that's supposed to be permanent. A save code loaded on a different
# browser/device therefore resumes the exact in-progress run, but keeps
# whatever skill tree/legacy history (or lack of it) already exists
# locally — consistent with how that persistence already behaves
# independent of any one run.
def get_state():
    """Return the current run's in-memory state as a plain JSON-safe dict.
    `event_log` is deep-copied — it's a list of dicts, and a shallow copy
    would still alias it, so continued play after taking a "snapshot"
    would silently mutate the saved copy."""
    return {
        "run_number": run.run_number,
        "event_index": run.event_index,
        "resources": run.resources,
        "resilience_capacity": run.resilience_capacity,
        "growth_capacity": run.growth_capacity,
        "damage_taken": run.damage_taken,
        "event_log": copy.deepcopy(run.event_log),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back by load_state() below.
        "achievements_earned": achievement_ids_earned(),
    }


# Direct key access (data["run_number"], etc.), no defensive handling --
# unlike SkillTreeState.load()'s try/except. This is intentional, not an
# oversight: a real save handed here always came from this same site's own
# get_state() via the save widget's fetch/PUT round trip, so a malformed
# payload means something upstream already went wrong, and a loud KeyError
# is preferable to silently starting a run in a half-restored state. Pinned
# by tests/test_save_system.py::test_load_state_on_a_malformed_dict_raises_rather_than_corrupting_the_run
# so this stays a deliberate choice, not something a future change reverts.
def load_state(data):
    """The exact inverse of get_state() — rebuilds the current run from a
    saved dict and re-renders so the UI reflects the loaded run
    immediately. Constructs a fresh RunState (which reads current
    skill-tree bonuses, same as starting any new run) and then overwrites
    every field with the saved values, so the restored run matches
    exactly what was saved regardless of the skill tree's state now."""
    global run
    run = RunState(run_number=data["run_number"])
    run.event_index = data["event_index"]
    run.resources = data["resources"]
    run.resilience_capacity = data["resilience_capacity"]
    run.growth_capacity = data["growth_capacity"]
    run.damage_taken = data["damage_taken"]
    run.event_log = copy.deepcopy(data["event_log"])
    render()
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1. Re-seed
    # the toast baseline instead of leaving it as-is, so a loaded save with
    # several achievements already earned doesn't flood the player with
    # toasts for all of them at once (same reasoning as setup()'s seed).
    _seed_achievement_toast_baseline()
    return True


def _make_unlock_handler(skill_id):
    def handler(event=None):
        skill_tree.unlock(skill_id)
        render()
        _check_new_achievements_for_toast()
    return handler


def setup():
    document.getElementById("resilience-invest-button").addEventListener(
        "click", create_proxy(on_invest_resilience)
    )
    document.getElementById("growth-invest-button").addEventListener(
        "click", create_proxy(on_invest_growth)
    )
    document.getElementById("resolve-event-button").addEventListener(
        "click", create_proxy(on_resolve_event)
    )
    document.getElementById("new-run-button").addEventListener(
        "click", create_proxy(start_new_run)
    )
    for skill_id in SKILLS:
        document.getElementById(f"skill-{skill_id}-unlock-button").addEventListener(
            "click", create_proxy(_make_unlock_handler(skill_id))
        )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("achievement-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
