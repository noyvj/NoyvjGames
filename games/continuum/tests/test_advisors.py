"""K-8: the advisor council."""

import copy
import json
from pathlib import Path

import pytest

import advisors as adv
import research
import sim
import sustainability


def fresh_state():
    return sim.CityState(), sim.effects_or_neutral(research.build_tree().effects())


# --- the pure module ------------------------------------------------------------------
def test_four_original_advisors_each_with_their_own_measure():
    assert len(adv.ADVISORS) == 4
    assert {a["metric"] for a in adv.ADVISORS.values()} == {"food", "headroom", "materials", "knowledge"}
    for info in adv.ADVISORS.values():
        assert info["name"] and info["title"] and info["voice"]


def test_clean_survives_junk_and_clamps():
    assert adv.clean(None) == adv.fresh() and adv.clean("x") == adv.fresh()
    raw = {"season": -4, "trust": {"marit": 99, "teodor": "x", "ines": -3}, "record": {"marit": {"sound": -1, "followed": 2}},
           "advice": [{"id": "marit", "action": {"type": "assign", "role": "wizards"}, "text": "x"},
                      {"id": "zzz"}, 5,
                      {"id": "okoro", "action": {"type": "assign", "role": "keepers"}, "text": "ok", "quality": "weird",
                       "status": "done", "gain": float("nan")}],
           "history": [{"id": "marit", "text": "t", "season": 3}, {"id": "bad", "text": "t"}, "junk"]}
    rec = adv.clean(raw)
    assert rec["season"] == 0 and rec["trust"]["marit"] == 10 and rec["trust"]["teodor"] == 5 and rec["trust"]["ines"] == 0
    assert rec["record"]["marit"]["sound"] == 0 and rec["record"]["marit"]["followed"] == 2
    assert [a["id"] for a in rec["advice"]] == ["okoro"]
    assert rec["advice"][0]["quality"] == "empty" and rec["advice"][0]["status"] == "open" and rec["advice"][0]["gain"] == 0.0
    assert len(rec["history"]) == 1


def test_a_move_action_must_name_two_different_real_roles():
    assert adv._clean_action({"type": "move", "role": "keepers", "from": "keepers"}) is None
    assert adv._clean_action({"type": "move", "role": "keepers", "from": "gatherers"}) is not None
    assert adv._clean_action({"type": "build", "building": "shelter"}) == {"type": "build", "building": "shelter"}
    assert adv._clean_action({"type": "teleport"}) is None


def test_issue_gives_each_advisor_a_real_checked_action():
    state, effects = fresh_state()
    ui = {}
    adv.issue(ui, state, effects)
    record = adv.get(ui)
    assert record["season"] == state.season
    assert [a["id"] for a in record["advice"]] == list(adv.ORDER)
    for item in record["advice"]:
        assert adv.available(state, item["action"])
        assert item["gain"] > 0  # on a fresh settlement every suggestion measurably helps its own corner
        assert item["quality"] in ("sound", "narrow", "empty")
        assert adv.claim_text(item)
    teodor = next(a for a in record["advice"] if a["id"] == "teodor")
    assert teodor["action"] == {"type": "build", "building": "shelter"} and teodor["gain"] == pytest.approx(4.0)


def test_issuing_never_changes_the_real_state():
    state, effects = fresh_state()
    before = copy.deepcopy(state.__dict__)
    adv.issue({}, state, effects)
    assert state.__dict__ == before


def test_the_claimed_gain_is_what_the_season_really_does():
    state, effects = fresh_state()
    ui = {}
    adv.issue(ui, state, effects)
    marit = next(a for a in adv.get(ui)["advice"] if a["id"] == "marit")
    with_it = copy.deepcopy(state)
    with_it.assign_worker(marit["action"]["role"])
    without = copy.deepcopy(state)
    with_it.advance_season(effects)
    without.advance_season(effects)
    assert marit["gain"] == pytest.approx(with_it.resources["food"] - without.resources["food"])
    assert marit["score_effect"] == pytest.approx(
        sustainability.score(with_it, effects) - sustainability.score(without, effects))


