"""Continuum — real-world info-panel content, keyed by era.

Milestone 5 of Phase 1: the design doc's Core system 6, a single "Info"
button that expands a panel of real-world sources for the settlement's
CURRENT era. Content here is drawn from `continuum-real-world-sources.md`
in this same directory — reference material to draw from, not text to dump
wholesale into the game, same rule the climate quartet's research docs
followed.

Only "tribal" has a real entry so far, matching `sim.IMPLEMENTED_ERAS`.
Phase 3 adds one entry per era as that era's content ships; nothing else
in this file needs to change when it does; `era_info_page()` already
handles an era with no entry yet.

Kept as its own module rather than folded into game.py for two reasons:
it is data, not DOM logic (matching the "dedicated engine modules, game.py
stays a thin browser layer" convention the rest of Phase 1 established),
and it is the one piece of Phase 3's per-era content that has nothing to
do with simulation, research or the score — it doesn't belong in sim.py,
research.py or sustainability.py either.
"""

# Each entry is shaped exactly the way shared/info_page.py's render()
# already expects ({"framing", "mechanic_tie_in", "sources"}), so Continuum
# can reuse that shared module unchanged — the only difference from the
# climate quartet's games is that there are seven of these dicts, keyed by
# era, instead of one static module-level dict.
ERA_INFO_PAGE = {
    "tribal": {
        "framing": (
            "Continuum's Tribal era leans on real anthropology for its "
            "scale, not an invented one. Early human groups organised as "
            "small, mobile \"bands\" before growing into settled \"tribes\" "
            "as village size and permanent architecture appeared — and "
            "Dunbar's number describes the same kind of threshold: roughly "
            "5, 15, 50 and 150 people, each layer needing a different kind "
            "of social structure to hold together. Where a settlement "
            "chooses to put itself down was never arbitrary either — early "
            "settlement-location research shows groups weighing geography "
            "and environment much the way this game's land-health system "
            "rewards paying attention to what a plot of land can actually "
            "give."
        ),
        "mechanic_tie_in": (
            "Çatalhöyük, one of the earliest known settlements, is the "
            "real-world anchor for Continuum's starting conditions: "
            "comparably-sized dwellings with no architectural sign of "
            "hierarchy, which is why the four Tribal roles — foragers, "
            "gatherers, crafters, keepers — start as equals rather than a "
            "ranked ladder, and why the sustainability score's equity "
            "component is capped by whichever need is worst-met rather "
            "than the average."
        ),
        "sources": [
            {
                "label": "Pressbooks Nebraska — \"Political Systems\" (Introduction to Anthropology)",
                "url": "https://pressbooks.nebraska.edu/anth110/chapter/political-systems/",
                "note": (
                    "The real anthropological distinction between bands and "
                    "tribes, and how village growth and architecture marked "
                    "the shift — the real-world basis for this era's "
                    "population and settlement mechanics."
                ),
            },
            {
                "label": "UNESCO World Heritage Centre — Neolithic Site of Çatalhöyük",
                "url": "https://whc.unesco.org/en/list/1405/",
                "note": (
                    "One of the earliest known settlements, notable for its "
                    "egalitarian layout — comparably-sized dwellings, no "
                    "social hierarchy visible in the architecture — a "
                    "direct anchor for the Tribal era's non-hierarchical "
                    "starting roles."
                ),
            },
            {
                "label": (
                    "PMC — \"The study of early human settlement preference "
                    "and settlement prediction in Xinjiang, China\""
                ),
                "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8948180/",
                "note": (
                    "How early humans actually chose settlement locations "
                    "based on geography and environment — the real-world "
                    "counterpart to this game's land-health/sustainable-"
                    "yield system."
                ),
            },
            {
                "label": "Research Outreach / Medium — Dunbar's Number",
                "url": "https://researchoutreach.org/articles/size-matters-social-groups-human-evolution/",
                "note": (
                    "The real cognitive/social limit on stable group size "
                    "(~150, in a layered structure of 5/15/50/150/500/1500) "
                    "— the basis for calibrating this era's population "
                    "thresholds."
                ),
            },
        ],
    },
}

# Shown for an era with no entry above yet. Kept intentionally sparse — an
# empty source list rather than invented placeholder links — so the panel
# never implies research exists for an era that doesn't have it.
_PENDING = {
    "framing": (
        "Real-world sources for this era haven't been written yet — Phase "
        "3 adds one era's content at a time, from "
        "continuum-real-world-sources.md."
    ),
    "mechanic_tie_in": "",
    "sources": [],
}


def era_info_page(era):
    """The info-page dict for one era, or the pending placeholder.

    The one function game.py calls; keeping the era lookup here (rather
    than in game.py) means adding a second era's content later is a matter
    of adding one entry to ERA_INFO_PAGE, not touching the render path.
    """
    return ERA_INFO_PAGE.get(era, _PENDING)
