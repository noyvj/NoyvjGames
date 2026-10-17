"""Tipping cascades, the carbon bank, supply crates, shared research, framings, the long game and the thaw forecast."""

import math

from js import document

import thaw_runstate as runstate
from thaw_model import deg, region, region_b, region_c, region_d
from thaw_rules import (
    CASCADE_BUMP, CASCADE_CHANCE, FORECAST_MAX, FORECAST_MIN, FORECAST_TOLERANCE, LONG_GAME_INCOME_SCALE,
    LONG_GAME_WARMING_SCALE,
)
from thaw_sciencelog import _log_action


# ===========================================================================
# G5: the tipping cascade. When Region A or Region B tips into melt, there is
# a small chance the shock spreads down the chain (A to B, B to C) as a
# one-time CASCADE_BUMP of warming. The game has no random number source
# (every round is reproducible), so the "chance" is a fixed pseudo-random
# roll derived from the round and source region: the same run always
# cascades the same way, but a player cannot predict or reroll it. The bump
# lands on both the receiving region's temperature and its own
# counterfactual, because no intervention could have prevented it (so
# "degrees saved" is unaffected). The chain is deliberately one-way and
# never reaches Region A or Region D, keeping D identical to A's
# counterfactual.
# ===========================================================================


def cascade_roll(source_label, round_number):
    """A deterministic roll in [0, 1) for one (source region, round) pair."""
    mixed = (round_number * 2654435761 + ord(source_label) * 40503) % (2 ** 32)
    return (mixed % 1000) / 1000.0


def apply_tipping_cascades():
    """Called once per Advance Round after every region has advanced. A
    source region that started melting this very round may cascade onto
    the next region in the chain."""
    for label, source, target in (("A", region, region_b), ("B", region_b, region_c)):
        if "melt" not in source.round_events:
            continue
        if cascade_roll(label, source.round_number - 1) >= CASCADE_CHANCE:
            continue
        target.temperature += CASCADE_BUMP
        target.counterfactual_temperature += CASCADE_BUMP
        if target.temperature_history:
            target.temperature_history[-1] += CASCADE_BUMP
        target.round_events.append("cascade")


# ===========================================================================
# G3: the permafrost carbon bank. A region that keeps warming acceleration
# under CARBON_BANK_MAX_ACCELERATION while actively protecting its peat
# (at least one Preservation unit) banks one carbon credit per round into a
# shared bank. CARBON_CREDITS_PER_GRANT credits can be spent for a one-time
# CARBON_GRANT_FUNDS grant to any one of Regions A-C: sustained good play in
# one place funds a push somewhere else. Region D never earns or receives.
# ===========================================================================
CARBON_BANK_MAX_ACCELERATION = 1.2
CARBON_CREDITS_PER_GRANT = 10
CARBON_GRANT_FUNDS = 120.0
CARBON_BANK_CAP = 50


def _carbon_target(key):
    return {"a": region, "b": region_b, "c": region_c}[key]


def bank_carbon_credits():
    """Called once per Advance Round after the regions have advanced.
    Returns how many credits this round added (before the cap)."""
    earned = 0
    for r in (region, region_b, region_c):
        if r.capacity["preserve"] >= 1 and r._investment_acceleration_factor() <= CARBON_BANK_MAX_ACCELERATION:
            earned += 1
    runstate.carbon_bank = min(CARBON_BANK_CAP, runstate.carbon_bank + earned)
    return earned


def spend_carbon_credits(key):
    """Spends one grant's worth of credits to give region `key` extra funds.
    Returns True if it happened."""
    if key not in ("a", "b", "c") or runstate.carbon_bank < CARBON_CREDITS_PER_GRANT:
        return False
    runstate.carbon_bank -= CARBON_CREDITS_PER_GRANT
    _carbon_target(key).funds += CARBON_GRANT_FUNDS
    _log_action(key.upper(), f"a carbon-bank grant of {CARBON_GRANT_FUNDS:.0f} funds was spent.")
    return True


def render_carbon_bank():
    document.getElementById("carbon-bank-display").innerText = (
        f"Carbon bank: {runstate.carbon_bank} credit{'s' if runstate.carbon_bank != 1 else ''} "
        f"(cap {CARBON_BANK_CAP}). A region earns 1 a round by holding warming under "
        f"{CARBON_BANK_MAX_ACCELERATION}x with Preservation in place; "
        f"{CARBON_CREDITS_PER_GRANT} credits fund a one-time +{CARBON_GRANT_FUNDS:.0f} grant."
    )
    for key in ("a", "b", "c"):
        document.getElementById(f"carbon-bank-{key}-button").disabled = runstate.carbon_bank < CARBON_CREDITS_PER_GRANT


