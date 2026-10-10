"""Evidence Hunt -- the About page: what the game is, what it will never do, and the fiction notice."""

NOTICE = ("This is a fiction game. The spirits, the rules and the houses are all invented, and the game says nothing about the real "
          "world. Nobody is ever harmed in it.")

PLEDGE = (
    "There is no timer, no energy and no waiting: the house never changes while you think.",
    "Nothing jumps out, nothing chases you and nobody is harmed. Every spirit is gentle, and a solved case ends with a quiet note about who they were.",
    "Naming the wrong spirit costs one point on the case's seal and nothing else. Your notebook stays, you can name again, and Restore is always free.",
    "Progress is only ever added. Seals only go up, and nothing expires or can be missed.",
    "No randomness anywhere in a case: the same actions in the same case always do the same thing. A practice code always makes the same house.",
    "Hints are free, asked for by you, and never touch a seal. The answer is one tap away whenever you want it.",
    "No audio, no purchases, no leaderboards.",
)

FRAMING = ("Evidence Hunt is a quiet investigator's notebook. Each case is a house drawn as a dark floor plan. You open the client's book of "
           "visitors, pack a few pieces of equipment, walk the rooms and take readings, and work out which of twelve invented kinds of "
           "spirit is there. It is a puzzle about reading evidence, not a fright.")

HOW = (
    "Read the sheet. Each kind lists its three pieces of evidence and its two habits. Overlaps are on purpose: one reading never decides alone.",
    "Pack a bag before your first reading. It holds only a few pieces, so choose the ones that tell the suspects apart. A different bag later is a second trip and costs 1.",
    "Walk into a room by tapping it. Walking is free. A restless room has a spirit in it, and a still room does not.",
    "A reading is yes, no or doubtful. Doubtful means the house fooled it (a draught, old wiring, a keepsake) and it tells you nothing about the spirit.",
    "The client's account and a keepsake's line are true. A kind that keeps to one room is restless in exactly one; a kind that roams is restless in two or more.",
    "When only one kind fits your notebook, name it. Every case can be solved cleanly: the careful plan never needs a wrong guess.",
)


def view():
    return {"framing": FRAMING, "notice": NOTICE, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW)}
