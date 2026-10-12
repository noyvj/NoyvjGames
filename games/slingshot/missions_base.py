"""Slingshot -- shared pieces for the mission files: the three kinds of scene and the mission builder.

A mission is plain data (a dict): who it is, the desk's note, the scene the flight happens in, the goal, and (from refplans.py, which
tools/solve.py writes) the stored reference plan, its fuel cost and the budget. Nothing here reads a clock or a random source.

Three kinds of scene:
  earth_scene  the probe starts on a circular Earth orbit and the Moon moves on its circle; a step is 0.1 hour
  sun_scene    the probe starts co-moving with Earth on its circle around the Sun; the planets sit where the JPL mean longitudes put
               them on the mission's start date; a step is a quarter of a day
  mars_scene   the probe starts on a circular Mars orbit and Phobos and Deimos move on their circles; a step is one minute
"""

UNITS = {
    "h": {"name": "hours", "short": "h", "per_step": 0.1, "digits": 1},
    "min": {"name": "minutes", "short": "min", "per_step": 1.0, "digits": 0},
    "d": {"name": "days", "short": "d", "per_step": 0.25, "digits": 2},
}


def earth_scene(r0=42164.0, moon_phase=40.0, steps=3600, stride=6):
    return {"central": "earth", "children": ["moon"], "dt": 360.0, "steps": steps, "stride": stride, "unit": "h", "view": 470000.0,
            "start": {"orbit": {"r": r0, "theta": 0.0, "dir": 1}}, "phases": {"moon": moon_phase}}


def sun_scene(epoch, children, steps=2400, view_au=1.75):
    return {"central": "sun", "children": list(children), "dt": 21600.0, "steps": steps, "stride": 8, "unit": "d", "view": view_au * 149597870.7,
            "start": {"comove": "earth"}, "epoch": tuple(epoch)}


def mars_scene(r0, phobos_phase, deimos_phase, steps, view=30000.0):
    return {"central": "mars", "children": ["phobos", "deimos"], "dt": 60.0, "steps": steps, "stride": 4, "unit": "min", "view": view,
            "start": {"orbit": {"r": r0, "theta": 0.0, "dir": 1}}, "phases": {"phobos": phobos_phase, "deimos": deimos_phase},
            "rendezvous": ["phobos", "deimos"]}


def mission(mid, chapter, number, name, dest, brief, goal_text, note, scene, goal, **extra):
    m = {"id": mid, "chapter": chapter, "number": number, "name": name, "dest": dest, "brief": brief, "goal_text": goal_text, "note": note,
         "scene": scene, "goal": goal}
    m.update(extra)
    return m
