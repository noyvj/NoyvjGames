"""Pocket Bazaar -- the About page: what the game is and what it will never do."""

from pledge import PLEDGE

FRAMING = ("Pocket Bazaar is a small invented market: its customers, goods and festivals are made up, and nothing in "
           "it comes from a real shop or event. It is built for short sittings (a market day takes a few minutes) and "
           "for long ones, and it asks nothing of you in between.")

HOW = (
    "Customers wait in beats, not seconds. A beat is a crate, a merge, a sweep or a hand-over; thinking is free.",
    "Combos, chains and wildcards reward good play inside a day. Nothing carries over between days except what you "
    "own, your renown and your personal bests.",
    "Renown only goes up and opens new crates and customers. Coins buy permanent upgrades and decorations.",
)


def view():
    return {"framing": FRAMING, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it stays calm", "how": list(HOW)}
