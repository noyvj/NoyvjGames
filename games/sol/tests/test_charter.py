"""A-5 / A-6 (Mission Board, Charter stamps) and A-13 / A-14 (Megaprojects)."""

import json


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _open(env):
    env.elements["charter-toggle-button"].dispatch("click")


def _buttons(env, text_part):
    return [e for e in env.elements["charter-panel"].descendants()
            if getattr(e, "tagName", "") == "BUTTON" and text_part in e.innerText]


# --- Mission Board -------------------------------------------------------------


def test_board_starts_with_three_earth_missions(game_env):
    m = game_env.module
    m.tick()
    assert m.mission_slots == ["earth_crew", "earth_hoard", "earth_lean"]
    assert m.mission_stamps == []


def test_every_mission_has_known_world_positive_target_and_a_working_measure(game_env):
    m = game_env.module
    worlds = set(m.PLANETS) | {"all"}
    ids = [x["id"] for x in m.MISSIONS]
    assert len(set(ids)) == len(ids)
    for mission in m.MISSIONS:
        assert mission["world"] in worlds and mission["target"] > 0 and mission["label"]
        assert 0 <= m.mission_progress(mission) <= mission["target"]


def test_finishing_a_mission_stamps_the_charter_and_posts_the_next(game_env):
    m = game_env.module
    m.tick()
    game_env.earth["resource_count"] = 5000
    m.tick()
    assert "earth_hoard" in m.mission_stamps
    assert "earth_hoard" not in m.mission_slots
    assert len(m.mission_slots) == 3 or len(m._mission_candidates()) == 0


def test_new_worlds_bring_new_missions(game_env):
    m = game_env.module
    m.tick()
    assert all(MISSION_WORLD(m, x) == "Earth" for x in m.mission_slots)
    game_env.unlock_tier(1)
    game_env.earth["resource_count"] = 5000
    m.tick()
    assert any(MISSION_WORLD(m, x) in ("Mars", "Moon") for x in m.mission_slots)


def MISSION_WORLD(m, mission_id):
    return m.MISSION_BY_ID[mission_id]["world"]


def test_stamp_bonus_is_small_per_world_and_applies_to_clicks_and_automation(game_env):
    m = game_env.module
    assert m.stamp_bonus("Earth") == 0
    m.mission_stamps[:] = ["earth_crew", "earth_hoard"]
    assert abs(m.stamp_bonus("Earth") - 0.02) < 1e-12
    assert m.stamp_bonus("Mars") == 0
    game_env.earth["resource_count"] = 0.0
    game_env.click()
    assert abs(game_env.earth["resource_count"] - 1.02) < 1e-9
    m.mission_stamps[:] = ["web_of_routes"]
    assert abs(m.stamp_bonus("Mars") - 0.005) < 1e-12


def test_reroll_swaps_for_the_next_mission_and_costs_a_small_amount(game_env):
    m = game_env.module
    m.tick()
    game_env.unlock_tier(1)
    game_env.earth["resource_count"] = 150
    assert m.reroll_mission("earth_crew")
    assert "earth_crew" not in m.mission_slots and len(m.mission_slots) == 3
    assert abs(game_env.earth["resource_count"] - 50) < 1e-9


def test_reroll_needs_a_pile_and_a_posted_mission(game_env):
    m = game_env.module
    m.tick()
    game_env.earth["resource_count"] = 99
    assert m.reroll_source() is None
    assert m.reroll_mission("earth_crew") is False
    game_env.earth["resource_count"] = 500
    assert m.reroll_mission("not_posted") is False
    assert game_env.earth["resource_count"] == 500


def test_reroll_is_deterministic(game_env):
    m = game_env.module
    game_env.unlock_tier(1)
    m.tick()
    game_env.earth["resource_count"] = 1000
    a = m.reroll_mission("earth_crew"), list(m.mission_slots)
    m.mission_slots[:] = ["earth_crew", "earth_hoard", "earth_lean"]
    game_env.earth["resource_count"] = 1000
    b = m.reroll_mission("earth_crew"), list(m.mission_slots)
    assert a == b


def test_panel_shows_board_and_swap_button_with_a_text_cost(game_env):
    m = game_env.module
    m.tick()
    game_env.earth["resource_count"] = 300
    _open(game_env)
    joined = "\n".join(_texts(game_env.elements["charter-panel"]))
    assert "Mission Board" in joined and "Run Earth with 5 Auto-Miners" in joined
    assert _buttons(game_env, "Swap for another mission (100 Iron)")


def test_panel_click_reroll_works_through_the_delegated_handler(game_env):
    m = game_env.module
    game_env.unlock_tier(1)
    m.tick()
    game_env.earth["resource_count"] = 400
    _open(game_env)
    game_env.panel_click("charter-panel", action="reroll", mission="earth_lean")
    assert "earth_lean" not in m.mission_slots


