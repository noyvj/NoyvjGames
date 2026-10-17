"""'What the colours and icons mean': the list of every indicator on the farm and how a sample of each is drawn.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from js import document

import champ_runstate as runstate
from champ_rules import STAGE_AUTOMATED, STAGE_ORDER, STAGE_SEED, STAGE_SPROUT
from champ_model import state
from champ_labels import (
    DUE_MESSAGE_MANY, DUE_NOTE, LOCK_NOTE, ROW_DUE_NOTE, STAGE_ICON, STAGE_LABEL, WEEDS_LEGEND,
    WILTING_LEGEND,
)
from champ_util import _element
from champ_points import GOLDEN_POINTS, QUESTS_PER_DAY
from champ_growth import GROWTH_INFO
from champ_leech import LEECH_THRESHOLD
from champ_semesters import SEMESTER_CHIP
from champ_arrange import FARM_FILTERS, FARM_TYPE_ORDER


# ===========================================================================
# LM-2: "What the colours and icons mean"
# ===========================================================================
#
# One list, legend_indicators(), says what every indicator on the farm means and
# how to draw a sample of it. It is built on each call from the tables the farm
# itself draws from (STAGE_ICON/STAGE_LABEL, WILTING_LEGEND, WEEDS_LEGEND,
# LOCK_NOTE, ROW_DUE_NOTE, FARM_FILTERS, GROWTH_INFO, ...), and a sample is drawn
# with the very same CSS classes the farm uses, so a restyle shows up in the guide
# too and the words cannot drift from the real indicators. The tests check the
# other direction: every class _plot_classes() can emit, every `.plot--*` rule in
# style.css, every row part build_farm() makes and every readout in the status
# area has an entry here.

LEGEND_GROUPS = [
    ("growth", "Growth stages (the picture on a plot)"),
    ("state", "Marks on a plot"),
    ("kind", "Kind of plot (the border)"),
    ("row", "Week rows and semester bands"),
    ("meter", "Meters and tallies"),
    ("tag", "Tags on question screens"),
]
STAGE_LEGEND_EXTRA = {STAGE_AUTOMATED: " A blue dot in the corner is the sprinkler."}
KIND_BORDER_WORDS = {
    "vocab": "A thin solid border: one word.",
    "phrase": "A dotted border: a whole phrase.",
    "grammar": "A dashed border: a grammar rule.",
    "phonetic": "A double border: a sound or a letter.",
}
GROWTH_TAG_MEANING = {
    "none": "Your answers here count toward your practice score, but no plot grows.",
    "apply": "Nothing changes while you answer. Press Apply at the end to sprout the weeks you passed.",
}
GROWTH_TAG_DEFAULT_MEANING = "A right answer waters the real plot it asks about (the first one each day), later ones only nudge it."


def _legend_sentence(legend):
    """"Name — a, b" becomes "A: b." so a one-line legend phrase reads as a sentence."""
    rest = legend.partition(" — ")[2].replace(", ", ": ", 1)
    return rest[:1].upper() + rest[1:] + "."


def legend_indicators():
    """[{id, group, name, meaning, sample, classes, icon, text, elements, locked_row}]
    in the order the guide lists them. `classes` are the CSS classes the sample is
    drawn with (and so the ones the coverage tests look for)."""
    items = []

    def add(group, key, name, meaning, sample, classes=(), icon="", text="", elements=(), locked_row=False, growth=""):
        items.append({
            "id": key, "group": group, "name": name, "meaning": meaning, "sample": sample,
            "classes": list(classes), "icon": icon, "text": text, "elements": list(elements),
            "locked_row": locked_row, "growth": growth,
        })

    for stage in STAGE_ORDER:
        name, _sep, rest = STAGE_LABEL[stage].partition(" — ")
        add("growth", f"stage-{stage}", name, rest[:1].upper() + rest[1:] + "." + STAGE_LEGEND_EXTRA.get(stage, ""),
            "plot", ["plot", f"plot--{stage}"], icon=STAGE_ICON[stage])

    seed, sprout = STAGE_ICON[STAGE_SEED], STAGE_ICON[STAGE_SPROUT]
    add("state", "mark-wilting", "Drooping", _legend_sentence(WILTING_LEGEND),
        "plot", ["plot", f"plot--{STAGE_SPROUT}", "plot--wilting"], icon=sprout)
    add("state", "mark-weeds", "Weeds", _legend_sentence(WEEDS_LEGEND) + " A small olive dot sits in the corner.",
        "plot", ["plot", f"plot--{STAGE_SPROUT}", "plot--weeds"], icon=sprout)
    add("state", "mark-due", "Ready for water", "Due today: a thin inner outline. " + DUE_NOTE[:1].upper() + DUE_NOTE[1:] + ".",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--due"], icon=seed)
    add("state", "mark-golden", "Golden plot", f"Today's golden plot, a gold ring. A correct answer on it earns {GOLDEN_POINTS} practice points.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--golden"], icon=seed)
    add("state", "mark-leech", "Stubborn weed", f"Missed {LEECH_THRESHOLD} times in a row: a dark corner wedge. A short re-teach card shows before the question.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--leech"], icon=seed)
    add("state", "mark-amis", "False friend", "Its French word looks like an English one but means something else: a dark wedge in the opposite corner.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--amis"], icon=seed)
    add("state", "mark-locked", "Locked", "Faded and greyed out. Its week opens when the week before has all sprouted.",
        "plot", ["plot", f"plot--{STAGE_SEED}", "plot--locked"], icon=seed)
    add("state", "mark-skin", "Plot skin", "A frame from the Farm shop. It changes the ring and corners only, never the marks above.",
        "text", [], icon="🪙", text="Farm shop skin")

    for kind in FARM_TYPE_ORDER:
        add("kind", f"type-{kind}", FARM_FILTERS[kind], KIND_BORDER_WORDS[kind],
            "plot", ["plot", f"plot--{STAGE_SEED}", f"plot--type-{kind}"], icon=seed)

    example = state.rows[0] if state.rows else None
    add("row", "row-label", "Week label", "The week's place in the farm, then its course and its week in that course.",
        "row", ["row-label"], text=example.label if example else "1. FREN151 wk 1")
    add("row", "row-chapter", "Chapter", "The chapter the week belongs to.",
        "row", ["row-chapter"], text=example.chapter_label if example else "Ch. 1")
    add("row", "row-progress", "Growth count", "Plots grown past Seed out of the plots in the week. Hover it to see how many were ever watered.",
        "row", ["row-progress"], text="3/12")
    add("row", "row-due", "Ready count", "How many plots in the week are ready for water.",
        "row", ["row-due"], text=ROW_DUE_NOTE.format(count=5))
    add("row", "row-perfect-badge", "Perfect week", "Every plot in the week answered right this session with no miss. It clears when you close the page.",
        "row", ["row-perfect-badge"], text="⭐ Perfect this session")
    add("row", "row-lock", "Locked week", "A dashed, faded week. It opens when every plot in the week before has at least sprouted.",
        "row", ["row--locked", "row-lock"], text=LOCK_NOTE.format(previous=4), locked_row=True)
    add("row", "semester-head", "Semester band", "One heading per semester, with its own progress line and meter. Hide weeks folds it away; the farm stays one list.",
        "row", ["semester-head", "semester-title"], text="Semester 1 · FREN151")
    add("row", "semester-chip", "Semester summary", "One line per semester above the farm: how much of it is growing and automated.",
        "text", ["semester-chip"], text=SEMESTER_CHIP.format(name="Semester 1", course="FREN151", percent=40, automated=6))

    add("meter", "automated-meter", "Automated meter", "How much of the whole farm is automated, filling left to right.",
        "meter", ["automated-meter", "automated-bar"], text="35", elements=["automated-meter", "automated-bar"])
    add("meter", "semester-meter", "Semester meter", "How much of one semester is growing (past Seed), filling left to right.",
        "meter", ["automated-meter", "semester-meter", "automated-bar"], text="60")
    add("meter", "stage-summary", "Stage tally", "How many plots sit at each growth stage.",
        "text", ["stage-summary"], text=" · ".join(f"{STAGE_ICON[stage]} {count}" for stage, count in zip(STAGE_ORDER, (40, 12, 8, 4, 2))),
        elements=["stage-summary-display"])
    add("meter", "readout-day", "Day", "The farm's own day. It only moves when you press Next day.", "text", [], text="Day 3", elements=["day-display"])
    add("meter", "readout-due", "Plots ready", "How many plots are ready for water today.",
        "text", ["status-line--due"], text=DUE_MESSAGE_MANY.format(count=12), elements=["due-display"])
    add("meter", "readout-progress", "Growing count", "Plots past Seed out of all plots, and how many are automated.",
        "text", [], text="40 of 790 plots growing · 6 automated", elements=["progress-display"])
    add("meter", "readout-rows-open", "Rows open", "How many weeks have opened so far.", "text", [], text="8 of 23 rows open", elements=["row-summary-display"])
    add("meter", "readout-practice-score", "Practice score", "Points from minigames, drills and tests. Every practice answer adds to it.",
        "text", [], text="Practice score: 12", elements=["practice-score-display"])
    add("meter", "readout-exam", "Exam countdown", "Days to your exam date and how much of the farm should be automated by then. Hidden until you set a date.",
        "text", [], text="Exam in 12 days · about 40% automated by then", elements=["exam-countdown-display"])
    add("meter", "readout-golden", "Golden plot line", "Names today's golden plot, or says you have claimed it.",
        "text", [], text=f"Golden plot claimed today: +{GOLDEN_POINTS} practice points.", elements=["golden-display"])
    add("meter", "readout-goals", "Daily goals", "How many of today's three goals are done.", "text", [], text=f"Daily goals: 1 of {QUESTS_PER_DAY} done", elements=["quest-display"])
    add("meter", "readout-coins", "Coins", "One coin for each full watering. Spend them in the Farm shop.", "text", [], text="🪙 7 coins", elements=["coins-display"])
    add("meter", "readout-combo", "Combo", "Shows after two or more right answers in a row. It is a nice moment, not a score to protect.",
        "text", [], text="3 correct in a row — nice pace.", elements=["combo-display"])
    add("meter", "readout-buddy", "Study buddy", "Only with Study buddy on: a suggestion for how long to study today.",
        "text", [], text="Study buddy: a short session is enough today.", elements=["study-buddy-display"])

    seen = set()
    for _key, (kind, text, _tip) in GROWTH_INFO.items():
        if text in seen:
            continue
        seen.add(text)
        add("tag", f"tag-{kind}", text, GROWTH_TAG_MEANING.get(kind, GROWTH_TAG_DEFAULT_MEANING),
            "tag", ["growth-marker"], text=text, growth=kind)
    return items


def _legend_sample(item):
    """The drawn sample for one indicator, using the farm's own CSS classes."""
    kind = item["sample"]
    wrapper = document.createElement("span")
    wrapper.className = "legend-sample"
    wrapper.setAttribute("aria-hidden", "true")
    if kind == "plot":
        cell = document.createElement("span")
        cell.className = " ".join(item["classes"])
        cell.innerText = item["icon"]
        wrapper.appendChild(cell)
    elif kind == "row":
        card = document.createElement("span")
        card.className = "row legend-row-sample" + (" row--locked" if item["locked_row"] else "")
        inner = document.createElement("span")
        inner.className = " ".join(c for c in item["classes"] if c != "row--locked")
        inner.innerText = item["text"]
        card.appendChild(inner)
        wrapper.appendChild(card)
    elif kind == "meter":
        meter = document.createElement("span")
        meter.className = " ".join(c for c in item["classes"] if c != "automated-bar") + " legend-meter"
        bar = document.createElement("span")
        bar.className = "automated-bar"
        bar.style.width = f"{item['text']}%"
        meter.appendChild(bar)
        wrapper.appendChild(meter)
    elif kind == "tag":
        tag = document.createElement("span")
        tag.className = "growth-marker"
        tag.setAttribute("data-growth", item["growth"])
        tag.innerText = item["text"]
        wrapper.appendChild(tag)
    else:
        text = document.createElement("span")
        text.className = "legend-sample-text dashboard-health-row " + " ".join(item["classes"])
        text.innerText = (item["icon"] + " " if item["icon"] else "") + item["text"]
        wrapper.appendChild(text)
    return wrapper


