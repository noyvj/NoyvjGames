"""setup(): wires every button on the page to its handler, hands the farm to the minigames and draws the first screen.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from pyodide.ffi import create_proxy

import minigames
import champ_runstate as runstate
from champ_model import state
from champ_qbuild import variants_for
from champ_questions import generate_question
from champ_grading import check_question_answer
from champ_util import _element, pref_get, pref_set, speak_french, speech_available
from champ_calendar import on_calendar_next, on_calendar_prev, on_toggle_calendar
from champ_points import on_toggle_study_buddy, record_practice
from champ_reportlog import on_toggle_report_log
from champ_growth import (
    credit_game_item, credit_game_plot_id, growth_credit_text, plot_for_fr, render_growth_markers,
    reset_growth_credit,
)
from champ_practice_base import close_practice
from champ_reports import submit_pronunciation_report, submit_report
from champ_leech import rest_leech
from champ_semesters import _load_semester_prefs
from champ_arrange import on_farm_filter_change, on_farm_sort_change
from champ_legend import on_toggle_legend
from champ_review_base import _populate_cram_selects
from champ_review import (
    close_review, next_review_question, on_quick_water, on_review_answer_keydown, on_review_submit_typed,
    on_start_cram_review, on_start_grammar_review, on_start_marathon_review, on_start_weak_spot_review,
    on_start_word_review, on_toggle_review, submit_review_pronunciation_report, submit_review_report,
)
from champ_proficiency import (
    close_proficiency_test, next_proficiency_question, on_proficiency_answer_keydown,
    on_proficiency_submit_typed, submit_proficiency_pronunciation_report, submit_proficiency_report,
)
from champ_bonus import (
    advance_from_order, close_bonus_section, next_bonus_sentence, next_bonus_tile,
    on_bonus_sentence_answer_keydown, on_bonus_sentence_submit_typed, on_bonus_tile_answer_keydown,
    on_bonus_tile_submit_typed, submit_bonus_sentence_pronunciation_report, submit_bonus_sentence_report,
    submit_bonus_tile_pronunciation_report, submit_bonus_tile_report,
)
from champ_builder import (
    close_sentence_builder, next_builder_sentence, start_sentence_builder, undo_builder_tile,
)
from champ_listening import (
    close_listening, next_listening_question, on_listening_play, on_listening_slow, start_listening,
)
from champ_conversation import close_conversation, next_conversation_turn, start_conversation
from champ_placement import (
    begin_placement_test, close_placement, next_placement_question, on_apply_placement,
    on_placement_answer_keydown, on_placement_submit_typed, start_placement,
)
from champ_examformats import (
    close_formats, next_formats_question, on_formats_keydown, on_formats_submit, on_open_formats,
)
from champ_phrasebook import (
    on_bookmark_practice, on_bookmark_review, on_start_phrasebook_review, on_toggle_phrasebook_panel,
)
from champ_dashboard import on_toggle_cultural_notes, on_toggle_dashboard, on_toggle_deepdive
from champ_liaison import close_liaison_drill, next_liaison_question, on_toggle_liaison_drill
from champ_achievements import on_toggle_achievements, on_toggle_changelog
from champ_planner import (
    on_planner_clear, on_planner_date_change, on_planner_default, on_planner_minutes_change,
    on_toggle_planner,
)
from champ_accent import build_accent_bars
from champ_prefs import (
    PREF_ALWAYS_MC, format_schedule_lines, on_toggle_accent_sensitivity, on_toggle_always_mc,
)
from champ_shop import on_toggle_shop
from champ_practice import (
    forgive_slip, on_answer_keydown, on_next_day, on_next_practice_plot, on_submit_typed, on_water_next,
    set_confidence,
)
from champ_wateropts import (
    _populate_water_selects, on_review_listen, on_review_listen_show, on_toggle_water_options,
    on_water_listen_start, on_water_mc_start, on_water_next_option, on_water_row_change, on_water_row_start,
    on_water_topic_change, on_water_topic_start, on_water_typed_start, on_water_wilting_start,
)
from champ_farm import build_farm, render_legend
from champ_renderer import render


def setup():
    build_farm()
    render_legend()
    build_accent_bars()
    _element("practice-submit-button").addEventListener("click", create_proxy(on_submit_typed))
    _element("practice-answer-input").addEventListener("keydown", create_proxy(on_answer_keydown))
    _element("practice-close-button").addEventListener("click", create_proxy(close_practice))
    _element("practice-slip-button").addEventListener("click", create_proxy(forgive_slip))
    _element("practice-leech-rest-button").addEventListener("click", create_proxy(rest_leech))
    _element("practice-next-button").addEventListener(
        "click", create_proxy(on_next_practice_plot)
    )
    _element("practice-report-button").addEventListener("click", create_proxy(submit_report))
    _element("practice-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_pronunciation_report)
    )
    _element("practice-confidence-sure-button").addEventListener(
        "click", create_proxy(lambda event=None: set_confidence("sure"))
    )
    _element("practice-confidence-unsure-button").addEventListener(
        "click", create_proxy(lambda event=None: set_confidence("unsure"))
    )
    _element("water-next-button").addEventListener("click", create_proxy(on_water_next))
    _element("next-day-button").addEventListener("click", create_proxy(on_next_day))
    _element("accent-toggle-checkbox").addEventListener(
        "click", create_proxy(on_toggle_accent_sensitivity)
    )
    _element("accent-toggle-checkbox").checked = runstate.ACCENT_SENSITIVE
    _element("review-toggle-button").addEventListener("click", create_proxy(on_toggle_review))
    _element("cultural-notes-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_cultural_notes)
    )
    _element("dashboard-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_dashboard)
    )
    _element("calendar-toggle-button").addEventListener("click", create_proxy(on_toggle_calendar))
    _element("farm-filter-select").addEventListener("change", create_proxy(on_farm_filter_change))
    _element("farm-sort-select").addEventListener("change", create_proxy(on_farm_sort_change))
    _element("planner-toggle-button").addEventListener("click", create_proxy(on_toggle_planner))
    _element("planner-date-input").addEventListener("change", create_proxy(on_planner_date_change))
    _element("planner-minutes-input").addEventListener("input", create_proxy(on_planner_minutes_change))
    _element("planner-minutes-input").addEventListener("change", create_proxy(on_planner_minutes_change))
    _element("planner-clear-button").addEventListener("click", create_proxy(on_planner_clear))
    _element("planner-default-button").addEventListener("click", create_proxy(on_planner_default))
    _populate_cram_selects()
    _populate_water_selects()
    runstate.ALWAYS_MULTIPLE_CHOICE = pref_get(PREF_ALWAYS_MC) == "1"
    _load_semester_prefs()
    _element("always-mc-checkbox").checked = runstate.ALWAYS_MULTIPLE_CHOICE
    _element("format-schedule-note").innerText = " ".join(format_schedule_lines())
    _element("always-mc-checkbox").addEventListener("click", create_proxy(on_toggle_always_mc))
    _element("water-options-toggle-button").addEventListener("click", create_proxy(on_toggle_water_options))
    _element("water-options-close-button").addEventListener("click", create_proxy(on_toggle_water_options))
    _element("shop-toggle-button").addEventListener("click", create_proxy(on_toggle_shop))
    _element("shop-close-button").addEventListener("click", create_proxy(on_toggle_shop))
    _element("water-row-select").addEventListener("change", create_proxy(on_water_row_change))
    _element("water-topic-select").addEventListener("change", create_proxy(on_water_topic_change))
    _element("water-opt-next-button").addEventListener("click", create_proxy(on_water_next_option))
    _element("water-opt-row-button").addEventListener("click", create_proxy(on_water_row_start))
    _element("water-opt-topic-button").addEventListener("click", create_proxy(on_water_topic_start))
    _element("water-opt-wilting-button").addEventListener("click", create_proxy(on_water_wilting_start))
    _element("water-opt-mc-button").addEventListener("click", create_proxy(on_water_mc_start))
    _element("water-opt-typed-button").addEventListener("click", create_proxy(on_water_typed_start))
    _element("water-opt-listen-button").addEventListener("click", create_proxy(on_water_listen_start))
    _element("review-listen-button").addEventListener("click", create_proxy(on_review_listen))
    _element("review-listen-show-button").addEventListener("click", create_proxy(on_review_listen_show))
    _element("practice-deepdive-button").addEventListener("click", create_proxy(on_toggle_deepdive))
    _element("review-cram-button").addEventListener("click", create_proxy(on_start_cram_review))
    _element("review-weakspots-button").addEventListener("click", create_proxy(on_start_weak_spot_review))
    _element("phrasebook-toggle-button").addEventListener("click", create_proxy(on_toggle_phrasebook_panel))
    _element("phrasebook-practice-button").addEventListener("click", create_proxy(on_start_phrasebook_review))
    _element("practice-bookmark-button").addEventListener("click", create_proxy(on_bookmark_practice))
    _element("review-bookmark-button").addEventListener("click", create_proxy(on_bookmark_review))
    _element("calendar-prev-button").addEventListener("click", create_proxy(on_calendar_prev))
    _element("calendar-next-button").addEventListener("click", create_proxy(on_calendar_next))
    _element("review-word-button").addEventListener("click", create_proxy(on_start_word_review))
    _element("review-grammar-button").addEventListener(
        "click", create_proxy(on_start_grammar_review)
    )
    _element("quick-water-button").addEventListener("click", create_proxy(on_quick_water))
    _element("sentence-builder-button").addEventListener("click", create_proxy(start_sentence_builder))
    _element("conversation-button").addEventListener("click", create_proxy(start_conversation))
    _element("formats-button").addEventListener("click", create_proxy(on_open_formats))  # FS-17 to FS-22
    _element("formats-next-button").addEventListener("click", create_proxy(next_formats_question))
    _element("formats-close-button").addEventListener("click", create_proxy(close_formats))
    _element("formats-submit-button").addEventListener("click", create_proxy(on_formats_submit))
    _element("formats-input").addEventListener("keydown", create_proxy(on_formats_keydown))
    _element("listening-button").addEventListener("click", create_proxy(start_listening))
    _element("placement-button").addEventListener("click", create_proxy(start_placement))
    _element("placement-start-button").addEventListener("click", create_proxy(begin_placement_test))
    _element("placement-submit-button").addEventListener("click", create_proxy(on_placement_submit_typed))
    _element("placement-answer-input").addEventListener("keydown", create_proxy(on_placement_answer_keydown))
    _element("placement-next-button").addEventListener("click", create_proxy(next_placement_question))
    _element("placement-apply-button").addEventListener("click", create_proxy(on_apply_placement))
    _element("placement-cancel-button").addEventListener("click", create_proxy(close_placement))
    _element("placement-retry-button").addEventListener("click", create_proxy(begin_placement_test))
    _element("placement-close-button").addEventListener("click", create_proxy(close_placement))
    _element("listening-play-button").addEventListener("click", create_proxy(on_listening_play))
    _element("listening-slow-button").addEventListener("click", create_proxy(on_listening_slow))
    _element("listening-next-button").addEventListener("click", create_proxy(next_listening_question))
    _element("listening-close-button").addEventListener("click", create_proxy(close_listening))
    _element("conversation-next-button").addEventListener("click", create_proxy(next_conversation_turn))
    _element("conversation-close-button").addEventListener("click", create_proxy(close_conversation))
    _element("builder-undo-button").addEventListener("click", create_proxy(undo_builder_tile))
    _element("builder-next-button").addEventListener("click", create_proxy(next_builder_sentence))
    _element("builder-close-button").addEventListener("click", create_proxy(close_sentence_builder))
    _element("review-marathon-button").addEventListener(
        "click", create_proxy(on_start_marathon_review)
    )
    _element("study-buddy-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_study_buddy)
    )
    _element("review-submit-button").addEventListener(
        "click", create_proxy(on_review_submit_typed)
    )
    _element("review-answer-input").addEventListener(
        "keydown", create_proxy(on_review_answer_keydown)
    )
    _element("review-next-button").addEventListener("click", create_proxy(next_review_question))
    _element("review-close-button").addEventListener("click", create_proxy(close_review))
    _element("proficiency-submit-button").addEventListener(
        "click", create_proxy(on_proficiency_submit_typed)
    )
    _element("proficiency-answer-input").addEventListener(
        "keydown", create_proxy(on_proficiency_answer_keydown)
    )
    _element("proficiency-next-button").addEventListener(
        "click", create_proxy(next_proficiency_question)
    )
    _element("proficiency-close-button").addEventListener(
        "click", create_proxy(close_proficiency_test)
    )
    _element("liaison-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_liaison_drill)
    )
    _element("liaison-next-button").addEventListener(
        "click", create_proxy(next_liaison_question)
    )
    _element("liaison-close-button").addEventListener(
        "click", create_proxy(close_liaison_drill)
    )
    _element("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    _element("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    _element("legend-toggle-button").addEventListener("click", create_proxy(on_toggle_legend))
    _element("farm-legend-button").addEventListener("click", create_proxy(on_toggle_legend))
    _element("report-log-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_report_log)
    )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()
    # (unlike every *panel*, which gets its `hidden` state re-set on every
    # render()), so it needs its own starting state set here.
    _element("achievement-toast").hidden = True
    _element("bonus-order-continue-button").addEventListener(
        "click", create_proxy(advance_from_order)
    )
    _element("bonus-tile-submit-button").addEventListener(
        "click", create_proxy(on_bonus_tile_submit_typed)
    )
    _element("bonus-tile-answer-input").addEventListener(
        "keydown", create_proxy(on_bonus_tile_answer_keydown)
    )
    _element("bonus-tile-next-button").addEventListener("click", create_proxy(next_bonus_tile))
    _element("bonus-sentence-submit-button").addEventListener(
        "click", create_proxy(on_bonus_sentence_submit_typed)
    )
    _element("bonus-sentence-answer-input").addEventListener(
        "keydown", create_proxy(on_bonus_sentence_answer_keydown)
    )
    _element("bonus-sentence-next-button").addEventListener(
        "click", create_proxy(next_bonus_sentence)
    )
    _element("bonus-close-button").addEventListener("click", create_proxy(close_bonus_section))

    # Milestone 26: report buttons, extended from the main practice panel
    # into Review, Proficiency, and Bonus's tile/sentence tasks.
    _element("review-report-button").addEventListener("click", create_proxy(submit_review_report))
    _element("review-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_review_pronunciation_report)
    )
    _element("proficiency-report-button").addEventListener(
        "click", create_proxy(submit_proficiency_report)
    )
    _element("proficiency-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_proficiency_pronunciation_report)
    )
    _element("bonus-tile-report-button").addEventListener(
        "click", create_proxy(submit_bonus_tile_report)
    )
    _element("bonus-tile-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_bonus_tile_pronunciation_report)
    )
    _element("bonus-sentence-report-button").addEventListener(
        "click", create_proxy(submit_bonus_sentence_report)
    )
    _element("bonus-sentence-pronunciation-report-button").addEventListener(
        "click", create_proxy(submit_bonus_sentence_pronunciation_report)
    )

    # Milestones 27-30: the arcade minigame family -- hand in the live farm
    # plus the two question-generation functions every minigame reuses, then
    # let minigames.py wire its own DOM listeners entirely on its own (see
    # that module's docstring for why it stays fully self-contained).
    minigames.configure(
        state,
        generate_question,
        variants_for,
        record_practice,
        credit_plot_fn=credit_game_plot_id,
        credit_item_fn=credit_game_item,
        credit_reset_fn=reset_growth_credit,
        credit_text_fn=growth_credit_text,
        plot_for_fr_fn=plot_for_fr,
        pref_get_fn=pref_get,
        pref_set_fn=pref_set,
        check_answer_fn=check_question_answer,
    )
    minigames.configure_speech(speak_french, speech_available)
    minigames.on_amis_loaded = render
    render_growth_markers()
    minigames.setup()

    render()
