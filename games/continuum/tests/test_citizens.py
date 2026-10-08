"""K-15 notable citizens and K-28 the citizen of the season."""

import pytest

import citizens
import sim

from .test_space_age_era import push_to_agrarian


def test_names_are_invented_from_the_lists_and_stable_per_seed():
    assert citizens.make_name(7, "tribal") == citizens.make_name(7, "tribal")
    seen = {citizens.make_name(seed, "tribal") for seed in range(1, 60)}
    assert len(seen) > 20
    for name in seen:
        first, _, last = name.partition(" ")
        assert first in citizens.FIRST_NAMES and last in citizens.LAST_NAMES
    assert citizens.clean_name("Maren Hearthwick") == "Maren Hearthwick"
    assert citizens.clean_name("Napoleon Bonaparte") == "" and citizens.clean_name(5) == ""
    assert citizens.clean_name("<b>Maren</b> Marsh") == ""


def test_no_line_of_flavour_names_a_real_place_person_or_date():
    text = " ".join(
        [line for variants in citizens.SPOTLIGHT.values() for line in variants]
        + [t["household"] + t["master"] for t in citizens.ERA_TRADES.values()]
    )
    assert not any(ch.isdigit() for ch in text)  # no dates or statistics to source


def test_one_child_per_era_follows_the_city_and_roster_is_idempotent():
    ui = {}
    added = citizens.ensure_roster(ui, "agrarian", seed_hint=11)
    assert [c["born"] for c in added] == ["tribal", "agrarian"]
    assert citizens.ensure_roster(ui, "agrarian") == []
    added = citizens.ensure_roster(ui, "medieval")
    assert [c["born"] for c in added] == ["classical", "medieval"]
    record = citizens.get(ui)
    assert record["seed"] == 11 and [c["born"] for c in record["roster"]] == ["tribal", "agrarian", "classical", "medieval"]
    assert citizens.ensure_roster(ui, "nonsense") == []


def test_the_life_thread_runs_child_apprentice_master_elder_remembered():
    citizen = {"name": "Maren Marsh", "born": "tribal"}
    stages = [citizens.stage_of(citizen, era)["stage"] for era in sim.ERA_ORDER[:6]]
    assert stages == ["child", "apprentice", "master", "elder", "remembered", "remembered"]
    master = citizens.stage_of(citizen, "classical")
    assert master["title"] == "Canal-warden" and master["bonus"] == {"materials_yield_mult": 0.02}
    elder = citizens.stage_of(citizen, "medieval")
    assert elder["bonus"] == {"tool_yield_mult": pytest.approx(0.015)}
    assert citizens.stage_of(citizen, "agrarian")["bonus"] == {}
    thread = citizens.thread(citizen, "classical")
    assert len(thread) == 3 and thread[0].startswith("Tribal:") and "canal-warden" in thread[2]


def test_bonuses_are_tiny_at_most_two_citizens_and_rest_or_switch_off():
    ui = {}
    citizens.ensure_roster(ui, "relay", seed_hint=3)
    for era in sim.ERA_ORDER:
        deltas = citizens.bonus_deltas(ui, era)
        assert all(v <= 0.06 for v in deltas.values())
        givers = [c for c in citizens.get(ui)["roster"] if citizens.stage_of(c, era)["bonus"]]
        assert len(givers) <= 2
    assert citizens.bonus_deltas(ui, "classical", resting=True) == {}
    citizens.set_off(ui, True)
    assert citizens.bonus_deltas(ui, "classical") == {}
    base = dict(sim.NEUTRAL_EFFECTS)
    assert citizens.apply_effects(base, ui, "classical") is base
    citizens.set_off(ui, False)
    merged = citizens.apply_effects(base, ui, "classical")
    assert merged["materials_yield_mult"] > 1.0 and base["materials_yield_mult"] == 1.0


@pytest.mark.parametrize("raw", [None, 4, [], {"roster": "x", "spots": 3}, {"roster": [{"name": "Evil <b>", "born": "tribal"}, 7]},
                                 {"roster": [{"name": "Maren Marsh", "born": "mars"}]}, {"seed": float("nan")},
                                 {"spots": [{"season": 0, "name": "x", "line": "y", "event": "calm"}]}])
def test_hostile_records_clean_to_nothing(raw):
    record = citizens.clean(raw)
    assert record["roster"] == [] and record["spots"] == []
    assert citizens.clean(record) == record


