"""F-27: every achievement that is not earned shows how far along it is; the card carries a mini
bar and the exact amount left, revealed on hover or keyboard focus."""


def _summary(env):
    return {entry["id"]: entry for entry in env.module.achievements_summary()}


def _cards(env):
    env.toggle_achievements()
    return {c.dataset.achievementId: c for c in env.elements["achievements-panel"].children if hasattr(c.dataset, "achievementId")}


def _texts(el):
    out = [el.innerText]
    for child in el.children:
        out.extend(_texts(child))
    return out


def test_every_achievement_has_a_progress_readout_on_a_fresh_farm(game_env):
    summary = _summary(game_env)
    assert {i for i, e in summary.items() if e["progress"] is None} == set()
    for entry in summary.values():
        current, target = entry["progress"]
        assert 0 <= current <= target and target >= 1


def test_the_new_readouts_follow_the_state(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 10000.0
    assert _summary(game_env)["first_herd"]["progress"] == (0, 1)
    game_env.grow_herd()
    assert _summary(game_env)["first_herd"]["progress"] == (1, 1)
    game_env.invest_decoupling("feed")
    game_env.invest_decoupling("caps")
    s = _summary(game_env)
    assert s["all_three_measures"]["progress"] == (2, 3)
    assert s["first_decoupling"]["progress"] == (1, 1)
    farm.certification_streak = 3
    assert _summary(game_env)["sustainably_certified"]["progress"] == (3, m.CERTIFICATION_ROUNDS_REQUIRED)
    farm.round_number = 9
    assert _summary(game_env)["outperforming_baseline"]["progress"] == (5, 5)
    assert _summary(game_env)["clean_operator"]["progress"] == (9, m.CLEAN_OPERATOR_MIN_ROUND)


def test_clean_operator_shows_nothing_once_it_is_lost_for_this_farm(game_env):
    game_env.farm.max_pressure_fraction_seen = 0.5
    assert _summary(game_env)["clean_operator"]["progress"] is None


def test_left_text_is_exact_and_names_the_unit(game_env):
    m = game_env.module
    assert m.progress_left_text(4, 10, " herd units") == "6 herd units to go (4 of 10)"
    assert m.progress_left_text(12, 10, "%") == "0% to go (12 of 10)"
    assert m.progress_percent(5, 10) == 50.0 and m.progress_percent(1, 0) == 0.0


def test_an_unearned_card_has_a_focusable_bar_and_left_line(game_env):
    game_env.farm.funds = 10000.0
    for _ in range(4):
        game_env.grow_herd()
    cards = _cards(game_env)
    card = cards["growing_operation"]
    assert card.getAttribute("tabindex") == "0"
    classes = [child.className for child in card.children]
    assert "achievement-card-bar" in classes and "achievement-card-left" in classes
    left = next(c for c in card.children if c.className == "achievement-card-left")
    assert left.innerText == "6 herd units to go (4 of 10)"
    bar = next(c for c in card.children if c.className == "achievement-card-bar")
    assert bar.children[0].style.width == "40%"
    assert "6 herd units to go" in card.getAttribute("aria-label")


def test_an_earned_card_has_no_bar(game_env):
    game_env.farm.funds = 10000.0
    game_env.grow_herd()
    card = _cards(game_env)["first_herd"]
    assert card.getAttribute("tabindex") is None
    assert all(child.className != "achievement-card-bar" for child in card.children)


def test_the_bar_and_text_are_hidden_until_hover_or_focus_in_css():
    from pathlib import Path
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    assert ".achievement-card-bar { height: 6px;" in css and "opacity: 0;" in css
    assert ".achievement-card:focus-within .achievement-card-bar" in css
