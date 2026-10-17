"""Plot-growth credit: which practice surfaces grow plots, the 'Plot growth credited' lines and the markers on each panel.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import re

import champ_runstate as runstate
from champ_model import state
from champ_util import _element
from champ_watering import water_plot


# ---------------------------------------------------------------------------
# Which activities grow plots
# ---------------------------------------------------------------------------
# Every question screen says, in a small text marker, whether it grows plots
# and how, and every activity that credits plots says what it credited at the
# end of a session ("watered N plots, nudged M"). A game score never grows a
# plot by itself: crediting goes through water_plot() only, a plot's stage
# never goes down, and a wrong answer changes nothing.
_RULE_TIP = (
    "The first correct answer for a plot each in-game day waters it fully: its interval, ease, "
    "streak and growth stage all update, exactly like watering it on the farm. Later correct "
    "answers for the same plot that day only nudge its next review a day later. A wrong answer "
    "changes nothing, and a stage never goes down."
)
_WATERS = ("review", "Grows plots: waters, then nudges")
GROWTH_INFO = {
    "practice": ("full", "Grows plots: waters, then nudges", _RULE_TIP),
    "review": (_WATERS[0], _WATERS[1], _RULE_TIP),
    "proficiency": (
        _WATERS[0],
        _WATERS[1],
        "The test asks about real plots, so it counts like Review. " + _RULE_TIP,
    ),
    "placement": (
        "apply",
        "Grows plots only if you apply the result",
        "Answering changes no plot. If you press Apply, plots in the weeks you passed that were never watered become Sprouts (never higher, and nothing is lowered).",
    ),
    "blitz": (
        _WATERS[0],
        _WATERS[1],
        "Each question is about one real plot from weeks 1-11; the line under the question names it. " + _RULE_TIP,
    ),
    "racer": (
        _WATERS[0],
        _WATERS[1],
        "Each question is about one real grammar plot from weeks 12-15; the line under the question names it. " + _RULE_TIP,
    ),
    "sprint": (
        _WATERS[0],
        _WATERS[1],
        "Each question is about one real passé composé plot (weeks 21-23); the line under the question names it. " + _RULE_TIP,
    ),
    "boutique": (
        _WATERS[0],
        _WATERS[1],
        "A correct sale waters the plots for the garment and the colour you picked. " + _RULE_TIP,
    ),
    "cafe": (
        _WATERS[0],
        _WATERS[1],
        "A correct order waters the plot for that dish (and the passé composé plot in a twist round). " + _RULE_TIP,
    ),
    "pairs": (
        _WATERS[0],
        _WATERS[1],
        "Every correct pair waters the plot behind that word or phrase (weeks 12-23). " + _RULE_TIP,
    ),
    "gaps": (
        _WATERS[0],
        _WATERS[1],
        "Each gap is about one real grammar plot (weeks 1-11 and 16-20); the line under it names the plot. " + _RULE_TIP,
    ),
    "listenpick": (
        _WATERS[0],
        _WATERS[1],
        "Each sound is one real vocabulary, phrase or pronunciation plot; the line under the question names it. " + _RULE_TIP,
    ),
    "wordorder": (
        _WATERS[0],
        _WATERS[1],
        "Each sentence is an example from one real grammar plot; a correct order waters that plot. " + _RULE_TIP,
    ),
    "amis": (
        "none",
        "Does not grow plots",
        "The words come from a live list of false friends, not from your farm, so there is no plot to grow. Your answers still count toward your practice score. Plots whose French word is on the list carry a small false-friend badge on the farm.",
    ),
    "bonus": (
        "none",
        "Does not grow plots",
        "These sentences are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "builder": (
        "none",
        "Does not grow plots",
        "These sentences are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "conversation": (
        "none",
        "Does not grow plots",
        "These dialogue lines are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "listening": (
        "none",
        "Does not grow plots",
        "These sentences are hand-written, so they are not plots on the farm and there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "liaison": (
        "none",
        "Does not grow plots",
        "These sound-rule questions are hand-written and are not tied to any plot, so there is nothing to grow. Your answers still count toward your practice score.",
    ),
    "formats": (
        "none",
        "Does not grow plots",
        "These exam-format questions are made from patterns (times, short texts, rewriting rules), not from plots on the farm, so there is nothing to grow. Your answers still count toward your practice score, one entry for each format.",
    ),
}
GROWTH_SURFACES = (
    "review", "proficiency", "blitz", "racer", "boutique", "cafe", "sprint",
    "pairs", "gaps", "listenpick", "wordorder",
)
growth_credit = {surface: {"full": 0, "nudge": 0} for surface in GROWTH_SURFACES}
_credit_seen = {surface: {} for surface in GROWTH_SURFACES}


def growth_marker(key):
    """(kind, text, tooltip) for an activity's marker."""
    return GROWTH_INFO[key]


