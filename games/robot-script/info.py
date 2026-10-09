"""Robot Script -- the About page: what the game is and what it will never do. It states no real-world facts."""

PLEDGE = (
    "There is no timer, no energy and no waiting: a run takes as long as you like and the room never changes while you think.",
    "A failed run costs nothing. The robot stops where it went wrong, says why, and your list is still there to fix.",
    "Progress is only ever added. Medals go up and never down, and nothing expires or can be missed.",
    "No randomness anywhere: the same list in the same room always does the same thing.",
    "No audio, no ads inside the game, no purchases, and no leaderboards.",
    "Hints are free and never touch a medal. The answer is one tap away whenever you want it.",
)

FRAMING = ("Robot Script is a small invented place: a worn-out maintenance deck, a literal-minded robot and a salvage drone called "
           "Scrap that you rebuild one part at a time. It is a puzzle about writing short lists of instructions, in the spirit "
           "of the old programming-toy puzzles. Nothing in it comes from a real station or a real machine.")

HOW = (
    "Steps are instructions: every instruction, repeat, branch and call counts one, and a saved routine counts its own contents. "
    "Gold is at or under the reference list, silver within about a third more, bronze for any clear.",
    "A room is cleared when your list ends with every goal met: the exit reached, the sockets filled, the switches lit.",
    "The robot does exactly what the list says. If a step cannot be done (a wall, a shut door, nothing to pick up) it stops there and tells you.",
)


def view():
    return {"framing": FRAMING, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW)}
