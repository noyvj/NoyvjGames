"""Milestone 26: the two report mechanisms from the main practice panel
(Milestone 9's "I think this should count" correctness report, Milestone
24's "Report a pronunciation concern" button), extended into Review,
Proficiency, and Bonus (tasks 2 and 3). Reported directly from live play --
see CLAUDE.md's Milestone 26 build note for why Milestone 11's original
"not in scope" call was revisited.

Mirrors tests/test_report_button.py and tests/test_pronunciation_reports.py,
adapted per mode. Same trust boundary as those: the actual network POST is
out of scope for this fake-DOM harness (js.window doesn't exist here), so
these pin the payload's shape and the buttons' visibility/one-shot behaviour
instead.
"""


# --- helpers: land on a typed-mode question in each mode --------------------


def _open_typed_review_question(game_env, mode="word"):
    module = game_env.module
    game_env.elements["review-count-input"].value = "50"
    module.start_review(mode)
    guard = 0
    while (
        module.review_question is not None
        and module.review_question["mode"] != "typed"
        and guard < 100
    ):
        module.submit_review_answer(module.review_question["answer"])
        module.next_review_question()
        guard += 1
    return module.review_question


def _open_typed_proficiency_question(game_env, sequence=1):
    module = game_env.module
    module.start_proficiency_test(sequence)
    guard = 0
    while module.proficiency_index < len(module.proficiency_questions) and guard < 100:
        question = module.proficiency_questions[module.proficiency_index]["question"]
        if question["mode"] == "typed":
            return question
        module.submit_proficiency_answer(question["answer"])
        module.next_proficiency_question()
        guard += 1
    return None


def _complete_order_task(module):
    sentence = module.bonus_queue[module.bonus_index]
    for tile in sentence["tiles"]:
        index = next(
            i for i, t in enumerate(module.bonus_tile_pool) if t["fr"] == tile["fr"]
        )
        module.place_bonus_tile(index)
    module.advance_from_order()


def _complete_tile_task(module):
    sentence = module.bonus_queue[module.bonus_index]
    for tile in sentence["tiles"]:
        module.submit_bonus_tile_translation(tile["en"])
        module.next_bonus_tile()


# --- Review ------------------------------------------------------------


def test_review_report_button_hidden_before_any_answer(game_env):
    game_env, module = game_env, game_env.module
    _open_typed_review_question(game_env)
    module.render()
    assert game_env.elements["review-report-button"].hidden is True


def test_review_report_button_appears_on_a_wrong_typed_answer(game_env):
    module = game_env.module
    question = _open_typed_review_question(game_env)
    assert question is not None, "catalog should offer a typed Word Review question"
    module.submit_review_answer("definitely not the answer 12345")
    assert module.review_result is False
    assert game_env.elements["review-report-button"].hidden is False


def test_review_report_button_hidden_for_a_correct_answer(game_env):
    module = game_env.module
    question = _open_typed_review_question(game_env)
    module.submit_review_answer(question["answer"])
    assert module.review_result is True
    assert game_env.elements["review-report-button"].hidden is True


def test_review_report_payload_matches_the_documented_shape(game_env):
    module = game_env.module
    question = _open_typed_review_question(game_env)
    module.submit_review_answer("wrong answer")

    payload = module._review_report_payload()
    assert set(payload) == {
        "game_id", "item_id", "submitted_answer", "marked_correct_answer", "topic_type",
    }
    assert payload["item_id"] == question["plot_id"]
    assert payload["submitted_answer"] == "wrong answer"
    # The canonical answer always leads the list; a LENIENT item may also
    # contribute its own generated accepted-variant phrasings after it
    # (see _typed_wrong_report_payload()), which this question is picked at
    # random from Review's own queue and so isn't guaranteed to avoid.
    assert payload["marked_correct_answer"][0] == question["answer"]
    assert payload["topic_type"] == question["topic_type"]


def test_submit_review_report_is_one_shot(game_env):
    module = game_env.module
    _open_typed_review_question(game_env)
    module.submit_review_answer("wrong answer")

    button = game_env.elements["review-report-button"]
    button.dispatch("click", None)
    assert module.review_report_sent is True
    assert button.disabled is True

    assert module.submit_review_report() is None  # nothing new to send


def test_review_report_state_resets_on_the_next_question(game_env):
    module = game_env.module
    _open_typed_review_question(game_env)
    module.submit_review_answer("wrong answer")
    module.submit_review_report()
    assert module.review_report_sent is True

    module.next_review_question()
    assert module.review_report_sent is False
    assert module.review_pronunciation_report_sent is False


