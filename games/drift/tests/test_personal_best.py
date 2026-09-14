"""Addendum I10: a locally-stored "best run" stat (highest
wellbeing_score() any session on this device has ever reached),
persisted via localStorage -- same pattern as Thaw's G19/Canopy's
B14/Tide's D13. Deliberately not part of get_state()/the save-code
system: this is a per-browser record across every session/save on this
device, not one save's snapshot.

The pytest fake `js` module has no localStorage, so
_read_local_storage_item/_write_local_storage_item degrade to a no-op
in every test here -- this file exercises the pure defaulting/update
logic (load_personal_best, _maybe_update_personal_best,
render_personal_best), not real browser storage.
"""


def test_load_personal_best_defaults_to_zero_without_storage(game_env):
    assert game_env.module.load_personal_best() == {"wellbeing_score": 0.0}


def test_personal_best_reflects_initial_render(game_env):
    # setup() calls render() at import time, which already bumps
    # personal_best to the fresh region's starting wellbeing_score()
    # (load_personal_best() itself still defaults to zero -- see the
    # test above -- but render() runs immediately after).
    assert game_env.module.personal_best["wellbeing_score"] == game_env.region.wellbeing_score()


def test_maybe_update_personal_best_bumps_on_higher_score(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 1000.0  # economic_health -> 100, others 100/0 by default
    module._maybe_update_personal_best()
    assert module.personal_best["wellbeing_score"] == region.wellbeing_score()


def test_maybe_update_personal_best_never_decreases(game_env):
    module = game_env.module
    region = game_env.region
    region.funds = 1000.0
    module._maybe_update_personal_best()
    best_after_high = module.personal_best["wellbeing_score"]

    region.funds = 0.0  # wellbeing_score() now lower
    module._maybe_update_personal_best()
    assert module.personal_best["wellbeing_score"] == best_after_high


def test_render_personal_best_sets_display_text(game_env):
    game_env.module.render()
    text = game_env.elements["personal-best-display"].innerText
    assert "Personal best" in text


def test_render_updates_personal_best_display_after_wellbeing_rises(game_env):
    game_env.region.funds = 1000.0
    game_env.module.render()
    text = game_env.elements["personal-best-display"].innerText
    assert str(round(game_env.region.wellbeing_score())) in text
