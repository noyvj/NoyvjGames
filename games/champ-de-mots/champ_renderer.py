"""render(): the one function that redraws the whole page. It also hands render() to every earlier module that calls it.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import minigames
from champ_calendar import render_calendar
from champ_reportlog import render_report_log
from champ_legend import render_legend_guide
from champ_review import render_review
from champ_proficiency import render_proficiency
from champ_bonus import render_bonus
from champ_builder import render_builder
from champ_listening import render_listening
from champ_conversation import render_conversation
from champ_placement import render_placement
from champ_examformats import render_formats
from champ_phrasebook import render_phrasebook
from champ_dashboard import render_cultural_notes, render_dashboard, render_deepdive
from champ_liaison import render_liaison_drill
from champ_achievements import render_achievements, render_changelog
from champ_planner import render_planner
from champ_accent import render_accent_bars
from champ_shop import render_shop
from champ_practice import render_practice
from champ_wateropts import render_water_options
from champ_farm import render_farm, render_status
import sys


def render():
    render_deepdive()
    render_calendar()
    render_phrasebook()
    render_farm()
    render_status()
    render_practice()
    render_review()
    render_proficiency()
    render_bonus()
    render_builder()
    render_conversation()
    render_formats()
    render_listening()
    render_placement()
    render_cultural_notes()
    render_dashboard()
    render_liaison_drill()
    render_achievements()
    render_changelog()
    render_legend_guide()
    render_report_log()
    render_planner()
    render_accent_bars()
    render_water_options()
    render_shop()
    minigames.render()


# Hand render() to every earlier module that calls it before this file exists (see the `render = None` lines).
for _name in (
    "champ_points",
    "champ_reportlog",
    "champ_practice_base",
    "champ_reports",
    "champ_arrange",
    "champ_review",
    "champ_proficiency",
    "champ_bonus",
    "champ_builder",
    "champ_listening",
    "champ_conversation",
    "champ_placement",
    "champ_examformats",
    "champ_phrasebook",
    "champ_dashboard",
    "champ_liaison",
    "champ_achievements",
    "champ_planner",
    "champ_prefs",
    "champ_shop",
    "champ_practice",
    "champ_wateropts",
):
    sys.modules[_name].render = render
del _name
