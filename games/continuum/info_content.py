"""Continuum — real-world info-panel content, keyed by era.

Milestone 5 of Phase 1: the design doc's Core system 6, a single "Info"
button that expands a panel of real-world sources for the settlement's
CURRENT era. Content here is drawn from `continuum-real-world-sources.md`
in this same directory — reference material to draw from, not text to dump
wholesale into the game, same rule the climate quartet's research docs
followed.

"tribal" and "agrarian" have real entries so far, matching
`sim.IMPLEMENTED_ERAS`. Phase 3 adds one entry per remaining era as that
era's content ships; nothing else in this file needs to change when it
does; `era_info_page()` already handles an era with no entry yet.

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
    "agrarian": {
        "framing": (
            "The Neolithic Revolution is the real turning point Continuum's "
            "Agrarian era is built around: once farming could reliably "
            "produce more food than a settlement needed to survive the "
            "season, that storable surplus stopped being just insurance "
            "against a bad year and started being wealth — something to "
            "store, specialise around, and eventually fight or trade over. "
            "Pottery, dedicated tools, and the first urban clusters all "
            "followed directly from having a surplus to manage in the "
            "first place."
        ),
        "mechanic_tie_in": (
            "Farmland and Farmers exist because settled agriculture was "
            "genuinely more productive per person than foraging ever was — "
            "but the real history behind that surplus has a harder edge "
            "too: it's also the first documented point where property "
            "accumulation created social hierarchy. Continuum's `surplus` "
            "resource echoes both halves — banked value the settlement can "
            "draw on, but banking too much of it per person, unshared, "
            "costs the settlement's equity score rather than being a free "
            "win."
        ),
        "sources": [
            {
                "label": "National Geographic — \"What was the Neolithic Revolution?\"",
                "url": "https://www.nationalgeographic.com/culture/article/neolithic-agricultural-revolution",
                "note": (
                    "How early farmers produced storable surplus in the "
                    "first place — the direct real-world basis for this "
                    "era's surplus/storage mechanics."
                ),
            },
            {
                "label": "HISTORY — \"Neolithic Revolution\"",
                "url": "https://www.history.com/articles/neolithic-revolution",
                "note": (
                    "The shift from nomadic to settled farming life, with "
                    "Çatalhöyük (the Tribal era's own anchor) as the bridge "
                    "example — good grounding for the Tribal-to-Agrarian "
                    "transition specifically."
                ),
            },
            {
                "label": "EBSCO Research Starters — \"Neolithic Revolution\"",
                "url": "https://www.ebsco.com/research-starters/agriculture-and-agribusiness/neolithic-revolution",
                "note": (
                    "Specialized tools, pottery, and early urbanization as "
                    "direct consequences of food surplus — the real basis "
                    "for this era's research-tree nodes (Plow and Furrow, "
                    "Market Custom, and the rest)."
                ),
            },
            {
                "label": "TxWes Pressbooks — \"The Neolithic Revolution\" (World History)",
                "url": "https://txwes.pressbooks.pub/internationalstudies/chapter/2-3-the-neolithic-revolution-world-history-volume-1-to-1500-openstax/",
                "note": (
                    "Surplus specifically creating the first social "
                    "hierarchies and property accumulation — the direct "
                    "real-world basis for the sustainability score's "
                    "surplus-hoarding equity penalty this era."
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
