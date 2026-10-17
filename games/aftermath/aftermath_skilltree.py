"""SkillTreeState (unlock, reset, move, pins) and the first load of the saved records into the live game."""

import json

from js import localStorage

import aftermath_runstate as runstate
from aftermath_persist import (
    _storage_write, load_curriculum_progress, load_highest_awarded_run, load_legacy_event_counts,
    load_legacy_events, load_run_history,
)
from aftermath_rules import SKILLS, SKILL_TREE_STORAGE_KEY


SKILL_MOVE_FEE = 1  # AN-13: knowledge a move of one point costs (the lifetime total never changes)


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
        """E3: branching/prerequisite structure — a skill is unlockable
        only once every id in its own "prereqs" list is itself already
        unlocked (empty for the three original skills, so they're
        unaffected)."""
        skill = SKILLS[skill_id]
        if skill_id in self.unlocked or self.knowledge_points < skill["cost"]:
            return False
        return all(prereq in self.unlocked for prereq in skill.get("prereqs", []))

    def missing_prereqs(self, skill_id):
        """The subset of skill_id's prereqs not yet unlocked, in catalog
        order — used to tell the player *why* a skill is locked (E3)."""
        return [prereq for prereq in SKILLS[skill_id].get("prereqs", []) if prereq not in self.unlocked]

    def unlock(self, skill_id):
        if not self.can_unlock(skill_id):
            return False
        self.knowledge_points -= SKILLS[skill_id]["cost"]
        self.unlocked.add(skill_id)
        self.save()
        return True

    def move_check(self, from_id, to_id):
        """AN-13: moving ONE point from an owned skill to another costs SKILL_MOVE_FEE knowledge (never a
        restart). Returns (ok, reason in plain words). Rules: both must be real skills; the first owned and
        the second not; nothing else owned may need the first one; the second's prerequisites must still be
        met without the first; the refund plus the balance must cover the second skill and the fee."""
        if from_id not in SKILLS or to_id not in SKILLS or from_id == to_id:
            return False, "Pick one skill you own and a different skill to move to."
        if from_id not in self.unlocked:
            return False, f"{SKILLS[from_id]['label']} is not one of your skills."
        if to_id in self.unlocked:
            return False, f"{SKILLS[to_id]['label']} is already yours."
        dependants = [SKILLS[s]["label"] for s in self.unlocked if s != from_id and from_id in SKILLS[s].get("prereqs", [])]
        if dependants:
            return False, f"{SKILLS[from_id]['label']} is needed by {', '.join(sorted(dependants))}, so it cannot be moved."
        missing = [SKILLS[p]["label"] for p in SKILLS[to_id].get("prereqs", []) if p not in self.unlocked or p == from_id]
        if missing:
            return False, f"{SKILLS[to_id]['label']} needs {', '.join(missing)} first."
        left = self.knowledge_points + SKILLS[from_id]["cost"] - SKILLS[to_id]["cost"] - SKILL_MOVE_FEE
        if left < 0:
            return False, f"You would be {-left} knowledge short (the move costs {SKILL_MOVE_FEE} on top of the difference)."
        return True, ""

    def move(self, from_id, to_id):
        ok, _reason = self.move_check(from_id, to_id)
        if not ok:
            return False
        self.knowledge_points += SKILLS[from_id]["cost"] - SKILLS[to_id]["cost"] - SKILL_MOVE_FEE
        self.unlocked.discard(from_id)
        self.unlocked.add(to_id)
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
        _storage_write(SKILL_TREE_STORAGE_KEY, json.dumps(self.to_dict()))

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


runstate.skill_tree = SkillTreeState.load()
runstate.run_history = load_run_history()
runstate.legacy_events = load_legacy_events()

runstate.curriculum_progress = load_curriculum_progress()  # E19

runstate.legacy_event_counts = load_legacy_event_counts()

runstate.highest_awarded_run = load_highest_awarded_run()
