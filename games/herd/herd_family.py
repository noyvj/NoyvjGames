"""The Family Farm branching story (GF-10).
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate


# ---- GF-10 The Family Farm (branching story) ---------------------------------------------
# A short original story (FY-30): Grandpa Tobias and three ways the farm could go. It only reads the
# farm's round and certification to decide when a page is ready; nothing in it changes the simulation,
# and the Story pill hides the whole panel. No real-world facts are stated here (those live in the Real
# Story panel). Endings found are a collection that survives a handover.
FAMILY_BEAT1_ROUND = 4
FAMILY_BEAT2_ROUND = 10
FAMILY_ENDING_ROUND = 16
FAMILY_BRANCHES = {
    "sell": {
        "choice": "Sell the north field",
        "after": "The north field goes quietly. The money is real, the gate to it is someone else's now, and Grandpa stops talking about it on Tuesdays.",
        "beat2": "A dry spell bites, and the north-field money is thinner than it looked. A neighbour asks if the buyer might want the south field too.",
        "options": {"hold": "Hold the line and trim costs", "more": "Sell the south field too"},
        "ending_title": "The Quiet Sale",
        "endings": {
            "hold": "You hold what is left and tighten the ledger. The farm is smaller and sharper, and Grandpa admits over tea that smaller is not the same as lost.",
            "more": "The south field follows. What is left is a house, a barn and a very good view of other people's cows. Grandpa calls it retirement; you call it a lesson.",
        },
    },
    "organic": {
        "choice": "Go organic, slowly",
        "after": "Grandpa mutters that the soil will be the judge. The first season is thin and the paperwork is fussy, but the fence line starts to hum with bees.",
        "beat2": "A wet spring and a hungry pest turn the plan into a test. The old way would be one quick fix away.",
        "options": {"ride": "Ride it out with the soil", "fix": "Use one quick fix, just this once"},
        "ending_title": "The Slow Green",
        "endings": {
            "ride": "The soil holds. The second year is better than the first, and the label arrives in the post, slightly crumpled and entirely welcome.",
            "fix": "One fix, written honestly in the ledger. The label waits a season longer, and Grandpa decides that honesty is also a crop.",
        },
    },
    "subsidy": {
        "choice": "Take the barn grant",
        "after": "A new roof and a new rulebook. Grandpa signs with a flourish and reads the small print the next morning, aloud, with feeling.",
        "beat2": "The grant's rules change halfway through the year. Grandpa reads them out, then reads them out louder.",
        "options": {"comply": "Follow every new rule", "build": "Build around the rules, not for them"},
        "ending_title": "The Barn Grant",
        "endings": {
            "comply": "You follow every rule to the letter, and the paperwork grows into a second herd. The barn is excellent. The weekends are not.",
            "build": "You use the grant as scaffolding and add your own improvements. By the end the barn is yours, rules and all.",
        },
    },
}
FAMILY_BEAT1_TEXT = (
    "Grandpa Tobias waves a letter over his tea. A buyer wants the north field, a neighbour says he should go "
    "organic, and the county has a barn grant with strings. He asks what you would do. You are fairly sure he has already decided."
)
FAMILY_BRANCH_ORDER = ("sell", "organic", "subsidy")


def family_stage():
    """0 = waiting for the first choice, 1 = first made, 2 = both made."""
    return min(2, len(runstate.farm.story_choices))


def family_beat_ready():
    """Is the next page of the story unlocked for this farm right now?"""
    stage = family_stage()
    if stage == 0:
        return runstate.farm.round_number >= FAMILY_BEAT1_ROUND
    if stage == 1:
        return runstate.farm.round_number >= FAMILY_BEAT2_ROUND
    return False


def family_ending_ready():
    return family_stage() == 2 and (runstate.farm.round_number >= FAMILY_ENDING_ROUND or runstate.farm.certified)


def family_choices_now():
    """(button id, label) pairs for the choices on offer right now, or an empty list."""
    if not family_beat_ready():
        return []
    stage = family_stage()
    if stage == 0:
        return [(branch, FAMILY_BRANCHES[branch]["choice"]) for branch in FAMILY_BRANCH_ORDER]
    branch = runstate.farm.story_choices[0]
    return list(FAMILY_BRANCHES[branch]["options"].items())


def family_choose(choice):
    """Makes the choice if it is on offer. Returns True when it was taken."""
    if choice not in dict(family_choices_now()):
        return False
    runstate.farm.story_choices.append(choice)
    return True


def family_ending_text():
    branch, option = runstate.farm.story_choices[0], runstate.farm.story_choices[1]
    spec = FAMILY_BRANCHES[branch]
    return spec["ending_title"], spec["endings"][option]


def _family_record_ending():
    branch = runstate.farm.story_choices[0]
    if branch not in runstate.family_endings:
        runstate.family_endings.append(branch)
        return True
    return False


def family_endings_message():
    names = [FAMILY_BRANCHES[b]["ending_title"] if b in runstate.family_endings else "???" for b in FAMILY_BRANCH_ORDER]
    return f"Endings found: {len(runstate.family_endings)} of {len(FAMILY_BRANCH_ORDER)} ({', '.join(names)})."


def family_text_and_status():
    """(story text, status line) for the current page of the story."""
    stage = family_stage()
    if stage == 0:
        if not family_beat_ready():
            return "", f"The first page of The Family Farm turns at round {FAMILY_BEAT1_ROUND}."
        return FAMILY_BEAT1_TEXT, "Pick what the farm does. It changes the story, not your numbers."
    branch = runstate.farm.story_choices[0]
    spec = FAMILY_BRANCHES[branch]
    if stage == 1:
        if not family_beat_ready():
            return spec["after"], f"The next page turns at round {FAMILY_BEAT2_ROUND}."
        return f"{spec['after']} {spec['beat2']}", "One more choice."
    if family_ending_ready():
        title, text = family_ending_text()
        return f"{title}. {text}", "The end of this telling. Tell it again to see another ending."
    return (
        f"{spec['after']} {spec['options'][runstate.farm.story_choices[1]]}.",
        f"The ending arrives at round {FAMILY_ENDING_ROUND}, or sooner if the farm is certified.",
    )


def render_family_story():
    ending_now = family_ending_ready()
    if ending_now:
        _family_record_ending()
    text, status = family_text_and_status()
    document.getElementById("family-story-text").innerText = text
    document.getElementById("family-story-status").innerText = status
    document.getElementById("family-story-endings").innerText = family_endings_message()
    offered = family_choices_now()
    for slot, button_id in enumerate(("family-story-choice-a", "family-story-choice-b", "family-story-choice-c")):
        button = document.getElementById(button_id)
        if slot < len(offered):
            button.innerText = offered[slot][1]
            button.hidden = False
        else:
            button.hidden = True
    document.getElementById("family-story-retell-button").hidden = not ending_now
    document.getElementById("family-story-summary").innerText = family_summary_text()


def family_summary_text():
    """The panel's heading: it says when a page is waiting, so nothing pops up over the game."""
    if family_choices_now():
        return "Farm story: The Family Farm (a choice is waiting)"
    if family_ending_ready():
        return "Farm story: The Family Farm (the ending is ready)"
    return "Farm story: The Family Farm"
