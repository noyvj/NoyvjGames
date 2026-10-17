"""Headlines, the glossary, rolling temperature digits and the mascots."""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import thaw_runstate as runstate
from thaw_bridge import _escape
from thaw_model import deg, region, region_b, region_c
from thaw_rules import MELT_THRESHOLD


# ===========================================================================
# GG-26: a post-round ticker of made-up headlines from "The Tundra Tattler". Each one reacts to the
# state of the three managed regions; which line shows is fixed by the round number and the mood
# (no randomness, nothing saved, derived on every render). It is plainly fiction and is hidden by
# the Story switch. Even the critical headlines point at something the player can do.
# ===========================================================================
HEADLINE_MOODS = ("start", "calm", "shield", "melting", "critical", "restoring")
HEADLINES = {
    "start": (
        "Researchers arrive in the tundra and immediately lose a glove to the permafrost.",
        "Snow hare declines to comment on the weather, citing 'a busy schedule of sitting very still'.",
        "Local fox rehearses a complaint about mud, just in case.",
    ),
    "calm": (
        "Fox complains about mud, although the ground is still frozen solid.",
        "Arctic tern files a flight plan; the committee asks for a second copy.",
        "Snow hare declares the season 'suspiciously fine' and keeps watching the thermometer.",
        "Lemmings hold a meeting about nothing in particular. Attendance is excellent.",
        "A very cold puddle is reported. Scientists are delighted.",
    ),
    "shield": (
        "Marmot installs a monitoring dish, files three reports and takes all the credit.",
        "Owl praises the new preservation crews: 'Finally, someone who reads the manual.'",
        "Frost heaves politely over a protected peatland. No one is alarmed.",
        "Local lichen thanks the steward for 'a very stable fortnight'.",
    ),
    "melting": (
        "Fox complains about mud again; this time the mud is, technically, right.",
        "Ground squirrels reroute the commute as the tundra gets softer underfoot.",
        "Methane researchers sharpen pencils: 'Now it gets interesting, and a bit bumpy.'",
        "Hare unpacks rain boots she hoped not to need.",
        "Reindeer note the ground is squishier. Reindeer, as ever, keep walking.",
    ),
    "critical": (
        "Owl calls an emergency meeting; the agenda is short: protect more peat, and soon.",
        "Fox stops complaining about mud and starts drawing up a rescue plan.",
        "Research station lights stay on late, planning exactly where the next unit of protection goes.",
        "Hare reminds everyone that every degree held back still counts, and she can count.",
    ),
    "restoring": (
        "Peat begins to knit back together. Marmot is asked to stop poking it.",
        "Fox admits the mud is getting better and refuses to comment further.",
        "Owl reads the numbers twice: the feedback loop is under control.",
    ),
}


def headline_mood():
    managed = (region, region_b, region_c)
    if region.round_number == 1 and region_b.round_number == 1 and region_c.round_number == 1:
        return "start"
    if any(r.is_critical() for r in managed):
        return "critical"
    if any(r.restoration_active() for r in managed):
        return "restoring"
    if any(r.is_melting() for r in managed):
        return "melting"
    if max(r.feedback_dampening_fraction() for r in managed) >= 0.3:
        return "shield"
    return "calm"


def current_headline():
    mood = headline_mood()
    lines = HEADLINES[mood]
    return lines[(region.round_number - 1) % len(lines)]


def render_headline():
    document.getElementById("headline-ticker").innerText = (
        f"\U0001F4F0 The Tundra Tattler (fiction): {current_headline()}"
    )