def test_review_pronunciation_report_available_regardless_of_result(game_env):
    module, state = game_env.module, game_env.state
    game_env.elements["review-count-input"].value = "1"
    module.start_review("word")
    question = module.review_question
    module.submit_review_answer(question["answer"])
    assert module.review_result is True
    assert game_env.elements["review-pronunciation-report-button"].hidden is False

    payload = module.submit_review_pronunciation_report()
    plot = state.plots_by_id[question["plot_id"]]
    assert payload["item_id"] == question["plot_id"]
    assert payload["marked_correct_answer"] == [plot.items[0]["fr"]]
    assert payload["topic_type"] == "pronunciation"
    assert module.review_pronunciation_report_sent is True


def test_review_reports_are_hidden_once_the_panel_closes(game_env):
    module = game_env.module
    _open_typed_review_question(game_env)
    module.submit_review_answer("wrong answer")
    module.close_review()
    assert game_env.elements["review-report-button"].hidden is True
    assert game_env.elements["review-pronunciation-report-button"].hidden is True


def test_no_review_report_payload_with_nothing_open(game_env):
    module = game_env.module
    assert module._review_report_payload() is None
    assert module.submit_review_pronunciation_report() is None


# --- Proficiency ---------------------------------------------------------


def test_proficiency_report_button_appears_on_a_wrong_typed_answer(game_env):
    module = game_env.module
    question = _open_typed_proficiency_question(game_env)
    assert question is not None, "a full week's proficiency test should offer a typed question"
    module.submit_proficiency_answer("definitely not the answer 12345")
    assert module.proficiency_result is False
    assert game_env.elements["proficiency-report-button"].hidden is False


def test_proficiency_report_button_hidden_for_a_correct_answer(game_env):
    module = game_env.module
    question = _open_typed_proficiency_question(game_env)
    module.submit_proficiency_answer(question["answer"])
    assert module.proficiency_result is True
    assert game_env.elements["proficiency-report-button"].hidden is True


def test_proficiency_report_payload_matches_the_documented_shape(game_env):
    module = game_env.module
    question = _open_typed_proficiency_question(game_env)
    module.submit_proficiency_answer("wrong answer")

    payload = module._proficiency_report_payload()
    assert payload["item_id"] == question["plot_id"]
    assert payload["submitted_answer"] == "wrong answer"
    assert payload["marked_correct_answer"][0] == question["answer"]
    assert payload["topic_type"] == question["topic_type"]


def test_submit_proficiency_report_is_one_shot(game_env):
    module = game_env.module
    _open_typed_proficiency_question(game_env)
    module.submit_proficiency_answer("wrong answer")

    button = game_env.elements["proficiency-report-button"]
    button.dispatch("click", None)
    assert module.proficiency_report_sent is True
    assert button.disabled is True
    assert module.submit_proficiency_report() is None


def test_proficiency_report_state_resets_on_the_next_question(game_env):
    module = game_env.module
    _open_typed_proficiency_question(game_env)
    module.submit_proficiency_answer("wrong answer")
    module.submit_proficiency_report()
    assert module.proficiency_report_sent is True

    module.next_proficiency_question()
    assert module.proficiency_report_sent is False
    assert module.proficiency_pronunciation_report_sent is False


def test_proficiency_pronunciation_report_available_regardless_of_result(game_env):
    module = game_env.module
    module.start_proficiency_test(1)
    question = module.proficiency_questions[0]["question"]
    module.submit_proficiency_answer(question["answer"])
    assert module.proficiency_result is True
    assert game_env.elements["proficiency-pronunciation-report-button"].hidden is False

    payload = module.submit_proficiency_pronunciation_report()
    plot = module.state.plots_by_id[question["plot_id"]]
    assert payload["marked_correct_answer"] == [plot.items[0]["fr"]]
    assert payload["topic_type"] == "pronunciation"


def test_proficiency_reports_hidden_once_the_test_closes(game_env):
    module = game_env.module
    _open_typed_proficiency_question(game_env)
    module.submit_proficiency_answer("wrong answer")
    module.close_proficiency_test()
    assert game_env.elements["proficiency-report-button"].hidden is True
    assert game_env.elements["proficiency-pronunciation-report-button"].hidden is True


def test_no_proficiency_report_payload_with_nothing_open(game_env):
    module = game_env.module
    assert module._proficiency_report_payload() is None
    assert module.submit_proficiency_pronunciation_report() is None


# --- Bonus: task 2 (tile translation) -------------------------------------


