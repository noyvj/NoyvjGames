"""I-29 glossary popovers, I-4 Region Report, GI-29 band-change confetti."""

import sys
import types


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


# ---- I-29 ---------------------------------------------------------------------------------------------
def test_four_terms_each_with_a_one_line_definition(game_env):
    m = game_env.module
    assert list(m.GLOSSARY_ORDER) == ["capacity", "strain", "integration", "control"]
    for term in m.GLOSSARY_ORDER:
        entry = m.GLOSSARY[term]
        assert entry["label"] and "\n" not in entry["text"] and 40 < len(entry["text"]) < 260


def test_the_popover_starts_closed(game_env):
    game_env.module.render()
    assert game_env.elements["glossary-pop"].hidden is True


def test_click_opens_the_definition_and_a_second_click_closes_it(game_env):
    el = game_env.elements
    _click(game_env, "glossary-strain-button")
    assert el["glossary-pop"].hidden is False
    assert el["glossary-pop-text"].innerText.startswith("Strain: ")
    assert el["glossary-strain-button"].attributes["aria-expanded"] == "true"
    assert el["glossary-capacity-button"].attributes["aria-expanded"] == "false"
    _click(game_env, "glossary-strain-button")
    assert el["glossary-pop"].hidden is True


def test_hover_and_focus_show_and_leaving_hides_unless_pinned(game_env):
    el = game_env.elements
    el["glossary-capacity-button"].dispatch("mouseenter", None)
    assert el["glossary-pop"].hidden is False
    el["glossary-capacity-button"].dispatch("mouseleave", None)
    assert el["glossary-pop"].hidden is True
    el["glossary-integration-button"].dispatch("focus", None)
    assert el["glossary-pop-text"].innerText.startswith("Integration: ")
    el["glossary-integration-button"].dispatch("blur", None)
    assert el["glossary-pop"].hidden is True
    _click(game_env, "glossary-integration-button")  # pinned by a click
    el["glossary-integration-button"].dispatch("mouseleave", None)
    assert el["glossary-pop"].hidden is False
    el["glossary-control-button"].dispatch("mouseenter", None)  # hovering another term does not replace a pinned one
    assert el["glossary-pop-text"].innerText.startswith("Integration: ")


def test_real_story_link_shows_only_where_relevant(game_env):
    el = game_env.elements
    _click(game_env, "glossary-capacity-button")
    assert el["glossary-more-button"].hidden is False
    _click(game_env, "glossary-capacity-button")
    _click(game_env, "glossary-control-button")
    assert el["glossary-more-button"].hidden is True


def test_real_story_button_opens_the_info_page_once(game_env):
    m = game_env.module
    opened = []
    toggle = game_env.elements["info-page-toggle-button"]
    toggle.click = lambda: opened.append(1)
    _click(game_env, "glossary-integration-button")
    _click(game_env, "glossary-more-button")
    assert opened == [1]
    m.info_page_open = True
    _click(game_env, "glossary-more-button")
    assert opened == [1]  # already open: no second click that would close it


def test_definitions_match_the_games_own_rules(game_env):
    m = game_env.module
    assert "Only Integration Services" in m.GLOSSARY["integration"]["text"]
    assert "dotted grey" in m.GLOSSARY["control"]["text"]
    assert "does not yet cover" in m.GLOSSARY["strain"]["text"]


# ---- I-4 ---------------------------------------------------------------------------------------------
def _play_a_little(env):
    env.region.region_name = "Lakeside"
    for _ in range(4):
        env.invest("housing")
        env.invest("services")
        env.advance_round()


def test_report_panel_toggles_like_the_other_windows(game_env):
    el = game_env.elements
    game_env.module.render()
    assert el["report-panel"].hidden is True
    _click(game_env, "report-toggle-button")
    assert el["report-panel"].hidden is False and el["report-toggle-button"].innerText == "Hide Region Report"
    assert "Region Report: Unnamed region" in el["report-card"].innerHTML
    _click(game_env, "report-toggle-button")
    assert el["report-panel"].hidden is True