def on_toggle_legend(event=None):
    runstate.legend_open = not runstate.legend_open
    render_legend_guide()
    if runstate.legend_open:
        try:
            getattr(_element("legend-panel"), "scrollIntoView")()
        except Exception:
            pass


def render_legend_guide():
    panel = _element("legend-panel")
    toggle = _element("legend-toggle-button")
    toggle.innerText = "Hide colours and icons" if runstate.legend_open else "🎨 Colours and icons"
    panel.hidden = not runstate.legend_open
    if not runstate.legend_open:
        runstate._legend_drawn = False
        return
    if runstate._legend_drawn:
        return
    runstate._legend_drawn = True
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "dashboard-heading legend-heading"
    heading.innerText = "What the colours and icons mean"
    panel.appendChild(heading)
    intro = document.createElement("p")
    intro.className = "dashboard-since"
    intro.innerText = "Each sample is drawn the way the farm draws it. Nothing here is a penalty: a plot can droop or tangle, but it never dies."
    panel.appendChild(intro)
    items = legend_indicators()
    for group, title in LEGEND_GROUPS:
        members = [item for item in items if item["group"] == group]
        if not members:
            continue
        group_heading = document.createElement("h3")
        group_heading.className = "legend-group-title dashboard-heading"
        group_heading.innerText = title
        panel.appendChild(group_heading)
        for item in members:
            row = document.createElement("div")
            row.id = f"legend-item-{item['id']}"
            row.className = "legend-item"
            row.appendChild(_legend_sample(item))
            words = document.createElement("span")
            words.className = "legend-words dashboard-health-row"
            name = document.createElement("strong")
            name.className = "legend-name"
            name.innerText = item["name"]
            words.appendChild(name)
            meaning = document.createElement("span")
            meaning.className = "legend-meaning"
            meaning.innerText = " " + item["meaning"]
            words.appendChild(meaning)
            row.appendChild(words)
            panel.appendChild(row)
