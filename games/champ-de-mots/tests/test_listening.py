"""L9 -- listening comprehension: the browser speaks a French sentence, you
pick its meaning. Speech is faked here through the page's champSpeak hook."""

import sys
import types


class _FakeSpeaker:
    def __init__(self):
        self.spoken = []

    def champSpeak(self, text, slow):  # noqa: N802 -- mirrors the JS hook's name
        self.spoken.append((text, slow))

    def champSpeechAvailable(self):  # noqa: N802
        return True


def _install_speech():
    speaker = _FakeSpeaker()
    sys.modules["js"].window = types.SimpleNamespace(
        champSpeak=speaker.champSpeak, champSpeechAvailable=speaker.champSpeechAvailable
    )
    return speaker


def _answer_correctly(m):
    correct = m.listening_queue[m.listening_index]["en"]
    return m.pick_listening_answer(m.listening_choices.index(correct))


def test_it_is_a_practice_mode(game_env):
    m = game_env.module
    assert "listening" in m.PRACTICE_MODES
    assert set(m.practice_ledger) == set(m.PRACTICE_MODES)


def test_without_speech_it_says_so_instead_of_starting(game_env):
    m = game_env.module
    assert m.speech_available() is False
    m.start_listening()
    assert m.listening_queue == []
    empty = game_env.elements["listening-empty-message"]
    assert empty.hidden is False and empty.innerText == m.LISTENING_UNAVAILABLE_MESSAGE
    assert game_env.elements["listening-card"].hidden is True


def test_a_session_speaks_the_first_sentence_and_offers_three_meanings(game_env):
    m = game_env.module
    speaker = _install_speech()
    game_env.elements["listening-button"].dispatch("click", None)
    assert m.listening_active and 1 <= len(m.listening_queue) <= m.LISTENING_SESSION_LENGTH
    sentence = m.listening_queue[0]
    assert speaker.spoken == [(sentence["fr"], False)]
    assert len(m.listening_choices) == 3 and len(set(m.listening_choices)) == 3
    assert sentence["en"] in m.listening_choices


def test_play_and_slower_replay_the_same_sentence(game_env):
    m = game_env.module
    speaker = _install_speech()
    m.start_listening()
    game_env.elements["listening-play-button"].dispatch("click", None)
    game_env.elements["listening-slow-button"].dispatch("click", None)
    fr = m.listening_queue[0]["fr"]
    assert speaker.spoken[1:] == [(fr, False), (fr, True)]


def test_right_and_wrong_answers_score_correctly(game_env):
    m = game_env.module
    _install_speech()
    m.start_listening()
    before = m.practice_score()
    assert _answer_correctly(m) is True
    assert game_env.elements["listening-feedback"].innerText == m.LISTENING_CORRECT
    assert m.practice_score() == before + 1
    m.next_listening_question()
    sentence = m.listening_queue[1]
    wrong = next(i for i, c in enumerate(m.listening_choices) if c != sentence["en"])
    assert m.pick_listening_answer(wrong) is False
    assert sentence["fr"] in game_env.elements["listening-feedback"].innerText
    assert m.practice_ledger["listening"]["total"] == 2 and m.practice_ledger["listening"]["correct"] == 1
    assert m.pick_listening_answer(0) is None  # already answered


def test_walks_to_a_summary_and_speaks_each_new_sentence(game_env):
    m = game_env.module
    speaker = _install_speech()
    m.start_listening()
    total = len(m.listening_queue)
    for _ in range(total):
        _answer_correctly(m)
        m.next_listening_question()
    assert len(speaker.spoken) == total
    summary = game_env.elements["listening-summary"]
    assert summary.hidden is False and f"{total}/{total}" in summary.innerText


def test_nothing_unlocked_shows_the_empty_message(game_env):
    m = game_env.module
    _install_speech()
    game_env.state.is_row_unlocked = lambda sequence: False
    m.start_listening()
    assert m.listening_queue == []
    assert game_env.elements["listening-empty-message"].innerText == m.LISTENING_EMPTY_MESSAGE


def test_close_resets_and_never_touches_a_plot(game_env):
    m = game_env.module
    _install_speech()
    snapshot = [(p.stage, p.last_reviewed, p.correct_streak) for p in game_env.state.plots]
    m.start_listening()
    _answer_correctly(m)
    game_env.elements["listening-close-button"].dispatch("click", None)
    assert m.listening_active is False and m.listening_queue == []
    assert game_env.elements["listening-panel"].hidden is True
    assert [(p.stage, p.last_reviewed, p.correct_streak) for p in game_env.state.plots] == snapshot