def test_report_data_has_every_section_asked_for(game_env):
    m = game_env.module
    _play_a_little(game_env)
    d = m.region_report_data()
    assert d["name"] == "Lakeside" and d["rounds"] == 4 and d["tier"] == "Gentle"
    assert [label for label, _ in d["key_rounds"]] == [
        "First purchase", "Net-positive turning point", "Thriving reached", "Second wave", "Strain peak"
    ]
    assert dict(d["key_rounds"])["First purchase"] == "round 1"
    assert [s["label"] for s in d["subscores"]] == ["Service quality", "Economic health", "Social cohesion"]
    assert all(s["first"] is not None and len(s["curve"]) == 4 for s in d["subscores"])
    assert [r["label"] for r in d["roi_rows"]] == ["Housing", "Integration Services", "Infrastructure", "Policies"]
    assert d["roi_rows"][0]["spent"] == 80.0 and d["roi_rows"][1]["spent"] == 80.0
    assert "no direct return" in d["roi_rows"][0]["return"]
    assert d["roi_total"] is not None


def test_report_text_carries_name_difficulty_key_rounds_trends_roi_and_coda(game_env):
    m = game_env.module
    _play_a_little(game_env)
    game_env.region.calendar_enabled = True
    game_env.region.council_picks = ["night_school"]
    game_env.region.coda_legacy_choice = "services"
    text = m.region_report_text()
    assert text.startswith("Region Report: Lakeside")
    assert "Difficulty: Standard (Crisis Calendar)" in text
    assert "Key rounds:" in text and "First purchase: round 1" in text
    assert "Sub-scores (first logged round -> now):" in text and "Service quality:" in text
    assert "Spending and return:" in text and "Integration Services: 80 funds" in text
    assert "Council programs: Night-School Network" in text
    assert "Carried forward: Public services" in text


def test_first_purchase_is_not_claimed_once_the_ledger_has_rolled_over(game_env):
    m = game_env.module
    _play_a_little(game_env)
    game_env.region.ledger = game_env.region.ledger[2:]
    assert m._first_purchase_round() is None
    assert dict(m.region_report_data()["key_rounds"])["First purchase"] == "not recorded"


def test_report_for_a_brand_new_region_is_honest(game_env):
    d = game_env.module.region_report_data()
    assert d["rounds"] == 0
    assert dict(d["key_rounds"])["Net-positive turning point"] == "not yet"
    assert dict(d["key_rounds"])["Strain peak"].startswith("none")
    assert game_env.module.region_report_text().count("\n") > 8


def test_report_html_escapes_the_region_name(game_env):
    game_env.region.region_name = "<b>Bold</b> & co"
    html = game_env.module.region_report_html()
    assert "<b>Bold" not in html and "&lt;b&gt;Bold&lt;/b&gt; &amp; co" in html


def test_copy_falls_back_to_a_text_box_and_says_so(game_env):
    el = game_env.elements
    _click(game_env, "report-copy-button")
    assert el["report-copy-area"].hidden is False
    assert el["report-copy-area"].value.startswith("Region Report: Unnamed region")
    assert "Could not copy" in el["report-copy-status"].innerText


def test_copy_uses_the_clipboard_when_there_is_one(game_env):
    written = []
    sys.modules["js"].navigator = types.SimpleNamespace(clipboard=types.SimpleNamespace(writeText=written.append))
    _click(game_env, "report-copy-button")
    assert written and written[0].startswith("Region Report:")
    assert game_env.elements["report-copy-area"].hidden is True
    assert "Copied" in game_env.elements["report-copy-status"].innerText


def test_print_fills_the_print_sheet_and_calls_print(game_env):
    calls = []
    sys.modules["js"].window = types.SimpleNamespace(print=lambda: calls.append(1))
    _click(game_env, "report-print-button")
    assert calls == [1]
    assert "Region Report:" in game_env.elements["report-print-sheet"].innerHTML
    assert "print dialog" in game_env.elements["report-copy-status"].innerText


