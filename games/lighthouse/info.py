"""Lighthouse -- the About the Light panel: the real history behind the rules, each fact reworded, with a named source
and the date it was read (all read live on 2026-10-09), and a plain account of how the light works in this game.
No fact here is invented: if it could not be sourced it was left out. No report-an-issue button (the site's version
posts to the live backend); the opening screen's Feedback button covers it."""

DATE_READ = "2026-10-09"

FRAMING = ("Lighthouse is a game, and its boats, people and weather are made up. A few of the ideas under the rules are real, and "
           "these are the ones that could be checked.")

FACTS = (
    {"id": "lens", "heading": "A lens that makes a beam",
     "fact": "Augustin-Jean Fresnel reinvented the lens for lighthouses in 1819. The first one was lit at Cordouan, in France, on 25 July 1823, and its light could be seen to the horizon, more than 32 km out.",
     "tie_in": "In the game: the Better lens upgrade makes the beam carry one step further.",
     "source": {"title": "Fresnel lens", "url": "https://en.wikipedia.org/wiki/Fresnel_lens", "publisher": "Wikipedia", "date_read": DATE_READ}},
    {"id": "clockwork", "heading": "Winding the clockwork",
     "fact": "Keepers wound the clockwork that turned a lighthouse's lens, sometimes as often as every two hours, so the flash kept its rhythm through the night.",
     "tie_in": "In the game: the clockwork runs down unless you wind it, and a stopped beam is only a fixed cone.",
     "source": {"title": "Lighthouse", "url": "https://en.wikipedia.org/wiki/Lighthouse", "publisher": "Wikipedia", "date_read": DATE_READ}},
    {"id": "fuel", "heading": "What the lamp burned",
     "fact": "Early lighthouse lamps burned whale oil and, later, vegetable oils such as colza or olive. Kerosene became popular in the 1870s, and electricity and acetylene began to replace it around 1900.",
     "tie_in": "In the game: oil is the thing you can never have enough of, and the supply boat is how it comes.",
     "source": {"title": "Lighthouse", "url": "https://en.wikipedia.org/wiki/Lighthouse", "publisher": "Wikipedia", "date_read": DATE_READ}},
    {"id": "bell", "heading": "Bells for the fog",
     "fact": "A fog bell was an early fog signal, struck by hand or by a clockwork mechanism. Later signals included gongs, small cannons, steam whistles and, eventually, compressed-air diaphones.",
     "tie_in": "In the game: the Fog bell upgrade takes some of the fog's cost off your beam.",
     "source": {"title": "Fog signal", "url": "https://en.wikipedia.org/wiki/Fog_signal", "publisher": "Wikipedia", "date_read": DATE_READ}},
)

HOW = (
    "Each evening you set a lamp level for dusk, deep night and dawn. Dim, Standard, Bright and Storm reach 3, 5, 7 and 9 steps and burn 0.6, 1.0, 1.6 and 2.6 oil every ten minutes.",
    "Weather takes reach away from the beam: haze 1, fog 2, squall 2, storm 3. A ship passes safely when the beam reaches it for half of its time near the rock.",
    "A ship that cannot find the light turns back or runs on the shoals, and everyone aboard is always safe. Nothing you do can end the game.",
    "The barometer is right about nine nights in ten. The harbour board lists tonight's ships. Both are only hints.",
    "Nothing waits for the real clock. The night runs only while the page is open, and you can pause it whenever you like.",
)


def view():
    return {"framing": FRAMING, "facts": [dict(f) for f in FACTS], "how": list(HOW)}
