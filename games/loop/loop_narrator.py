"""The narrator ticker (GH-19): topic and line choice, session history."""

import html

from js import document

import loop_runstate as runstate
from loop_rules import RIVAL_NAME, rival_funds_after


# ===========================================================================
# Oct 11 batch: GH-19 narrator ticker, H-3 multi-cycle planner, H-8 Assist mode,
# H-26 ring-node sparklines, GH-28 / H-7 ghost run codes and comparison cards.
# Pure functions of state plus a few module-level lists, so they are directly testable.
# ===========================================================================

# ---- GH-19 snarky supply-chain narrator -------------------------------------------------------------------------
NARRATOR_HISTORY_MAX = 4  # the line in force plus the few before it
narrator_history = []  # newest last; a ticker for this session only, never saved

NARRATOR_LINES = {
    "opening": [
        "Day one. The chain is a perfectly straight line and it is extremely pleased with itself.",
        "A fresh chain. Everything it makes is already planning to become somebody's rubbish.",
        "Nothing bought yet. The mine is thrilled. The mine is always thrilled.",
    ],
    "idle": [
        "Cycle {n} and still nothing bought. The raw material pile is not going to dig itself, but it will keep trying.",
        "{extracted} units dug up this cycle. The planet has filed a polite complaint.",
        "Still a straight line. Straight lines are tidy. They are also how this whole mess started.",
    ],
    "started": [
        "Some of it comes back now ({pct}%). The bin is mildly suspicious.",
        "{pct}% circular. The first stuff is returning from the dead, a little embarrassed.",
        "A start: {pct}% loops home instead of landing in a pit. Keep going.",
    ],
    "progress": [
        "{pct}% circular. The recycling lorry has started waving at the repair van.",
        "{pct}% looped. Repair, reuse and recycling are finally on speaking terms.",
        "{pct}% and climbing. The landfill is looking at its calendar nervously.",
    ],
    "almost": [
        "{pct}% circular. The mine has begun updating its CV.",
        "So nearly closed ({pct}%). The last few units are hiding. Find them.",
        "{pct}% looped. Even the discard bin is starting to feel redundant.",
    ],
    "damage": [
        "Damage at {damage}% and the loop still open. Raw material is getting pricey, and the mine knows it.",
        "{damage}% damage. Every dug-up unit now costs more, which the mine finds flattering.",
        "The damage meter is at {damage}%. Nobody is blaming you. The meter, however, is keeping notes.",
    ],
    "shock": [
        "The market is having a moment. A tidy loop barely notices; a straight line really does.",
        "Shock in the news: the closed loop shrugs, the straight line weeps into its invoices.",
        "Market chaos! Good thing your supply is mostly your own.",
    ],
    "closed": [
        "Loop closed. Nothing new dug up this cycle. The mine has gone for a long lunch.",
        "Zero extraction. Your waste has just been promoted to raw material.",
        "A closed loop. The discard bin has nothing to do and is taking it personally.",
    ],
    "streak": [
        "{streak} perfect cycles in a row. The mine is writing you a stern letter.",
        "Streak of {streak}. The bin has stopped answering your calls.",
        "{streak} cycles with nothing dug up. This is what showing off looks like.",
    ],
    "rival_ahead": [
        "{rival} is ahead on funds, mostly because it is digging faster than it should. Hold your nerve.",
        "{rival} leads for now. Its raw material bill is growing, though. Patience.",
    ],
    "rival_behind": [
        "You are ahead of {rival}. It is still extracting. It does not know any other way.",
        "{rival} is behind you now. Its costs are doing the talking.",
    ],
}


def narrator_topic():
    """Which kind of comment fits the chain right now (the first rule that matches wins)."""
    fraction = runstate.chain.circular_fraction_this_cycle()
    done = runstate.chain.cycle_number - 1
    if runstate.chain.is_loop_closed():
        return "streak" if runstate.chain.closed_loop_streak >= 2 else "closed"
    if runstate.chain.market_shocks and (runstate.chain.active_shock() is not None or runstate.chain.next_shock() is not None):
        return "shock"
    if done == 0 and runstate.chain.lifetime_investment_spend == 0:
        return "opening"
    if runstate.chain.rival_on and done > 0:
        return "rival_ahead" if rival_funds_after(done) > runstate.chain.funds else "rival_behind"
    if runstate.chain.damage_fraction() >= 0.5 and fraction < 0.5:
        return "damage"
    if fraction >= 0.75:
        return "almost"
    if fraction >= 0.25:
        return "progress"
    if fraction > 0:
        return "started"
    return "idle"


def narrator_line():
    """The narrator's comment for the chain as it stands. Fixed by the state (no randomness): the variant is picked
    from the cycle number, so the same position always reads the same."""
    topic = narrator_topic()
    variants = NARRATOR_LINES[topic]
    template = variants[(runstate.chain.cycle_number + len(topic)) % len(variants)]
    return template.format(
        n=runstate.chain.cycle_number,
        extracted=f"{runstate.chain.new_extraction_needed():.0f}",
        pct=f"{runstate.chain.circular_fraction_this_cycle() * 100:.0f}",
        damage=f"{runstate.chain.damage_fraction() * 100:.0f}",
        streak=runstate.chain.closed_loop_streak,
        rival=RIVAL_NAME,
    )


def record_narrator(line):
    """Files `line` at the end of the ticker when it differs from the last one."""
    if not narrator_history or narrator_history[-1] != line:
        narrator_history.append(line)
        del narrator_history[:-NARRATOR_HISTORY_MAX]


def render_narrator():
    line = narrator_line()
    record_narrator(line)
    document.getElementById("narrator-line").innerText = line
    older = list(reversed(narrator_history[:-1]))
    document.getElementById("narrator-history").innerHTML = "".join(f"<li>{html.escape(item)}</li>" for item in older)
