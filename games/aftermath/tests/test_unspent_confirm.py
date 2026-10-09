"""E-28: the optional 'keep N resources unspent?' check before Face Next Event (default OFF)."""

from .test_confirm_dialog import install_fake_confirm_dialog


def _enable(game_env):
    game_env.module.localStorage.setItem(game_env.module.CONFIRM_UNSPENT_STORAGE_KEY, "true")


def test_off_by_default_so_resolving_never_asks(game_env):
    fake = install_fake_confirm_dialog()
    game_env.resolve_event()
    assert fake.ConfirmDialog.calls == []
    assert game_env.run.event_index == 1


def test_when_on_it_asks_and_the_event_waits_for_the_answer(game_env):
    _enable(game_env)
    fake = install_fake_confirm_dialog()
    game_env.resolve_event()
    assert game_env.run.event_index == 0 and len(fake.ConfirmDialog.calls) == 1
    call = fake.ConfirmDialog.calls[0]
    assert call["id"] == "aftermath-unspent-resources"
    assert "Keep 200 resources unspent?" in call["message"]
    assert "up to 8 resilience" in call["message"] and "up to 10 growth" in call["message"]
    assert "Flood" in call["message"]
    assert call["allowSkip"] is False
    fake.ConfirmDialog.confirm()
    assert game_env.run.event_index == 1


def test_cancelling_leaves_the_run_untouched(game_env):
    _enable(game_env)
    install_fake_confirm_dialog()
    before = game_env.module.get_state()
    game_env.resolve_event()  # dialog pending, never confirmed
    assert game_env.module.get_state() == before


def test_it_does_not_ask_when_nothing_is_worth_spending(game_env):
    m = game_env.module
    _enable(game_env)
    fake = install_fake_confirm_dialog()
    m.run.resources = 15.0  # cannot afford even one growth unit (20)
    game_env.resolve_event()
    assert fake.ConfirmDialog.calls == [] and m.run.event_index == 1


def test_it_does_not_ask_once_the_run_is_complete(game_env):
    m = game_env.module
    _enable(game_env)
    assert m.unspent_confirm_message(m.run) is not None
    m.run.event_index = len(m.run.schedule)
    assert m.unspent_confirm_message(m.run) is None


def test_without_a_dialog_available_it_resolves_straight_away(game_env):
    _enable(game_env)  # no fake window installed: the helper falls through
    game_env.resolve_event()
    assert game_env.run.event_index == 1


def test_the_message_only_names_what_is_affordable(game_env):
    m = game_env.module
    m.run.resources = 22.0
    message = m.unspent_confirm_message(m.run)
    assert "up to 1 growth" in message and "resilience" not in message
