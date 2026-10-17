"""The tick loop and on_advance_season(): the one place a season actually happens."""

import advisors
import challengerun
import challenges
import consulting
import dynasty
import eastereggs
import founding
import neighbours
import rewind
import sandbox
import sim
import statlog
import sustainability
import techdebt
import trajectory

import continuum_runstate as runstate
from continuum_achievements import _check_new_achievements_for_toast
from continuum_base import MAX_SEASONS_PER_TICK, _resting, current_effects
from continuum_beyond import _beyond_after_season
from continuum_challenge import _finish_challenge_run
from continuum_citizens import _citizens_after_season, _neighbours_allowed, _player_era_index
from continuum_clock import render_clock, season_length
from continuum_dynasty import _dynasty_start_message
from continuum_extras import _bank_if_collapsed
from continuum_founders import _tick_play_time
from continuum_orders import _run_standing_orders
from continuum_peers import _notify_peers
from continuum_techdebt import _easter_egg

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

def tick_clock(dt):
    """Advances the clock by `dt` real seconds. Returns how many seasons
    passed (0 while paused, in a Look Back, or for a bad `dt`)."""
    if runstate.sim_speed == 0 or runstate.campaign.revisiting:
        return 0
    if not isinstance(dt, (int, float)) or isinstance(dt, bool) or dt != dt or dt <= 0:
        return 0
    runstate.season_progress += min(float(dt), 1.0) * runstate.sim_speed
    passed = 0
    while runstate.season_progress >= season_length() and passed < MAX_SEASONS_PER_TICK:
        runstate.season_progress -= season_length()
        on_advance_season()
        passed += 1
    if passed == MAX_SEASONS_PER_TICK and runstate.season_progress >= season_length():
        runstate.season_progress = 0.0
    render_clock()
    return passed


def on_advance_season(event=None):
    # K-17: remember the world just before the season runs, so it can be unwound once.
    runstate._rewind_snapshot = rewind.capture(runstate.campaign)
    effects = current_effects()
    # O-7: a pending founder's legacy arrives with the opening season, once.
    delivered = founding.apply_legacy(runstate.campaign, consulting.get(runstate.campaign.ui) is not None)
    if delivered is not None:
        legacy = founding.LEGACIES[delivered["id"]]
        runstate.chronicle.log_challenge(
            runstate.state.season,
            runstate.state.era,
            f"Founder's legacy arrives: {legacy['label']} ({founding.bonus_text(delivered)}). {legacy['blurb']}",
        )
    # K-2: the Dynasty's starting perks arrive with the opening season, once (they rest in a
    # challenge run or consulting case, and the turn is used up either way).
    if runstate.campaign.revisiting is None:
        bonuses = dynasty.apply_start(runstate.campaign, _resting())
        if bonuses:
            runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, _dynasty_start_message(bonuses))
            effects = current_effects()
    runstate.found_status = ""
    report = runstate.state.advance_season(effects)
    if runstate.sandbox_active:  # Z-18: resources are not binding and the settlement cannot collapse
        sandbox.relief(runstate.state, effects)
    if runstate.campaign.revisiting is None:
        settle = techdebt.after_season(runstate.campaign.ui, runstate.state)
        if settle["refactored"]:
            _easter_egg(eastereggs.on_refactor(runstate.campaign.ui, runstate.state))
            runstate.chronicle.log_challenge(
                runstate.state.season,
                runstate.state.era,
                f"Refactor season complete: technical debt eased from {settle['before'] * 100:.0f}% "
                f"to {settle['after'] * 100:.0f}%. The crews spent the season rewriting, not producing.",
            )
        elif settle["warn"]:
            runstate.chronicle.log_challenge(
                runstate.state.season,
                runstate.state.era,
                "Technical debt has passed 50%: the old shortcuts are failing more often and upkeep is "
                "climbing. A refactor season would pay it down.",
            )
    runstate.state.record_score(sustainability.score(runstate.state, effects))
    if runstate.campaign.revisiting is None:
        _beyond_after_season(sustainability.score(runstate.state, effects))
    if runstate.campaign.revisiting is None:
        run_result = challengerun.after_season(runstate.campaign, sustainability.score(runstate.state, effects))
        if run_result is not None:
            _finish_challenge_run(run_result)
    trajectory.record(runstate.state, report, sustainability.livability(runstate.state, effects) * 100.0)
    if runstate.campaign.revisiting is None:
        # K-27/K-16/K-18/K-14: one row of stats per completed season (statlog.py).
        statlog.record(runstate.campaign.ui, runstate.state, effects, report, len(runstate.tree.researched))
        _notify_peers()
    before = consulting.get(runstate.campaign.ui)
    after = consulting.step(runstate.campaign, effects)
    if after is not None and after["result"] and (before is None or before["result"] is None):
        runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, consulting.status_text(after, runstate.state))
    event = challenges.after_season(runstate.state, report, effects)
    if event is not None:
        runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, event["text"])
    runstate.chronicle.check_population(runstate.state)
    runstate.chronicle.check_livability(runstate.state, effects)
    if runstate.campaign.revisiting is None:
        _run_standing_orders(effects)
    if runstate.campaign.revisiting is None:
        digital_rows = sum(
            1 for row in statlog.rows(runstate.campaign.ui) if int(statlog.value(row, "era")) == sim.era_index(eastereggs.DIGITAL_ERA)
        )
        _easter_egg(eastereggs.on_season(runstate.campaign.ui, runstate.state, digital_rows))
        # K-8: the council's advice for the season that just ended is judged now; new advice is
        # issued when the panel next draws (so a closed council costs nothing).
        advisors.settle(runstate.campaign.ui, runstate.state, current_effects())
    if runstate.campaign.revisiting is None:
        _citizens_after_season(report)
        if _neighbours_allowed():
            for text in neighbours.after_season(runstate.campaign.ui, runstate.state.season, runstate.state.resources, _player_era_index()):
                runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, text)
        _bank_if_collapsed()
    _tick_play_time()
    render()
    _check_new_achievements_for_toast()
