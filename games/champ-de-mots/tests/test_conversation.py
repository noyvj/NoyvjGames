"""L5 -- the conversation simulator: scripted dialogues built from catalog phrases."""


def _play_perfectly(m):
    while m.conversation_turn < len(m.conversation["turns"]):
        correct = m.conversation["turns"][m.conversation_turn]["options"][0]
        m.pick_conversation_line(m.conversation_choices.index(correct))
        m.next_conversation_turn()


def test_every_dialogue_is_well_formed(game_env):
    m = game_env.module
    topic_ids = {t["id"] for w in m.CATALOG["weeks"] for t in w["topics"]}
    ids = [c["id"] for c in m.CONVERSATIONS]
    assert len(ids) == len(set(ids)) >= 5
    for c in m.CONVERSATIONS:
        assert c["title"] and c["turns"], c["id"]
        assert set(c["topics"]) <= topic_ids, c["id"]
        for turn in c["turns"]:
            assert ("npc" in turn) != ("cue" in turn), (c["id"], turn)
            if "npc" in turn:
                assert turn["gloss"]
            assert len(turn["options"]) == 3 and len(set(turn["options"])) == 3, (c["id"], turn)


def test_a_dialogue_opens_only_when_all_its_topics_are_unlocked(game_env):
    m = game_env.module
    first = m.CONVERSATIONS[0]
    assert m.conversation_available(first)
    game_env.state.is_row_unlocked = lambda sequence: False
    assert m.available_conversations() == []
    game_env.state.is_row_unlocked = lambda sequence: sequence <= 1
    assert all(
        all(m._topic_sequence(t) <= 1 for t in c["topics"]) for c in m.available_conversations()
    )


def test_button_opens_a_dialogue_with_shuffled_options(game_env):
    m = game_env.module
    game_env.elements["conversation-button"].dispatch("click", None)
    assert m.conversation_active and m.conversation is not None
    assert game_env.elements["conversation-panel"].hidden is False
    assert sorted(m.conversation_choices) == sorted(m.conversation["turns"][0]["options"])
    assert game_env.elements["conversation-title"].innerText == m.conversation["title"]


def test_a_fitting_reply_scores_and_a_wrong_one_shows_the_right_line(game_env):
    m = game_env.module
    m.start_conversation(conversation_id="meeting")
    turn = m.conversation["turns"][0]
    assert m.pick_conversation_line(m.conversation_choices.index(turn["options"][0])) is True
    assert game_env.elements["conversation-feedback"].innerText == m.CONVERSATION_CORRECT
    m.next_conversation_turn()
    turn = m.conversation["turns"][1]
    wrong = m.conversation_choices.index(turn["options"][1])
    before = m.practice_score()
    assert m.pick_conversation_line(wrong) is False
    assert turn["options"][0] in game_env.elements["conversation-feedback"].innerText
    assert m.practice_score() == before  # a wrong pick earns nothing
    assert m.practice_ledger["conversation"]["total"] == 2
    assert m.practice_ledger["conversation"]["correct"] == 1


def test_cannot_pick_twice_or_skip_ahead(game_env):
    m = game_env.module
    m.start_conversation(conversation_id="meeting")
    assert m.next_conversation_turn() is None  # not answered yet
    assert m.pick_conversation_line(99) is None
    m.pick_conversation_line(0)
    assert m.pick_conversation_line(1) is None  # already answered


def test_a_perfect_run_ends_in_the_summary(game_env):
    m = game_env.module
    m.start_conversation(conversation_id="shopping")
    total = len(m.conversation["turns"])
    _play_perfectly(m)
    assert m.conversation_score == {"correct": total, "total": total}
    summary = game_env.elements["conversation-summary"]
    assert summary.hidden is False and f"{total}/{total}" in summary.innerText
    assert game_env.elements["conversation-card"].hidden is True


def test_answer_buttons_render_and_lock_after_answering(game_env):
    m = game_env.module
    m.start_conversation(conversation_id="restaurant")
    box = game_env.elements["conversation-choices"]
    assert len(box.children) == 3 and not any(child.disabled for child in box.children)
    m.pick_conversation_line(0)
    assert all(child.disabled for child in game_env.elements["conversation-choices"].children)


def test_a_different_dialogue_is_preferred_next_time(game_env):
    m = game_env.module
    m.start_conversation()
    first = m.conversation["id"]
    for _ in range(10):
        m.start_conversation()
        assert m.conversation["id"] != first
        first = m.conversation["id"]


def test_nothing_unlocked_shows_the_empty_message(game_env):
    m = game_env.module
    game_env.state.is_row_unlocked = lambda sequence: False
    m.start_conversation()
    assert m.conversation is None
    empty = game_env.elements["conversation-empty-message"]
    assert empty.hidden is False and empty.innerText == m.CONVERSATION_EMPTY_MESSAGE


def test_close_resets_and_it_never_touches_a_plot(game_env):
    m = game_env.module
    snapshot = [(p.stage, p.last_reviewed, p.correct_streak) for p in game_env.state.plots]
    m.start_conversation(conversation_id="meeting")
    m.pick_conversation_line(0)
    game_env.elements["conversation-close-button"].dispatch("click", None)
    assert m.conversation_active is False and m.conversation is None
    assert game_env.elements["conversation-panel"].hidden is True
    assert [(p.stage, p.last_reviewed, p.correct_streak) for p in game_env.state.plots] == snapshot


def test_it_is_a_practice_mode(game_env):
    m = game_env.module
    assert "conversation" in m.PRACTICE_MODES
    assert set(m.practice_ledger) == set(m.PRACTICE_MODES)
