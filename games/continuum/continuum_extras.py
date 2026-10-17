"""The standing-advantage rows of the City Views dashboard, and the hook that banks a collapsed settlement's Dynasty legacy."""

import doctrines
import dynasty
import geography
import sim

import continuum_runstate as runstate
from continuum_base import _bank_current, _citizens_on, _geo_seed, _resting
from continuum_beyond import _beyond_summary_text
from continuum_citizens import _citizen_effects_text
from continuum_heritage import _heritage_summary_text


def _extra_dashboard_sections():
    """Standing advantages as dashboard rows, so none is ever a hidden mechanic."""
    resting = _resting()
    record = dynasty.get(runstate.campaign.ui)
    if record["off"]:
        perks = "switched off"
    elif resting:
        perks = "resting (comparable run)"
    else:
        perks = f"{len(record['owned'])} owned"
    doctrine_rows = doctrines.history(runstate.campaign.ui)
    doctrine_text = ", ".join(f"{doctrines.DOCTRINES[d]['label']} ({sim.ERA_LABEL[e]})" for e, d in doctrine_rows) or "none"
    rows = [
        ("Dynasty perks", perks),
        ("Dynasty rank", dynasty.rank_name(record["earned"])),
        ("Doctrines", doctrine_text),
        ("Citizen bonuses", _citizen_effects_text() if _citizens_on() else "switched off"),
        ("Heritage sites", _heritage_summary_text()),
        ("The Beyond", _beyond_summary_text()),
        ("Geography", geography.summary_text(geography.generate(_geo_seed()))),
    ]
    return [{"title": "Standing advantages", "rows": rows}]


def _bank_if_collapsed():
    """A collapsed settlement banks what it reached, once."""
    if runstate.sandbox_active or runstate.campaign.revisiting is not None or not dynasty.is_collapsed(runstate.state):
        return
    if dynasty.get_run(runstate.campaign.ui)["failed"]:
        return
    result, info = _bank_current()
    if result["points"] > 0:
        runstate.chronicle.log_challenge(
            runstate.state.season, runstate.state.era,
            f"The settlement has failed. Its lessons are banked in the Dynasty: {result['gained']} Legacy points.",
        )