def test_toggle_label_counts_stamps_and_hides_the_panel(game_env):
    m = game_env.module
    toggle = game_env.elements["charter-toggle-button"]
    assert game_env.elements["charter-panel"].hidden is True
    m.tick()
    assert "(0/15)" in toggle.innerText
    _open(game_env)
    assert game_env.elements["charter-panel"].hidden is False and toggle.innerText.startswith("Hide Charter")
    _open(game_env)
    assert game_env.elements["charter-panel"].hidden is True


def test_overview_card_lists_stamps(game_env):
    m = game_env.module
    m.mission_stamps[:] = ["earth_crew"]
    game_env.elements["overview-toggle-button"].dispatch("click")
    m.tick()
    texts = "\n".join(_texts(game_env.elements["overview-panel"]))
    assert "Charter stamps:" in texts and "+1% yield" in texts


def test_mission_save_round_trip_and_validation(game_env):
    m = game_env.module
    state = m.serialize_state()
    assert "mission_stamps" not in state and "mission_slots" not in state  # the default board is not saved
    m.mission_stamps[:] = ["earth_hoard"]
    m.mission_slots[:] = ["earth_crew", "earth_lean"]
    state = json.loads(json.dumps(m.serialize_state()))
    m.mission_stamps.clear()
    m.mission_slots.clear()
    m.deserialize_state(state)
    m._refill_mission_slots()  # what _full_render does after every load; the default board is not saved
    assert m.mission_stamps == ["earth_hoard"] and m.mission_slots == ["earth_crew", "earth_lean"]
    m.mission_slots[:] = ["earth_lean", "earth_crew"]  # a board that differs from the default is saved
    state = json.loads(json.dumps(m.serialize_state()))
    assert state["mission_slots"] == ["earth_lean", "earth_crew"]
    m.deserialize_state(state)
    assert m.mission_slots == ["earth_lean", "earth_crew"]
    m.deserialize_state({"mission_stamps": ["earth_crew", "earth_crew", "zzz", 4],
                         "mission_slots": ["earth_crew", "mars_routes", "mars_calm", "moon_stock", "nope"]})
    assert m.mission_stamps == ["earth_crew"]
    assert m.mission_slots == ["mars_routes", "mars_calm", "moon_stock"]  # stamped ids never on the board, cap 3
    m.deserialize_state({"mission_stamps": "x", "mission_slots": 7})
    assert m.mission_stamps == [] and m.mission_slots == []


def test_prestige_keeps_stamps(game_env):
    m = game_env.module
    m.mission_stamps[:] = ["earth_crew"]
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert m.mission_stamps == ["earth_crew"]


# --- Megaprojects --------------------------------------------------------------


def _all_worlds(env):
    env.unlock_tier(2)
    for p in env.module.PLANETS:
        env.module.planet_state[p]["resource_count"] = 10 ** 6


def test_four_projects_with_perks_and_needs_from_several_worlds(game_env):
    m = game_env.module
    assert [p["id"] for p in m.MEGAPROJECTS] == ["orbital_mirror", "ring_habitat", "dyson_sail", "deep_core_tap"]
    for project in m.MEGAPROJECTS:
        assert len({planet for planet, _ in project["needs"]}) >= 3
        assert project["perk"]
    assert m.megaproject_percent("orbital_mirror") == 0


def test_sending_moves_stock_and_fills_the_ring_by_contributor(game_env):
    m = game_env.module
    _all_worlds(game_env)
    game_env.earth["resource_count"] = 1000
    sent = m.send_to_megaproject("orbital_mirror", "Earth")
    assert sent == 1000 and game_env.earth["resource_count"] == 0
    assert abs(m.megaproject_percent("orbital_mirror") - 100 * (1000 / 4000) / 3) < 1e-9
    assert m.send_to_megaproject("orbital_mirror", "Earth") == 0  # nothing banked


def test_sending_never_overfills_a_line(game_env):
    m = game_env.module
    _all_worlds(game_env)
    assert m.send_to_megaproject("orbital_mirror", "Earth") == 4000
    assert m.send_to_megaproject("orbital_mirror", "Earth") == 0
    assert game_env.earth["resource_count"] == 10 ** 6 - 4000


def test_cannot_send_from_a_world_you_cannot_reach_or_for_a_bad_project(game_env):
    m = game_env.module
    game_env.mars["resource_count"] = 5000
    assert m.send_to_megaproject("orbital_mirror", "Mars") == 0
    assert m.send_to_megaproject("nope", "Earth") == 0
    assert m.send_to_megaproject("orbital_mirror", "Moon") == 0
    assert game_env.mars["resource_count"] == 5000