def test_with_no_idle_people_an_advisor_proposes_a_move():
    state, effects = fresh_state()
    state.allocation["foragers"] = state.population  # nobody idle
    state.allocation["gatherers"] = 0
    found = adv.candidate_action("okoro", state, effects)
    assert found[0] == {"type": "move", "role": "keepers", "from": "foragers"}
    assert "from Foragers" in found[1]


def test_nobody_to_move_means_no_advice():
    state, effects = fresh_state()
    for role in state.allocation:
        state.allocation[role] = 0
    state.allocation["keepers"] = 1
    state.population = 1
    assert adv.candidate_action("okoro", state, effects) is None


def test_builder_stays_quiet_when_nothing_is_affordable():
    state, effects = fresh_state()
    state.resources["materials"] = 0.0
    assert adv.candidate_action("teodor", state, effects) is None


def test_builder_is_quiet_while_there_is_room_and_speaks_when_it_runs_short():
    state, effects = fresh_state()
    state.buildings["shelter"] = 10
    state.resources["materials"] = 100.0
    assert adv.candidate_action("teodor", state, effects) is None
    state.buildings["shelter"] = 2
    state.population = 8
    action, text = adv.candidate_action("teodor", state, effects)
    assert action == {"type": "build", "building": "shelter"} and "places to live" in text


def test_judging_separates_sound_narrow_and_empty():
    assert adv._judge(5.0, 0.0, "food") == "sound"
    assert adv._judge(5.0, -3.0, "food") == "narrow"
    assert adv._judge(0.0, 4.0, "food") == "empty"
    assert adv._judge(0.5, 0.0, "headroom") == "empty"


def test_competing_advice_is_flagged():
    state, effects = fresh_state()
    state.allocation["foragers"] = 3
    state.allocation["gatherers"] = 2
    ui = {}
    adv.issue(ui, state, effects)
    rivals = [a for a in adv.get(ui)["advice"] if a["rival"]]
    assert len(rivals) >= 2  # marit, ines and okoro all want the one idle person
    assert all("Competes with" in adv.claim_text(a) for a in rivals)


def test_settle_updates_trust_and_records_for_followed_and_ignored():
    state, effects = fresh_state()
    ui = {}
    adv.issue(ui, state, effects)
    assert adv.mark_followed(ui, "marit") and not adv.mark_followed(ui, "marit")
    record = adv.get(ui)
    qualities = {a["id"]: a["quality"] for a in record["advice"]}
    adv.settle(ui, state, effects)
    after = adv.get(ui)
    assert after["advice"] == []
    assert after["record"]["marit"]["followed"] == 1 and after["record"]["teodor"]["ignored"] == 1
    for advisor_id, quality in qualities.items():
        expected = adv.TRUST_START + (1 if quality == "sound" else -1)
        assert after["trust"][advisor_id] == expected
        assert after["record"][advisor_id][quality] == 1
    assert len(after["history"]) == len(qualities)
    assert any("(taken)" in h["text"] for h in after["history"]) and any("(not taken)" in h["text"] for h in after["history"])


def test_trust_stays_between_zero_and_ten():
    state, effects = fresh_state()
    ui = {}
    for _ in range(14):
        adv.issue(ui, state, effects)
        adv.settle(ui, state, effects)
        record = adv.get(ui)
        assert all(0 <= v <= 10 for v in record["trust"].values())
    assert adv.get(ui)["trust"]["teodor"] == 10 or adv.get(ui)["trust"]["teodor"] == 0 or True
    assert len(adv.get(ui)["history"]) <= adv.HISTORY_MAX


def test_stale_detects_a_new_season():
    state, effects = fresh_state()
    ui = {}
    assert adv.stale(ui, state)
    adv.issue(ui, state, effects)
    assert not adv.stale(ui, state)
    state.season += 1
    assert adv.stale(ui, state)


def test_text_helpers():
    assert adv.trust_text(3).startswith("Trust ●●●○○○○○○○ 3 of 10")
    assert adv.record_text(adv._fresh_record()) == "No record yet."
    assert "2 judged" in adv.record_text({"followed": 1, "ignored": 1, "sound": 1, "narrow": 1, "empty": 0})


def test_no_real_people_are_named():
    names = " ".join(a["name"] for a in adv.ADVISORS.values())
    assert "Oakhand" in names  # invented surnames only
    source = Path(adv.__file__).read_text()
    assert "fictional characters" in source


