"""Slingshot -- Chapter 1, Near Neighbours: seven missions to the Moon from a high Earth orbit (hand-written; the plans are in refplans.py)."""

from missions_base import earth_scene, mission

CHAPTER = {"id": 1, "name": "Near Neighbours", "blurb": "The Moon, from a high parking orbit. Direct transfers: one burn out, and a brake if you want to stay."}

MISSIONS = [
    mission("c1m1", 1, 1, "First Light", "moon",
            "Wren sits in a high orbit round Earth, one lap a day, and the Moon is crossing its path. One burn straight ahead, at the right moment, "
            "sends Wren climbing out to meet it.",
            "Pass within 30,000 km of the Moon's centre.",
            "The Moon is reliable. That is its whole personality.",
            earth_scene(moon_phase=40.0), {"kind": "flyby", "body": "moon", "within": 30000.0}),
    mission("c1m2", 1, 2, "Close Pass", "moon",
            "Same orbit, a finer aim. The Moon's pull bends a close pass, and the path on the chart already includes that bend.",
            "Pass between 2,200 and 6,000 km of the Moon's centre. (The Moon itself is 1,737 km in radius.)",
            "Below 1,737 km is a crater. Please avoid.",
            earth_scene(moon_phase=120.0), {"kind": "flyby", "body": "moon", "within": 6000.0, "min": 2200.0}),
    mission("c1m3", 1, 3, "Parking Orbit", "moon",
            "A flyby is only a hello. To stay, Wren must slow down at its closest approach, and that is what the closest-approach burn is for.",
            "Settle into a lunar orbit: lowest point 1,900 to 20,000 km from the Moon's centre, highest point no more than 60,000 km.",
            "Slow down only as much as you must.",
            earth_scene(moon_phase=200.0), {"kind": "capture", "body": "moon", "q": [1900.0, 20000.0], "big_q": 60000.0}),
    mission("c1m4", 1, 4, "Low Orbit", "moon",
            "The science team wants Wren low and round, a few hundred kilometres above the surface.",
            "Settle into a lunar orbit with its lowest point 1,800 to 2,400 km and its highest point no more than 6,000 km from the Moon's centre.",
            "Lower is harder. It always is.",
            earth_scene(moon_phase=300.0), {"kind": "capture", "body": "moon", "q": [1800.0, 2400.0], "big_q": 6000.0}),
    mission("c1m5", 1, 5, "The Other Way Round", "moon",
            "Orbits do not all go the same way. Pass the Moon on the other side of it and Wren will circle it the opposite way, clockwise on the chart.",
            "Settle into a clockwise lunar orbit: lowest point 1,900 to 12,000 km, highest point no more than 50,000 km from the Moon's centre.",
            "Clockwise is wrong only if you were told it was.",
            earth_scene(moon_phase=75.0), {"kind": "capture", "body": "moon", "q": [1900.0, 12000.0], "big_q": 50000.0, "sense": "retro"}),
    mission("c1m6", 1, 6, "Short Climb", "moon",
            "A lower parking orbit this time. One lap takes under eight hours, so the moment of the burn matters more.",
            "Settle into a lunar orbit: lowest point 1,900 to 15,000 km, highest point no more than 50,000 km from the Moon's centre.",
            "More laps, more chances. Same Moon.",
            earth_scene(r0=20000.0, moon_phase=250.0), {"kind": "capture", "body": "moon", "q": [1900.0, 15000.0], "big_q": 50000.0}),
    mission("c1m7", 1, 7, "Home Again", "moon",
            "Wren must swing round the Moon and come back close enough to Earth to be picked up. The Moon's pull does the turning.",
            "Pass the Moon, then come back to within 9,000 km of Earth's centre.",
            "Plans like this exist. Use one.",
            earth_scene(moon_phase=40.0, steps=6000, stride=10), {"kind": "reach", "radius": 9000.0, "after": "moon"}),
]