def test_finishing_a_project_applies_its_perk(game_env):
    m = game_env.module
    _all_worlds(game_env)
    for planet, _ in m.MEGAPROJECT_BY_ID["orbital_mirror"]["needs"]:
        m.send_to_megaproject("orbital_mirror", planet)
    assert m.megaprojects_built == ["orbital_mirror"]
    assert m.megaproject_percent("orbital_mirror") == 100
    assert m.megaproject_factor("terraform") == 1.25
    assert m.megaproject_factor("produce") == 1.0


def test_each_perk_does_what_it_says(game_env):
    m = game_env.module
    _all_worlds(game_env)
    m.planet_state["JupiterMoons"]["sky_city_count"] = 3
    before = m.sky_city_bonus_per_city("JupiterMoons")
    for pid in ("ring_habitat", "dyson_sail", "deep_core_tap"):
        for planet, _ in m.MEGAPROJECT_BY_ID[pid]["needs"]:
            m.send_to_megaproject(pid, planet)
    assert m.sky_city_bonus_per_city("JupiterMoons") == 2 * before
    assert m.megaproject_factor("produce") == 1.2 and m.megaproject_factor("recycle") == 1.5


def test_all_four_unlock_the_secret_epilogue_line_for_good(game_env):
    m = game_env.module
    _all_worlds(game_env)
    for project in m.MEGAPROJECTS:
        for planet, _ in project["needs"]:
            m.send_to_megaproject(project["id"], planet)
    assert m.megaprojects_all_ever is True
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    m.epilogue_open = True
    m.update_epilogue_display()
    body = "\n".join(_texts(game_env.elements["epilogue-body"]))
    assert "four great works" in body
    game_env.prestige()
    assert m.megaprojects_built == [] and m.megaproject_progress == {}  # the works are per run
    assert m.megaprojects_all_ever is True  # the ending line is kept


def test_plain_epilogue_has_no_secret_line(game_env):
    m = game_env.module
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    m.epilogue_open = True
    m.update_epilogue_display()
    assert "four great works" not in "\n".join(_texts(game_env.elements["epilogue-body"]))


def test_panel_send_button_and_rings_on_the_overview(game_env):
    m = game_env.module
    game_env.earth["resource_count"] = 700
    _open(game_env)
    buttons = _buttons(game_env, "Send what you can")
    assert buttons and any(not b.disabled for b in buttons)
    game_env.panel_click("charter-panel", action="send", project="orbital_mirror", planet="Earth")
    assert m.megaproject_progress["orbital_mirror"]["Earth"] == 700
    game_env.elements["overview-toggle-button"].dispatch("click")
    m.tick()
    rings = game_env.module._overview_refs["_rings"]
    assert set(rings) == {p["id"] for p in m.MEGAPROJECTS}
    assert rings["orbital_mirror"].innerText == "6%"  # 700 of 4000 on one of three lines
    assert "aria-label" in rings["orbital_mirror"]._attrs


def test_unreachable_lines_say_so_in_words(game_env):
    _open(game_env)
    joined = "\n".join(_texts(game_env.elements["charter-panel"]))
    assert "reach Mars first" in joined


def test_megaproject_save_round_trip_and_validation(game_env):
    m = game_env.module
    state = m.serialize_state()
    for key in ("megaproject_progress", "megaprojects_built", "megaprojects_all_ever"):
        assert key not in state
    _all_worlds(game_env)
    game_env.earth["resource_count"] = 900
    m.send_to_megaproject("orbital_mirror", "Earth")
    state = json.loads(json.dumps(m.serialize_state()))
    assert state["megaproject_progress"] == {"orbital_mirror": {"Earth": 900.0}}
    m.megaproject_progress.clear()
    m.deserialize_state(state)
    assert m.megaproject_progress == {"orbital_mirror": {"Earth": 900.0}}


def test_bad_megaproject_saves_are_cleaned(game_env):
    m = game_env.module
    m.deserialize_state({"megaproject_progress": {"orbital_mirror": {"Earth": 10 ** 7, "Pluto": 5, "Mars": -3, "Moon": "x"},
                                                  "bogus": {"Earth": 1}, "dyson_sail": 5},
                         "megaprojects_built": ["orbital_mirror", "zzz", "orbital_mirror"],
                         "megaprojects_all_ever": "yes"})
    assert m.megaproject_progress == {"orbital_mirror": {"Earth": 4000.0}}  # clamped to the need; junk lines dropped
    assert m.megaprojects_built == ["orbital_mirror"]
    assert m.megaprojects_all_ever is False
    m.deserialize_state({"megaproject_progress": "x", "megaprojects_built": 4})
    assert m.megaproject_progress == {} and m.megaprojects_built == []
    m.deserialize_state({"megaprojects_built": [p["id"] for p in m.MEGAPROJECTS]})
    assert m.megaprojects_all_ever is True
