"""The settlement mood strip and look, the achievements tree strip, the docked resources line and the damage hit effects."""

from js import document, localStorage

import aftermath_runstate as runstate
from aftermath_achievements import achievement_ids_earned, achievements_summary
from aftermath_bonuses import DEFAULT_LOOK, SETTLEMENT_LOOKS, look_label, look_thresholds, looks_seen
from aftermath_panels import _flash_element
from aftermath_persist import _el, skill_tree_strength
from aftermath_rules import EVENT_CATEGORY, EVENT_ICON, MAX_MITIGATION, SKILLS


# ---------------------------------------------------------------------------
# GE-20: the settlement mood strip. Five tiny citizens whose faces move from grinning to grim as the
# run's resources and mitigation change. Purely a readout (no number in the game reads it), always
# also written as words, and redrawn by every render() so each allocation click moves it.
# ---------------------------------------------------------------------------
MOOD_FACES = ("\U0001F600", "\U0001F642", "\U0001F610", "\U0001F61F", "\U0001F628")  # grinning .. fearful
MOOD_WORDS = ("cheerful", "content", "uneasy", "worried", "frightened")
MOOD_CITIZENS = 5
# Each citizen leans a little differently, so the strip changes one face at a time rather than all at once.
MOOD_LEANS = (-0.10, -0.04, 0.0, 0.05, 0.11)
MOOD_RESOURCE_FULL = 200.0  # resources that count as "comfortable" (the classic starting purse)


def settlement_mood_score(run_state):
    """0.0 (grim) to 1.0 (grinning): half from resources in hand against a comfortable purse, half from
    how much of the damage the settlement is currently shrugging off (mitigation against its 85% cap)."""
    purse = min(1.0, max(0.0, run_state.resources / MOOD_RESOURCE_FULL))
    shelter = min(1.0, max(0.0, run_state.mitigation_fraction() / MAX_MITIGATION))
    return 0.5 * purse + 0.5 * shelter


def mood_levels(score):
    """One face level per citizen, 0 (grinning) to 4 (fearful)."""
    levels = []
    for lean in MOOD_LEANS:
        value = min(0.999, max(0.0, score + lean))
        levels.append(min(len(MOOD_FACES) - 1, int((1.0 - value) * len(MOOD_FACES))))
    return levels


def mood_summary(run_state):
    """(faces, label) for the strip: the faces in order and the text that says the same in words."""
    levels = mood_levels(settlement_mood_score(run_state))
    smiling = sum(1 for level in levels if level <= 1)
    average = round(sum(levels) / len(levels))
    word = MOOD_WORDS[min(len(MOOD_WORDS) - 1, max(0, average))]
    label = f"Settlement mood: {word}. {smiling} of {len(levels)} citizens are smiling."
    return [MOOD_FACES[level] for level in levels], label


_mood_parts = []


def render_mood_strip():
    strip = _el("mood-strip")
    caption = _el("mood-caption")
    if strip is None:
        return  # a cached older page without the strip
    if not _mood_parts:
        for _ in range(MOOD_CITIZENS):
            face = document.createElement("span")
            face.className = "mood-face"
            face.setAttribute("aria-hidden", "true")
            strip.appendChild(face)
            _mood_parts.append(face)
    faces, label = mood_summary(runstate.run)
    for part, glyph in zip(_mood_parts, faces):
        part.innerText = glyph
    strip.setAttribute("aria-label", label)
    strip.title = label
    if caption is not None:
        caption.innerText = label


def look_text(run_state):
    thresholds = look_thresholds()
    current = getattr(run_state, "look", DEFAULT_LOOK)
    owned = skill_tree_strength()
    keys = [key for key, _label in SETTLEMENT_LOOKS]
    nxt = next((key for key in keys if thresholds[key] > owned and keys.index(key) > keys.index(current)), None)
    where = f"{owned} of {len(SKILLS)} skills owned"
    if nxt:
        where += f"; {look_label(nxt)} at {thresholds[nxt]}"
    if run_state.normalised:
        return f"Settlement look: {look_label(current)} (a friend's challenge run ignores your tree). Looks seen: {len(looks_seen(run_state))} of {len(SETTLEMENT_LOOKS)}."
    return f"Settlement look: {look_label(current)} ({where}). Looks seen: {len(looks_seen(run_state))} of {len(SETTLEMENT_LOOKS)}."


