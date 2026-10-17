"""setup(): wires every button, then starts the game. The two research-filter handlers sit here too."""

from js import document
from pyodide.ffi import create_proxy

import challengerun
import consulting
import research
import sim

import continuum_runstate as runstate
from continuum_achievements import _seed_achievement_toast_baseline, on_toggle_achievements
from continuum_advisors import on_toggle_advisors
from continuum_archive import on_found_new_settlement, on_toggle_postmortem, on_toggle_summary_panel
from continuum_base import _pc_layout
from continuum_beyond import on_beyond_start, on_beyond_stop, on_toggle_beyond
from continuum_challenge import (
    _build_challenge_controls, on_challenge_abandon, on_challenge_copy_code, on_challenge_custom_start,
    on_challenge_daily_start, on_challenge_input, on_challenge_load_code, on_toggle_challenge,
)
from continuum_citizens import on_citizens_off, on_toggle_citizens, on_toggle_neighbours
from continuum_clock import _make_speed_handler
from continuum_dynasty import (
    _adopt_local_dynasty, on_dynasty_bank, on_dynasty_off, on_rewind, on_toggle_doctrines,
    on_toggle_dynasty,
)
from continuum_founders import (
    on_add_founders_note, on_name_keydown, on_name_save, on_name_suggest, on_toggle_founders,
    on_toggle_minutes,
)
from continuum_geography import on_geography_new, on_geography_off, on_geography_use_seed, on_toggle_geography
from continuum_hamlet import _hamlet_storage_get, on_toggle_hamlet
from continuum_heritage import on_toggle_heritage
from continuum_infopanels import (
    on_toggle_changelog, on_toggle_info_page, submit_info_page_report, update_changelog_display,
)
from continuum_orders import on_orders_add, on_orders_master, on_toggle_orders
from continuum_panels import render_research, research_branch_filter
from continuum_peers import on_peer_hide, on_peer_metric
from continuum_progress import on_advance_era, on_exit_revisit
from continuum_renderer import render
from continuum_scenario import (
    _make_consulting_start_handler, _make_select_scenario_handler, on_consulting_abandon,
    on_toggle_hard_mode,
)
from continuum_techdebt import on_toggle_quick_build, on_toggle_refactor
from continuum_timelapse import (
    on_timelapse_next, on_timelapse_play, on_timelapse_prev, on_timelapse_scrub, on_timelapse_strip,
    on_toggle_timelapse,
)
from continuum_views import VIEW_TABS, _make_views_tab_handler, on_toggle_views


def _make_branch_chip_handler(branch):
    def handler(event=None):
        if branch in research_branch_filter:
            research_branch_filter.discard(branch)
        else:
            research_branch_filter.add(branch)
        for b in research.BRANCHES:
            chip = document.getElementById(f"research-branch-{b}-button")
            on = b in research_branch_filter
            chip.classList.toggle("active", on)
            chip.setAttribute("aria-pressed", "true" if on else "false")
        render_research()
    return handler


def on_research_search_input(event=None):
    runstate.research_search_query = document.getElementById("research-search-input").value
    render_research()


