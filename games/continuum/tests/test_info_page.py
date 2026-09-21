"""Milestone 5 — collapsed, era-aware real-world info panel.

Covers the three things the design doc actually asks for: collapsed by
default, toggling opens/closes it, and the content shown tracks whatever
era the settlement is currently in (including an era this build has no
content for yet, since Phase 3 ships the other six eras one at a time).
Rendering itself is `shared/info_page.py`, already exercised by every
climate-quartet game's own tests — these tests are about the era-lookup
seam Continuum adds on top (`info_content.era_info_page()`), and about the
open/closed flag surviving a save/load round trip.
"""

import info_content
import sim


def test_panel_is_collapsed_by_default(game_env):
    panel = game_env.elements["info-page-panel"]
    assert panel.hidden is True
    assert game_env.module.info_page_open is False


def test_toggle_button_opens_and_closes_the_panel(game_env):
    toggle = game_env.elements["info-page-toggle-button"]
    panel = game_env.elements["info-page-panel"]

    toggle.dispatch("click", None)
    assert game_env.module.info_page_open is True
    assert panel.hidden is False

    toggle.dispatch("click", None)
    assert game_env.module.info_page_open is False
    assert panel.hidden is True


def test_open_panel_shows_the_current_era_sources(game_env):
    game_env.elements["info-page-toggle-button"].dispatch("click", None)

    tribal = info_content.era_info_page("tribal")
    assert game_env.elements["info-page-framing"].innerText == tribal["framing"]
    assert game_env.elements["info-page-tie-in"].innerText == tribal["mechanic_tie_in"]
    assert len(game_env.elements["info-page-sources"].children) == len(tribal["sources"])


def test_tribal_sources_are_real_not_placeholder(game_env):
    """Milestone 5 explicitly asks for real content, not a stub, since
    continuum-real-world-sources.md already has four verified Tribal
    sources."""
    tribal = info_content.era_info_page("tribal")
    assert len(tribal["sources"]) == 4
    for source in tribal["sources"]:
        assert source["url"].startswith("https://")
        assert source["label"]
        assert source["note"]


def test_an_era_with_no_content_yet_falls_back_to_the_pending_placeholder():
    """Phase 3 ships one era's content at a time; every era with no content
    of its own yet (Tribal, Agrarian and, since Milestone 9, Classical are
    done) should degrade gracefully rather than raising a KeyError the
    moment a save (or, later, real play) reaches it."""
    done_eras = set(info_content.ERA_INFO_PAGE.keys())
    for era in sim.ERA_ORDER:
        if era in done_eras:
            continue
        pending = info_content.era_info_page(era)
        assert pending["sources"] == []
        assert pending is info_content.era_info_page(era)  # same fallback object


def test_panel_reflects_era_changes_without_reopening(game_env):
    """The panel is era-aware: it should show whatever era is CURRENT, not
    whichever era was current the first time it was opened."""
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("tribal")["framing"]
    )

    # Simulate having reached a later era (Phase 3's era-transition system
    # will do this for real; Milestone 5 only needs the lookup to be live).
    game_env.state.era = "agrarian"
    game_env.module.render()

    assert (
        game_env.elements["info-page-framing"].innerText
        == info_content.era_info_page("agrarian")["framing"]
    )


def test_info_page_open_flag_survives_a_save_round_trip(game_env):
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert game_env.module.info_page_open is True

    saved = game_env.module.get_state()
    assert saved["ui"]["info_page_open"] is True

    # Close it, then load the save back — it should reopen.
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert game_env.module.info_page_open is False

    assert game_env.module.load_state(saved) is True
    assert game_env.module.info_page_open is True
    assert game_env.elements["info-page-panel"].hidden is False


def test_load_state_without_a_saved_toggle_defaults_closed(game_env):
    """An old save written before Milestone 5 existed has no "ui" entry for
    this at all -- it should load as closed, not raise."""
    saved = game_env.module.get_state()
    saved["ui"] = {}

    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert game_env.module.info_page_open is True

    assert game_env.module.load_state(saved) is True
    assert game_env.module.info_page_open is False


# ---------------------------------------------------------------------
# Z16 audit: the info-panel "Report an issue with this info" button.
# Mirrors games/champ-de-mots/tests/test_pronunciation_reports.py's own
# coverage shape (payload contents, visibility, one-shot behaviour) for
# the closest equivalent this game has to that game's report button.
# ---------------------------------------------------------------------


def test_report_button_is_hidden_while_the_panel_is_closed(game_env):
    assert game_env.module.info_page_open is False
    assert game_env.elements["info-page-report-button"].hidden is True


def test_report_button_appears_once_the_panel_is_open(game_env):
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    button = game_env.elements["info-page-report-button"]
    assert button.hidden is False
    assert button.innerText == game_env.module.INFO_PAGE_REPORT_BUTTON_LABEL
    assert button.disabled is False


def test_report_button_is_hidden_for_an_era_with_no_sources_yet(game_env):
    """An era with no info-panel content yet (the _PENDING placeholder) has
    nothing worth flagging -- the button shouldn't offer to report it."""
    game_env.state.era = "does-not-exist-yet"
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    assert game_env.elements["info-page-report-button"].hidden is True


def test_submitting_a_report_sends_the_current_eras_source_labels(game_env):
    module = game_env.module
    game_env.elements["info-page-toggle-button"].dispatch("click", None)

    payload = module.submit_info_page_report()

    tribal = info_content.era_info_page("tribal")
    assert payload["game_id"] == "continuum"
    assert payload["item_id"] == "info-tribal"
    assert payload["submitted_answer"] == module.INFO_PAGE_REPORT_MARKER
    assert payload["marked_correct_answer"] == [s["label"] for s in tribal["sources"]]
    assert payload["topic_type"] == "info_panel"


def test_a_second_report_for_the_same_era_is_a_no_op(game_env):
    module = game_env.module
    game_env.elements["info-page-toggle-button"].dispatch("click", None)

    first = module.submit_info_page_report()
    assert first is not None
    assert module.submit_info_page_report() is None

    button = game_env.elements["info-page-report-button"]
    assert button.disabled is True
    assert button.innerText == module.INFO_PAGE_REPORT_SENT_LABEL


def test_switching_eras_reopens_the_report(game_env):
    """Reporting Tribal's sources shouldn't silently disable the button
    forever once the settlement reaches a later era with different, equally
    reportable sources."""
    module = game_env.module
    game_env.elements["info-page-toggle-button"].dispatch("click", None)
    module.submit_info_page_report()

    game_env.state.era = "agrarian"
    module.render()

    button = game_env.elements["info-page-report-button"]
    assert button.disabled is False
    assert button.innerText == module.INFO_PAGE_REPORT_BUTTON_LABEL
