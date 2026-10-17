"""Sentences for random events and disruptions (event_message, disruption_reason, severity classes).
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from grid_rules import DAMAGE_SEVERITY_THRESHOLD, PLANT_LABEL


def event_message(event):
    if event is None:
        return "No disruptions last round."
    if event["type"] == "damage":
        plant_name = PLANT_LABEL[event["damaged_plant"]]
        return (
            f"Damage! A {plant_name} plant went offline "
            f"(lost {event['revenue_loss']:.0f} funds in the disruption)."
        )
    # C3: name the specific plant type most responsible, rather than a
    # generic "the grid" message -- falls back to a lingering-emissions
    # framing for the (rarer) case of a brownout with no fossil plant
    # currently standing to attribute it to (historical emissions from
    # fossil capacity retired earlier this run can still be driving risk).
    cause_plant = event.get("cause_plant")
    if cause_plant:
        plant_name = PLANT_LABEL[cause_plant]
        return (
            f"Brownout! {plant_name} generation strained the grid "
            f"(lost {event['revenue_loss']:.0f} funds to instability)."
        )
    return f"Brownout! Lost {event['revenue_loss']:.0f} funds to lingering historical emissions."


def disruption_reason(event):
    """C10: a 'why this happened' line tied to the specific plant behind the
    event, for the disruption toast."""
    severity_pct = event["severity"] * 100
    if event["type"] == "damage":
        plant = PLANT_LABEL[event["damaged_plant"]]
        return (
            f"Why: accumulated emissions put disruption severity at {severity_pct:.0f}%, past the "
            f"{DAMAGE_SEVERITY_THRESHOLD * 100:.0f}% damage line -- your largest fossil fleet ({plant}) took the hit."
        )
    cause = event.get("cause_plant")
    if cause:
        return (
            f"Why: emissions put disruption severity at {severity_pct:.0f}%, and {PLANT_LABEL[cause]} "
            "is your biggest emissions source."
        )
    return f"Why: historical emissions still put disruption severity at {severity_pct:.0f}%."


def event_severity_class(event):
    """CSS class for the event notification — visually distinct so a real
    disruption doesn't read the same as "nothing happened"."""
    if event is None:
        return "event-display"
    if event["type"] == "damage":
        return "event-display event-display--danger"
    return "event-display event-display--warning"
