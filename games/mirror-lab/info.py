"""Mirror Lab -- the "About" page: the real ideas behind the bench, each with its source named on screen and the date it was read, and what
this game will never do.

Every fact below was read live from the named page on the date given and is reworded here, never copied. The game is a SIMPLIFICATION, not
an optics simulator: a beam is a line one cell wide on a grid that only turns by quarter turns, a prism makes exactly two beams (a short S
beam and a long L beam) instead of a spread of colours, and a filter keeps or stops a whole kind. A fact with no source would be left out."""

DATE_READ = "2026-10-12"

FRAMING = ("Mirror Lab is a game, not an optics simulator. A beam is a line on a grid that turns by quarter turns, a prism makes just two "
           "beams (a short S beam and a long L beam) instead of a spread of colours, and a splitter, a filter and an absorber are idealised "
           "pieces. Arden Relay is invented. The ideas behind the bench are real, and these are some of the places they come from.")

FACTS = (
    {
        "id": "reflection", "heading": "Why a mirror turns the beam",
        "fact": "The law of reflection says a reflected ray leaves a surface at the same angle to the surface's normal (the line straight out "
                "of it) as the incoming ray arrived at, on the opposite side of that line. A mirror-like surface that does this is called "
                "specular, and it differs from a rough surface that scatters light in every direction.",
        "tie_in": "On the bench the angle is always a quarter turn: a slash or a backslash mirror sends a beam off at a right angle.",
        "source": {"title": "Specular reflection", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Specular_reflection"},
    },
    {
        "id": "dispersion", "heading": "Why a prism splits white light",
        "fact": "A glass prism separates white light into colours because the glass bends each wavelength by a slightly different amount. "
                "In ordinary clear materials, shorter wavelengths such as blue bend more than longer ones such as red.",
        "tie_in": "The prism here is simplified to two beams, S for short and L for long, one leaving on each side. Real light does not split into just two.",
        "source": {"title": "Dispersion (optics)", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Dispersion_(optics)"},
    },
    {
        "id": "filter", "heading": "What a filter does",
        "fact": "An optical filter, often a sheet of glass or plastic in the light path, lets some wavelengths through and blocks others. Some "
                "absorb the unwanted light with dye and some reflect it with a thin coating. A band-pass filter passes only a chosen range.",
        "tie_in": "An S filter and an L filter work the same way on the bench: they keep one kind of beam and stop the other.",
        "source": {"title": "Optical filter", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Optical_filter"},
    },
    {
        "id": "moon", "heading": "Mirrors left on the Moon",
        "fact": "Six reflector arrays sit on the Moon: three left by the Apollo 11, 14 and 15 missions (the first in July 1969), two carried by "
                "the Soviet Lunokhod rovers and one on India's Chandrayaan-3 lander in 2023. Scientists send laser pulses from Earth, time "
                "the round trip of about two and a half seconds and use the speed of light to measure the distance to the Moon, which averages "
                "about 385,000 kilometres, down to millimetres.",
        "tie_in": "A beam, a few mirrors and a sensor that waits to be lit: the bench is the smallest version of the same set-up.",
        "source": {"title": "Lunar Laser Ranging experiment", "publisher": "Wikipedia",
                   "url": "https://en.wikipedia.org/wiki/Lunar_Laser_Ranging_experiment"},
    },
)

PLEDGE = (
    "There is no timer, no energy and no waiting: a bench takes as long as you like and never changes while you think.",
    "Nothing is lost. A piece can always be picked up, a cleared bench stays cleared, and a bench can be tried again with fewer pieces.",
    "No randomness anywhere: every bench has been checked by a solver to have at least one solution, and the same pieces always give the same beams.",
    "Hints are free and only come when you ask. The answer is one press away whenever you want it, and the bench still counts.",
    "No sound and no ads inside the game, no purchases, and no leaderboards. Every state is also written in words, never colour alone.",
)

HOW = (
    "Choose a piece from the tray, then tap a dashed slot. Tap a placed mirror or prism to flip it. A splitter lets the beam go on and sends a copy to the left of its travel.",
    "A white beam is a thin solid line, an S beam is short dashes with an S and an L beam is long dashes with an L. A sensor never stops a beam.",
    "A crossed sensor is a decoy and must stay dark. An absorber stops any beam. An S filter turns a white beam short and stops a long one; an L filter does the opposite.",
    "Clear 5 benches of a chapter to open the next one. Inside a chapter, play any bench in any order.",
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ, "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS],
            "pledge_heading": "What this game will never do", "pledge": list(PLEDGE), "how_heading": "How it works", "how": list(HOW)}