def test_bonus_tile_report_button_appears_on_a_wrong_answer(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    module.submit_bonus_tile_translation("absolutely not the right answer")
    assert module.bonus_tile_result is False
    assert game_env.elements["bonus-tile-report-button"].hidden is False


def test_bonus_tile_report_button_hidden_for_a_correct_answer(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    module.submit_bonus_tile_translation(sentence["tiles"][0]["en"])
    assert module.bonus_tile_result is True
    assert game_env.elements["bonus-tile-report-button"].hidden is True


def test_bonus_tile_report_payload_names_the_sentence_and_tile(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    module.submit_bonus_tile_translation("nope")

    payload = module._bonus_tile_report_payload()
    assert payload["item_id"] == f"{sentence['id']}-tile-0"
    assert payload["submitted_answer"] == "nope"
    assert sentence["tiles"][0]["en"] in payload["marked_correct_answer"]
    assert payload["topic_type"] == module.BONUS_TILE_REPORT_TOPIC_TYPE


def test_submit_bonus_tile_report_is_one_shot(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    module.submit_bonus_tile_translation("nope")

    button = game_env.elements["bonus-tile-report-button"]
    button.dispatch("click", None)
    assert module.bonus_tile_report_sent is True
    assert button.disabled is True
    assert module.submit_bonus_tile_report() is None


def test_bonus_tile_report_state_resets_on_the_next_tile(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    if len(sentence["tiles"]) < 2:
        return  # nothing to advance into
    module.submit_bonus_tile_translation("nope")
    module.submit_bonus_tile_report()
    assert module.bonus_tile_report_sent is True

    module.next_bonus_tile()
    assert module.bonus_tile_report_sent is False
    assert module.bonus_tile_pronunciation_report_sent is False


def test_bonus_tile_pronunciation_report_available_regardless_of_result(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    tile = sentence["tiles"][0]
    module.submit_bonus_tile_translation(tile["en"])
    assert module.bonus_tile_result is True
    assert game_env.elements["bonus-tile-pronunciation-report-button"].hidden is False

    payload = module.submit_bonus_tile_pronunciation_report()
    assert payload["item_id"] == f"{sentence['id']}-tile-0"
    assert payload["marked_correct_answer"] == [tile["fr"]]
    assert payload["topic_type"] == "pronunciation"


def test_bonus_tile_reports_hidden_during_the_order_task(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    assert module.bonus_task == "order"
    assert game_env.elements["bonus-tile-report-button"].hidden is True
    assert game_env.elements["bonus-tile-pronunciation-report-button"].hidden is True
    assert module._bonus_tile_report_payload() is None
    assert module._bonus_tile_pronunciation_report_payload() is None


# --- Bonus: task 3 (whole-sentence translation) ---------------------------


def test_bonus_sentence_report_button_appears_on_a_wrong_answer(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    module.submit_bonus_sentence_translation("nothing at all like it")
    assert module.bonus_sentence_result is False
    assert game_env.elements["bonus-sentence-report-button"].hidden is False


def test_bonus_sentence_report_payload_names_the_sentence(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    module.submit_bonus_sentence_translation("nope")

    payload = module._bonus_sentence_report_payload()
    assert payload["item_id"] == sentence["id"]
    assert payload["submitted_answer"] == "nope"
    assert sentence["en"] in payload["marked_correct_answer"]
    assert payload["topic_type"] == module.BONUS_SENTENCE_REPORT_TOPIC_TYPE


def test_submit_bonus_sentence_report_is_one_shot(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    module.submit_bonus_sentence_translation("nope")

    button = game_env.elements["bonus-sentence-report-button"]
    button.dispatch("click", None)
    assert module.bonus_sentence_report_sent is True
    assert button.disabled is True
    assert module.submit_bonus_sentence_report() is None


def test_bonus_sentence_pronunciation_report_available_regardless_of_result(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    module.submit_bonus_sentence_translation(sentence["en"])
    assert module.bonus_sentence_result is True
    assert game_env.elements["bonus-sentence-pronunciation-report-button"].hidden is False

    payload = module.submit_bonus_sentence_pronunciation_report()
    assert payload["item_id"] == sentence["id"]
    assert payload["marked_correct_answer"] == [sentence["fr"]]
    assert payload["topic_type"] == "pronunciation"


def test_bonus_sentence_reports_reset_on_the_next_sentence(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    sentence = module.bonus_queue[module.bonus_index]
    module.submit_bonus_sentence_translation("nope")
    module.submit_bonus_sentence_report()
    assert module.bonus_sentence_report_sent is True

    module.next_bonus_sentence()
    assert module.bonus_sentence_report_sent is False
    assert module.bonus_sentence_pronunciation_report_sent is False


def test_bonus_reports_hidden_once_the_section_closes(game_env):
    module = game_env.module
    module.start_bonus_section(1)
    _complete_order_task(module)
    _complete_tile_task(module)
    module.submit_bonus_sentence_translation("nope")
    module.close_bonus_section()
    assert game_env.elements["bonus-sentence-report-button"].hidden is True
    assert game_env.elements["bonus-sentence-pronunciation-report-button"].hidden is True
    assert game_env.elements["bonus-tile-report-button"].hidden is True
    assert game_env.elements["bonus-tile-pronunciation-report-button"].hidden is True


def test_no_bonus_report_payloads_with_nothing_open(game_env):
    module = game_env.module
    assert module._bonus_tile_report_payload() is None
    assert module._bonus_sentence_report_payload() is None
    assert module.submit_bonus_tile_pronunciation_report() is None
    assert module.submit_bonus_sentence_pronunciation_report() is None