# ===========================================================================
# G-28: glossary. Four underlined key terms near the top of Region A's block pop up a one-line
# definition on hover or keyboard focus (CSS only), and a "Key terms" disclosure lists the whole
# glossary. The same wording closes the How to Play walkthrough (index.html and pc.js).
# ===========================================================================
# (key, term, one-line definition); "{melt}" and "{second}" are filled in with the chosen unit.
GLOSSARY = (
    ("melt", "Melt threshold",
     "The temperature ({melt}) past which permafrost starts to melt and methane begins adding to the warming rate."),
    ("dampening", "Feedback dampening",
     "How much of the methane feedback your Preservation and Monitoring units remove; it never touches the fixed background rise."),
    ("acceleration", "Acceleration factor",
     "How many times faster than the steady background rise warming is going right now; 1x means no feedback yet."),
    ("monitoring", "Monitoring & Response",
     "Units that each remove a little of the feedback (4%) and add to the shared research station; they never earn funds."),
    ("preservation", "Permafrost Preservation",
     "Units that each remove more of the feedback (8%) and, once the loop is held steady, power restoration."),
    ("background", "Background rise",
     "The fixed warming every round that nothing you invest in can change; only the methane feedback on top of it can be slowed."),
    ("tipping", "Tipping event",
     "Permafrost starting to melt, or warming going critical. The game counts the rounds since the last one."),
    ("critical", "Critical tier",
     "Acceleration at 2x the background rate or more. The one-time emergency rescue becomes available while a region is critical."),
    ("saved", "Degrees saved",
     "How much cooler a region is than its shadow twin, which faced the same background but never invested in protection."),
    ("restoration", "Restoration",
     "After three steady rounds with the loop held down, each Preservation unit pulls a little melt-driven warming back."),
)
STRIP_TERMS = ("melt", "dampening", "acceleration", "monitoring")


def glossary_definition(key):
    for entry_key, _term, text in GLOSSARY:
        if entry_key == key:
            return text.format(melt=deg(MELT_THRESHOLD, 0, plus=True))
    return ""


def glossary_strip_html():
    parts = []
    for key, term, _text in GLOSSARY:
        if key in STRIP_TERMS:
            definition = _escape(glossary_definition(key))
            parts.append(
                f'<span class="gloss-wrap"><button type="button" class="gloss" aria-describedby="gloss-pop-{key}">{_escape(term)}</button>'
                f'<span class="gloss-pop" role="tooltip" id="gloss-pop-{key}">{definition}</span></span>'
            )
    return "".join(parts)


def glossary_list_html():
    return "".join(
        f"<dt>{_escape(term)}</dt><dd>{_escape(glossary_definition(key))}</dd>" for key, term, _text in GLOSSARY
    )


def render_glossary():
    document.getElementById("glossary-strip-terms").innerHTML = glossary_strip_html()
    document.getElementById("glossary-list").innerHTML = glossary_list_html()


# ===========================================================================
# GG-19: rolling digits. After Advance Round the Region A temperature readout counts up from its old
# value to the new one in a few quick steps, faster the higher the acceleration, then lands on exactly
# the figure render() wrote. It is instant (no rolling) with the "Instant temperature numbers" switch,
# Reduce motion, lite mode or the system's reduced-motion setting, and wherever there is no page (tests).
# Only presentation: the real value is already set, and any render() in the middle cancels the roll.
# ===========================================================================
ROLL_STEPS = 8
ROLL_BASE_MS = 70
ROLL_MIN_MS = 25


def roll_step_ms(acceleration):
    """Milliseconds between digit steps: faster when warming is accelerating (never under ROLL_MIN_MS)."""
    try:
        factor = max(1.0, float(acceleration))
    except (TypeError, ValueError):
        factor = 1.0
    return max(ROLL_MIN_MS, int(ROLL_BASE_MS / factor))


def roll_values(old, new, steps=ROLL_STEPS):
    """The figures shown on the way from old to new (the last one is exactly new)."""
    steps = max(1, int(steps))
    return [old + (new - old) * i / steps for i in range(1, steps)] + [new]


