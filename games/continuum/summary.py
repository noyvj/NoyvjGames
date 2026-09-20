"""Continuum — K5: the civilization summary report engine.

planning/TODO.md's K5: "a summary screen/panel shown when the player
reaches the end state (or opts to view it), recapping key stats across all
seven eras played." Continuum has no forced end state by design — Space
Age is the last era `transition.py` knows how to leave
(`transition.next_era_for("space")` returns `None`), but nothing stops the
player from continuing to play there indefinitely, the same "no hard
fail/win state" shape Grid's own CLAUDE.md documents for its own Run
Summary panel. Per K5's own instruction ("if there's no explicit end
state... make it accessible as an on-demand summary/report panel
instead"), this is exactly that: an on-demand toggle panel, the same
hidden-until-opened idiom the achievements/changelog panels already use —
not a forced end screen.

A pure function of a `Campaign`'s own state (its live city, its era
snapshots, its score history) — no DOM code, matching every other engine
module's "pure function of state" rule (`visual.py` is the closest
analogue: same statelessness, same plain-dict-out shape).
`game.py`'s `update_summary_panel()` is the only thing that turns this
into DOM.
"""

import sim
import sustainability


def _snapshot_row(era, snapshot):
    """One completed era's summary row, from its frozen `era_snapshots`
    entry (see save.snapshot_of()) — never re-derived, since the whole
    point of a snapshot is that it's how the era actually ended, not a
    live recomputation."""
    if not isinstance(snapshot, dict):
        return None
    city = snapshot.get("city")
    city = city if isinstance(city, dict) else {}
    score = snapshot.get("score")
    return {
        "era": era,
        "label": sim.ERA_LABEL.get(era, era.title()),
        "completed": True,
        "season_reached": snapshot.get("season"),
        "score": score,
        "score_label": (
            sustainability.score_label(score, bool(city.get("hard_mode", False)))
            if isinstance(score, (int, float))
            else None
        ),
        "population": city.get("population"),
        "land_health": city.get("land_health"),
    }


def eras_played(campaign):
    """One row per era the settlement has ever set foot in, oldest first:
    a completed row from `era_snapshots` for every era already left behind,
    plus one live (incomplete) row for wherever the settlement is playing
    right now. While mid-revisit, the currently-loaded era is already a
    completed one (a revisit can only ever be entered on a completed era),
    so it's covered by the snapshot row alone — no live row is added for
    it, the same way a revisited era has no "current, still in progress"
    reading to show.
    """
    rows = []
    for era in sim.ERA_ORDER:
        snapshot = campaign.era_snapshots.get(era)
        row = _snapshot_row(era, snapshot)
        if row is not None:
            rows.append(row)
        if era == campaign.state.era and campaign.revisiting is None:
            effects = campaign.tree.effects()
            rows.append(
                {
                    "era": era,
                    "label": sim.ERA_LABEL.get(era, era.title()),
                    "completed": False,
                    "season_reached": campaign.state.season,
                    "score": sustainability.score(campaign.state, effects),
                    "score_label": sustainability.score_label(
                        sustainability.score(campaign.state, effects),
                        sustainability.is_hard_mode(campaign.state),
                    ),
                    "population": campaign.state.population,
                    "land_health": campaign.state.land_health,
                }
            )
    return rows


def _live_progress_city(campaign):
    """The real forward-progress city dict, correct even mid-revisit (K7):
    `campaign.state` briefly holds a revisited era's own restored
    snapshot while looking back, not the campaign's actual forward
    progress, which is parked in `campaign.parked_state` for exactly that
    reason — the same distinction `save.Campaign.exit_revisit()` itself
    is built around."""
    if campaign.revisiting is not None and isinstance(campaign.parked_state, dict):
        city = campaign.parked_state.get("city")
        if isinstance(city, dict):
            return city
    return None


def total_seasons(campaign):
    """Real elapsed turns for the whole playthrough."""
    parked_city = _live_progress_city(campaign)
    if parked_city is not None and isinstance(parked_city.get("season"), (int, float)):
        return parked_city["season"]
    return campaign.state.season


def peak_population(campaign, rows):
    """The largest population this settlement has ever reached, across
    every completed era's snapshot, the live row, and (if mid-revisit) the
    parked forward-progress state that `rows` alone wouldn't otherwise
    see."""
    values = [row["population"] for row in rows if isinstance(row.get("population"), (int, float))]
    parked_city = _live_progress_city(campaign)
    if parked_city is not None and isinstance(parked_city.get("population"), (int, float)):
        values.append(parked_city["population"])
    return max(values) if values else 0


def peak_score(campaign):
    """The highest sustainability score ever recorded by the settlement's
    real forward progress — `state.score_history` is a genuine, append-
    only per-completed-season time series (see `sim.CityState.
    score_history`), not a snapshot-derived estimate, so this is an actual
    historical high, not a reconstruction."""
    history = campaign.state.score_history
    parked_city = _live_progress_city(campaign)
    if parked_city is not None and isinstance(parked_city.get("score_history"), list):
        history = parked_city["score_history"]
    numeric = [v for v in history if isinstance(v, (int, float))]
    return max(numeric) if numeric else None


# K17: a Bronze/Silver/Gold "efficiency rank" from the peak sustainability
# score's own label, so it follows the same (hard-mode-aware) bands the rest
# of the game already uses rather than a second set of thresholds.
RANKS = {"Thriving": "Gold", "Steady": "Silver"}


def efficiency_rank(peak, hard_mode=False):
    """'Gold' / 'Silver' / 'Bronze' city, or None with no score yet."""
    if not isinstance(peak, (int, float)) or peak != peak:
        return None
    return RANKS.get(sustainability.score_label(peak, hard_mode), "Bronze")


def stakeholder_statement(data, rank):
    """K7: the report's in-character opening paragraph, in the register of
    an annual report to stakeholders. Plain facts, framed; no new numbers."""
    rating = f"{data['peak_score']:.0f}/100" if data["peak_score"] is not None else "not yet rated"
    rank_text = f" The council's efficiency rank stands at {rank}." if rank else ""
    return (
        f"To the citizens and stakeholders of the settlement: over {data['total_seasons']} seasons "
        f"we grew to a peak of {data['peak_population']} people and reached the "
        f"{data['furthest_era_label']} era. Our sustainability rating at its best was {rating}."
        f"{rank_text} What follows is the record of how each era went."
    )


def summary(campaign):
    """The full civilization summary report — a plain, JSON-safe dict, the
    same "pure function of state" shape `visual.visual_state()` already
    established. Nothing here touches the page; `game.py`'s
    `update_summary_panel()` is the only thing that renders it."""
    rows = eras_played(campaign)
    completed = [row for row in rows if row["completed"]]
    journey_complete = sim.era_index(campaign.furthest_era) >= sim.era_index(sim.ERA_ORDER[-1])
    return {
        "eras": rows,
        "eras_completed": len(completed),
        "eras_total": len(sim.ERA_ORDER),
        "furthest_era": campaign.furthest_era,
        "furthest_era_label": sim.ERA_LABEL.get(campaign.furthest_era, campaign.furthest_era),
        "total_seasons": total_seasons(campaign),
        "peak_population": peak_population(campaign, rows),
        "peak_score": peak_score(campaign),
        "has_revisited": campaign.has_revisited,
        "journey_complete": journey_complete,
        "rank": efficiency_rank(peak_score(campaign), bool(campaign.state.hard_mode)),
    }
