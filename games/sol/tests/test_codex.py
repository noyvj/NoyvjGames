"""A-19 / A-20: the hidden Codex (seven odd sentences in the world notes, silly curios)."""

import json


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _panel_text(env):
    return "\n".join(_texts(env.elements["charter-panel"]))


def _open(env):
    env.elements["charter-toggle-button"].dispatch("click")


def test_seven_clues_one_per_world_with_a_hint_and_an_odd_sentence_in_the_note(game_env):
    m = game_env.module
    assert len(m.CLUES) == 7
    worlds = [c["world"] for c in m.CLUES]
    assert len(set(worlds)) == 7 and "Earth" not in worlds
    for clue in m.CLUES:
        assert clue["hint"] and clue["name"] and clue["curio"]
        assert m.WORLD_NOTES[clue["world"]].count(". ") >= 1  # a plain description, then the odd sentence


def test_overview_cards_carry_the_notes_and_a_pointer(game_env):
    m = game_env.module
    m.unlocked_bodies.add("Moon")
    game_env.elements["overview-toggle-button"].dispatch("click")
    m.tick()
    text = "\n".join(_texts(game_env.elements["overview-panel"]))
    assert m.WORLD_NOTES["Moon"] in text
    assert "odd sentence" in text


def test_codex_and_its_count_are_hidden_until_the_first_clue(game_env):
    m = game_env.module
    _open(game_env)
    assert "Codex" not in _panel_text(game_env) and "clues found" not in _panel_text(game_env)
    m.planet_state["Moon"]["generator_count"] = 13
    m.tick()
    assert m.codex_found == ["bakers_dozen"]
    text = _panel_text(game_env)
    assert "Codex: 1 of 7 clues found" in text and "The Baker's Dozen" in text


def test_each_condition_fires_only_when_acted_on(game_env):
    m = game_env.module
    ps = m.planet_state
    m.governor_budget_pct = 0.0  # the Governor would otherwise spend the banked Methane
    m.tick()
    assert m.codex_found == []
    ps["Moon"]["generator_count"] = 12
    ps["Mars"]["trade_routes"] = {"Earth": 6}
    ps["AsteroidBelt"].update(generator_count=5, recycler_count=5)
    ps["Pluto"].update(generator_count=0, ecology_health=0.0)
    ps["JupiterMoons"].update(sky_city_count=3, recycler_count=1)
    ps["SaturnMoons"]["resource_count"] = 9999
    m.tick()
    assert m.codex_found == []
    ps["Moon"]["generator_count"] = 13
    ps["Mars"]["trade_routes"] = {"Earth": 7}
    ps["AsteroidBelt"].update(recycler_count=4)
    ps["Pluto"].update(generator_count=2)
    ps["JupiterMoons"].update(recycler_count=0)
    ps["SaturnMoons"]["resource_count"] = 10000
    m.tick()
    assert set(m.codex_found) == {"bakers_dozen", "seven_kettles", "off_by_one", "pluto_is_fine", "quiet_choir",
                                  "round_number"}


def test_trade_routes_must_deliver_to_earth(game_env):
    m = game_env.module
    m.planet_state["Mars"]["trade_routes"] = {"Moon": 7}
    m.tick()
    assert "seven_kettles" not in m.codex_found


def test_venus_last_needs_every_other_world_done_first(game_env):
    m = game_env.module
    done = m.TERRAFORM_MAX
    # Venus first: the others are not done, so no.
    m.planet_state["Venus"]["terraform_progress"] = done
    m.tick()
    assert "last_on_purpose" not in m.codex_found
    # Reset it, finish the others, then Venus.
    m.planet_state["Venus"]["terraform_progress"] = 50.0
    m.tick()
    for p in m.PLANETS:
        if p != "Venus":
            m.planet_state[p]["terraform_progress"] = done
    m.tick()
    assert "last_on_purpose" not in m.codex_found
    m.planet_state["Venus"]["terraform_progress"] = done
    m.tick()
    assert "last_on_purpose" in m.codex_found


def test_venus_and_another_world_finishing_together_is_not_last(game_env):
    m = game_env.module
    for p in m.PLANETS:
        if p not in ("Venus", "Pluto"):
            m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    m.tick()
    m.planet_state["Venus"]["terraform_progress"] = m.TERRAFORM_MAX
    m.planet_state["Pluto"]["terraform_progress"] = m.TERRAFORM_MAX
    m.tick()
    assert "last_on_purpose" not in m.codex_found


def test_a_loaded_save_counts_finished_worlds_as_earlier(game_env):
    m = game_env.module
    for p in m.PLANETS:
        if p != "Venus":
            m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    m._full_render()  # what a load runs
    m.planet_state["Venus"]["terraform_progress"] = m.TERRAFORM_MAX
    m.tick()
    assert "last_on_purpose" in m.codex_found


def test_unfound_clues_show_the_note_sentence_and_a_hint_only_on_request(game_env):
    m = game_env.module
    m.planet_state["Moon"]["generator_count"] = 13
    m.tick()
    _open(game_env)
    text = _panel_text(game_env)
    assert "Not found yet" in text and "Hint:" not in text
    assert "Seven kettles will always find Earth." in text
    game_env.panel_click("charter-panel", action="hint", clue="seven_kettles")
    assert "Hint: Have at least 7 trade routes" in _panel_text(game_env)
    game_env.panel_click("charter-panel", action="hint", clue="bogus")  # ignored


def test_every_open_clue_offers_a_hint_button(game_env):
    m = game_env.module
    m.planet_state["Moon"]["generator_count"] = 13
    m.tick()
    _open(game_env)
    buttons = [e for e in game_env.elements["charter-panel"].descendants()
               if getattr(e, "tagName", "") == "BUTTON" and e.innerText == "Show a hint"]
    assert len(buttons) == 6


def test_finding_a_clue_toasts_and_never_repeats(game_env):
    m = game_env.module
    toasts = []
    m._display_toast = toasts.append
    m.planet_state["Moon"]["generator_count"] = 13
    m.tick()
    assert "Codex entry found: The Baker's Dozen" in toasts
    toasts.clear()
    m.tick()
    assert m.codex_found == ["bakers_dozen"] and not [t for t in toasts if t.startswith("Codex")]


def test_found_clues_stay_found_when_the_condition_stops(game_env):
    m = game_env.module
    m.planet_state["Moon"]["generator_count"] = 13
    m.tick()
    m.planet_state["Moon"]["generator_count"] = 14
    m.tick()
    assert m.codex_found == ["bakers_dozen"]


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "codex_found" not in m.serialize_state()
    m.codex_found[:] = ["round_number", "bakers_dozen"]
    state = json.loads(json.dumps(m.serialize_state()))
    m.codex_found.clear()
    m.deserialize_state(state)
    assert m.codex_found == ["round_number", "bakers_dozen"]
    m.deserialize_state({"codex_found": ["bakers_dozen", "bakers_dozen", "zzz", 3, None]})
    assert m.codex_found == ["bakers_dozen"]
    m.deserialize_state({"codex_found": "bakers_dozen"})
    assert m.codex_found == []
