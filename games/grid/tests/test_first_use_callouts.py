"""C20: one-time first-use callouts for Retire's refund math and
Maintain's cost math, so the explanation isn't left only inside the small
"i" tooltip. Each shows once, the first time that action actually
succeeds, is dismissible, and never reappears once dismissed or once a
save already has the persisted "seen" flag set (no re-flash on load)."""


def test_callouts_hidden_on_a_fresh_game(game_env):
    assert game_env.elements["retire-callout"].hidden is True
    assert game_env.elements["maintain-callout"].hidden is True


def test_retire_callout_appears_on_first_successful_retire(game_env):
    game_env.build("coal")
    assert game_env.elements["retire-callout"].hidden is True
    game_env.retire("coal")
    assert game_env.elements["retire-callout"].hidden is False


def test_retire_callout_does_not_appear_for_a_failed_retire(game_env):
    # No coal built -- retire_plant() returns False, nothing to show yet.
    game_env.retire("coal")
    assert game_env.elements["retire-callout"].hidden is True
    assert game_env.state.seen_retire_callout is False


def test_maintain_callout_appears_on_first_successful_maintain(game_env):
    game_env.build("coal")
    assert game_env.elements["maintain-callout"].hidden is True
    game_env.maintain("coal")
    assert game_env.elements["maintain-callout"].hidden is False


def test_retire_callout_is_dismissible(game_env):
    game_env.build("coal")
    game_env.retire("coal")
    assert game_env.elements["retire-callout"].hidden is False
    game_env.elements["retire-callout-dismiss-button"].dispatch("click", None)
    assert game_env.elements["retire-callout"].hidden is True


def test_maintain_callout_is_dismissible(game_env):
    game_env.build("coal")
    game_env.maintain("coal")
    game_env.elements["maintain-callout-dismiss-button"].dispatch("click", None)
    assert game_env.elements["maintain-callout"].hidden is True


def test_retire_callout_does_not_reappear_after_being_seen(game_env):
    game_env.build("coal")
    game_env.build("coal")
    game_env.retire("coal")  # shows + dismisses would both flip the flag
    game_env.elements["retire-callout-dismiss-button"].dispatch("click", None)
    game_env.retire("coal")  # a second retire -- already seen, must not re-show
    assert game_env.elements["retire-callout"].hidden is True


def test_seen_flags_round_trip_through_save_load(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.retire("coal")
    snapshot = module.get_state()
    assert snapshot["seen_retire_callout"] is True
    assert snapshot["seen_maintain_callout"] is False

    module.load_state(snapshot)
    assert module.state.seen_retire_callout is True


def test_loading_a_save_with_the_seen_flag_does_not_flash_the_callout(game_env):
    """A returning player who already saw this once shouldn't see it
    flash again just from loading their save."""
    module = game_env.module
    game_env.build("coal")
    game_env.retire("coal")
    game_env.elements["retire-callout-dismiss-button"].dispatch("click", None)
    snapshot = module.get_state()

    module.load_state(snapshot)

    assert game_env.elements["retire-callout"].hidden is True
