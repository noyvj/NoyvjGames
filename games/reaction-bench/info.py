"""Reaction Bench -- the About page: what the game is, what it will never do, and the real history of the equations it borrows.

The station, Fennel and the orders are invented. The chemistry is real: every equation is balanced by a program and checked
twice, and the facts below were read from the named source on the date given and are reworded here, never copied. The page also
reads the Wikipedia summary of "Chemical equation" live when About is opened and names the day it was read; if that fails, the
notes below stand, with their own read date. Nothing here depends on a clock: the live read date is made by the page.
"""

DATE_READ = "2026-10-12"
LIVE_SOURCE = {"title": "Chemical equation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Chemical_equation",
               "api": "https://en.wikipedia.org/api/rest_v1/page/summary/Chemical_equation"}

FRAMING = ("Reaction Bench is invented: a night-shift lab on a research station called Halde, with a robot called Fennel. "
           "The chemistry on the bench is real, and the facts about it below are named with their sources.")

PLEDGE = (
    "Nothing is timed. There is no clock, no energy, no waiting and no streak: an order takes as long as you like.",
    "Nothing can go wrong. A wrong setting only shows what is off in the ledger, and a shelved compound stays on the shelf for good.",
    "No luck and no guessing. Every equation was balanced by a program that finds the one lowest whole-number answer, and checked a second way by trying every setting and by weighing both sides.",
    "Only everyday, textbook-safe chemistry: water, rust, salt, lime, fertiliser and fuels burning. There are no instructions for making anything, only the equations.",
    "No sound, no pictures from anywhere else (every flask and atom is drawn by code), no purchases and no leaderboards.",
)

HOW = (
    "An order is an equation with a dial in front of each formula. The number on a dial says how many of that substance take part.",
    "The ledger counts every element on the left and on the right. Turn the dials until every row reads equal; then Run, and the compound goes on the shelf.",
    "From chapter 2 you first choose what comes out from four lists, and only one of them can be balanced. A wrong choice never costs anything: it just says why.",
    "A bracket, like (OH) in Ca(OH)2, is a group: the number after the bracket multiplies every atom inside it.",
    "Each new element you use lights a tile on the periodic table, and its card tells you what it is for.",
    "Five orders on the shelf open the next chapter. Inside a chapter, any order in any order.",
)

FACTS = (
    {
        "id": "equation", "heading": "What an equation is",
        "fact": "A chemical equation is a short way of writing a reaction: the starting substances on the left, the products on the right, "
                "and an arrow between them. A number in front of a formula says how many of that substance take part, and when no number is "
                "written it means one.",
        "tie_in": "Your dials are those numbers, and a dial left at 1 is the same as writing nothing.",
        "source": {"title": "Chemical equation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Chemical_equation"},
    },
    {
        "id": "balance", "heading": "Why it has to balance",
        "fact": "Ordinary chemical reactions do not turn one element into another, so every element has to appear the same number of times "
                "on both sides of the equation.",
        "tie_in": "That is exactly what the ledger counts. The Run button waits until every row reads equal.",
        "source": {"title": "Chemical equation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Chemical_equation"},
    },
    {
        "id": "beguin", "heading": "The first one",
        "fact": "The first chemical equation is credited to Jean Beguin, who drew one in 1615.",
        "tie_in": "Four centuries on, the same idea sits on a bench with dials.",
        "source": {"title": "Chemical equation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Chemical_equation"},
    },
    {
        "id": "table", "heading": "The table that fills",
        "fact": "Dmitri Mendeleev published the first widely accepted periodic table in 1869 and used its pattern to predict elements that "
                "had not yet been found. Today 118 elements are known, laid out in 18 columns called groups and rows called periods.",
        "tie_in": "Your table has all 118 places. Tiles for elements an order uses light up when you first use them.",
        "source": {"title": "Periodic table", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Periodic_table"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW), "facts_heading": "The real chemistry",
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS], "live": dict(LIVE_SOURCE)}
