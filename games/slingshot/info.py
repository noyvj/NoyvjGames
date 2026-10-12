"""Slingshot -- the About page: what the game is, what it will never do, what it simplifies, and the real numbers behind it.

Kestrel Desk, the probe Wren and its flight planners are invented. The numbers are real: the Sun's and planets' pull, sizes, orbit radii and
periods come from NASA/JPL (read on the date below and named on the Sources page); the facts below are reworded from Wikipedia on the date given,
never copied. The model is simplified on purpose and says so here, plainly.
"""

import bodies_data as D

DATE_READ = D.READ

FRAMING = ("Slingshot is set at Kestrel Desk, a small invented mission desk. You plan burns for a probe called Wren on a quiet chart, press Fly, "
           "and Wren follows the plan exactly. The Sun, planets and moons are real: their sizes, pull and orbits come from NASA and JPL, with the date "
           "each was read on the Sources page.")

PLEDGE = (
    "Nothing is timed. There is no clock, no energy, no waiting and no streak. A plan never changes while you think.",
    "Nothing can fail. A miss is a report, not a loss: Wren is fine, the plan stays on the screen and you change it. Fuel you spend is not lost either; "
    "every flight starts with the whole budget again.",
    "No luck. The same plan always flies the same path, to the last digit, on any device. Every mission was checked by a program that flew a stored plan "
    "and reached the goal with fuel to spare.",
    "No sound and no pictures from anywhere else: every planet, path and chart is drawn by the page. No purchases, no leaderboards, no accounts needed.",
)

HOW = (
    "Each mission names a goal and gives a fuel budget in kilometres per second (km/s), the usual unit for the change of speed a burn gives, called delta-v.",
    "A burn has three numbers: when, which way and how hard. The way is an angle from Wren's own direction of travel: 0 is straight ahead, 180 is backwards, "
    "90 is to the left. Burns are instant. Waiting costs nothing.",
    "The chart shows the whole flight as soon as the plan changes, so you never fly blind. Move the time slider to see where everything is at any moment, "
    "then press Fly to make the flight count.",
    "When Wren comes inside a body's sphere of influence, the region where that body's pull wins, the pass is solved exactly. A closest-approach burn "
    "happens at the nearest point of that pass: slow down there to be captured, or leave it at zero to fly by and keep the bend.",
    "A burn at the nearest point of an orbit (periapsis) or the farthest point (apoapsis) can be set to follow that point, so you do not have to find the "
    "exact moment.",
    "A mission is done when the flight meets its goal inside the fuel budget. Five missions in a chapter open the next chapter. Inside a chapter, any order.",
)

MODEL = (
    "Everything moves on circles in one flat plane. Real orbits are slightly oval, so a planet can be a few degrees from its real place (Mars the most).",
    "Wren feels one body's pull at a time: the Sun's between planets, a planet's inside its sphere of influence. This is the patched-conic method that mission designers use for first sketches.",
    "Burns are instant and the fuel counts only from the starting orbit: launch from the ground is not simulated. Each flight is solved with a fixed time step, "
    "so the same plan always gives the same answer.",
    "Phobos and Deimos are too small for a real sphere of influence, so you reach them by rendezvous: come close, at nearly their own speed.",
)

FACTS = (
    {
        "id": "patched", "heading": "One pull at a time",
        "fact": "Mission designers often simplify a trip through the pull of several bodies by treating one body at a time and joining the pieces. "
                "The method is called the patched conic approximation.",
        "tie_in": "That is how Slingshot works: the Sun's pull between planets, and a planet's pull once you are inside its sphere of influence.",
        "source": {"title": "Patched conic approximation", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Patched_conic_approximation"},
    },
    {
        "id": "assist", "heading": "A pull that pays",
        "fact": "A gravity assist uses a planet's own movement and gravity to change a spacecraft's path and speed round the Sun, usually to save fuel and cost.",
        "tie_in": "Chapter 3 is built on it: a pass of Venus does for Wren what a very large burn would.",
        "source": {"title": "Gravity assist", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Gravity_assist"},
    },
    {
        "id": "soi", "heading": "Whose pull wins",
        "fact": "A body's sphere of influence is the region in which it is the main gravitational influence on an orbiting object. Planets win over the much "
                "heavier but distant Sun there, which is why moons stay with their planets.",
        "tie_in": "The Moon's sphere in the game is about 66,000 km wide; Mars's is about 577,000 km. The numbers are worked out from each body's real pull and distance.",
        "source": {"title": "Sphere of influence (astrodynamics)", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Sphere_of_influence_(astrodynamics)"},
    },
    {
        "id": "hohmann", "heading": "Two burns between orbits",
        "fact": "A Hohmann transfer moves a spacecraft between two circular orbits with two engine burns: the first puts it on an ellipse that touches both "
                "orbits, the second matches the target orbit.",
        "tie_in": "Reaching Phobos from a low Mars orbit is exactly this, and the Earth-to-Mars trip is the same shape on a bigger scale.",
        "source": {"title": "Hohmann transfer orbit", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Hohmann_transfer_orbit"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ, "pledge_heading": "What this game will never do", "pledge": list(PLEDGE),
            "how_heading": "How it works", "how": list(HOW), "model_heading": "What is simplified", "model": list(MODEL),
            "facts_heading": "The real Solar System",
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS]}
