"""Continuum -- K-6: era doctrines.

When the settlement enters a new era you may adopt one doctrine for it: a way the people
choose to look at the world. A doctrine makes some research branches cheaper and adds one
small standing bonus. It is recorded in the founder's log and tied to the Dynasty (the
perk "Schools of Thought" makes the discounts five points deeper).

Deliberately small and forgiving, in keeping with the game's "easy to complete" rule:

* One doctrine per era, chosen at any time while you are in that era (the first era has
  none: doctrines mark transitions). An era you leave without choosing is simply missed.
* A choice is final for that era, so it has to be weighed, but it cannot trap you: the
  discounts are 5 to 15 percent and the bonuses a few percent.
* Each *kind* of doctrine counts once, however many eras you gave it to; adopting the same
  one a second time deepens it to half again as strong ("entrenched"). All discounts on a
  branch together are capped at 40 percent.
* Doctrines are your own play, so they stay on during a challenge run; only the Dynasty
  edge (the perk) rests there.

The original design note also asked doctrines to "unlock different buildings". That is not
built: every building already belongs to a fixed era and role pair across the game's
engine, Hamlet view and tests, and adding era-conditional buildings would touch all of
them. The standing bonus is the second effect instead.

Pure functions of a plain dict (`campaign.ui`), validated on every read.
"""

import dynasty
import research
import sim

KEY = "doctrines"
MAX_DISCOUNT_PERCENT = 40
ENTRENCHED_FACTOR = 1.5
MAJOR_DISCOUNT_FROM = 10  # a discount of this many percent or more counts as a doctrine's main branch

DOCTRINES = {
    "maritime": {
        "label": "Maritime",
        "blurb": "Look outward along the water: harvests and trade reach further than any one field.",
        "discounts": {"provision": 15, "community": 5},
        "effects": {"food_storage_bonus": 4.0},
    },
    "highland": {
        "label": "Highland",
        "blurb": "Terraces and quarries: shape the stone and the slope, and take only what the hill can give back.",
        "discounts": {"craft": 15, "provision": 5},
        "effects": {"regen_mult": 0.04},
    },
    "caravan": {
        "label": "Caravan",
        "blurb": "Keep moving and keep meeting people: the roads, the markets and the pacts are the real wealth.",
        "discounts": {"community": 15, "craft": 5},
        "effects": {"surplus_conversion_bonus": 0.04},
    },
    "scholarly": {
        "label": "Scholarly",
        "blurb": "Write it down, argue it out, teach it on: a little less cost to every branch, and sharper keepers.",
        "discounts": {"provision": 8, "community": 8, "craft": 8},
        "effects": {"knowledge_mult": 0.04},
    },
}
DOCTRINE_IDS = tuple(DOCTRINES)


def clean(raw):
    """{'chosen': {era id: doctrine id}}: known eras after the first, known doctrines only."""
    chosen = {}
    source = raw.get("chosen") if isinstance(raw, dict) else None
    if isinstance(source, dict):
        for era, doctrine in source.items():
            if isinstance(era, str) and era in sim.ERA_ORDER and era != sim.FIRST_ERA \
                    and isinstance(doctrine, str) and doctrine in DOCTRINES:
                chosen[era] = doctrine
    return {"chosen": chosen}


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else clean(None)


def put(ui, record):
    record = clean(record)
    if not record["chosen"]:
        ui.pop(KEY, None)
    else:
        ui[KEY] = record
    return record


def chosen_for(ui, era):
    return get(ui)["chosen"].get(era)


def is_open(ui, era):
    """True when a doctrine can still be adopted for `era` (any era but the first, none chosen yet)."""
    return era in sim.ERA_ORDER and era != sim.FIRST_ERA and chosen_for(ui, era) is None


def choose(ui, era, doctrine_id):
    """Adopts a doctrine for `era`. Returns (ok, reason)."""
    if doctrine_id not in DOCTRINES:
        return False, "That is not a doctrine."
    if era == sim.FIRST_ERA or era not in sim.ERA_ORDER:
        return False, "Doctrines begin with the first era transition."
    record = get(ui)
    if era in record["chosen"]:
        return False, "A doctrine has already been chosen for this era."
    record["chosen"][era] = doctrine_id
    put(ui, record)
    return True, ""


def counts(ui):
    """{doctrine id: eras it was adopted in}."""
    out = {}
    for doctrine in get(ui)["chosen"].values():
        out[doctrine] = out.get(doctrine, 0) + 1
    return out


def strength(count):
    """How strong a doctrine is: 1.0, or 1.5 once adopted in a second era."""
    return ENTRENCHED_FACTOR if count >= 2 else 1.0


def discounts(ui, edge=0):
    """{branch: total percent off research cost}, capped. `edge` extra points go on each
    branch a doctrine discounts by 10 percent or more (the Dynasty perk)."""
    totals = {branch: 0.0 for branch in research.BRANCHES}
    major = set()
    for doctrine_id, count in counts(ui).items():
        factor = strength(count)
        for branch, percent in DOCTRINES[doctrine_id]["discounts"].items():
            totals[branch] += percent * factor
            if percent >= MAJOR_DISCOUNT_FROM:
                major.add(branch)
    if edge:
        for branch in major:
            totals[branch] += edge
    return {branch: min(float(MAX_DISCOUNT_PERCENT), value) for branch, value in totals.items()}


def cost_multipliers(ui, edge=0):
    """{branch: research cost multiplier}; empty when no doctrine applies, so the tree is untouched."""
    totals = discounts(ui, edge)
    if not any(totals.values()):
        return {}
    return {branch: round(1.0 - percent / 100.0, 4) for branch, percent in totals.items() if percent}


def effect_deltas(ui):
    out = {}
    for doctrine_id, count in counts(ui).items():
        factor = strength(count)
        for key, value in DOCTRINES[doctrine_id]["effects"].items():
            out[key] = out.get(key, 0.0) + value * factor
    return out


def apply_effects(effects, ui):
    """`effects` with the doctrines' standing bonuses added (a copy), or `effects` itself with none."""
    deltas = effect_deltas(ui)
    if not deltas:
        return effects
    return dynasty.add_deltas(effects, deltas)


def discount_text(doctrine_id):
    discounts_ = DOCTRINES[doctrine_id]["discounts"]
    return ", ".join(
        f"{research.BRANCH_LABEL[branch]} research {percent}% cheaper"
        for branch, percent in sorted(discounts_.items(), key=lambda item: (-item[1], item[0]))
    )


def effect_text(doctrine_id):
    node = type("Node", (), {"effects": DOCTRINES[doctrine_id]["effects"]})
    return research.describe_effects(node)


def history(ui):
    """[(era id, doctrine id)] in era order."""
    chosen = get(ui)["chosen"]
    return [(era, chosen[era]) for era in sim.ERA_ORDER if era in chosen]


def log_line(era, doctrine_id):
    """The founder's-log note written when a doctrine is adopted (kept under the 200-character cap)."""
    return f"Doctrine of the {DOCTRINES[doctrine_id]['label']} adopted for the {sim.ERA_LABEL[era]} era."