def render_growth_markers():
    for key, (kind, text, tip) in GROWTH_INFO.items():
        element = _element(f"growth-marker-{key}")
        element.innerText = text
        element.title = tip
        element.setAttribute("aria-label", f"{text}. {tip}")
        element.setAttribute("data-growth", kind)


def reset_growth_credit(surface):
    if surface in growth_credit:
        growth_credit[surface] = {"full": 0, "nudge": 0}
        _credit_seen[surface] = {}


def _note_credit(surface, plot, kind):
    """Count a plot once per session: 'watered N plots, nudged M' are distinct
    plots, not answers."""
    if surface not in growth_credit or kind not in growth_credit[surface]:
        return
    seen = _credit_seen[surface]
    if plot.plot_id in seen:
        return
    seen[plot.plot_id] = kind
    growth_credit[surface][kind] += 1


def credit_correct(plot, surface):
    """A correct answer on a real plot in a review-style session, a proficiency
    test or an arcade game: water it (or nudge it), and remember which for the
    end-of-session line. Returns WATER_FULL, WATER_NUDGE or None."""
    kind = water_plot(plot)
    if kind is not None:
        _note_credit(surface, plot, kind)
    return kind


def credit_review_plot(plot, surface):
    """A correct answer on a real plot in Review or a proficiency test."""
    return credit_correct(plot, surface)


def credit_game_plot(plot, surface):
    """An arcade game's correct answer on a real plot (it waters, or nudges)."""
    return credit_correct(plot, surface)


def credit_game_plot_id(plot_id, surface):
    return credit_game_plot(state.plots_by_id.get(plot_id), surface)


def _plot_by_fr():
    """Lowercased French text (parentheses dropped, each side of a slash) ->
    the vocab plot that holds it, for the shop games' item orders."""
    if runstate._plot_by_fr_index is None:
        index = {}
        for plot in state.plots:
            if plot.topic_type == "grammar":
                continue
            for item in plot.items:
                fr = item.get("fr")
                if not fr:
                    continue
                for part in re.sub(r"\([^)]*\)", "", fr).split(" / "):
                    key = " ".join(part.split()).lower()
                    if key:
                        index.setdefault(key, plot)
        runstate._plot_by_fr_index = index
    return runstate._plot_by_fr_index


def plot_for_fr(fr):
    """The plot behind a French text; a "a / b" pair (two names for one dish,
    say) finds the plot of either side."""
    index = _plot_by_fr()
    key = " ".join(str(fr).split()).lower()
    if key in index:
        return index[key]
    for part in re.sub(r"\([^)]*\)", "", str(fr)).split(" / "):
        found = index.get(" ".join(part.split()).lower())
        if found is not None:
            return found
    return None


def credit_game_item(fr, surface):
    """Credit the plot behind a shop-game item's French text, if there is one."""
    return credit_game_plot(plot_for_fr(fr), surface)


def growth_credit_text(surface):
    counts = growth_credit.get(surface)
    if counts is None:
        return ""
    parts = []
    if counts["full"]:
        parts.append(f"watered {counts['full']} plot{'s' if counts['full'] != 1 else ''}")
    if counts["nudge"]:
        parts.append(
            f"nudged {counts['nudge']}" if counts["full"] else
            f"nudged {counts['nudge']} plot{'s' if counts['nudge'] != 1 else ''}"
        )
    if parts:
        return "Plot growth credited: " + ", ".join(parts) + "."
    return "Plot growth credited: none this session."