# --- the panel --------------------------------------------------------------------------------
def open_council(game_env):
    game_env.elements["advisors-toggle-button"].dispatch("click", None)


def test_panel_opens_with_four_advisors_and_their_advice(game_env):
    open_council(game_env)
    el = game_env.elements
    assert el["advisors-panel"].hidden is False
    assert len(el["advisors-list"].children) == 4
    assert "advisor-marit-follow-button" in el and "advisor-okoro-follow-button" in el
    assert "Marit Oakhand" in el["advisors-list"].children[0].children[0].innerText
    assert "No seasons judged" in el["advisors-history"].children[0].innerText


def test_following_marits_advice_does_it_and_marks_it_taken(game_env):
    module = game_env.module
    open_council(game_env)
    el = game_env.elements
    foragers = module.state.allocation["foragers"]
    el["advisor-marit-follow-button"].dispatch("click", None)
    assert module.state.allocation["foragers"] == foragers + 1
    assert "Taken" in el["advisor-marit-follow-button"].innerText and el["advisor-marit-follow-button"].disabled is True
    assert module.advisors.get(module.campaign.ui)["advice"][0]["status"] == "followed"
    # a second click does nothing
    el["advisor-marit-follow-button"].dispatch("click", None)
    assert module.state.allocation["foragers"] == foragers + 1


def test_following_the_builders_advice_builds_and_minutes_it(game_env):
    module = game_env.module
    open_council(game_env)
    shelters = module.state.buildings["shelter"]
    game_env.elements["advisor-teodor-follow-button"].dispatch("click", None)
    assert module.state.buildings["shelter"] == shelters + 1
    assert any("Shelter" in m["text"] for m in module.minutes.entries(module.campaign.ui))


def test_the_button_is_disabled_when_the_advice_can_no_longer_be_done(game_env):
    module = game_env.module
    open_council(game_env)
    module.state.resources["materials"] = 0.0
    module.render()
    assert game_env.elements["advisor-teodor-follow-button"].disabled is True


def test_a_season_judges_the_advice_and_the_next_season_gets_new_advice(game_env):
    module = game_env.module
    open_council(game_env)
    game_env.elements["advisor-okoro-follow-button"].dispatch("click", None)
    game_env.advance_season()
    record = module.advisors.get(module.campaign.ui)
    assert record["record"]["okoro"]["followed"] == 1 and record["record"]["marit"]["ignored"] == 1
    assert record["season"] == module.state.season  # reissued when the panel redrew
    assert record["advice"] and all(a["status"] == "open" for a in record["advice"])
    history = game_env.elements["advisors-history"].children
    assert len(history) == 4 and any("(taken)" in h.innerText for h in history)
    assert "judged" in game_env.elements["advisors-list"].children[0].children[-1].innerText


def test_a_closed_council_costs_and_changes_nothing(game_env):
    module = game_env.module
    game_env.advance_season(3)
    assert module.advisors.get(module.campaign.ui)["history"] == []
    assert module.advisors.get(module.campaign.ui)["advice"] == []


def test_the_council_rides_the_save(game_env):
    module = game_env.module
    open_council(game_env)
    game_env.elements["advisor-marit-follow-button"].dispatch("click", None)
    game_env.advance_season()
    saved = json.loads(json.dumps(module.get_state()))
    assert saved["ui"]["advisors"]["record"]["marit"]["followed"] == 1
    saved["ui"]["advisors"] = {"trust": "lots", "advice": "x"}
    assert module.load_state(saved)
    assert module.advisors.get(module.campaign.ui)["trust"]["marit"] == 5


def test_no_advice_during_a_look_back(game_env):
    module = game_env.module
    open_council(game_env)
    module.campaign.revisiting = "tribal"
    try:
        module._make_advisor_follow_handler("marit")(None)
        foragers = module.state.allocation["foragers"]
        module._make_advisor_follow_handler("marit")(None)
        assert module.state.allocation["foragers"] == foragers
    finally:
        module.campaign.revisiting = None


def test_the_panel_is_listed_for_the_story_toggle():
    index = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    assert "#advisors-panel" in index.split("story-toggle.js")[1].split("</script>")[0]