def _digits_instant():
    """True when the rolling should be skipped."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        root = window.document.documentElement
    except Exception:  # noqa: BLE001 -- no page: stay instant
        return True
    for attr in ("data-instant-digits", "data-reduced-motion", "data-lite"):
        if root.getAttribute(attr) == "true":
            return True
    try:
        return bool(window.matchMedia("(prefers-reduced-motion: reduce)").matches)
    except Exception:  # noqa: BLE001 -- no matchMedia
        return False


def _temperature_line(value):
    return f"Global temperature: {deg(value, plus=True)}"


def start_temperature_roll(old, new):
    """Counts the readout from `old` to `new` (call right after render())."""
    if old is None or abs(new - old) < 1e-9 or _digits_instant():
        return False
    runstate._roll_token += 1
    token = runstate._roll_token
    values = roll_values(old, new)
    delay = roll_step_ms(region.acceleration_factor())
    element = document.getElementById("temperature-display")
    element.innerText = _temperature_line(old)

    def step(index):
        if token != runstate._roll_token:
            return
        element.innerText = _temperature_line(values[index])
        if index + 1 < len(values):
            schedule(index + 1)

    def schedule(index):
        proxy = create_proxy(lambda *args: (step(index), proxy.destroy()))
        setTimeout(proxy, delay)

    schedule(0)
    return True


# ===========================================================================
# GG-15: a snow hare and an arctic fox in the status block, drawn as emoji with a one-line comment
# each. The pair react to the state of the three managed regions (the same mood the headline ticker
# reads): calm, shivering when melt has started, cheering when protection is up or restoration runs,
# and fainting dramatically at the critical tier (their lines still point at something to do). Every
# fourth round they bicker instead. Everything is fixed by the round and the mood: no randomness,
# nothing saved, no sound. The Story switch hides them, as does "Hide the hare and the fox".
# ===========================================================================
MASCOT_POSES = {
    "start": "calm", "calm": "calm", "shield": "cheer", "melting": "shiver",
    "critical": "faint", "restoring": "cheer",
}
MASCOT_FACE = {"calm": "\U0001F642", "cheer": "\U0001F389", "shiver": "\U0001F976", "faint": "\U0001F635"}
MASCOT_LINES = {
    "start": (
        ("Hare", "Nothing to report. I like nothing to report."),
        ("Fox", "Nothing to report is a report with the good bits left out."),
    ),
    "calm": (
        ("Hare", "The ground is still frozen solid. Lovely."),
        ("Fox", "I will believe it when the thermometer stops climbing."),
    ),
    "shield": (
        ("Hare", "Those protection crews are doing real work."),
        ("Fox", "Fine. I will admit the dampening number looks good."),
    ),
    "melting": (
        ("Hare", "My ears are cold and the ground is soft. That is a bad mix."),
        ("Fox", "Soft ground is a planning problem. Add protection, then we talk."),
    ),
    "critical": (
        ("Hare", "I am fainting. Briefly. Then I am helping."),
        ("Fox", "Rescue plan on the table, protection on the map. Go."),
    ),
    "restoring": (
        ("Hare", "The peat is knitting back together!"),
        ("Fox", "Do not say it too loudly. It might hear."),
    ),
}
MASCOT_BICKER = (
    (("Hare", "I counted the rounds. We are doing well."), ("Fox", "You counted wrong, and we are doing fine.")),
    (("Hare", "It is my turn to read the thermometer."), ("Fox", "It was your turn last time. And the time before.")),
    (("Hare", "Your tail is in my graph."), ("Fox", "Your graph is in my way.")),
    (("Fox", "Mud."), ("Hare", "It is not even mud yet.")),
)
MASCOT_BICKER_EVERY = 4


def mascot_lines():
    """[(who, text)] for the two mascots this round: a bicker every fourth round, else the mood's pair."""
    rnd = region.round_number
    if rnd > 1 and (rnd - 1) % MASCOT_BICKER_EVERY == 0:
        return list(MASCOT_BICKER[((rnd - 1) // MASCOT_BICKER_EVERY - 1) % len(MASCOT_BICKER)])
    return list(MASCOT_LINES[headline_mood()])


def render_mascots():
    pose = MASCOT_POSES[headline_mood()]
    icons = {"Hare": "\U0001F407", "Fox": "\U0001F98A"}
    items = "".join(
        f'<span class="mascot mascot--{pose}"><span class="mascot-face" aria-hidden="true">'
        f'{icons[who]}{MASCOT_FACE[pose]}</span> <strong>{who}:</strong> {_escape(text)}</span>'
        for who, text in mascot_lines()
    )
    document.getElementById("mascots").innerHTML = items
