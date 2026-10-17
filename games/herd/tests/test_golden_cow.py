"""GF-21: the golden cow. Deterministic (every 8 rounds), no timer, visits pile up, small real-farm bonus."""
import json
from pathlib import Path
from .pagefiles import game_css, page_text

ROOT = Path(__file__).resolve().parent.parent


def rounds_to(game_env, target):
    g = game_env.module
    while g.farm.round_number < target:
        g.farm.round_number += 1
        g.farm.methane_history.append(g.farm.methane)
        g.farm.funds_history.append(g.farm.funds)


def test_no_cow_before_round_nine(game_env):
    g = game_env.module
    assert g.golden_cows_due() == 0
    assert game_env.elements["golden-cow-claim-button"].hidden is True
    assert game_env.elements["golden-cow-panel"].hidden is True
    assert game_env.elements["golden-cow-glider"].hidden is True
    rounds_to(game_env, 8)
    assert g.golden_cows_due() == 0
    assert g.welcome_golden_cow() is None


def test_cow_arrives_at_round_nine_and_pays_a_small_bonus(game_env):
    g = game_env.module
    g.farm.herd_size = 6
    rounds_to(game_env, 9)
    g.render()
    assert g.golden_cows_due() == 1
    button = game_env.elements["golden-cow-claim-button"]
    assert button.hidden is False and "golden cow" in button.innerText.lower()
    assert game_env.elements["golden-cow-glider"].hidden is False
    before = g.farm.funds
    expected = g.golden_cow_bonus()
    assert g.GOLDEN_COW_MIN <= expected <= g.GOLDEN_COW_MAX
    button.dispatch("click")
    assert g.farm.funds == before + expected
    assert g.farm.golden_claimed == 1 and g.farm.golden_funds == expected
    assert g.golden_cows_due() == 0 and button.hidden is True
    assert game_env.elements["golden-cow-panel"].hidden is False, "the tally stays visible once a cow was welcomed"
    assert "Golden cows welcomed: 1" in game_env.elements["golden-cow-summary"].innerText
    assert "left" in game_env.elements["golden-cow-status"].innerText


def test_the_glider_does_the_same_thing_and_only_once_per_visit(game_env):
    g = game_env.module
    rounds_to(game_env, 9)
    g.render()
    game_env.elements["golden-cow-glider"].dispatch("click")
    game_env.elements["golden-cow-glider"].dispatch("click")
    game_env.elements["golden-cow-claim-button"].dispatch("click")
    assert g.farm.golden_claimed == 1


def test_missed_visits_pile_up_and_are_never_lost(game_env):
    g = game_env.module
    rounds_to(game_env, 25)
    assert g.golden_cows_due() == 3
    g.render()
    assert "3 waiting" in game_env.elements["golden-cow-claim-button"].innerText
    for _ in range(3):
        game_env.elements["golden-cow-claim-button"].dispatch("click")
    assert g.farm.golden_claimed == 3 and g.golden_cows_due() == 0


def test_bonus_never_touches_the_baseline_and_keeps_the_streak_fair(game_env):
    g = game_env.module
    rounds_to(game_env, 9)
    base = (g.farm.counterfactual_funds, g.farm.counterfactual_methane)
    paid = g.welcome_golden_cow()
    assert (g.farm.counterfactual_funds, g.farm.counterfactual_methane) == base
    assert g.farm.funds_history[-1] == g.farm.funds, "the funds record includes the bonus, so it cannot fake a perfect round"
    assert paid > 0


def test_bonus_is_a_share_of_income_within_bounds(game_env):
    g = game_env.module
    g.farm.herd_size = 0
    assert g.golden_cow_bonus() == g.GOLDEN_COW_MIN
    g.farm.herd_size = 400
    assert g.golden_cow_bonus() == g.GOLDEN_COW_MAX


def test_saved_only_after_a_welcome_and_round_trips(game_env):
    g = game_env.module
    assert "golden_claimed" not in g.get_state()
    rounds_to(game_env, 9)
    g.welcome_golden_cow()
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["golden_claimed"] == 1 and saved["golden_funds"] > 0
    g.farm.golden_claimed = 0
    g.farm.golden_funds = 0.0
    assert g.load_state(saved)
    assert g.farm.golden_claimed == 1 and g.farm.golden_funds == saved["golden_funds"]


def test_hostile_save_values_load_as_zero(game_env):
    g = game_env.module
    base = g.get_state()
    for bad in ({"golden_claimed": "many"}, {"golden_claimed": -5}, {"golden_claimed": True},
                {"golden_claimed": 2, "golden_funds": "lots"}, {"golden_claimed": 2, "golden_funds": -4},
                {"golden_claimed": float("nan")}, {"golden_funds": 50}):
        data = dict(base)
        data.update(bad)
        assert g.load_state(data)
        assert g.farm.golden_funds >= 0 and g.farm.golden_claimed >= 0
        assert g.farm.golden_claimed == 0 or g.farm.golden_claimed == 2
        if g.farm.golden_claimed == 0:
            assert g.farm.golden_funds == 0.0


def test_a_new_generation_starts_without_visits(game_env):
    g = game_env.module
    rounds_to(game_env, 9)
    g.welcome_golden_cow()
    g.farm.certified = True
    g.hand_over_farm()
    assert g.farm.golden_claimed == 0 and g.golden_cows_due() == 0


def test_both_pages_have_the_ids_and_the_css_respects_reduced_motion():
    for page in ("index.html", "pc.html"):
        text = page_text(page)
        for ident in ("golden-cow-panel", "golden-cow-summary", "golden-cow-claim-button", "golden-cow-status", "golden-cow-glider"):
            assert f'id="{ident}"' in text, (page, ident)
    css = game_css()
    assert "prefers-reduced-motion: reduce) { .golden-cow-glider" in css
    assert 'html[data-reduced-motion="true"] .golden-cow-glider' in css