def test_the_spotlight_is_tied_to_the_most_notable_event_and_stored_once_per_season():
    ui = {}
    citizens.ensure_roster(ui, "tribal", seed_hint=5)
    quiet = citizens.make_spotlight(ui, "tribal", 4, {"deaths": 0, "births": 0, "spoiled": 0, "fed_fraction": 1.0}, [])
    assert quiet["event"] == "calm"
    hungry = citizens.make_spotlight(ui, "tribal", 5, {"deaths": 2, "births": 1}, [])
    assert hungry["event"] == "hunger"
    motions = [{"kind": "research", "era": "tribal", "season": 6, "text": "Motion carried: the council resolves to study Fire-Keeping."}]
    studied = citizens.make_spotlight(ui, "tribal", 6, {}, motions)
    assert studied["event"] == "research" and "Fire-Keeping" in studied["line"]
    again = citizens.make_spotlight(ui, "tribal", 6, {"deaths": 5}, [])
    assert again == studied
    assert len(citizens.get(ui)["spots"]) == 3
    for spot in citizens.get(ui)["spots"]:
        assert "{" not in spot["line"]


def test_the_spotlight_keeps_only_the_last_few_and_can_be_switched_off():
    ui = {}
    for season in range(1, 30):
        citizens.make_spotlight(ui, "tribal", season, {}, [])
    assert len(citizens.get(ui)["spots"]) == citizens.MAX_SPOTS
    assert citizens.latest_spot(ui)["season"] == 29
    citizens.set_off(ui, True)
    assert citizens.make_spotlight(ui, "tribal", 40, {}, []) is None
    assert citizens.make_spotlight({}, "mars", 3, {}, []) is None


def test_the_same_save_always_shows_the_same_people():
    a, b = {}, {}
    for ui in (a, b):
        citizens.ensure_roster(ui, "classical", seed_hint=99)
        citizens.make_spotlight(ui, "classical", 12, {"births": 1}, [])
    assert a == b


# --- in the game -----------------------------------------------------------------------------
def test_children_and_the_spotlight_appear_as_seasons_pass(game_env):
    module = game_env.module
    assert module.citizens.get(module.campaign.ui)["roster"] == []
    game_env.advance_season()
    record = module.citizens.get(module.campaign.ui)
    assert len(record["roster"]) == 1 and len(record["spots"]) == 1
    card = game_env.elements["citizen-spotlight"]
    assert card.hidden is False and record["spots"][0]["name"] in card.innerText
    assert "Citizen of the season" in card.innerText
    assert any("is born among" in e.text for e in module.chronicle.entries)


def test_the_panel_lists_the_thread_and_the_switch_removes_everything(game_env):
    module = game_env.module
    game_env.advance_season(2)
    game_env.elements["citizens-toggle-button"].dispatch("click", None)
    assert game_env.elements["citizens-panel"].hidden is False
    assert len(game_env.elements["citizens-list"].children) == 1
    assert "standing bonus" in game_env.elements["citizens-bonus"].innerText
    game_env.elements["citizens-off-button"].dispatch("click", None)
    assert game_env.elements["citizens-off-button"].innerText == "Notable citizens: OFF"
    assert game_env.elements["citizens-list"].children == []
    assert game_env.elements["citizen-spotlight"].hidden is True
    before = len(module.citizens.get(module.campaign.ui)["spots"])
    game_env.advance_season()
    assert len(module.citizens.get(module.campaign.ui)["spots"]) == before


def test_a_new_era_brings_a_new_child_and_the_dashboard_shows_the_bonus_row(game_env):
    module = game_env.module
    game_env.advance_season()
    push_to_agrarian(game_env)
    game_env.advance_season()
    record = module.citizens.get(module.campaign.ui)
    assert [c["born"] for c in record["roster"]] == ["tribal", "agrarian"]
    rows = dict(module._extra_dashboard_sections()[0]["rows"])
    assert rows["Citizen bonuses"] and rows["Dynasty perks"] and "Doctrines" in rows
    game_env.elements["views-toggle-button"].dispatch("click", None)
    assert game_env.elements["views-dashboard"].children


def test_the_switch_survives_founding_a_new_settlement(game_env):
    import sys
    import types

    class Store:
        data = {}

        def getItem(self, key):
            return self.data.get(key)

        def setItem(self, key, value):
            self.data[key] = value

    sys.modules["js"].window = types.SimpleNamespace(localStorage=Store())
    module = game_env.module
    game_env.advance_season(3)
    module.on_citizens_off()
    assert module.found_new_settlement() is True
    assert module.citizens.is_on(module.campaign.ui) is False
    assert module.citizens.get(module.campaign.ui)["roster"] == []