def setup():
    # Work/Build row buttons are wired inside render_work()/render_buildings()
    # themselves now (Milestone 8) — those rows are rebuilt every render, the
    # same as the research panel's Study buttons already were, so wiring them
    # here would just be wiring buttons that don't exist yet.
    for speed, key in ((0, "pause"), (1, "1x"), (2, "2x"), (4, "4x")):
        document.getElementById(f"speed-{key}-button").addEventListener(
            "click", create_proxy(_make_speed_handler(speed))
        )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    # U2: the optional Hamlet view. Preference is read once at load; the
    # toggle button itself is only shown on a desktop-class screen.
    runstate.hamlet_on = _pc_layout() or _hamlet_storage_get() == "on"
    document.getElementById("hamlet-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hamlet)
    )
    document.getElementById("info-page-report-button").addEventListener(
        "click", create_proxy(submit_info_page_report)
    )
    document.getElementById("advance-era-button").addEventListener(
        "click", create_proxy(on_advance_era)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("exit-revisit-button").addEventListener(
        "click", create_proxy(on_exit_revisit)
    )
    for _branch in research.BRANCHES:
        document.getElementById(f"research-branch-{_branch}-button").addEventListener(
            "click", create_proxy(_make_branch_chip_handler(_branch))
        )
    document.getElementById("research-search-input").addEventListener(
        "input", create_proxy(on_research_search_input)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary_panel)
    )
    document.getElementById("founders-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_founders)
    )
    document.getElementById("minutes-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_minutes)
    )
    document.getElementById("views-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_views)
    )
    for _tab in VIEW_TABS:
        document.getElementById(f"views-tab-{_tab}-button").addEventListener(
            "click", create_proxy(_make_views_tab_handler(_tab))
        )
    # K-14: a hidden twin of the in-panel buttons, so the Desktop window frame
    # can close the post-mortem through the same handler (keeps one open flag).
    document.getElementById("postmortem-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_postmortem)
    )
    document.getElementById("founders-add-button").addEventListener(
        "click", create_proxy(on_add_founders_note)
    )
    document.getElementById("settlement-name-suggest-button").addEventListener(
        "click", create_proxy(on_name_suggest)
    )
    document.getElementById("settlement-name-save-button").addEventListener(
        "click", create_proxy(on_name_save)
    )
    document.getElementById("settlement-name-input").addEventListener(
        "keydown", create_proxy(on_name_keydown)
    )
    # K12 — three static scenario buttons (never rebuilt at runtime, unlike
    # the dynamic per-era rows elsewhere in this file), so each gets its
    # own one-shot proxy here rather than the "destroy the stale proxy"
    # discipline render_research()/render_work() need for rows that are
    # rebuilt every render.
    for _scenario_id in sim.SCENARIOS:
        document.getElementById(f"scenario-{_scenario_id}-button").addEventListener(
            "click", create_proxy(_make_select_scenario_handler(_scenario_id))
        )
    document.getElementById("hard-mode-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_mode)
    )
    document.getElementById("challenge-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_challenge)
    )
    _build_challenge_controls()
    for _name in challengerun.RANGES:
        document.getElementById(f"challenge-dial-{_name}").addEventListener(
            "input", create_proxy(on_challenge_input)
        )
    document.getElementById("challenge-modifier-select").addEventListener(
        "change", create_proxy(on_challenge_input)
    )
    document.getElementById("challenge-hard-checkbox").addEventListener(
        "change", create_proxy(on_challenge_input)
    )
    for _id, _handler in (
        ("challenge-daily-start-button", on_challenge_daily_start),
        ("challenge-custom-start-button", on_challenge_custom_start),
        ("challenge-abandon-button", on_challenge_abandon),
        ("challenge-code-copy-button", on_challenge_copy_code),
        ("challenge-code-load-button", on_challenge_load_code),
    ):
        document.getElementById(_id).addEventListener("click", create_proxy(_handler))
    document.getElementById("timelapse-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_timelapse)
    )
    document.getElementById("timelapse-scrub").addEventListener("input", create_proxy(on_timelapse_scrub))
    for _id, _handler in (
        ("timelapse-prev-button", on_timelapse_prev),
        ("timelapse-next-button", on_timelapse_next),
        ("timelapse-play-button", on_timelapse_play),
        ("timelapse-strip-button", on_timelapse_strip),
    ):
        document.getElementById(_id).addEventListener("click", create_proxy(_handler))
    document.getElementById("advisors-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_advisors)
    )
    document.getElementById("quick-build-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_quick_build)
    )
    document.getElementById("refactor-button").addEventListener(
        "click", create_proxy(on_toggle_refactor)
    )
    for _case_id in consulting.CASES:
        document.getElementById(f"consulting-case-{_case_id}-button").addEventListener(
            "click", create_proxy(_make_consulting_start_handler(_case_id))
        )
    document.getElementById("consulting-abandon-button").addEventListener(
        "click", create_proxy(on_consulting_abandon)
    )
    document.getElementById("found-settlement-button").addEventListener(
        "click", create_proxy(on_found_new_settlement)
    )
    for _id, _handler in (
        ("dynasty-toggle-button", on_toggle_dynasty),
        ("dynasty-bank-button", on_dynasty_bank),
        ("dynasty-off-button", on_dynasty_off),
        ("doctrines-toggle-button", on_toggle_doctrines),
        ("citizens-toggle-button", on_toggle_citizens),
        ("citizens-off-button", on_citizens_off),
        ("neighbours-toggle-button", on_toggle_neighbours),
        ("orders-toggle-button", on_toggle_orders),
        ("heritage-toggle-button", on_toggle_heritage),
        ("beyond-toggle-button", on_toggle_beyond),
        ("geography-toggle-button", on_toggle_geography),
        ("geography-new-button", on_geography_new),
        ("geography-off-button", on_geography_off),
        ("geography-use-seed-button", on_geography_use_seed),
        ("beyond-start-button", on_beyond_start),
        ("beyond-stop-button", on_beyond_stop),
        ("orders-master-button", on_orders_master),
        ("orders-add-button", on_orders_add),
        ("rewind-button", on_rewind),
        ("peer-hide-button", on_peer_hide),
        ("peer-metric-button", on_peer_metric),
    ):
        document.getElementById(_id).addEventListener("click", create_proxy(_handler))
    _adopt_local_dynasty()
    # Belt-and-suspenders: the toast starts hidden via the static `hidden`
    # attribute in index.html, but every other stateful element in this
    # file (panels, buttons) has its shown/hidden state actively driven by
    # code rather than left to rely on markup alone — setting it here too
    # means the toast's default state doesn't depend on the static HTML
    # attribute ever being present or correct.
    document.getElementById("achievement-toast").hidden = True
    update_changelog_display()
    render()
    _seed_achievement_toast_baseline()


setup()
