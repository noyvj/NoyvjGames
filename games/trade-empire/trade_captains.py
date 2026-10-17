"""Captain perks (the four captains, their numbers and multipliers) and the captain table."""

import trade_runstate as runstate
from trade_colony import colony_states
from trade_rules import ALL_COLONIES


# ---------------------------------------------------------------------------
# J-7/J-8 -- Fleet Captains. A ship that has become a veteran hauler (five
# round trips on one route) earns a captain: the player CHOOSES which of four
# named captains to put in the seat from a visible roster, so nothing is a
# random draw. Each captain's perk has a built-in trade-off, a captain serves
# on one ship at a time, and a captain may be moved to a different ship once
# per charter. Captains are met once and remembered across charters (a small
# collection); their postings reset with every renewal, like the fleet.
# Without a captain every helper below returns the plain value.
# ---------------------------------------------------------------------------
CAPTAIN_SWAPS_PER_CHARTER = 1  # moves of one captain after the first posting
LUCKY_EVERY = 4  # every Nth delivery by a Lucky Trader pays extra
LUCKY_BONUS = 0.40
LUCKY_OFF_BEAT = -0.03
FRUGAL_PROCEEDS = 0.08
FRUGAL_CARGO = 0.90
NIGHT_OWL_MIN_TICKS = 3  # a trip must be at least this long to save a tick
NIGHT_OWL_PROCEEDS = -0.05
PERFECTIONIST_BONUS = 0.12
PERFECTIONIST_BELOW = 0.6
PERFECTIONIST_PENALTY = -0.05
PERFECTIONIST_ABOVE = 0.9
CAPTAINS = {
    "frugal": {
        "label": "Frugal", "name": "Captain Ilsa Brandt",
        "perk": f"+{int(FRUGAL_PROCEEDS * 100)}% on this ship's sales.",
        "tradeoff": f"Holds {int(round((1 - FRUGAL_CARGO) * 100))}% less cargo (hurts a Fast hull most; a Cargo-heavy hull hides it).",
        "quote": "Every crate counted twice.",
    },
    "lucky": {
        "label": "Lucky Trader", "name": "Captain Joss Marrow",
        "perk": f"Every {LUCKY_EVERY}th delivery pays +{int(LUCKY_BONUS * 100)}%.",
        "tradeoff": f"The other deliveries pay {int(LUCKY_OFF_BEAT * 100)}%, so it is a small average gain, not a jackpot.",
        "quote": "I never gamble. The odds are simply fond of me.",
    },
    "night_owl": {
        "label": "Night Owl", "name": "Captain Sef Okonkwo",
        "perk": f"Trips of {NIGHT_OWL_MIN_TICKS}+ ticks arrive one tick sooner.",
        "tradeoff": f"{int(NIGHT_OWL_PROCEEDS * 100)}% on sales, and no gain on a Fast hull already near the one-tick floor.",
        "quote": "Dock lights are for people who sleep.",
    },
    "perfectionist": {
        "label": "Perfectionist", "name": "Captain Rhea Vance",
        "perk": f"+{int(PERFECTIONIST_BONUS * 100)}% when delivering to a colony under {int(PERFECTIONIST_BELOW * 100)}% satisfied.",
        "tradeoff": f"{int(PERFECTIONIST_PENALTY * 100)}% when the colony is already over {int(PERFECTIONIST_ABOVE * 100)}% satisfied.",
        "quote": "If it is not needed, it is not on my manifest.",
    },
}
CAPTAIN_IDS = tuple(CAPTAINS)

runstate.captain_assignments = {perk_id: 0 for perk_id in CAPTAINS}  # postings this charter (the 2nd is the swap)


def captain_of(ship):
    perk_id = getattr(ship, "captain", None)
    return perk_id if perk_id in CAPTAINS else None


def captain_cargo_multiplier(ship):
    return FRUGAL_CARGO if captain_of(ship) == "frugal" else 1.0


def captain_adjusted_ticks(ship, ticks):
    if captain_of(ship) == "night_owl" and ticks >= NIGHT_OWL_MIN_TICKS:
        return ticks - 1
    return ticks


def captain_proceeds_multiplier(ship, destination, good):
    perk_id = captain_of(ship)
    if perk_id is None:
        return 1.0
    if perk_id == "frugal":
        return 1.0 + FRUGAL_PROCEEDS
    if perk_id == "night_owl":
        return 1.0 + NIGHT_OWL_PROCEEDS
    if perk_id == "lucky":
        lucky_trip = (ship.captain_deliveries + 1) % LUCKY_EVERY == 0
        return 1.0 + (LUCKY_BONUS if lucky_trip else LUCKY_OFF_BEAT)
    state = colony_states.get(destination)
    if state is None:
        return 1.0
    satisfaction = state.need_satisfaction if ALL_COLONIES[destination]["needs"] == good else state.secondary_need_satisfaction
    if satisfaction < PERFECTIONIST_BELOW:
        return 1.0 + PERFECTIONIST_BONUS
    if satisfaction > PERFECTIONIST_ABOVE:
        return 1.0 + PERFECTIONIST_PENALTY
    return 1.0