def render_settlement_look():
    visual = _el("settlement-visual")
    if visual is not None:
        for key, _label in SETTLEMENT_LOOKS:
            visual.classList.remove(f"settlement-visual--{key}")
        visual.classList.add(f"settlement-visual--{getattr(runstate.run, 'look', DEFAULT_LOOK)}")
    text = _el("settlement-look-display")
    if text is not None:
        text.innerText = look_text(runstate.run)


# ---------------------------------------------------------------------------
# E-31: the achievements as a small tree beside the toolbar. A trunk with six branches (grouped by what the
# achievement is about, from the ids; an id nobody listed lands on "More"), every achievement a node: earned
# nodes are lit and filled with a check mark, unearned ones hollow, and the shape differs as well as the
# colour. Each branch says "3/4" in words and every node has its name as a label (and shows it on hover or
# focus). It only reads what the catalog already knows; nothing is stored.
# ---------------------------------------------------------------------------
ACHIEVEMENT_BRANCHES = (
    ("Getting started", ("first_event_faced", "first_resilience_investment", "first_growth_investment", "run_complete_1")),
    ("Keep going", ("run_complete_5", "run_complete_10", "knowledge_25", "knowledge_100", "come_back_stronger")),
    ("Skill tree", ("unlock_reinforced_infrastructure", "unlock_community_reserves", "unlock_early_warning", "full_skill_tree")),
    ("Playstyles", ("iron_defenses", "profitable_run", "growth_focused", "resilience_focused", "balanced_strategy",
                    "deep_specialist", "broad_generalist", "both_paths")),
    ("Hard hits", ("severe_survivor", "flawless_defense")),
    ("Codex", ("codex_complete", "heat_health_faced", "codex_full_record")),
)


def achievement_tree_branches(summary=None):
    """[(branch label, [summary entries])] in catalog order inside each branch; branches with nothing in the
    catalog are left out and every catalog entry appears exactly once (unlisted ones under "More")."""
    summary = achievements_summary() if summary is None else summary
    by_id = {entry["id"]: entry for entry in summary}
    placed = set()
    branches = []
    for label, ids in ACHIEVEMENT_BRANCHES:
        entries = [by_id[i] for i in ids if i in by_id and i not in placed]
        placed.update(entry["id"] for entry in entries)
        if entries:
            branches.append((label, entries))
    rest = [entry for entry in summary if entry["id"] not in placed]
    if rest:
        branches.append(("More", rest))
    return branches


def achievement_tree_summary_text(summary=None):
    summary = achievements_summary() if summary is None else summary
    earned = sum(1 for entry in summary if entry["earned"])
    return f"Achievements: {earned} of {len(summary)} earned"


def render_achievement_strip():
    strip = _el("achievement-strip")
    if strip is None:
        return  # a cached older page without the strip
    signature = tuple(achievement_ids_earned())
    if signature == runstate._achievement_strip_signature:
        return  # nothing earned since the last drawing
    runstate._achievement_strip_signature = signature
    summary = achievements_summary()
    text = achievement_tree_summary_text(summary)
    summary_el = _el("achievement-strip-summary")
    if summary_el is not None:
        summary_el.innerText = "\U0001f3c6 " + text
    strip.setAttribute("aria-label", text)
    strip.innerHTML = ""
    for label, entries in achievement_tree_branches(summary):
        earned = sum(1 for entry in entries if entry["earned"])
        branch = document.createElement("div")
        branch.className = "achievement-branch"
        branch.setAttribute("role", "group")
        branch.setAttribute("aria-label", f"{label}: {earned} of {len(entries)} earned")
        name = document.createElement("span")
        name.className = "achievement-branch-name"
        name.innerText = f"{label} {earned}/{len(entries)}"
        branch.appendChild(name)
        nodes = document.createElement("span")
        nodes.className = "achievement-branch-nodes"
        for entry in entries:
            node = document.createElement("span")
            node.className = "achievement-node achievement-node--earned" if entry["earned"] else "achievement-node"
            node.innerText = "\u2713" if entry["earned"] else ""
            state = "earned" if entry["earned"] else "not earned yet"
            node.setAttribute("role", "img")
            node.setAttribute("tabindex", "0")
            node.setAttribute("aria-label", f"{entry['label']}: {state}")
            node.setAttribute("data-detail", f"{entry['label']} ({state}): {entry['description']}")
            node.title = f"{entry['label']} ({state})"
            nodes.appendChild(node)
        branch.appendChild(nodes)
        strip.appendChild(branch)


