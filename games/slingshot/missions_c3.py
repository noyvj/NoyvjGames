"""Slingshot -- Chapter 3, Slingshots: Venus, and what Venus's pull can do for a probe heading for the Sun (hand-written; the plans are in refplans.py)."""

from missions_base import mission, sun_scene

CHAPTER = {"id": 3, "name": "Slingshots", "blurb": "Venus, and a gravity assist: a planet's pull turns your path and changes your speed round the Sun, for free."}

AU = 149597870.7
_VENUS = ("mercury", "venus", "earth")
_EPOCH = (2026, 7, 1)

MISSIONS = [
    mission("c3m1", 3, 1, "Venus Flyby", "venus",
            "Venus is closer to the Sun, so Wren has to slow down to fall towards it: a burn backwards, not forwards. The trip is about five months.",
            "Pass within 300,000 km of Venus's centre.",
            "Inward is down. Down is cheap. Coming back up is the bill.",
            sun_scene(_EPOCH, _VENUS, steps=1600, view_au=1.1), {"kind": "flyby", "body": "venus", "within": 300000.0}),
    mission("c3m2", 3, 2, "Venus Orbit", "venus",
            "Same trip, but this time Wren stays. The brake at closest approach does it, with a small course correction on the way.",
            "Settle into a Venus orbit: lowest point 6,200 to 40,000 km from Venus's centre, highest point no more than 400,000 km.",
            "Venus's surface is under 6,100 km from its centre and it is not friendly. Stay above.",
            sun_scene(_EPOCH, _VENUS, steps=1600, view_au=1.1), {"kind": "capture", "body": "venus", "q": [6200.0, 40000.0], "big_q": 400000.0}),
    mission("c3m3", 3, 3, "Express to Venus", "venus",
            "A shorter trip, with more fuel to pay for it. Faster arrival means a harder brake.",
            "Settle into a Venus orbit within 110 days of the start: lowest point 6,200 to 40,000 km, highest point no more than 600,000 km.",
            "The Desk would like it by Thursday. It is a planet.",
            sun_scene((2026, 7, 28), _VENUS, steps=1600, view_au=1.1), {"kind": "capture", "body": "venus", "q": [6200.0, 40000.0], "big_q": 600000.0, "by": 440}),
    mission("c3m4", 3, 4, "Low Venus Pass", "venus",
            "A gravity assist is a flyby close enough to bend the path. The closer the pass, the harder the bend. This one is for practice: aim low and keep going.",
            "Pass between 6,300 and 9,000 km of Venus's centre.",
            "Skimming a planet is a skill. Hitting it is an option.",
            sun_scene(_EPOCH, _VENUS, steps=1600, view_au=1.1), {"kind": "flyby", "body": "venus", "within": 9000.0, "min": 6300.0}),
    mission("c3m5", 3, 5, "Sunward", "sun",
            "Getting close to the Sun means shedding most of Earth's sideways speed, which costs a fortune. Venus can take some of it for you, if you pass it the right way.",
            "Pass Venus, then come within 0.60 AU of the Sun.",
            "One astronomical unit is the distance from Earth to the Sun. Wren would like fewer.",
            sun_scene(_EPOCH, _VENUS, steps=2400, view_au=1.1), {"kind": "reach", "radius": 0.60 * AU, "after": "venus"}),
    mission("c3m6", 3, 6, "Deeper Sunward", "sun",
            "Venus is not quite enough on its own this time. A burn after the flyby, at the right point of the new orbit, finishes the job.",
            "Pass Venus, then come within 0.45 AU of the Sun.",
            "A second burn is not a failure. It is a second burn.",
            sun_scene(_EPOCH, _VENUS, steps=2400, view_au=1.1), {"kind": "reach", "radius": 0.45 * AU, "after": "venus"}),
    mission("c3m7", 3, 7, "Mercury's Orbit", "mercury",
            "Mercury goes round the Sun at 0.39 AU. A probe that gets that deep needs both the assist and a long, careful burn on the far side.",
            "Pass Venus, then come within 0.39 AU of the Sun.",
            "Going straight there would take more fuel than Wren weighs, in some sense.",
            sun_scene(_EPOCH, _VENUS, steps=2400, view_au=1.1), {"kind": "reach", "radius": 0.39 * AU, "after": "venus"}),
]
