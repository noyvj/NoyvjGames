"""Picture Grid -- the About page: what the game is, what it will never do, and the real history of the puzzle it borrows.

The pictures, the station and the gallery are invented. Only the puzzle form is real, and its facts below were read from the
named source on the date given and are reworded here, never copied. The page also tries to read the same source live when About
is opened (app.js asks Wikipedia's summary service) and names the day it was read; if that fails, the notes below stand, with
their own read date. Nothing here depends on a clock: the live read date is made by the page.
"""

DATE_READ = "2026-10-12"
LIVE_SOURCE = {"title": "Nonogram", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Nonogram",
               "api": "https://en.wikipedia.org/api/rest_v1/page/summary/Nonogram"}

FRAMING = ("Picture Grid is invented: a closed gallery on a quiet station, and every picture in it was drawn for this game. "
           "The puzzle form is real and has a history of its own, told below with its source.")

PLEDGE = (
    "Nothing is timed. There is no clock, no energy, no waiting and no streak: a frame takes as long as you like and never changes while you think.",
    "Nothing can go wrong. Any mark can be cleared, undone or redone, and a hung picture stays hung for good.",
    "No luck and no guessing. Every one of the 60 pictures was proved by a program to have exactly one answer, and to be solvable one row or column at a time.",
    "Help only when you ask. Hints open one rung at a time, each on a press, and Check mistakes, Auto-dot and Row focus are off until you switch them on.",
    "No sound, no pictures from anywhere else (every picture is a small grid written out by hand), no purchases and no leaderboards.",
)

HOW = (
    "Each row and column carries numbers. A number is the length of a run of filled cells, and the runs go in that order with at least one empty cell between them: 3 1 means a run of three, a gap, then a single cell.",
    "Fill the cells you are sure belong to the picture, and put a dot on cells you are sure are empty. A line turns grey with a tick once its filled cells make exactly its numbers.",
    "When every row and column is right, the picture is hung on the wall of its gallery. Six hung pictures in a gallery open the next one; inside a gallery, any frame in any order.",
    "Where no line has a certain move, you can always ask for a suggestion: a nudge says which line, a hint says what kind of reasoning works there, and the last rung fills that line for you.",
)

FACTS = (
    {
        "id": "inventors", "heading": "Two people, one idea",
        "fact": "Nonograms were invented in Japan in the late 1980s. Non Ishida, a graphics editor in Tokyo, thought of them in 1987 after a "
                "competition that used the lit windows of skyscrapers as a picture, and Tetsuya Nishio, a professional puzzle author, came up "
                "with similar puzzles on his own. Ishida's first ones appeared in 1988 as Window Art Puzzles.",
        "tie_in": "The numbers on your rows and columns are the same device: lit windows and dark ones, counted in runs.",
        "source": {"title": "Nonogram", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Nonogram"},
    },
    {
        "id": "names", "heading": "Many names",
        "fact": "The puzzle goes by several names: Hanjie, Paint by Numbers, Griddlers, Pic-a-Pix and Picross among them. The English word "
                "nonogram was coined by a British puzzle collector who helped publish the puzzles abroad, and it honours Non Ishida.",
        "tie_in": "Picture Grid calls them frames and hangs each finished one on a wall instead of scoring it.",
        "source": {"title": "Nonogram", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Nonogram"},
    },
    {
        "id": "logic", "heading": "Logic, or a guess",
        "fact": "Many nonograms can be solved by reasoning about one line at a time. Harder ones can leave a solver trying a value for a cell "
                "to see whether it leads to a contradiction, and a wrong guess can spread errors across the grid. Deciding in general whether "
                "a nonogram has a solution is a hard problem for computers too (NP-complete).",
        "tie_in": "That is why every picture here was checked by a program and redrawn if it could not be finished by line logic alone: you never need to guess.",
        "source": {"title": "Nonogram", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Nonogram"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW), "facts_heading": "The real puzzle",
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS], "live": dict(LIVE_SOURCE)}