# ---------------------------------------------------------------------------
# E-26: on a phone the investments and Face Next Event are pinned to the bottom of the screen
# (shared/mobile-dock.js), so the numbers they spend are repeated as one line at the top of that bar.
# CSS shows it only while the bar is docked; the real status lines (and the sticky top bar) are unchanged.
# ---------------------------------------------------------------------------
def dock_resources_text(run_state):
    return (
        f"Resources {run_state.resources:.0f} \u00b7 Resilience {run_state.resilience_capacity} "
        f"\u00b7 Growth {run_state.growth_capacity}"
    )


def render_dock_resources():
    element = _el("dock-resources")
    if element is not None:
        element.innerText = dock_resources_text(runstate.run)


# ---------------------------------------------------------------------------
# GE-14: per-category event hit effects. When an event resolves the settlement art gets one short effect
# for that kind of event (a ripple for floods, a heat pulse for heatwaves and heat-health emergencies, a
# shake and flash for storms, a flicker for infrastructure failure, a dim for supply-chain trouble, a red
# shudder for civil unrest) and the damage number is shown large beside it. The effects are one CSS class on
# the art for under a second; every one is also written in words by the unchanged Last-event line, so
# nothing depends on them. A Settings switch turns them off, and Reduce motion always does.
# ---------------------------------------------------------------------------
EFFECTS_STORAGE_KEY = "aftermath-effects"  # settings.js writes "true" or "false"; missing = on
REDUCED_MOTION_STORAGE_KEY = "aftermath-reduced-motion"
HIT_EFFECT_MS = 900
EVENT_HIT_EFFECT = {
    "flood": "ripple",
    "heatwave": "heat",
    "heat_mortality": "heat",
    "storm": "storm",
    "supply_chain": "dim",
    "infrastructure_failure": "spark",
    "civil_unrest": "shudder",
}
HIT_EFFECT_CLASSES = tuple(f"hit-{name}" for name in sorted(set(EVENT_HIT_EFFECT.values())))


def effects_enabled():
    """True unless the player switched the shake-and-flash effects off, or Reduce motion is on."""
    try:
        if localStorage.getItem(REDUCED_MOTION_STORAGE_KEY) == "true":
            return False
        return localStorage.getItem(EFFECTS_STORAGE_KEY) != "false"
    except Exception:
        return False


def hit_effect_class(event_type):
    return f"hit-{EVENT_HIT_EFFECT.get(event_type, 'dim')}"


def hit_number_text(entry):
    """The big number for the last event: its icon, the damage and a word, so it never relies on colour."""
    return f"{EVENT_ICON[entry['type']]} \u2212{entry['damage']:.0f} damage"


def render_hit_number():
    element = _el("hit-number")
    if element is None:
        return
    entry = runstate.run.event_log[-1] if runstate.run.event_log else None
    element.hidden = entry is None
    if entry is None:
        element.innerText = ""
        element.className = "hit-number"
        return
    element.innerText = hit_number_text(entry)
    element.className = f"hit-number event-category--{EVENT_CATEGORY[entry['type']]}"


def _flash_if_present(element_id, duration_ms, css_class):
    if _el(element_id) is not None:
        _flash_element(element_id, duration_ms, css_class)


def play_hit_effect(entry):
    """Plays the effect for a just-resolved event (no-op when effects are off)."""
    if not effects_enabled():
        return False
    _flash_if_present("settlement-visual", HIT_EFFECT_MS, hit_effect_class(entry["type"]))
    _flash_if_present("hit-number", HIT_EFFECT_MS, "hit-number--pop")
    return True
