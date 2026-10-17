"""The pasture: cow moods, quips and speech bubbles, the pasture picture, named cows and the hall of fame.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import html

from js import document, setTimeout
from pyodide.ffi import create_proxy

import herd_runstate as runstate
from herd_rules import BASE_COUPLING_RATIO, COW_NAMES, HALL_OF_FAME_SIZE, HALL_PER_HANDOVER


# F2 — scale the pasture visual's cow count with real herd size. The
# hero illustration has 5 fixed cow elements; rather than dynamically
# generating DOM nodes for an unbounded herd size, cows are progressively
# revealed at these herd-size thresholds and the rest stay hidden, so an
# empty pasture (herd_size == 0) reads as genuinely empty.
PASTURE_COW_THRESHOLDS = [
    ("pasture-cow-a", 1),
    ("pasture-cow-b", 3),
    ("pasture-cow-c", 6),
    ("pasture-cow-d", 10),
    ("pasture-cow-e", 15),
]


# GF-12 -- cow reactions: the pasture cows hop when the herd is well and clean, nap when it is strained, and
# say a dry one-liner when clicked (or when the Listen button is pressed, the keyboard way). The mood only
# reads the farm; it never changes it.
COW_HOP_MIN_WELFARE = 70
COW_HOP_MAX_RATIO = 0.7
COW_NAP_MAX_WELFARE = 45
COW_NAP_MIN_PRESSURE = 0.4
COW_BUBBLE_MS = 4000
COW_QUIPS = {
    "hop": [
        "That was a small victory hop. I would like it on the record.",
        "The air smells fine today. Whatever you changed, keep changing it.",
        "Hay is good, the haze is smaller. I approve.",
        "I am not showing off. I am just very well run.",
    ],
    "nap": [
        "Five more minutes. Maybe ten.",
        "I am not tired, I am conserving methane.",
        "The air is thick and so is my schedule. Nap.",
        "Wake me when the ratio improves.",
    ],
    "graze": [
        "Moo. (A neutral moo.)",
        "Grass: acceptable. Management: under review.",
        "I have opinions about the feed budget. Moo.",
        "Ask me again after the next round.",
    ],
}
COW_MOOD_WORDS = {"hop": "hopping", "nap": "napping", "graze": "calm"}
COW_IDS = [element_id for element_id, _threshold in PASTURE_COW_THRESHOLDS]


def herd_mood():
    if runstate.farm.welfare() >= COW_HOP_MIN_WELFARE and runstate.farm.coupling_ratio() <= COW_HOP_MAX_RATIO:
        return "hop"
    if runstate.farm.welfare() <= COW_NAP_MAX_WELFARE or runstate.farm.pressure_fraction() >= COW_NAP_MIN_PRESSURE:
        return "nap"
    return "graze"


def cow_quip(index=None):
    """One line for the herd's mood, fixed by how many have been heard (no luck). With a cow number the line
    starts with that animal's name; an empty pasture has nothing to say."""
    if runstate.farm.herd_size < 1:
        return "The pasture is empty. Not one moo."
    lines = COW_QUIPS[herd_mood()]
    line = lines[runstate.cow_quip_count % len(lines)]
    runstate.cow_quip_count += 1
    name = cow_name(index if index is not None else (runstate.cow_quip_count - 1) % runstate.farm.herd_size)
    return f"{name}: {line}"


def say_cow_quip(index=None):
    bubble = document.getElementById("cow-bubble")
    bubble.innerText = cow_quip(index)
    bubble.hidden = False
    runstate.cow_bubble_token += 1
    token = runstate.cow_bubble_token

    def _hide(*args):
        if token == runstate.cow_bubble_token:
            document.getElementById("cow-bubble").hidden = True
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, COW_BUBBLE_MS)


def _make_cow_click_handler(slot):
    def handler(event=None):
        threshold = PASTURE_COW_THRESHOLDS[slot][1]
        say_cow_quip(threshold - 1)
    return handler


def on_cow_listen(event=None):
    say_cow_quip()


def update_pasture_visual():
    mood = herd_mood()
    for element_id, threshold in PASTURE_COW_THRESHOLDS:
        cow = document.getElementById(element_id)
        cow.hidden = runstate.farm.herd_size < threshold
        cow.title = pasture_cow_title(threshold)  # GF-13: hover shows the animal's name
        for name in ("hop", "nap"):
            if mood == name:
                cow.classList.add(f"cow-mood-{name}")
            else:
                cow.classList.remove(f"cow-mood-{name}")
    listen = document.getElementById("cow-listen-button")
    listen.innerText = f"\U0001F404 Listen to the herd ({COW_MOOD_WORDS[mood]})"
    listen.disabled = runstate.farm.herd_size < 1
    # F2 — a small herd-size number overlay alongside the cow visual.
    count = document.getElementById("pasture-herd-count")
    count.innerText = f"Herd: {runstate.farm.herd_size}"
    count.hidden = runstate.farm.herd_size < 1
    # F30 — methane wisps thin out as the coupling ratio improves,
    # reinforcing the haze cue with motion: fainter with a lower ratio,
    # gone once the farm is ~90% decoupled.
    wisp_opacity = max(0.0, min(1.0, runstate.farm.coupling_ratio() / BASE_COUPLING_RATIO))
    for element_id in ("pasture-wisp-a", "pasture-wisp-c"):
        wisp = document.getElementById(element_id)
        wisp.style.opacity = f"{wisp_opacity:.2f}"
        wisp.hidden = runstate.farm.decoupled_fraction() >= 0.9


def cow_name(index, gen=None):
    """The name of herd unit `index` (0 = the first animal bought) in a generation. Fixed by
    position, so the same after any reload; a different generation starts further along the list."""
    gen = runstate.generation if gen is None else gen
    position = index + (gen - 1) * 7
    lap, slot = divmod(position, len(COW_NAMES))
    name = COW_NAMES[slot]
    if lap == 0:
        return name
    numerals = ["", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    return f"{name} {numerals[lap] if lap < len(numerals) else lap + 1}"


def cow_roster():
    """(name, rounds served) for every herd unit, oldest first."""
    return [
        (cow_name(i), max(0, runstate.farm.round_number - bought))
        for i, bought in enumerate(runstate.farm.herd_unit_rounds())
    ]


def retire_herd_to_hall():
    """Called on handover: the longest-serving animals of the outgoing farm join the hall of fame."""
    roster = [(name, served) for name, served in cow_roster() if served > 0]
    roster.sort(key=lambda entry: -entry[1])
    for name, served in roster[:HALL_PER_HANDOVER]:
        runstate.hall_of_fame.append([name, served, runstate.generation])
    runstate.hall_of_fame.sort(key=lambda entry: (-entry[1], entry[2]))
    del runstate.hall_of_fame[HALL_OF_FAME_SIZE:]


def hall_of_fame_html():
    if not runstate.hall_of_fame:
        return (
            "<li>No animals retired yet. Hand a certified farm to the next generation and its "
            "longest-serving animals are honoured here.</li>"
        )
    return "".join(
        f"<li>{html.escape(str(name))}: {served} round{'s' if served != 1 else ''} "
        f"(generation {gen})</li>"
        for name, served, gen in runstate.hall_of_fame
    )


def pasture_cow_title(threshold):
    """Hover text for a pasture cow: the animal that revealed it (the threshold-th unit)."""
    roster = cow_roster()
    if len(roster) < threshold:
        return ""
    name, served = roster[threshold - 1]
    return f"{name}, animal #{threshold}, {served} round{'s' if served != 1 else ''} on the farm"
