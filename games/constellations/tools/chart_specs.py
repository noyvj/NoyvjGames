"""The hand-written side of the charts: which constellations go in which season, in what order, and the short note on each card.

Everything numerical (positions, magnitudes, candidate lines, clues) is DERIVED by `build_charts.py` from the dated snapshot in
`data/snapshot.json`; only words live here. The notes are written for this game (they are not copied from any page); the facts in them
are the ordinary, well-attested ones, and the sources are named on each card and on the About page.

`cap` trims a long figure down by dropping its faintest outlying stars first (the figure stays connected), `drop` removes named stars
(joining their two neighbours when the star sat in the middle of a line).
"""

READ_DATE = "2026-10-12"

SEASONS = [
    {"id": "winter", "name": "Winter Sky", "blurb": "Cold clear evenings, December to February: the brightest stars of the year.", "charts": [
        {"code": "Aur", "id": "auriga", "name": "Auriga", "meaning": "The Charioteer", "genitive": "Aurigae",
         "note": "A pentagon of bright stars led by Capella, one of the brightest stars of the northern sky. Ptolemy listed it nearly nineteen hundred years ago; its fifth corner, Elnath, is officially counted as part of Taurus."},
        {"code": "Col", "id": "columba", "name": "Columba", "meaning": "The Dove", "genitive": "Columbae",
         "note": "A small southern dove added to the sky by the Dutch astronomer Petrus Plancius in 1592. It sits just below Lepus, and from northern countries it hugs the southern horizon."},
        {"code": "Mon", "id": "monoceros", "name": "Monoceros", "meaning": "The Unicorn", "genitive": "Monocerotis", "drop": [30665],
         "note": "A faint unicorn lying along the Milky Way between Orion's two dogs. It has no bright stars, but its fields are rich with star clusters. It joined the star maps in the early 1600s."},
        {"code": "Tau", "id": "taurus", "name": "Taurus", "meaning": "The Bull", "genitive": "Tauri",
         "note": "One of the oldest figures in the sky: red Aldebaran is the bull's eye, with the V-shaped Hyades around it and the tiny Pleiades cluster on its shoulder. One of the twelve zodiac constellations."},
        {"code": "Gem", "id": "gemini", "name": "Gemini", "meaning": "The Twins", "genitive": "Geminorum", "cap": 12,
         "note": "Two bright stars, Castor and Pollux, mark the heads of the twins, and Pollux is the brighter of the two. The Geminid meteors seem to stream from this part of the sky every December."},
        {"code": "CMa", "id": "canis-major", "name": "Canis Major", "meaning": "The Greater Dog", "genitive": "Canis Majoris", "cap": 12, "drop": [33165],
         "note": "Home of Sirius, the brightest star in the night sky, which follows Orion across the winter sky like a dog at his heel. Sirius is only about 8.6 light years from us."},
        {"code": "Lep", "id": "lepus", "name": "Lepus", "meaning": "The Hare", "genitive": "Leporis",
         "note": "A hare crouched at Orion's feet, in Ptolemy's list of forty-eight. Its brightest star, Arneb, is a very distant supergiant."},
        {"code": "Ori", "id": "orion", "name": "Orion", "meaning": "The Hunter", "genitive": "Orionis", "drop": [22509, 22845, 22730, 27913, 28716, 29434, 29038],
         "note": "The easiest figure to find in the winter sky: three belt stars in a row, red Betelgeuse at one shoulder and blue-white Rigel at one foot. The glow below the belt is the Orion Nebula, a nursery of new stars."},
    ]},
    {"id": "spring", "name": "Spring Sky", "blurb": "Evenings from March to May, when the Milky Way lies low and faint galaxies rise high.", "charts": [
        {"code": "Crv", "id": "corvus", "name": "Corvus", "meaning": "The Crow", "genitive": "Corvi",
         "note": "A small, neat four-sided figure south of Virgo. In Greek myth Apollo's crow is stuck here beside the Cup and the Water Snake as a punishment for being late."},
        {"code": "Cnc", "id": "cancer", "name": "Cancer", "meaning": "The Crab", "genitive": "Cancri",
         "note": "The faintest of the twelve zodiac constellations. Its best sight is the Beehive Cluster, a hazy patch that shows to the eye from a dark place and breaks into stars in binoculars."},
        {"code": "UMi", "id": "ursa-minor", "name": "Ursa Minor", "meaning": "The Lesser Bear", "genitive": "Ursae Minoris", "best": "visible all year from the northern middle latitudes, highest in June",
         "note": "The Little Bear. Polaris, the North Star, sits at the end of its tail, close to the point the sky seems to turn around. Kochab and Pherkad, on the bowl's outer edge, were called the Guardians of the Pole."},
        {"code": "Crt", "id": "crater", "name": "Crater", "meaning": "The Cup", "genitive": "Crateris",
         "note": "A faint cup of stars set on the back of the Water Snake. Greek myth makes it Apollo's cup, the one the crow Corvus should have filled."},
        {"code": "Leo", "id": "leo", "name": "Leo", "meaning": "The Lion", "genitive": "Leonis",
         "note": "A lion whose head is a backwards question mark called the Sickle, ending at bright Regulus. Every November the Leonid meteors seem to stream from this part of the sky."},
        {"code": "Boo", "id": "bootes", "name": "Boötes", "meaning": "The Herdsman", "genitive": "Boötis",
         "note": "Led by orange Arcturus, the brightest star of the northern half of the sky. Follow the curve of the Big Dipper's handle to find it: arc to Arcturus."},
        {"code": "Vir", "id": "virgo", "name": "Virgo", "meaning": "The Maiden", "genitive": "Virginis",
         "note": "The second-largest constellation in the sky, with blue-white Spica as its brightest star. One of the twelve zodiac constellations."},
        {"code": "UMa", "id": "ursa-major", "name": "Ursa Major", "meaning": "The Great Bear", "genitive": "Ursae Majoris", "cap": 14,
         "note": "The Great Bear holds the Big Dipper, known as the Plough in Britain. The two stars at the end of the Dipper's bowl, Dubhe and Merak, point the way to Polaris."},
    ]},
    {"id": "summer", "name": "Summer Sky", "blurb": "Warm evenings from June to September, with the Milky Way running overhead.", "charts": [
        {"code": "Lyr", "id": "lyra", "name": "Lyra", "meaning": "The Lyre", "genitive": "Lyrae",
         "note": "A tiny lyre led by brilliant Vega, one of the brightest stars in the night sky and a corner of the Summer Triangle with Deneb and Altair. A small parallelogram of stars hangs beneath it."},
        {"code": "Del", "id": "delphinus", "name": "Delphinus", "meaning": "The Dolphin", "genitive": "Delphini",
         "note": "A small dolphin with a diamond-shaped body. Two of its stars are called Sualocin and Rotanev: read them backwards for Nicolaus Venator, the Latin form of the name of the Palermo Observatory assistant said to have named them after himself."},
        {"code": "Sge", "id": "sagitta", "name": "Sagitta", "meaning": "The Arrow", "genitive": "Sagittae",
         "note": "One of the smallest of all the constellations, an arrow shot into the summer Milky Way between Aquila and Cygnus. It is dim but easy to find because it is so compact."},
        {"code": "CrB", "id": "corona-borealis", "name": "Corona Borealis", "meaning": "The Northern Crown", "genitive": "Coronae Borealis",
         "note": "A neat half circle of stars. In Greek myth it is the crown given to Ariadne. Its brightest star, Alphecca, is also called Gemma, the jewel."},
        {"code": "Oph", "id": "ophiuchus", "name": "Ophiuchus", "meaning": "The Serpent Bearer", "genitive": "Ophiuchi",
         "note": "A large figure standing on Scorpius and holding the Serpent. The Sun passes through it for about two weeks in late November and December, though it is not one of the twelve astrological signs."},
        {"code": "Aql", "id": "aquila", "name": "Aquila", "meaning": "The Eagle", "genitive": "Aquilae",
         "note": "An eagle with bright Altair at its heart, a corner of the Summer Triangle. Altair spins so fast that it is noticeably flattened."},
        {"code": "Cyg", "id": "cygnus", "name": "Cygnus", "meaning": "The Swan", "genitive": "Cygni",
         "note": "The Swan flies down the Milky Way and is also called the Northern Cross. Deneb marks its tail; Albireo, at its beak, is a double star that looks gold and blue in a small telescope."},
        {"code": "Sco", "id": "scorpius", "name": "Scorpius", "meaning": "The Scorpion", "genitive": "Scorpii",
         "note": "A scorpion curling low across the summer sky, with red Antares at its heart and a hooked tail ending in a stinger. The name Antares means rival of Mars."},
    ]},
]
