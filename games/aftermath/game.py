"""Aftermath — Climate Adaptation & Resilience Game.

Runs in-browser via Pyodide. Milestone 1: the single-run core loop — a
fixed schedule of extreme weather events, resource allocation between
events (resilience vs. growth investment), and damage resolution.
Run scoring, the persistent skill tree, and cross-run comparisons land
in later milestones.
"""

import json

from js import document, localStorage
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
    "flood": "\U0001F30A",  # water wave
    "heatwave": "\U0001F525",  # fire
    "storm": "\U0001F32A️",  # tornado
    "supply_chain": "\U0001F4E6",  # package
    "infrastructure_failure": "⚡",  # high voltage
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


def event_severity(run_number, event_index):
    if run_number <= 1:
        return 1.0
    seed = (run_number * 97 + event_index * 31) % 100
    return SEVERITY_VARIATION_MIN + (seed / 100) * (SEVERITY_VARIATION_MAX - SEVERITY_VARIATION_MIN)


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
        return True

    def invest_growth(self):
        if self.resources < GROWTH_COST:
            return False
        self.resources -= GROWTH_COST
        self.growth_capacity += 1
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
        severity = event_severity(self.run_number, self.event_index)
        damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - self.mitigation_fraction())
        self.resources = max(0.0, self.resources - damage)
        self.damage_taken += damage
        self.event_log.append({"type": event_type, "damage": damage, "severity": severity})
        self.event_index += 1

        if self.is_complete():
            skill_tree.add_knowledge(self.knowledge_points_earned())
            skill_tree.save()
            run_history.append(self.run_score())
            save_run_history(run_history)
            legacy_events.update(entry["type"] for entry in self.event_log)
            save_legacy_events(legacy_events)

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

    def to_dict(self):
        return {"knowledge_points": self.knowledge_points, "unlocked": sorted(self.unlocked)}

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
        return instance


skill_tree = SkillTreeState.load()
run_history = load_run_history()
legacy_events = load_legacy_events()
run = RunState()


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


def render():
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


def on_invest_growth(event=None):
    run.invest_growth()
    render()


def on_resolve_event(event=None):
    run.resolve_next_event()
    render()


def start_new_run(event=None):
    """Starts a fresh run, reading current skill-tree bonuses — each run
    begins a little more capable than the last, per unlocked skills."""
    global run
    run = RunState(run_number=run.run_number + 1)
    render()


def _make_unlock_handler(skill_id):
    def handler(event=None):
        skill_tree.unlock(skill_id)
        render()
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
    render()


setup()
