"""Every minigame has a Slower / Normal / Faster setting (2026-10-08): it changes
the pressure (timer, lives, the rival's pace, the patience clock) and nothing
about the watering rule; it is remembered per game in this browser; the ledger
points do not scale with it, the game score does a little."""

import pytest

ALL = ("blitz", "racer", "boutique", "cafe", "sprint", "pairs", "gaps", "listenpick", "wordorder")


def _prefs(module):
    stored = {}
    module.minigames._pref_set = lambda key, value: stored.__setitem__(key, value)
    module.minigames._pref_get = lambda key: stored.get(key)
    return stored


def _select(game_env, key, level):
    select = game_env.elements[f"{key}-difficulty-select"]
    select.value = level
    select.dispatch("change", None)


@pytest.mark.parametrize("key", ALL)
def test_every_game_has_a_difficulty_select_with_three_levels(game_env, key):
    select = game_env.elements[f"{key}-difficulty-select"]
    assert [option.value for option in select.children] == ["slower", "normal", "faster"]
    assert [option.innerText for option in select.children] == ["Slower", "Normal", "Faster"]
    assert select.value == "normal"
    assert game_env.module.minigames.get_difficulty(key) == "normal"


@pytest.mark.parametrize("key", ALL)
def test_choosing_a_level_is_remembered_per_game(game_env, key):
    module = game_env.module
    stored = _prefs(module)
    _select(game_env, key, "slower")
    assert module.minigames.get_difficulty(key) == "slower"
    assert stored == {f"champ-difficulty-{key}": "slower"}
    other = next(k for k in ALL if k != key)
    assert module.minigames.get_difficulty(other) == "normal"  # per game, not global


def test_a_remembered_level_is_read_back_from_the_browsers_preferences(game_env):
    module = game_env.module
    mg = module.minigames
    mg._difficulty.clear()
    mg._pref_get = lambda key: {"champ-difficulty-blitz": "faster", "champ-difficulty-cafe": "garbage"}.get(key)
    assert mg.get_difficulty("blitz") == "faster"
    assert mg.get_difficulty("cafe") == "normal"  # junk falls back
    assert mg.get_difficulty("racer") == "normal"
    assert mg.set_difficulty("racer", "nonsense") == "normal"


def test_the_note_names_what_each_level_means(game_env):
    module = game_env.module
    mg = module.minigames
    mg.on_toggle_blitz()
    note = game_env.elements["blitz-difficulty-note"]
    assert note.innerText == "Normal: 60 seconds and 3 lives."
    _select(game_env, "blitz", "slower")
    assert note.innerText == "Slower: 90 seconds and 5 lives."
    _select(game_env, "blitz", "faster")
    assert note.innerText == "Faster: 45 seconds and 2 lives."


def test_the_select_is_locked_while_a_run_is_going(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_blitz()
    assert game_env.elements["blitz-difficulty-select"].disabled is True
    mg._end_blitz(mg.BLITZ_END_TIME)
    mg.render()
    assert game_env.elements["blitz-difficulty-select"].disabled is False


# --- the pressure really changes -----------------------------------------------------------------


def test_blitz_and_sprint_get_more_time_and_lives_when_slower(game_env):
    module = game_env.module
    mg = module.minigames
    for start, key, seconds_attr, lives_attr in (
        (mg.start_blitz, "blitz", "blitz_time_remaining", "blitz_lives"),
        (mg.start_sprint, "sprint", "sprint_time_remaining", "sprint_lives"),
    ):
        results = {}
        for level in ("slower", "normal", "faster"):
            mg.set_difficulty(key, level)
            start()
            results[level] = (getattr(mg, seconds_attr), getattr(mg, lives_attr))
        assert results["normal"] == (60, 3)
        assert results["slower"][0] > 60 > results["faster"][0]
        assert results["slower"][1] > 3 > results["faster"][1]
        assert results["slower"] == (90, 5)  # genuinely relaxed


def test_the_racers_rival_steps_slower_or_faster(game_env):
    module = game_env.module
    mg = module.minigames
    steps = {}
    for level in ("slower", "normal", "faster"):
        mg.set_difficulty("racer", level)
        mg.start_racer()
        for _ in range(12):
            mg.racer_tick()
        steps[level] = mg.racer_rival_position
        mg.close_racer()
    assert steps["slower"] < steps["normal"] < steps["faster"]
    assert steps == {"slower": 2, "normal": 4, "faster": 6}  # one step every 5 / 3 / 2 seconds


def test_shop_patience_is_longer_when_slower_and_never_shorter_than_its_floor(game_env):
    module = game_env.module
    mg = module.minigames
    for key, start, patience in (
        ("boutique", mg.start_boutique, lambda: mg.boutique_patience_max),
        ("cafe", mg.start_cafe, lambda: mg.cafe_patience_max),
    ):
        values = {}
        for level in ("slower", "normal", "faster"):
            mg.set_difficulty(key, level)
            start()
            values[level] = patience()
        assert values["slower"] == 18 > values["normal"] == 12 > values["faster"] == 8


def test_boutique_patience_floor_follows_the_level(game_env):
    module = game_env.module
    mg = module.minigames
    mg.set_difficulty("boutique", "slower")
    mg.start_boutique()
    for _ in range(14):
        mg.submit_boutique_choice(mg.boutique_order["answer"])
        if not mg.boutique_active:
            break
    assert mg.boutique_patience_max >= mg.BOUTIQUE_DIFFICULTY["slower"]["min"]


def test_new_games_have_a_relaxed_slower_and_a_tight_faster(game_env):
    module = game_env.module
    mg = module.minigames
    for game in mg.NEW_GAMES:
        table = game.difficulty_table
        assert table["slower"]["seconds"] > table["normal"]["seconds"] > table["faster"]["seconds"], game.key
        assert table["slower"]["lives"] >= table["normal"]["lives"] >= table["faster"]["lives"], game.key


def test_the_game_score_scales_a_little_but_the_ledger_does_not(game_env):
    module = game_env.module
    mg = module.minigames
    scores, ledger_points = {}, {}
    for level in ("slower", "normal", "faster"):
        module.practice_ledger = {mode: module._blank_practice_entry() for mode in module.PRACTICE_MODES}
        mg.set_difficulty("blitz", level)
        mg.start_blitz()
        mg.submit_blitz_choice(mg.blitz_question["answer"])
        scores[level] = mg.blitz_score
        ledger_points[level] = module.practice_ledger["blitz"]["points"]
    assert scores["slower"] < scores["normal"] < scores["faster"]
    assert scores["normal"] == 10
    assert set(ledger_points.values()) == {1}


@pytest.mark.parametrize("level", ["slower", "normal", "faster"])
def test_the_watering_rule_is_the_same_at_every_level(game_env, level):
    module, state = game_env.module, game_env.state
    mg = module.minigames
    mg.set_difficulty("blitz", level)
    mg.start_blitz()
    plot = state.plots_by_id[mg.blitz_question["plot_id"]]
    mg.submit_blitz_choice(mg.blitz_question["answer"])
    assert plot.stage == module.STAGE_SPROUT and plot.correct_streak == 1
    assert module.growth_credit["blitz"]["full"] == 1


def test_both_pages_have_the_difficulty_controls():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for name in ("index.html", "pc.html"):
        html = (root / name).read_text(encoding="utf-8")
        for key in ALL:
            assert f'id="{key}-difficulty-select"' in html and f'id="{key}-difficulty-note"' in html, (name, key)
            assert f'id="{key}-waters"' in html, (name, key)
        assert 'id="cafe-twist-waters"' in html