def test_print_without_a_window_says_what_to_do_instead(game_env):
    _click(game_env, "report-print-button")
    assert "Copy report as text" in game_env.elements["report-copy-status"].innerText


def test_report_describes_a_tier_and_assist(game_env):
    m = game_env.module
    _click(game_env, "tier-rigorous-button")
    _click(game_env, "assist-suggest-button")
    text = m.region_report_text()
    assert "Difficulty: Rigorous (Crisis Calendar, Accelerated Severity (2x)), assisted run" in text


# ---- GI-29 ---------------------------------------------------------------------------------------------
def test_band_rank_follows_the_four_bands(game_env):
    m = game_env.module
    assert [m.band_rank(s) for s in (10, 40, 70, 95)] == [0, 1, 2, 3]


def _force_score(m, score):
    """Pin the wellbeing score so a test controls which band a round ends in."""
    m.region.wellbeing_score = lambda: score


def test_rising_into_a_higher_band_plays_confetti_and_says_so(game_env):
    m = game_env.module
    _force_score(m, 30)
    scores = iter([30, 75])
    m.region.wellbeing_score = lambda: next(scores, 75)
    game_env.advance_round()
    el = game_env.elements
    assert el["band-confetti"].classList.contains("band-confetti--go")
    assert el["band-change-note"].hidden is False
    assert el["band-change-note"].innerText == "Wellbeing rose into the Thriving band."
    game_env.timers.flush()
    assert not el["band-confetti"].classList.contains("band-confetti--go")


def test_staying_in_the_band_or_falling_does_not(game_env):
    m = game_env.module
    _force_score(m, 50)
    game_env.advance_round()
    assert not game_env.elements["band-confetti"].classList.contains("band-confetti--go")
    assert game_env.elements["band-change-note"].hidden is True
    _force_score(m, 80)
    m.region.wellbeing_score = lambda: 80
    game_env.advance_round()
    scores = iter([80, 20])
    m.region.wellbeing_score = lambda: next(scores, 20)
    game_env.advance_round()
    assert game_env.elements["band-change-note"].hidden is True


def test_the_note_clears_on_the_next_advance(game_env):
    m = game_env.module
    scores = iter([30, 75])
    m.region.wellbeing_score = lambda: next(scores, 75)
    game_env.advance_round()
    assert game_env.elements["band-change-note"].hidden is False
    m.region.wellbeing_score = lambda: 75
    game_env.advance_round()
    assert game_env.elements["band-change-note"].hidden is True


def test_a_loaded_save_never_celebrates(game_env):
    m = game_env.module
    state = m.get_state()
    state["wellbeing_log"] = [30.0, 80.0]
    m.load_state(state)
    assert not game_env.elements["band-confetti"].classList.contains("band-confetti--go")
    assert game_env.elements["band-change-note"].hidden is True


def test_the_round_announcement_includes_the_band_rise(game_env):
    m = game_env.module
    spoken = []
    m.announce = spoken.append
    scores = iter([30, 75])
    m.region.wellbeing_score = lambda: next(scores, 75)
    game_env.advance_round()
    assert any("Wellbeing rose into the Thriving band." in line for line in spoken)


def test_play_rounds_and_autopilot_celebrate_too(game_env):
    m = game_env.module
    scores = iter([30])
    m.region.wellbeing_score = lambda: next(scores, 75)
    _click(game_env, "play-rounds-button")
    assert game_env.elements["band-confetti"].classList.contains("band-confetti--go")


def test_confetti_css_is_hidden_by_every_motion_setting():
    from pathlib import Path

    css = (Path(__file__).resolve().parent.parent / "style.css").read_text()
    assert "html.reduce-motion .band-confetti" in css
    assert 'html[data-anim-speed="off"] .band-confetti' in css
    assert "@media (prefers-reduced-motion: reduce) { .band-confetti { display: none; } }" in css
