"""Dead Reckoning -- the "About" page: the real ideas behind the game, each with its source named on screen and the date it was read.

Every fact below was read live from the named page on the date given and is reworded here, never copied. The game itself is an
ABSTRACTION, not a simulator: its numbers (the leeway share, the size of a fix error, the shape of its tides) are game constants
and the page says so. A fact with no source would be left out."""

DATE_READ = "2026-10-09"

FRAMING = ("Dead Reckoning is a game, not a simulator. Its sea, its numbers and its charts are invented and simplified: the share of the "
           "wind that becomes leeway, the size of a fix's error and the shape of its tides are game rules, and nothing here claims the accuracy "
           "of a real passage. The ideas behind it are real, and these are some of the places they come from.")

FACTS = (
    {
        "id": "dead-reckoning", "heading": "Estimating where you are",
        "fact": "Dead reckoning estimates a moving thing's present position from an earlier known position, its speed, its heading and the "
                "time that has passed. Errors add up the longer it runs, and a fresh fix partway through is what pulls the estimate back. "
                "A plain dead-reckoning plot at sea does not allow for currents or wind.",
        "tie_in": "Your dashed plot is exactly that, and the switch that allows for the chart is the game's way of adding what a careful navigator would add.",
        "source": {"title": "Dead reckoning", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Dead_reckoning"},
    },
    {
        "id": "nautical-mile", "heading": "How long a nautical mile is",
        "fact": "The international nautical mile is fixed at 1,852 metres, a value set at an international hydrographic conference in Monaco in 1929. "
                "A knot is one nautical mile an hour.",
        "tie_in": "Every distance on the chart is in these miles, and every speed in these knots.",
        "source": {"title": "Nautical mile", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Nautical_mile"},
    },
    {
        "id": "chip-log", "heading": "Where the knot comes from",
        "fact": "Sailors once measured speed with a chip log: a weighted board on a line tied with evenly spaced knots. The board was thrown "
                "astern and held roughly still while the line ran out for a set time, measured with a sandglass, and the knots that slipped "
                "past were counted. That count of knots is why a speed is still given in knots.",
        "tie_in": "Your speed and your time are all the game gives you, as they were all a navigator had.",
        "source": {"title": "Chip log", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Chip_log"},
    },
    {
        "id": "leeway", "heading": "Sliding sideways",
        "fact": "A sailing vessel is pushed sideways and downwind by the wind on her hull and rigging, so she makes good a track a little to "
                "leeward of the heading she steers. Navigators allow for this slip, and for currents, when they set a course.",
        "tie_in": "In the game the slip is a fixed share of the wind across the ship, a simplification. The currents are charted as a set (the way they run) and a drift (how fast).",
        "source": {"title": "Leeway", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Leeway"},
    },
    {
        "id": "compass-error", "heading": "A compass that does not read true",
        "fact": "Magnetic variation (also called declination) is the angle between magnetic north and true north at a place, and it changes from "
                "place to place and slowly over time. Deviation is a different error, caused by iron near the compass such as a ship's own.",
        "tie_in": "The compass chapter prints one error as a range and asks you to steer the heading that is already corrected.",
        "source": {"title": "Magnetic declination", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Magnetic_declination"},
    },
    {
        "id": "chronometer", "heading": "Longitude and the clock",
        "fact": "Finding longitude at sea depends on knowing the time at a reference place exactly, because the Earth turns at a steady rate. "
                "Pendulum clocks could not keep time on a rolling ship, and the marine chronometer, a portable timepiece that kept accurate time "
                "despite the ship's motion, was the practical answer.",
        "tie_in": "The game never asks you to find longitude from the stars; this is only a reminder of how hard knowing where you are once was.",
        "source": {"title": "Marine chronometer", "publisher": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Marine_chronometer"},
    },
)


def view():
    return {"framing": FRAMING, "date_read": DATE_READ,
            "facts": [dict(f, source=dict(f["source"], date_read=DATE_READ)) for f in FACTS]}
