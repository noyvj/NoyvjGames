"""Continuum — real-world info-panel content, keyed by era.

Milestone 5 of Phase 1: the design doc's Core system 6, a single "Info"
button that expands a panel of real-world sources for the settlement's
CURRENT era. Content here is drawn from `continuum-real-world-sources.md`
in this same directory — reference material to draw from, not text to dump
wholesale into the game, same rule the climate quartet's research docs
followed.

"tribal", "agrarian", "classical", "medieval" and "industrial" have real
entries so far, matching `sim.IMPLEMENTED_ERAS`. Phase 3 adds one entry per
remaining era as that era's content ships; nothing else in this file needs
to change when it does; `era_info_page()` already handles an era with no
entry yet.

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
    "classical": {
        "framing": (
            "Uruk, in Sumer, is Continuum's real anchor for the Classical "
            "era: intensive irrigation agriculture directed by temple "
            "estates let it grow into a walled city of tens of thousands "
            "— concrete estimates range from roughly 45,000 to as many as "
            "100,000 people — with trade networks reaching hundreds of "
            "miles, from what is now Turkey to what is now Iran. None of "
            "that scale was self-organizing: canal management specifically "
            "required centralized planning and coordinated labor, which is "
            "the real-world hinge this era's mechanics are built around. "
            "Recent research is a useful check on how much credit belongs "
            "to that planning versus the land itself — one recent study "
            "argues natural tidal irrigation helped jumpstart Sumerian "
            "urbanization before human coordination scaled it further."
        ),
        "mechanic_tie_in": (
            "Canals and Administrators exist as a pair on purpose: a canal "
            "you build but leave unstaffed delivers none of its bonus, "
            "mechanically insisting on the sources' own point that "
            "irrigation infrastructure was only ever as good as the "
            "coordinated labor running it. The reverse has a real cost "
            "too — a settlement that keeps assigning people to "
            "Administrators well past what its canals actually need "
            "staffed is pouring its workforce into coordination with "
            "nothing left to coordinate, which is why the sustainability "
            "score's resilience component starts marking that down once "
            "administrators make up too large a share of the workforce."
        ),
        "sources": [
            {
                "label": "The Getty — \"Mesopotamia: Civilization Begins\"",
                "url": "https://www.getty.edu/art/exhibitions/mesopotamia/explore.html",
                "note": (
                    "Uruk's growth into a walled city of roughly 100,000 "
                    "via intensive irrigation agriculture directed by "
                    "temple estates — the real model for this era's shift "
                    "from Agrarian surplus to coordinated civic "
                    "infrastructure, and the direct basis for Temple "
                    "Administration in the research tree."
                ),
            },
            {
                "label": (
                    "TheCollector — \"What Can Uruk and Ur Teach Us About "
                    "the Birth of Civilization?\""
                ),
                "url": "https://www.thecollector.com/uruk-and-ur-birth-of-civilization/",
                "note": (
                    "Canal management required centralized planning and "
                    "coordinated labor — the direct real-world basis for "
                    "why Canals need Administrators staffing them to "
                    "deliver their yield bonus at all."
                ),
            },
            {
                "label": "PLOS One — \"Morphodynamic Foundations of Sumer\"",
                "url": "https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0329084",
                "note": (
                    "Recent research proposing that natural tidal "
                    "irrigation, not just human planning, jumpstarted "
                    "Sumerian urbanization — a useful check on how much of "
                    "this era's scale to credit to coordinated labor "
                    "versus the land itself."
                ),
            },
            {
                "label": "GlobalSecurity.org — \"Uruk Period\"",
                "url": "https://www.globalsecurity.org/military/world/iraq/history-uruk.htm",
                "note": (
                    "Concrete scale figures — population around 45,000, a "
                    "trade network stretching from Turkey to Iran — the "
                    "real-world basis for calibrating this era's city "
                    "scale and for the Trade Networks research node."
                ),
            },
        ],
    },
    "medieval": {
        "framing": (
            "Medieval cities were not just bigger versions of the Classical "
            "ones before them — they were governed differently, and they "
            "regulated everyday life more directly. Real medieval "
            "authorities fined people for dumping waste and zoned toxic "
            "trades like tanning and dyeing away from the water everyone "
            "drank, and academic study of cities like late-medieval Ghent "
            "shows public-works spending being used specifically to guard "
            "against flood, disease and military vulnerability rather than "
            "simply to grow. One recent academic study of medieval England "
            "is literally titled around sustainability and resilience in "
            "urban infrastructure — about as direct a bridge to this "
            "game's own framing as any source in this file gets. "
            "Alongside that came a real shift in who got to decide any of "
            "it: guilds specialised by trade, and municipal charters "
            "granted whole towns a real, legal measure of self-government."
        ),
        "mechanic_tie_in": (
            "Guildmasters and Public Works exist as a pair, but not the "
            "same kind of pair Administrators and Canals were — a canal "
            "needed staffing to work at all, but public-works spending in "
            "the sources is a hedge paid for ahead of a season that might "
            "go badly, not a building that needs a crew to run. That's why "
            "Public Works has no worker requirement here: build it, and it "
            "covers more of the settlement against a shock the more of it "
            "exists, which is exactly the kind of investment the "
            "sustainability score's resilience component now rewards — "
            "the first bonus in this game's whole scoring system, rather "
            "than another way to be penalised. Guildmasters carry the "
            "other half of the era: specialists who make more of a tool "
            "economy the settlement already had, the same way Farmers "
            "once did more with the same land Foragers worked."
        ),
        "sources": [
            {
                "label": (
                    "Popular Archaeology — \"Inside a Medieval City: Public "
                    "Health, Housing, and Everyday Regulations\""
                ),
                "url": "https://popular-archaeology.com/article/inside-a-medieval-city-public-health-housing-and-everyday-regulations/",
                "note": (
                    "Real medieval sanitation regulation — waste fines, "
                    "zoning toxic trades away from drinking water — the "
                    "direct real-world basis for the Zoned Trades and "
                    "Public Sanitation research nodes."
                ),
            },
            {
                "label": (
                    "SAGE Journals — Coomans & Hermenault, \"Public Works, "
                    "Spatial Strategies, and Mobility in Late Medieval "
                    "Ghent\""
                ),
                "url": "https://journals.sagepub.com/doi/10.1177/00961442221124892",
                "note": (
                    "Academic analysis of medieval public-works investment "
                    "used specifically to mitigate risk — floods, disease, "
                    "military vulnerability — rather than to grow output. "
                    "The direct real-world basis for Public Works being a "
                    "resilience bonus rather than a production building."
                ),
            },
            {
                "label": (
                    "Johns Hopkins University Press — Magnusson, \"Urban "
                    "Infrastructure in Medieval England: Sustainability "
                    "and Resilience\""
                ),
                "url": "https://press.jhu.edu/books/title/12618/urban-infrastructure-medieval-england",
                "note": (
                    "A recent academic study literally framed around "
                    "sustainability and resilience in medieval public "
                    "works — this era's clearest direct bridge to the "
                    "game's own SDG 11 framing."
                ),
            },
            {
                "label": (
                    "Fiveable — \"Urban Revival and the Growth of Cities\" "
                    "(European History 1000-1500)"
                ),
                "url": "https://fiveable.me/europe-1000-1500/unit-7/urban-revival-growth-cities/study-guide/91Ey4PdQIbJK9yOx",
                "note": (
                    "Guild specialisation and municipal charters granting "
                    "real self-governance — the real-world basis for the "
                    "Guildmasters role and for the community branch's "
                    "Municipal Charter / Free City Charter research nodes."
                ),
            },
        ],
    },
    "industrial": {
        "framing": (
            "Industrial cities grew faster than anyone planned for them to "
            "— 19th-century industrial growth reliably outpaced the "
            "planning that was supposed to keep up with it, producing "
            "slums and disease that only sanitation reform eventually "
            "caught up with. The scale of that shift is hard to overstate: "
            "global urban population rose from roughly 3% of the world in "
            "1800 to nearly 50% by 2000. And the cost wasn't only a moral "
            "one — rigorous economic research on coal-smoke pollution "
            "during this era found it measurably reduced long-run city "
            "growth, a real, provable brake on the very growth industry "
            "was supposed to deliver."
        ),
        "mechanic_tie_in": (
            "This is the first era where that tension is mechanical, not "
            "just a number on the sustainability panel: Factory Workers "
            "produce far more than a Gatherer ever could, but every one of "
            "them adds to the settlement's pollution — and pollution "
            "doesn't just cost sustainability score, it measurably slows "
            "how fast the settlement can grow next season, the same "
            "real-world link the Economic Journal source describes. "
            "Sanitation Works doesn't touch production at all — like "
            "Medieval's Public Works, it's built rather than staffed — but "
            "it's the only thing that absorbs pollution once it exists, "
            "the direct mechanical echo of sanitation reform arriving only "
            "after industrial growth had already outpaced it."
        ),
        "sources": [
            {
                "label": "Britannica — \"Urban Planning: Industrialization, Infrastructure, Cities\"",
                "url": "https://www.britannica.com/topic/urban-planning/The-era-of-industrialization",
                "note": (
                    "19th-century industrial growth outpacing planning, "
                    "producing slums and disease before sanitation reform "
                    "caught up — the real-world basis for Factory Workers "
                    "outpacing Sanitation Works unless the settlement "
                    "deliberately builds it."
                ),
            },
            {
                "label": (
                    "The Economic Journal (Oxford Academic) — \"Coal Smoke, "
                    "City Growth, and the Costs of the Industrial "
                    "Revolution\""
                ),
                "url": "https://academic.oup.com/ej/article-abstract/130/626/462/5602598",
                "note": (
                    "Rigorous economic research showing industrial "
                    "pollution measurably reduced long-run city growth — "
                    "the direct real-world basis for pollution's growth-"
                    "side penalty, not only its sustainability-score one."
                ),
            },
            {
                "label": "Sociology.Institute — \"The Evolution of Industrial Cities\"",
                "url": "https://sociology.institute/urban-sociology/evolution-industrial-cities-work-urban-environment/",
                "note": (
                    "Global urban population rising from 3% (1800) to "
                    "nearly 50% (2000) — the real scale this era's "
                    "population thresholds and transition beat are meant "
                    "to gesture at."
                ),
            },
            {
                "label": (
                    "PMC — \"Bibliometric Analysis and Research Trend "
                    "Forecast of Healthy Urban Planning for 40 Years\""
                ),
                "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8464861/",
                "note": (
                    "How modern urban planning as a discipline emerged "
                    "directly in response to industrial-era public health "
                    "crises — the real bridge from this era's Public "
                    "Health Acts node into the Digital era's more "
                    "formalized SDG 11 framing."
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
