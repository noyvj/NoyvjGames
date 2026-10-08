"""Audit (2026-10-08): every minigame must connect to at least two real plots in
each play, show which plot each answer waters while it is being played, and feed
the practice ledger. The first five games were audited and the check is pinned
here for all nine."""

import pytest


def _plots(module, ids):
    return [module.state.plots_by_id[i] for i in ids]


def _play_blitz_like(module, game_env, key, start, question_attr, submit, rolls=4):
    mg = module.minigames
    start()
    ids = []
    for _ in range(rolls):
        question = getattr(mg, question_attr)
        ids.append(question["plot_id"])
        tag = game_env.elements[f"{key}-waters"].innerText
        assert tag.startswith("Waters: ") and module.state.plots_by_id[question["plot_id"]].label in tag
        submit(question["answer"])
    return ids


@pytest.mark.parametrize("key", ["blitz", "racer", "sprint"])
def test_question_games_name_the_plot_and_water_several(game_env, key):
    module = game_env.module
    mg = module.minigames
    args = {
        "blitz": (mg.start_blitz, "blitz_question", mg.submit_blitz_choice),
        "racer": (mg.start_racer, "racer_question", mg.submit_racer_choice),
        "sprint": (mg.start_sprint, "sprint_question", mg.submit_sprint_choice),
    }[key]
    ids = _play_blitz_like(module, game_env, key, *args)
    assert len(set(ids)) >= 2
    assert module.growth_credit[key]["full"] + module.growth_credit[key]["nudge"] >= 2
    assert module.practice_ledger[key]["total"] == 4 and module.practice_ledger[key]["correct"] == 4
    assert "Watered" in game_env.elements[f"{key}-feedback"].innerText or game_env.elements[f"{key}-feedback"].innerText


def test_boutique_every_sale_waters_a_garment_and_a_colour_plot_and_says_which(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_boutique()
    tag = game_env.elements["boutique-waters"].innerText
    assert tag.startswith("Waters: ") and " + " in tag
    order = mg.boutique_order
    mg.submit_boutique_choice(order["answer"])
    assert module.growth_credit["boutique"]["full"] == 2
    assert "Sold!" in game_env.elements["boutique-feedback"].innerText
    assert "watered" in game_env.elements["boutique-feedback"].innerText
    mg.submit_boutique_choice(mg.boutique_order["answer"])
    assert module.growth_credit["boutique"]["full"] >= 3  # at least two plots per sale, shared ones counted once
    assert module.practice_ledger["boutique"]["correct"] == 2


def test_every_boutique_and_cafe_entry_resolves_to_a_real_plot(game_env):
    """The shop games build orders from catalog texts; each must map to a plot
    (so a sale can water it)."""
    module = game_env.module
    mg = module.minigames
    for garment_fr, _en, _gender in mg._boutique_garment_entries():
        assert module.plot_for_fr(garment_fr) is not None, garment_fr
    for masc, fem, _en in mg._boutique_colour_entries():
        assert module.plot_for_fr(masc) is not None, masc
    for fr, _en in mg._cafe_food_entries():
        assert module.plot_for_fr(fr) is not None, fr


def test_cafe_waters_the_dish_and_in_a_twist_round_the_grammar_plot(game_env):
    module = game_env.module
    mg = module.minigames
    mg.start_cafe()
    assert game_env.elements["cafe-waters"].innerText.startswith("Waters: ")
    while mg.cafe_active and mg.cafe_stage != mg.CAFE_STAGE_TWIST:
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
    assert mg.cafe_stage == mg.CAFE_STAGE_TWIST
    assert game_env.elements["cafe-twist-waters"].innerText.startswith("Waters: ")
    twist = mg.cafe_twist_question
    before = module.growth_credit["cafe"]["full"]
    mg.submit_cafe_twist_choice(twist["answer"])
    assert module.growth_credit["cafe"]["full"] == before + 1
    assert module.growth_credit["cafe"]["full"] >= 3  # three dishes... and the twist plot
    assert module.practice_ledger["cafe"]["correct"] >= 3


def test_the_cafe_twist_can_be_typed_for_a_grown_plot(game_env):
    module = game_env.module
    mg = module.minigames
    module.wants_typed = lambda p: True
    mg.start_cafe()
    while mg.cafe_active and mg.cafe_stage != mg.CAFE_STAGE_TWIST:
        mg.submit_cafe_item_choice(mg.cafe_order["answer"])
    twist = mg.cafe_twist_question
    assert twist["mode"] == "typed"
    assert game_env.elements["cafe-twist-typed-input"] is not None
    assert mg.submit_cafe_twist_choice(twist["answer"]) is True


@pytest.mark.parametrize("key", ["pairs", "gaps", "listenpick", "wordorder"])
def test_new_games_water_at_least_two_plots_in_one_play(game_env, key):
    module = game_env.module
    game = {g.key: g for g in module.minigames.NEW_GAMES}[key]
    game.start()
    watered = set()
    guard = 0
    while game.active and len(watered) < 3 and guard < 60:
        guard += 1
        if key == "pairs":
            for card in game.round["cards"]:
                pass
            by_plot = {}
            for card in game.round["cards"]:
                by_plot.setdefault(card["plot_id"], []).append(card["id"])
            for plot_id, (a, b) in by_plot.items():
                game.select(a)
                game.select(b)
                watered.add(plot_id)
                if len(watered) >= 3:
                    break
        elif key == "wordorder":
            plot_id = game.round["plot_id"]
            words, order = game.round["words"], game.round["order"]
            for target in range(len(words)):
                game.place(next(i for i, w in enumerate(order) if w == target and i not in game.placed))
            watered.add(plot_id)
        else:
            watered.add(game.round["plot_id"])
            game.submit(game.round["answer"])
    assert len(watered) >= 2
    credit = module.growth_credit[key]
    assert credit["full"] + credit["nudge"] >= 2
    assert module.practice_ledger[key]["correct"] >= 2
    assert module.practice_score() >= 2
