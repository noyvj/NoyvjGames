"""Slingshot -- Chapter 2, The Inner Run: Mars from Earth, then Mars's two small moons (hand-written; the plans are in refplans.py)."""

from missions_base import mars_scene, mission, sun_scene

CHAPTER = {"id": 2, "name": "The Inner Run", "blurb": "Earth to Mars on the real dates, then up to Phobos and Deimos from a low Mars orbit."}

_INNER = ("venus", "earth", "mars")

MISSIONS = [
    mission("c2m1", 2, 1, "Red Planet Flyby", "mars",
            "Earth to Mars costs about three kilometres per second, spent in one forward burn once Mars is a good way ahead of us. The trip takes "
            "about nine months, and the chart already shows where Wren will be.",
            "Pass within 500,000 km of Mars's centre.",
            "Mars is not going anywhere. Neither, for now, are we.",
            sun_scene((2026, 10, 1), _INNER), {"kind": "flyby", "body": "mars", "within": 500000.0}),
    mission("c2m2", 2, 2, "Mars Orbit", "mars",
            "Arriving is the easy part; staying takes a burn. Expect a small course correction on the way, and the brake at closest approach.",
            "Settle into a Mars orbit: lowest point 3,600 to 60,000 km from Mars's centre, highest point no more than 400,000 km.",
            "A correction of a few metres per second, early, beats a big one late.",
            sun_scene((2026, 10, 1), _INNER), {"kind": "capture", "body": "mars", "q": [3600.0, 60000.0], "big_q": 400000.0}),
    mission("c2m3", 2, 3, "Low Mars Orbit", "mars",
            "A low orbit asks for a better aim and a better-judged brake.",
            "Settle into a Mars orbit with its lowest point 3,600 to 5,600 km and its highest point no more than 25,000 km from Mars's centre.",
            "Mars's radius is 3,390 km. That leaves you some air.",
            sun_scene((2026, 10, 5), _INNER), {"kind": "capture", "body": "mars", "q": [3600.0, 5600.0], "big_q": 25000.0}),
    mission("c2m4", 2, 4, "The Next Window", "mars",
            "The start date is later this time, and Mars is in a different place. The chart will show you how long to wait. Waiting is free.",
            "Settle into a Mars orbit: lowest point 3,600 to 30,000 km, highest point no more than 300,000 km from Mars's centre.",
            "Patience is a fuel.",
            sun_scene((2028, 4, 1), _INNER, steps=3200), {"kind": "capture", "body": "mars", "q": [3600.0, 30000.0], "big_q": 300000.0}),
    mission("c2m5", 2, 5, "Express to Mars", "mars",
            "The mission board wants Wren at Mars sooner and has given you more fuel to do it. A faster trip means a faster arrival, which means a bigger brake.",
            "Settle into a Mars orbit within 190 days of the start: lowest point 3,600 to 60,000 km, highest point no more than 600,000 km.",
            "Time is money. Here it is fuel.",
            sun_scene((2026, 10, 30), _INNER), {"kind": "capture", "body": "mars", "q": [3600.0, 60000.0], "big_q": 600000.0, "by": 760}),
    mission("c2m6", 2, 6, "Phobos", "phobos",
            "Wren is in a low Mars orbit. Phobos goes round Mars about three times a day, so a raised orbit can meet it. Two burns do it: one to climb, one to level off.",
            "Come within 400 km of Phobos, moving at no more than 0.25 km/s relative to it.",
            "A rendezvous, not a landing. Phobos is about 22 km across and quite fond of its schedule.",
            mars_scene(4000.0, 100.0, 250.0, 2880), {"kind": "rendezvous", "body": "phobos", "radius": 400.0, "speed": 0.25}),
    mission("c2m7", 2, 7, "Deimos", "deimos",
            "Deimos is the outer moon and the smaller one, and it takes about a day and a quarter to go round. The climb is longer and the timing is looser.",
            "Come within 800 km of Deimos, moving at no more than 0.2 km/s relative to it.",
            "Deimos is about 12 km across. Please do not be modest about 800.",
            mars_scene(4000.0, 100.0, 250.0, 5760, view=30000.0), {"kind": "rendezvous", "body": "deimos", "radius": 800.0, "speed": 0.2}),
    mission("c2m8", 2, 8, "Phobos From Above", "phobos",
            "This time Wren is higher than Phobos, and has to come down to meet it. Down is backwards: you slow down to fall.",
            "Come within 400 km of Phobos, moving at no more than 0.25 km/s relative to it.",
            "Falling is the one thing orbits do for free.",
            mars_scene(14000.0, 20.0, 250.0, 2880, view=30000.0), {"kind": "rendezvous", "body": "phobos", "radius": 400.0, "speed": 0.25}),
]
