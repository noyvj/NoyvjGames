"""Continuum -- K-23: a few quiet tech-industry in-jokes in the Digital Age log.

Six one-line log entries, each shown once, tied to real moments of the Digital
Age (reaching it, the first Transit Hub, the first Digital discovery, a first
quick build, a first refactor season, ten seasons in). They are pure flavour:
they change no number and unlock nothing. They are written into the same log
the story toggle already hides, so a player who turned the story off never sees
them, and nothing needed to play is ever in one.

Which have been shown rides in `campaign.ui["easter_eggs"]` (a list of ids,
validated on read; no save-schema change). Pure functions only; `game.py` writes
the returned lines into the log.
"""

import sim

KEY = "easter_eggs"
DIGITAL_ERA = "digital"
DIGITAL_FIRST_NODE_TIER_FROM = 11
SEASONS_IN = 10

EGGS = {
    "legacy_server": "Someone opens the closet by the boiler room and finds a legacy server, still humming. "
                     "Nobody remembers who set it up, so nobody dares to switch it off.",
    "guild_hall": "The first Transit Hub is open, and above it the settlement's first co-working guild hall: "
                  "forty desks, one good kettle, and a standing argument about the thermostat.",
    "meeting_rule": "The planning office adopts a new rule: no meeting that could have been a notice on the board.",
    "friday_shortcut": "A shortcut goes into the new works on a Friday afternoon. Everyone agrees it is temporary.",
    "workaround_funeral": "The old workaround is finally deleted. The crew holds a small funeral for it and "
                          "writes the date on the wall.",
    "blameless_outage": "A cable fails, and with it a half-forgotten shortcut. The review is blameless; "
                        "the fix is a sticky note that says what the shortcut was.",
}
ORDER = tuple(EGGS)


def seen(ui):
    raw = ui.get(KEY) if isinstance(ui, dict) else None
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[: len(ORDER) * 2]:
        if isinstance(item, str) and item in EGGS and item not in out:
            out.append(item)
    return out


def _grant(ui, egg_id):
    done = seen(ui)
    if egg_id in done:
        return None
    done.append(egg_id)
    ui[KEY] = done
    return egg_id, EGGS[egg_id]


def on_era(ui, era):
    """Reaching the Digital Age."""
    return _grant(ui, "legacy_server") if era == DIGITAL_ERA else None


def on_build(ui, state, building, quick=False):
    """A building was raised in the Digital Age."""
    if state.era != DIGITAL_ERA:
        return None
    if building == "transit_hubs":
        return _grant(ui, "guild_hall")
    if quick:
        return _grant(ui, "friday_shortcut")
    return None


def on_research(ui, state, tier):
    if state.era == DIGITAL_ERA and tier >= DIGITAL_FIRST_NODE_TIER_FROM:
        return _grant(ui, "meeting_rule")
    return None


def on_refactor(ui, state):
    return _grant(ui, "workaround_funeral") if sim.era_index(state.era) >= sim.era_index(DIGITAL_ERA) else None


def on_season(ui, state, seasons_in_digital):
    if state.era == DIGITAL_ERA and seasons_in_digital >= SEASONS_IN:
        return _grant(ui, "blameless_outage")
    return None
