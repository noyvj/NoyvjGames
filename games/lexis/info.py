"""Lexis -- the "About Lexis" page: real-world facts behind the three mechanics.

Every fact was read live from the named source on the date given (2026-10-07) and is reworded here, never
copied. The sources are named on screen with their date read. Lexis' own three languages are invented; only
the ideas behind them are real, and each fact says where the game differs.

A fact tied to a planet (`gate`) is shown only after contact with that planet, because it would otherwise
say what that planet's signs do. The rest are always readable.
"""

DATE_READ = "2026-10-07"

FRAMING = ("Lexis is invented: its languages, ship and worlds are made up. The ideas behind them are real, "
           "and these are some of the places they come from. Facts about a planet unlock after contact with it, "
           "so nothing here gives an answer away.")

FACTS = (
    {
        "id": "binary", "gate": "pulse", "heading": "Numbers by position",
        "fact": "A binary numeral is written in places, and each place is worth twice the one to its right. "
                "So 101 reads as four, plus no twos, plus one, which makes five.",
        "tie_in": "Planet 1 spells its numbers with three marks in exactly this way.",
        "source": {"title": "Binary number", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Binary_number"},
    },
    {
        "id": "characters", "gate": "compound", "heading": "Signs built from meaningful parts",
        "fact": "Most Chinese characters are assembled from smaller parts. Often one part hints at the meaning "
                "and another at the sound, so a character about washing can carry a part that stands for water.",
        "tie_in": "Planet 2's signs are built from parts too, though there every part carries meaning and none carries sound.",
        "source": {"title": "Chinese character classification", "publisher": "Wikipedia",
                   "url": "https://en.wikipedia.org/wiki/Chinese_character_classification"},
    },
    {
        "id": "plural", "gate": "bridge", "heading": "Saying there is more than one",
        "fact": "Languages mark plurals in many ways. An ending on the noun is the commonest, but others use a "
                "beginning, a changed vowel, a repeated word or a separate little word, and some mark it "
                "hardly at all.",
        "tie_in": "Planet 3 uses a separate small sign after the noun.",
        "source": {"title": "Coding of Nominal Plurality (chapter by Matthew S. Dryer)",
                   "publisher": "World Atlas of Language Structures Online", "url": "https://wals.info/chapter/33"},
    },
    {
        "id": "negation", "gate": "bridge", "heading": "Saying no",
        "fact": "A survey of 1,157 languages found that the two commonest ways to negate a statement are a "
                "separate particle (502 languages) and an affix on the verb (395). A few use both at once.",
        "tie_in": "Planet 3's negation is simpler than that: it removes a thing, not a whole statement.",
        "source": {"title": "Negative Morphemes (chapter by Matthew S. Dryer)",
                   "publisher": "World Atlas of Language Structures Online", "url": "https://wals.info/chapter/112"},
    },
    {
        "id": "linear_b", "gate": "", "heading": "Reading a script nobody could read",
        "fact": "Linear B was deciphered in 1952 without any text that was written twice, once in a known language. "
                "Alice Kober had shown that its words shared roots and endings, and Michael Ventris built on her "
                "tables of signs, finding place names that revealed the language was Greek.",
        "tie_in": "You are working the same way: patterns and context, with no dictionary to hand.",
        "source": {"title": "Linear B", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Linear_B"},
    },
    {
        "id": "arecibo", "gate": "", "heading": "A message meant for strangers",
        "fact": "In 1974 a radio message of 1,679 binary digits was sent from Puerto Rico toward a star cluster "
                "about 25,000 light years away. That total is 73 times 23, so the digits fold into a picture, "
                "and the message begins with the numbers one to ten. It was meant to show what people can do, "
                "not to expect a reply.",
        "tie_in": "Numbers and pictures were chosen because they might survive a trip between minds that share no language.",
        "source": {"title": "Arecibo message", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Arecibo_message"},
    },
)


def view(contact):
    """The page as data: unlocked facts in full, locked ones as a stub that names only what unlocks them."""
    facts = []
    for fact in FACTS:
        gate = fact["gate"]
        if gate and not contact.get(gate):
            facts.append({"id": fact["id"], "locked": True, "unlock": gate})
        else:
            facts.append({"id": fact["id"], "locked": False, "heading": fact["heading"], "fact": fact["fact"],
                          "tie_in": fact["tie_in"], "source": dict(fact["source"], date_read=DATE_READ)})
    return {"framing": FRAMING, "date_read": DATE_READ, "facts": facts}
