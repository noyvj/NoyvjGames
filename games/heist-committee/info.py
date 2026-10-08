"""Heist Committee -- the "How it works" panel.

The game is fiction: every target, crew member and complication is invented, so there are no real-world facts to
read from a live source and none are shown (the site's convention only applies when a game states real facts).
This panel instead explains how the plan resolves, so the numbers on screen never feel arbitrary.
"""

FRAMING = ("Heist Committee is fiction. Every place, person and problem in it is invented, so there are no real-world "
           "facts here and no sources to name. This page explains how a plan turns into a story, so nothing on the "
           "screen is a mystery.")

SECTIONS = (
    {"id": "plan", "heading": "The plan is a grid",
     "body": "Each row is one crew member and each column is one beat of the job. Put an action in a cell. Some "
             "take two beats. Odds are shown as words: Solid (you will almost certainly manage it), Risky "
             "(a coin flip between clean, messy and failed), Long shot, and No chance."},
    {"id": "odds", "heading": "Where the odds come from",
     "body": "Skill minus the action's difficulty, plus one, plus or minus anything else that applies: a trait, "
             "a feud or a friendship, a mentor working next door, a missing Lookout, an unlucky beat. Tap a "
             "filled cell to see every number added up. Nothing is hidden: the only secrets are a crew member's "
             "quirk and what the target's pool of trouble holds."},
    {"id": "trouble", "heading": "Trouble and chains",
     "body": "Each beat the job can throw a complication at you. Many only happen because of something earlier: "
             "a loud action wakes a guard, a guard on his rounds spoils the lockpick, a failed lockpick is "
             "loud. The payout shows the chain, with the first link marked, so the lesson is always where it started. "
             "A beat can only chain six links, and each complication happens once a heist."},
    {"id": "counters", "heading": "Standing by",
     "body": "Trouble can be absorbed instead of suffered. In order: a crew member on Standby for that kind of "
             "trouble, an Improvise gamble, a free crew member with the right skill, a piece of gear, then a trait "
             "like Calm. Standby costs a turn, so it is a trade-off, not a free shield."},
    {"id": "same", "heading": "The same night, every time",
     "body": "A heist is decided entirely by the plan and the job's seed. Retry the same job and the same trouble "
             "arrives on the same beats, so an improved plan really is an improved plan. A retry only pays what it "
             "adds beyond your best attempt, and only improvements earn reputation, so there is nothing to grind."},
    {"id": "nofail", "heading": "There is no game over",
     "body": "A bad night still pays the target's consolation money, a stuck purse is topped up by the committee, "
             "and nobody is ever lost. Failure is a story, and a reason to try again with a better plan."},
)


def view(meta):
    return {"framing": FRAMING, "sections": [dict(s) for s in SECTIONS], "jobs_done": meta.get("jobs_done", 0)}
