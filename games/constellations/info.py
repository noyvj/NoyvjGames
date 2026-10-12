"""Constellations -- the About page: what the game is, what it will never do, and the real sky behind it.

The observatory on Hollin Ridge and its keeper are invented. The stars are real: their positions and brightness come from the HYG star
database, the line figures from the Stellarium "modern" sky culture (the IAU constellation figures), and the facts below were read from the
named source on the date given and are reworded here, never copied. About also tries to read two things live when it is opened (app.js asks
Wikipedia's summary service, and reads today's Stellarium figures file to check the figures in your atlas) and names the day each was read; if that fails, the
notes below stand with their own read date. Nothing here
depends on a clock: the live read date is made by the page.
"""

DATE_READ = "2026-10-12"
LIVE_SOURCE = {"title": "IAU designated constellations", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/IAU_designated_constellations",
               "api": "https://en.wikipedia.org/api/rest_v1/page/summary/IAU_designated_constellations"}

LIVE_LINES = {"title": "Stellarium modern sky culture (IAU constellation figures)", "publisher": "Stellarium", "url": "https://stellarium.org",
                "api": "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern/index.json"}

FRAMING = ("Constellations is set in an invented dim observatory on Hollin Ridge. The sky is real: every star sits where it really is "
           "(drawn flat), and every figure you finish is a traditional constellation. The short notes and the facts below name their sources.")

PLEDGE = (
    "Nothing is timed. There is no clock, no energy, no waiting and no streak: a chart takes as long as you like and never changes while you think.",
    "Nothing can go wrong. Any line can be erased, undone or redone, and a constellation in your atlas stays there for good.",
    "No luck and no guessing. Every chart was proved by a program to have exactly one answer, and to be finished by following the numbers and the lines (one what-if at most).",
    "No sound, no pictures from anywhere else (every star and line is drawn by the page), no purchases and no leaderboards.",
)

HOW = (
    "Some stars carry a number: that many lines must touch the star. A star with no number can have any number of lines, or none.",
    "Draw a line by dragging from one star to another, or press one star and then the other. Press the same two stars again to take the line away. Only nearby pairs can be joined, and a held star shows which ones.",
    "Lines may not cross. All the lines together must make one connected figure. A solid thick line is already drawn for you; a pair with a cross through it can never be joined. (One chart, the Southern Cross, is the exception: its two traditional lines cross, so it says so, and where they cross they count as joined.)",
    "Stuck? The suggestion button never opens by itself. It asks \"Would you like a suggestion?\" and then goes one rung at a time: a nudge (which star), a hint (which line, and why it is certain) and the whole answer, which you can draw with one press. Easy opens the nudge and the hint together; Hard stops before the answer. Nothing is guessed: every suggestion is a certain deduction.",
    "When every number holds and the figure is one piece, Done adds the constellation to your atlas. Five finished charts in a season open the next season; inside a season, any order.",
)

FACTS = (
    {
        "id": "eighty-eight", "heading": "Eighty-eight",
        "fact": "The International Astronomical Union formally accepted the modern list of 88 constellations in 1922, and in 1928 it adopted "
                "borders for them, drawn along lines of right ascension and declination by Eugene Delporte, that together cover the whole sky.",
        "tie_in": "Each chart here is one of those 88 areas; the stick figure you draw is the traditional picture inside it, not the border.",
        "source": {"title": "Constellation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Constellation"},
    },
    {
        "id": "ptolemy", "heading": "Very old names",
        "fact": "Many of the figures are much older than the modern list. Ptolemy, writing in Alexandria, listed 48 traditional constellations in his "
                "Almagest: the zodiac plus 36 others (38 others by today's count, since the big ship Argo Navis was later split into three).",
        "tie_in": "Many of the figures in your atlas are on that old list, and a few small ones, a dove and a unicorn among them, were added in the 1500s and 1600s.",
        "source": {"title": "Constellation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Constellation"},
    },
    {
        "id": "moving", "heading": "The shapes are temporary",
        "fact": "Stars in a constellation are at very different distances, and each one moves through space on its own path, so the outlines are "
                "slowly changing. After tens to hundreds of thousands of years the familiar shapes will no longer be recognisable.",
        "tie_in": "The charts show the sky as the star database has it today, flattened onto the page, with a little spreading where stars are crowded.",
        "source": {"title": "Constellation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Constellation"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW), "facts_heading": "The real sky",
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS], "live": dict(LIVE_SOURCE), "live_lines": dict(LIVE_LINES)}
