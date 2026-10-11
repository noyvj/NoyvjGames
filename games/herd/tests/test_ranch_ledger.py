"""F-2 Ranch Ledger (planning/TODO.md "GF + F. Herd")."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _stored(env):
    return json.loads(env.local_storage.getItem("herd-ranch-ledger-v1"))


def test_an_empty_ledger_says_so(game_env):
    game_env.module.render()
    assert game_env.elements["ledger-summary"].innerText == "Nothing filed yet."
    assert game_env.elements["ledger-clear-button"].disabled
    assert "No farms filed" in game_env.elements["ledger-table"].innerHTML


def test_filing_the_current_farm_writes_one_compact_line(game_env):
    farm = game_env.farm
    farm.funds = 500.0
    game_env.grow_herd()
    game_env.invest_decoupling("capture")
    game_env.advance_round()
    _click(game_env, "ledger-add-button")
    entry = _stored(game_env)[0]
    assert entry["gen"] == 1 and entry["round"] == 2 and entry["mode"] == "plain" and entry["done"] is False
    assert entry["levers"]["capture"] == 1 and entry["herd"] == 1
    assert entry["score"] == round(farm.score(), 1) and entry["base"] == round(farm.counterfactual_score(), 1)
    assert "1 farm filed" in game_env.elements["ledger-summary"].innerText
    assert "<table" in game_env.elements["ledger-table"].innerHTML


def test_filing_the_same_farm_again_replaces_the_line(game_env):
    _click(game_env, "ledger-add-button")
    _click(game_env, "ledger-add-button")
    assert len(_stored(game_env)) == 1
    game_env.advance_round()
    _click(game_env, "ledger-add-button")
    assert len(_stored(game_env)) == 2


def test_a_handover_files_the_finished_farm_automatically(game_env):
    m = game_env.module
    game_env.farm.certified = True
    game_env.farm.herd_size = 4
    gen = m.generation
    m.hand_over_farm()
    entry = _stored(game_env)[0]
    assert entry["done"] is True and entry["gen"] == gen and entry["herd"] == 4
    assert m.generation == gen + 1


def test_modes_are_named_and_filterable(game_env):
    m = game_env.module
    farm = game_env.farm
    assert m.farm_mode() == "plain"
    m.ledger_record(m.ledger_entry())
    farm.round_number = 3
    farm.variation_enabled = True
    assert m.farm_mode() == "seasons"
    m.ledger_record(m.ledger_entry())
    farm.round_number = 4
    farm.variation_enabled, farm.regional_cap_enabled = False, True
    m.ledger_record(m.ledger_entry())
    farm.round_number = 5
    farm.variation_enabled = True
    assert m.farm_mode() == "seasons and cap"
    m.ledger_record(m.ledger_entry())
    counts = {}
    for which in ("all", "plain", "seasons", "cap"):
        game_env.elements["ledger-filter"].value = which
        game_env.elements["ledger-filter"].dispatch("change", None)
        counts[which] = game_env.elements["ledger-table"].innerHTML.count("<tr>") - 1
    assert counts == {"all": 4, "plain": 1, "seasons": 2, "cap": 2}
    game_env.elements["ledger-filter"].value = "bogus"
    game_env.elements["ledger-filter"].dispatch("change", None)
    assert m.ledger_filter == "all"


def test_trend_chart_needs_two_farms_and_is_labelled(game_env):
    m = game_env.module
    m.ledger_record(m.ledger_entry())
    assert m.ledger_chart_svg(m.ledger_rows()) == ""
    game_env.farm.round_number = 6
    game_env.farm.funds = 900.0
    m.ledger_record(m.ledger_entry())
    chart = m.ledger_chart_svg(m.ledger_rows())
    assert 'role="img"' in chart and "ledger-mark" in chart and "ledger-zero" in chart and "best" in chart


def test_custom_rule_farms_are_tagged(game_env):
    m = game_env.module
    m.set_rule("growth_slope", 1)
    m.ledger_record(m.ledger_entry())
    assert "custom rules, unranked" in m.ledger_table_html(m.ledger_rows())


def test_the_ledger_is_capped_and_never_in_a_save(game_env):
    m = game_env.module
    for i in range(m.LEDGER_MAX + 8):
        entry = m.ledger_entry()
        entry["round"] = i + 1
        m.ledger_record(entry)
    assert len(m.read_ledger()) == m.LEDGER_MAX
    assert "ledger" not in json.dumps(m.get_state()).lower()


def test_junk_in_storage_is_ignored_line_by_line(game_env):
    m = game_env.module
    good = m.ledger_entry()
    game_env.local_storage.setItem("herd-ranch-ledger-v1", json.dumps([
        good, "x", {"gen": "a"}, dict(good, mode="weird"), dict(good, funds=float("nan")), dict(good, levers=5),
        dict(good, round=9, levers={"feed": -4, "caps": "x"}),
    ]))
    rows = m.read_ledger()
    assert len(rows) == 2 and rows[1]["levers"]["feed"] == 0
    game_env.local_storage.setItem("herd-ranch-ledger-v1", "not json")
    assert m.read_ledger() == []
    game_env.local_storage.setItem("herd-ranch-ledger-v1", json.dumps({"a": 1}))
    assert m.read_ledger() == []
    m.render()  # must not raise


def test_clear_asks_first_and_empties_only_the_ledger(game_env):
    m = game_env.module
    m.ledger_record(m.ledger_entry())
    _click(game_env, "ledger-clear-button")  # no confirm dialog in the harness: it runs at once
    assert m.read_ledger() == []
    assert game_env.farm.funds == m.STARTING_FUNDS


def test_pages_and_desktop_config():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        for rid in ("ledger-panel", "ledger-add-button", "ledger-filter", "ledger-table", "ledger-chart"):
            assert f'id="{rid}"' in html
    cfg = json.loads((HERE / "pc-config.json").read_text(encoding="utf-8"))
    assert "#ledger-panel" in cfg["zones"]["side"]
