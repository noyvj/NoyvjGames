"""The sourced real-world note, the grid-size select render and the badge source copy."""

from js import document

import canopy_runstate as runstate
from canopy_helpers import _el
from canopy_rules import STAKEHOLDER_KIND_CLEAR


def on_copy_badge_source(event=None):
    """Nothing to do in Python: the copy itself is a plain-JS clipboard call
    (see index.html), which reads the badge text from the DOM."""


def render_grid_size_select():
    """Keeps the grid-size <select> showing whatever preset is actually
    live -- needed because reset_session() can change current_grid_size
    from code paths other than the dropdown itself (a loaded save, e.g.),
    which wouldn't otherwise be reflected back into the control."""
    select = document.getElementById("grid-size-select")
    if select is None:
        return
    select.value = runstate.current_grid_size
    difficulty_select = document.getElementById("difficulty-select")
    if difficulty_select is not None:
        difficulty_select.value = runstate.current_difficulty
    for element_id, value in (("challenge-select", runstate.current_challenge), ("request-pace-select", runstate.current_pace), ("scenario-select", runstate.current_scenario)):
        extra_select = _el(element_id)
        if extra_select is not None:
            extra_select.value = value


# ===========================================================================
# W2-canopy -- "In the real world": a collapsible note that pairs what you
# just did (or what the community is asking) with one real, sourced example.
# Every figure below was read from the linked page on 2026-09-27 (nothing
# recalled from memory); where a page gave no number, none is quoted. The note
# is chosen deterministically (no RNG) and never changes any number in a run:
#   * a pending community request wins (a clear request -> community forestry,
#     an incentive / replant-fund offer -> funded restoration),
#   * else the newest mapped forest-log event (clear, replant, wildlife /
#     preserve / recovered, mature),
#   * else it rotates through the examples every REAL_WORLD_ROTATE_TICKS ticks.
# ===========================================================================
REAL_WORLD_READ_DATE = "2026-09-27"
REAL_WORLD_ROTATE_TICKS = 10
REAL_WORLD_ORDER = ["forest_loss", "restoration", "wildlife", "carbon", "community", "funded_restoration"]
REAL_WORLD_LOG_TOPICS = {
    "clear": "forest_loss",
    "replant": "restoration",
    "wildlife": "wildlife",
    "preserve": "wildlife",
    "recovered": "wildlife",
    "mature": "carbon",
    "rare": "wildlife",
    "discovery": "wildlife",
}
REAL_WORLD_EXAMPLES = {
    "forest_loss": {
        "title": "Global forest loss, and how it has slowed",
        "text": "Clearing forest is a real trade-off worldwide. The FAO's 2020 assessment put deforestation at 10 million hectares a year in 2015-2020, down from 17.6 million hectares a year in 1990-2000.",
        "source": "Wikipedia, Deforestation", "url": "https://en.wikipedia.org/wiki/Deforestation",
    },
    "restoration": {
        "title": "The Atlantic Forest Restoration Pact (Brazil)",
        "text": "Replanting can be organised at scale. The Pact for Atlantic Forest Restoration has brought together over 100 businesses, non-governmental and governmental organisations around a goal of restoring 15 million hectares of the original ecosystem by 2050.",
        "source": "Wikipedia, Atlantic Forest", "url": "https://en.wikipedia.org/wiki/Atlantic_Forest",
    },
    "wildlife": {
        "title": "How fast regrown forest recovers its wildlife",
        "text": "Studies of secondary forest find that species richness can quickly recover to pre-disturbance levels, but the relative abundances and identities of species can take much longer, and in the tropics biodiversity takes longer to recover than carbon stores.",
        "source": "Wikipedia, Secondary forest", "url": "https://en.wikipedia.org/wiki/Secondary_forest",
    },
    "carbon": {
        "title": "Forests as carbon sinks",
        "text": "Standing forest and the climate are linked. Forests are described as sequestering approximately 25% of human carbon emissions each year, though in 2019 they took up a third less carbon than in the 1990s, due to higher temperatures, droughts and deforestation.",
        "source": "Wikipedia, Carbon sink", "url": "https://en.wikipedia.org/wiki/Carbon_sink",
    },
    "community": {
        "title": "Community forestry in Nepal",
        "text": "Communities can manage forest themselves: over 19,000 community forest user groups exist in Nepal, covering one fourth of national forests and 1.6 million households. The same source notes that wealthier households can hold more decision-making power, which can reduce participation by poorer households.",
        "source": "Wikipedia, Community forestry in Nepal", "url": "https://en.wikipedia.org/wiki/Community_forestry_in_Nepal",
    },
    "funded_restoration": {
        "title": "Africa's Great Green Wall",
        "text": "Outside funding and partnership can back restoration, but progress can be hard to measure. The African Union adopted the Great Green Wall in 2007 with a goal of restoring 100 million hectares by 2030; the page cites about 30 million hectares restored as of 2024, and its progress figures differ between years and reports (for example 4% of the planned area in 2020).",
        "source": "Wikipedia, Great Green Wall (Africa)", "url": "https://en.wikipedia.org/wiki/Great_Green_Wall_(Africa)",
    },
}


def real_world_topic():
    """Which example the note shows right now (pure function of run state)."""
    request = runstate.pending_stakeholder_request
    if request is not None:
        if request.get("kind", STAKEHOLDER_KIND_CLEAR) == STAKEHOLDER_KIND_CLEAR:
            return "community"
        return "funded_restoration"
    for entry in reversed(runstate.forest_log):
        topic = REAL_WORLD_LOG_TOPICS.get(entry["kind"])
        if topic is not None:
            return topic
    return REAL_WORLD_ORDER[(runstate.forest_tick // REAL_WORLD_ROTATE_TICKS) % len(REAL_WORLD_ORDER)]


def render_real_world():
    box = document.getElementById("real-world-note")
    example = REAL_WORLD_EXAMPLES[real_world_topic()]
    box.hidden = False
    document.getElementById("real-world-text").innerText = f"{example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {REAL_WORLD_READ_DATE})"
    link.href = example["url"]