# ===========================================================================
# GG-22: supply crates. After every sixth round a crate arrives and waits (it never expires). Opening
# one gives a perk that is fixed in advance: crates cycle Preserve unit, Monitor unit, funds box, and the
# page always says what the next one holds and which region it would go to. Nothing about it is random.
# ===========================================================================
CRATE_EVERY = 6
CRATE_FUNDS = 50.0
CRATE_PERKS = (  # (key, what it is, plural-free shelf name)
    ("preserve", "a Preserve unit", "Preserve"),
    ("monitor", "a Monitor unit", "Monitor"),
    ("funds", f"{CRATE_FUNDS:.0f} funds", "funds"),
)
CRATE_MAX = 100000


def crate_perk(number):
    """The perk of the `number`th crate (1-based): a fixed rotation."""
    return CRATE_PERKS[(number - 1) % len(CRATE_PERKS)]


def crates_ready():
    return runstate.crates_delivered - runstate.crates_opened


def next_crate_round():
    """The round number at which the next crate arrives (a crate lands when the round counter reaches
    7, 13, 19 ...)."""
    return ((region.round_number - 1) // CRATE_EVERY + 1) * CRATE_EVERY + 1


def _crate_target(kind):
    """The managed region a perk goes to: the one with the least dampening (units) or the fewest funds
    (a funds box); ties go to the earlier region, A first."""
    managed = (("A", region), ("B", region_b), ("C", region_c))
    if kind == "funds":
        return min(managed, key=lambda pair: pair[1].funds)
    return min(managed, key=lambda pair: pair[1].feedback_dampening_fraction())


def deliver_crate_if_due():
    """Called once per Advance Round after the rounds have moved: a crate lands when the round counter
    reaches 7, 13, 19 ... Returns True when one arrived."""
    if region.round_number <= 1 or (region.round_number - 1) % CRATE_EVERY != 0:
        return False
    if runstate.crates_delivered >= CRATE_MAX:
        return False
    runstate.crates_delivered += 1
    _log_action("A", "a supply crate arrived at the station (open it from the Supply crates box).")
    return True


def open_crate():
    """Opens the oldest waiting crate and applies its perk. Returns (label, text) or None when no crate waits."""
    if crates_ready() <= 0:
        return None
    key, what, _shelf = crate_perk(runstate.crates_opened + 1)
    label, target = _crate_target(key)
    if key == "funds":
        target.funds += CRATE_FUNDS
    else:
        target.capacity[key] += 1
        target.just_invested_intervention = True
    runstate.crates_opened += 1
    runstate._crate_just_opened = key
    text = f"supply crate opened: {what} for Region {label}."
    _log_action(label, text)
    return label, text


def crate_shelf_counts():
    """How many of each perk have been opened so far, in rotation order."""
    counts = {key: 0 for key, _w, _s in CRATE_PERKS}
    for number in range(1, runstate.crates_opened + 1):
        counts[crate_perk(number)[0]] += 1
    return counts


def crate_text():
    """Short readout: crates waiting, what the next one holds and where it would go, and the shelf."""
    ready = crates_ready()
    key, what, _shelf = crate_perk(runstate.crates_opened + 1)
    label, _target = _crate_target(key)
    if ready > 0:
        first = f"{ready} supply crate{'s' if ready != 1 else ''} waiting."
        second = f"The next one holds {what}, for Region {label} right now."
    else:
        first = "No supply crate waiting."
        second = f"The next arrives in round {next_crate_round()} and holds {what} (Region {label} right now)."
    counts = crate_shelf_counts()
    shelf = ", ".join(f"{counts[k]} {shelf_name}" for k, _w, shelf_name in CRATE_PERKS)
    return f"{first} {second} Opened so far: {runstate.crates_opened} ({shelf})."


def render_crate():
    document.getElementById("crate-display").innerText = crate_text()
    button = document.getElementById("crate-open-button")
    button.disabled = crates_ready() <= 0
    button.innerText = "Open crate" if crates_ready() <= 1 else f"Open crate ({crates_ready()} waiting)"
    visual = document.getElementById("crate-visual")
    visual.className = "crate-visual" + (" crate-opening" if runstate._crate_just_opened else "") + (
        " crate-waiting" if crates_ready() > 0 else ""
    )
    runstate._crate_just_opened = None


# ===========================================================================
# G17: "four regions, one story". A light narrative thread tying the four
# regions together through one shared research station: every Monitoring &
# Response unit funded in Regions A, B or C feeds a common pool of
# observations, and as the pool grows the story advances a chapter. Region D
# (the unmanaged what-if) contributes nothing but is written into the final
# chapter as the control every paper cites. Derived entirely from live
# capacity -- no state of its own, nothing to save -- and it never feeds
# back into any region's mechanics, so the four stay independent.
# ===========================================================================
SHARED_RESEARCH_CHAPTERS = (  # (units needed, title, text), ascending
    (
        0,
        "The shared station",
        "Four regions, one research station. Every Monitoring & Response unit any "
        "region funds adds to a common pool of observations.",
    ),
    (
        3,
        "Chapter 1 \u2014 The network hums",
        "With a few monitors reporting in, the station can line the regions up "
        "side by side: permafrost thaw in one place turns out to rhyme with the others.",
    ),
    (
        8,
        "Chapter 2 \u2014 The joint paper",
        "Enough shared data to publish. The paper shows the same feedback loop at work "
        "in every region, and that early, steady investment blunts it in each one.",
    ),
    (
        15,
        "Chapter 3 \u2014 A shared warning system",
        "The network becomes an early-warning system. Region D, the one region nobody "
        "funded, is the control every paper cites: proof of what the others avoided.",
    ),
)


def shared_research_units():
    """Total Monitoring & Response capacity across the three managed regions."""
    return sum(r.capacity["monitor"] for r in (region, region_b, region_c))


def shared_research_chapters_reached():
    units = shared_research_units()
    return [c for c in SHARED_RESEARCH_CHAPTERS if units >= c[0]]


def render_shared_research():
    units = shared_research_units()
    reached = shared_research_chapters_reached()
    upcoming = [c for c in SHARED_RESEARCH_CHAPTERS if c[0] > units]
    if upcoming:
        progress = f"Shared observations: {units} monitoring units (next chapter at {upcoming[0][0]})."
    else:
        progress = f"Shared observations: {units} monitoring units \u2014 every chapter unlocked."
    document.getElementById("shared-research-progress").innerText = progress
    document.getElementById("shared-research-story").innerHTML = "".join(
        f"<li><strong>{title}</strong> {text}</li>" for _, title, text in reached
    )


# ===========================================================================
# G29: the "global vs. regional" framing toggle. The same three regions and
# the same numbers, reframed: "regional" reads them as the player's own
# region's choices; "global" reads Regions A-C together as one aggregate
# planet. Presentation only -- no mechanic reads it, and Region D (the
# unmanaged what-if) is never part of either summary.
# ===========================================================================
FRAMINGS = ("regional", "global")


def framing_summary_text():
    if runstate.framing == "global":
        regions = [region, region_b, region_c]
        mean_temp = sum(r.temperature for r in regions) / len(regions)
        mean_saved = sum(r.temperature_saved() for r in regions) / len(regions)
        melting = sum(1 for r in regions if r.is_melting())
        return (
            f"Global picture, Regions A\u2013C together: {deg(mean_temp, plus=True)} average warming, "
            f"{melting} of {len(regions)} regions melting, {deg(mean_saved)} saved on average "
            f"versus no action."
        )
    return (
        f"Your region's choices (Region A): {deg(region.temperature, plus=True)} warming, "
        f"{deg(region.temperature_saved())} saved versus no action."
    )


def _render_framing():
    document.getElementById("framing-toggle-button").innerText = (
        "Framing: global aggregate" if runstate.framing == "global" else "Framing: my region's choices"
    )
    document.getElementById("framing-summary").innerText = framing_summary_text()


# ===========================================================================
# G9: the long-game toggle. Only available before any region has played a
# round, since switching mid-run would change the meaning of every number
# already on screen.
# ===========================================================================
def can_toggle_long_game():
    return all(r.round_number == 1 for r in (region, region_b, region_c, region_d))


def set_long_game(enabled):
    if not can_toggle_long_game():
        return False
    if enabled and runstate.hold_the_line:
        return False
    runstate.long_game = bool(enabled)
    return True


def unranked_reasons():
    """FY-32: the custom rules that change the numbers of a run (the long game and Hold the Line), which
    keep it out of the community comparison. Hard mode only hides previews and a custom preset is only a
    shortcut, so neither one counts."""
    reasons = []
    if runstate.long_game:
        reasons.append("the long game")
    if runstate.hold_the_line:
        reasons.append("Hold the Line")
    return reasons


def run_unranked():
    return bool(unranked_reasons())


def unranked_note():
    """FY-32: one sentence saying a run is unranked and why; empty for a standard run."""
    reasons = unranked_reasons()
    if not reasons:
        return ""
    return (
        f"Unranked run: {' and '.join(reasons)} change{'s' if len(reasons) == 1 else ''} the rules, so this "
        "run is kept out of the community comparison. Start a standard game to be compared."
    )


def long_game_text():
    if runstate.long_game:
        return (
            f"Long game is on: warming runs at {LONG_GAME_WARMING_SCALE * 100:.0f}% speed and Output pays "
            f"{LONG_GAME_INCOME_SCALE * 100:.0f}% as much, so the full trajectory takes about "
            f"{1 / LONG_GAME_WARMING_SCALE:.1f}x as many rounds. This makes it an unranked run: it is kept out of "
            "the community comparison."
        )
    return "Standard game. A long game stretches the whole trajectory over roughly two and a half times as many rounds."


def _render_long_game():
    button = document.getElementById("long-game-toggle-button")
    button.innerText = "Long game: on" if runstate.long_game else "Long game: off"
    button.disabled = not can_toggle_long_game() or (runstate.hold_the_line and not runstate.long_game)
    document.getElementById("long-game-display").innerText = long_game_text() + (
        "" if can_toggle_long_game() else " (Locked once the first round has been played.)"
    )


# ===========================================================================
# G27: the "thaw forecast" mini-game. Before advancing, the player may lock
# in a guess of Region A's temperature after the coming round; on advance
# the guess is scored against the real number. Purely cosmetic: a running
# record and a title, no effect on any mechanic. The game is deterministic,
# so a careful player can hit every forecast from the displayed warming
# rate alone -- deliberately, since the point is engaging with that number
# (restoration and rescue make the arithmetic a little less obvious).
# ===========================================================================
FORECAST_TITLES = (  # (min attempts, min hit rate, title), best first
    (10, 0.75, "Master Forecaster"),
    (5, 0.5, "Seasoned Forecaster"),
    (1, 0.0, "Apprentice Forecaster"),
)


def forecast_title():
    if runstate.forecast_total <= 0:
        return None
    rate = runstate.forecast_hits / runstate.forecast_total
    for min_attempts, min_rate, title in FORECAST_TITLES:
        if runstate.forecast_total >= min_attempts and rate >= min_rate:
            return title
    return None


def lock_forecast(raw):
    """Parses and stores a guess. Returns True if it was accepted."""
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return False
    if not math.isfinite(value) or not (FORECAST_MIN <= value <= FORECAST_MAX):
        return False
    runstate.forecast_guess = value
    return True


def resolve_forecast():
    """Scores a locked-in guess against Region A's temperature now (call
    right after the region has advanced). No guess, no-op."""
    if runstate.forecast_guess is None:
        return
    actual = region.temperature
    hit = abs(actual - runstate.forecast_guess) <= FORECAST_TOLERANCE
    runstate.forecast_miss_total += abs(actual - runstate.forecast_guess)
    runstate.forecast_total += 1
    if hit:
        runstate.forecast_hits += 1
    runstate.forecast_last = (runstate.forecast_guess, actual, hit)
    runstate.forecast_guess = None


def _render_forecast():
    status = document.getElementById("forecast-status")
    record = document.getElementById("forecast-record")
    if runstate.forecast_guess is not None:
        status.innerText = f"Forecast locked in: {deg(runstate.forecast_guess, plus=True)} after the next round."
    elif runstate.forecast_last is not None:
        guess, actual, hit = runstate.forecast_last
        verdict = "Nailed it" if hit else "Not quite"
        status.innerText = (
            f"{verdict} \u2014 you forecast {deg(guess, plus=True)}, the real figure was {deg(actual, plus=True)}."
        )
    else:
        status.innerText = (
            f"Optional: forecast Region A's temperature after the next round "
            f"(within {deg(FORECAST_TOLERANCE)} counts)."
        )
    title = forecast_title()
    if title is None:
        record.innerText = ""
        record.hidden = True
    else:
        record.innerText = f"{title} \u2014 {runstate.forecast_hits} of {runstate.forecast_total} forecasts on target."
        record.hidden = False
    document.getElementById("forecast-lock-button").innerText = (
        "Change forecast" if runstate.forecast_guess is not None else "Lock in forecast"
    )
