"""Hull Repair -- the About page: what the game is and what it will never do. It states no real-world facts."""

PLEDGE = (
    "There is no timer, no energy and no waiting: a board takes as long as you like and never changes while you think.",
    "A wrong line costs nothing. Lines can be trimmed, cut, undone or cleared, hints are free, and nothing can be lost by trying.",
    "Progress is only ever added. A patched room stays patched, a restored room stays restored, and nothing expires or can be missed.",
    "No randomness anywhere: every board is hand-checked to have exactly one restored layout, and the same drawing always gives the same result.",
    "No audio, no ads inside the game, no purchases, and no leaderboards.",
    "The answer is one tap away whenever you want it. Using it is never hidden or shamed, and the room still counts.",
)

FRAMING = ("Hull Repair is a small invented place: a dark station called Tern, forty rooms that need their power and pipes laid "
           "again, and a repair log written by the people who left. It is a routing puzzle in the spirit of the old "
           "connect-the-matching-ports games. Nothing in it comes from a real station or a real person.")

HOW = (
    "Join each source port (solid) to the sink port of the same shape and letter (ringed) with a line. Lines move one cell at a time and never cross or share a cell.",
    "Patched means every line is joined. Restored means every open cell is covered as well, and every board has exactly one way to do that.",
    "Holes are hull that is gone. A bridge lets two lines cross, one straight over the other. A valve lets a line through straight, the way its arrow points, from source to sink. A mixer takes two named lines, one from each side.",
    "A deck opens once five rooms of the one before are patched. Inside a deck, any room in any order.",
)


def view():
    return {"framing": FRAMING, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW)}
