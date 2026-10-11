"""I-14: three named budget templates (per browser)."""

import json
import sys


def _fake_storage(initial=None):
    store = dict(initial or {})

    class Storage:
        def getItem(self, key):
            return store.get(key)

        def setItem(self, key, value):
            store[key] = value

    sys.modules["js"].localStorage = Storage()
    return store


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def test_three_empty_plans_to_start(game_env):
    m = game_env.module
    assert [t["name"] for t in m.budget_templates] == ["Plan 1", "Plan 2", "Plan 3"]
    assert all(t["buys"] == {} for t in m.budget_templates)
    game_env.module.render()
    assert game_env.elements["template-1-apply"].disabled
    assert "empty" in game_env.elements["template-1-summary"].innerText


def test_purchase_counts_come_from_the_funds_spent_this_round(game_env):
    game_env.invest("housing")
    game_env.invest("housing")
    game_env.invest("services")
    assert game_env.module.round_purchase_counts() == {"housing": 2, "services": 1, "infrastructure": 0}
    game_env.advance_round()
    assert game_env.module.round_purchase_counts() == {"housing": 0, "services": 0, "infrastructure": 0}


def test_save_needs_something_bought(game_env):
    _fake_storage()
    game_env.module.render()
    assert game_env.elements["template-1-save"].disabled
    _click(game_env, "template-1-save")
    assert "Nothing bought" in game_env.elements["template-note"].innerText


def test_save_then_apply_next_round_buys_the_same(game_env):
    store = _fake_storage()
    game_env.invest("housing")
    game_env.invest("services")
    game_env.invest("services")
    game_env.elements["template-2-name"].value = "Services first"
    _click(game_env, "template-2-save")
    plan = game_env.module.budget_templates[1]
    assert plan == {"name": "Services first", "buys": {"housing": 1, "services": 2}}
    assert json.loads(store["drift_budget_templates_v1"])[1]["name"] == "Services first"
    game_env.advance_round()
    before = dict(game_env.region.capacity)
    _click(game_env, "template-2-apply")
    after = game_env.region.capacity
    assert after["services"] - before["services"] == 2 * game_env.module.CAPACITY_PER_INVESTMENT["services"]
    assert after["housing"] - before["housing"] == game_env.module.CAPACITY_PER_INVESTMENT["housing"]
    assert "bought 2 Integration Services, 1 Housing" in game_env.elements["template-note"].innerText


def test_apply_buys_what_funds_allow_services_first_and_reports_the_rest(game_env):
    _fake_storage()
    m = game_env.module
    m.budget_templates[0] = {"name": "Big", "buys": {"housing": 5, "services": 5, "infrastructure": 5}}
    game_env.region.funds = 45.0  # two services at 20
    bought, short = m.apply_template(0)
    assert bought == {"services": 2} and short == {"services": 3, "housing": 5, "infrastructure": 5}
    assert game_env.region.funds == 5.0


def test_apply_message_names_what_could_not_be_afforded(game_env):
    _fake_storage()
    game_env.module.budget_templates[0] = {"name": "Big", "buys": {"housing": 3}}
    game_env.region.funds = 25.0
    _click(game_env, "template-1-apply")
    note = game_env.elements["template-note"].innerText
    assert "bought 1 Housing" in note and "Could not afford 2 Housing" in note


def test_apply_with_no_funds_and_an_empty_plan_say_so(game_env):
    _fake_storage()
    game_env.module.budget_templates[0] = {"name": "Big", "buys": {"housing": 3}}
    game_env.region.funds = 0.0
    _click(game_env, "template-1-apply")
    assert "not enough funds" in game_env.elements["template-note"].innerText
    game_env.elements["template-2-apply"].dispatch("click", None)  # empty plan: button is disabled in the page
    assert game_env.module.budget_templates[1]["buys"] == {}


def test_applied_purchases_can_be_refunded_with_reset_round(game_env):
    _fake_storage()
    game_env.module.budget_templates[0] = {"name": "P", "buys": {"housing": 2}}
    funds = game_env.region.funds
    _click(game_env, "template-1-apply")
    assert game_env.region.funds < funds
    _click(game_env, "reset-round-button")
    assert game_env.region.funds == funds


def test_a_plan_pops_a_building_once(game_env):
    _fake_storage()
    game_env.module.budget_templates[0] = {"name": "P", "buys": {"housing": 3}}
    _click(game_env, "template-1-apply")
    assert game_env.module.building_pop_count == 1


def test_rename_trims_caps_and_ignores_blanks(game_env):
    _fake_storage()
    m = game_env.module
    assert m.rename_template(0, "  A very long plan name that will not fit  ")
    assert m.budget_templates[0]["name"] == "A very long plan nam"
    assert not m.rename_template(0, "   ") and not m.rename_template(5, "x") and not m.rename_template(0, 7)
    assert m.budget_templates[0]["name"] == "A very long plan nam"


def test_stored_templates_are_validated(game_env):
    m = game_env.module
    messy = [
        {"name": "  ok  ", "buys": {"housing": 3, "services": 0, "infrastructure": 99, "junk": 2}},
        "nope",
        {"name": 5, "buys": {"housing": True, "services": 2.5}},
        {"name": "fourth is ignored"},
    ]
    clean = m._clean_templates(messy)
    assert len(clean) == 3
    assert clean[0] == {"name": "ok", "buys": {"housing": 3}}
    assert clean[1] == {"name": "Plan 2", "buys": {}} and clean[2] == {"name": "Plan 3", "buys": {}}
    assert m._clean_templates("junk") == m._default_templates() and m._clean_templates(None) == m._default_templates()


def test_templates_load_from_storage_and_survive_bad_json(game_env):
    m = game_env.module
    _fake_storage({"drift_budget_templates_v1": json.dumps([{"name": "Mine", "buys": {"housing": 2}}])})
    assert m._load_templates()[0] == {"name": "Mine", "buys": {"housing": 2}}
    _fake_storage({"drift_budget_templates_v1": "{broken"})
    assert m._load_templates() == m._default_templates()


def test_templates_never_ride_the_save(game_env):
    _fake_storage()
    game_env.module.budget_templates[0] = {"name": "P", "buys": {"housing": 2}}
    assert "template" not in json.dumps(game_env.module.get_state())


def test_the_note_clears_when_the_round_advances(game_env):
    _fake_storage()
    game_env.invest("housing")
    _click(game_env, "template-1-save")
    assert game_env.elements["template-note"].innerText
    game_env.advance_round()
    assert game_env.elements["template-note"].innerText == ""
