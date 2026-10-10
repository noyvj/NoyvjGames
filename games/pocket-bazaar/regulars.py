"""Pocket Bazaar -- the regulars: twelve named customers who come back, each with a favourite family of goods and three
short lines that unlock as you serve them (bond levels 1, 2 and 3).

A regular is an ordinary Regular customer with a name worth remembering: three of them step up on each market day, in a
fixed rotation, so every regular is back every fourth day and nothing depends on luck. Serving one raises their bond;
a regular who leaves unserved costs you nothing but that visit. The lines are story text (the shared story toggle hides
them); the bond level and the count of visits are plain numbers that always show.
"""

BOND_AT = (1, 2, 3)              # visits served for bond levels 1, 2, 3 (was 1, 3, 5 until M-4b-11)
PER_DAY = 3

# (id, name, family, role, (line at level 1, line at level 2, line at level 3))
REGULARS = (
    ("mira", "Mira", "produce", "a herbalist",
     ("Mira smells every berry before she nods. 'Good,' she says, which from her is a speech.",
      "Mira admits she grows half of what she asks for, and only buys yours to compare.",
      "Mira leaves a pressed leaf in the till: 'For the stall. Yours is better than mine.'")),
    ("brandt", "Brandt", "textiles", "a retired ferryman",
     ("Brandt wants a scarf 'that has opinions about wind'. You do not ask.",
      "Brandt says the river taught him patience and the ferry timetable took it back.",
      "Brandt hangs one of your ribbons on a post by the old dock. It is still there.")),
    ("sunniva", "Sunniva", "ceramics", "a potter on a day off",
     ("Sunniva turns every cup upside down to read the maker's mark. Yours has none; she approves.",
      "Sunniva shows you a thumbprint in one of her own pots and says that is the signature.",
      "Sunniva brings you a chipped bowl as a gift: 'It taught me something. Now it can teach you.'")),
    ("kasimir", "Kasimir", "spices", "a ship's cook",
     ("Kasimir tastes the air at your stall before he orders. 'Cinnamon, bay, someone's lunch.'",
      "Kasimir has fed forty sailors on two coins of pepper and calls it his finest hour.",
      "Kasimir writes you a recipe on the back of a receipt. It begins: 'Start with courage.'")),
    ("dalia", "Dalia", "sweets", "a pastry student",
     ("Dalia photographs nothing and tastes everything. She is taking notes in a very small book.",
      "Dalia failed a layered cake three times and tells you how, in loving detail.",
      "Dalia leaves a tiny cake on your counter, slightly crooked: 'Fourth try. I think it works.'")),
    ("ptolemy", "Ptolemy", "produce", "a night-shift astronomer",
     ("Ptolemy shops at odd hours and apologises for the sky. It is fine; the stall is open.",
      "Ptolemy says plums taste better when you have just counted a thousand stars.",
      "Ptolemy gives you a hand-drawn chart where the market is a small bright dot labelled 'good'.")),
    ("wilhelmina", "Wilhelmina", "textiles", "a tailor who dislikes pins",
     ("Wilhelmina tests a thread by pulling it. It holds. She looks almost betrayed.",
      "Wilhelmina has not used a pin in twenty years and will explain exactly how, if you let her.",
      "Wilhelmina sews a small stall-coloured patch onto your apron without asking. It fits perfectly.")),
    ("rune", "Rune", "ceramics", "a stage-set painter",
     ("Rune squints at your urns the way other people squint at the sun.",
      "Rune paints fake marble for plays and wants real clay for once, 'something that can break'.",
      "Rune paints a tiny picture of your stall inside a cup. You find it later, at the bottom.")),
    ("esme", "Esme", "spices", "a perfume blender",
     ("Esme sniffs a chest of spices and sneezes. 'Honest,' she says, wiping her eyes.",
      "Esme blends scents for people who do not know what they want yet, and says you are one of them.",
      "Esme mixes a small packet just for you, labelled 'for the stall, not for sale'. It smells like Tuesday.")),
    ("bartholomew", "Bartholomew", "sweets", "a very serious toffee judge",
     ("Bartholomew rates each toffee out of ten and will not tell you the number. Only a nod or a sigh.",
      "Bartholomew confides that the number is always seven, because ten would end the hobby.",
      "Bartholomew awards you a ten, in secret, on a card that says 'never mention this'.")),
    ("yara", "Yara", "produce", "a market gardener with a cart",
     ("Yara sells her own produce two streets over and buys yours out of curiosity.",
      "Yara swaps a basket of her pears for a basket of yours, and they are both perfect.",
      "Yara plants one of your orchard-basket seeds by your stall. A small tree is, impossibly, coming up.")),
    ("cato", "Cato", "ceramics", "a night watchman with a flask",
     ("Cato wants a cup 'that will not tip over when the cat jumps'. There is no cat. Probably.",
      "Cato has taken the same cup to work for eleven years and wants a spare in case it retires.",
      "Cato keeps your spare cup on the watch-house shelf, and the cat, it turns out, is real.")),
)

BY_ID = {r[0]: r for r in REGULARS}
IDS = tuple(r[0] for r in REGULARS)


def level(visits):
    """Bond level 0-3 for a number of visits served."""
    return sum(1 for need in BOND_AT if visits >= need)


def rotation(day_number):
    """The regulars who step up on this day: three of the twelve, in a fixed rotation (day 1 has none: it is the first
    day and a gentle one)."""
    if day_number < 2:
        return []
    start = ((day_number - 2) * PER_DAY) % len(REGULARS)
    return [REGULARS[(start + k) % len(REGULARS)][0] for k in range(PER_DAY)]


def line_for(regular_id, new_level):
    return BY_ID[regular_id][4][new_level - 1]


def view(visits):
    """The Regulars page: name, role, favourite, bond level, visits and the lines unlocked so far (the rest hidden)."""
    out = []
    for rid, name, family, role, lines in REGULARS:
        n = visits.get(rid, 0)
        lv = level(n)
        out.append({"id": rid, "name": name, "family": family, "role": role, "visits": n, "level": lv,
                    "next_at": next((need for need in BOND_AT if n < need), None), "lines": list(lines[:lv])})
    return out


def max_level(visits):
    return max([level(visits.get(r, 0)) for r in IDS] or [0])
