"""GF-28: the opt-in blind run. The baseline comparison stays hidden everywhere until it is revealed;
the simulation itself must not change."""
import json
from pathlib import Path
from .pagefiles import page_text

ROOT = Path(__file__).resolve().parent.parent


def play(game_env, rounds=3):
    g = game_env.module
    g.farm.funds += 300
    for _ in range(4):
        game_env.grow_herd()
    game_env.invest_decoupling("feed")
    for _ in range(rounds):
        game_env.advance_round()
    return g


def turn_on(game_env):
    box = game_env.elements["blind-run-checkbox"]
    box.checked = True
    box.dispatch("click")


def test_off_by_default_and_the_normal_text_is_unchanged(game_env):
    g = game_env.module
    assert g.blind_hidden() is False
    play(game_env, 2)
    assert "points" in game_env.elements["counterfactual-comparison-display"].innerText
    assert "Baseline:" in game_env.elements["gauge-range-display"].innerText
    assert game_env.elements["blind-run-panel"].hidden is True
    assert "blind_run" not in g.get_state()


def test_only_before_the_first_round(game_env):
    g = game_env.module
    assert game_env.elements["blind-run-checkbox"].disabled is False
    game_env.advance_round()
    assert game_env.elements["blind-run-checkbox"].disabled is True
    assert g.set_blind_run(True) is False and g.farm.blind_run is False
    assert "before the first round" in game_env.elements["blind-run-note"].innerText


def test_switching_on_and_off_before_round_one(game_env):
    g = game_env.module
    turn_on(game_env)
    assert g.blind_hidden() is True and game_env.elements["blind-run-panel"].hidden is False
    game_env.elements["blind-run-checkbox"].checked = False
    game_env.elements["blind-run-checkbox"].dispatch("click")
    assert g.blind_hidden() is False and game_env.elements["blind-run-panel"].hidden is True


def test_everything_that_leaks_the_baseline_is_hidden(game_env):
    g = game_env.module
    turn_on(game_env)
    play(game_env, 4)
    base = f"{g.farm.counterfactual_score():.0f}"
    els = game_env.elements
    assert els["baseline-score-display"].innerText == "Score: hidden"
    assert els["baseline-funds-display"].innerText == "Funds: hidden"
    assert els["baseline-methane-display"].innerText == "Methane: hidden"
    assert els["counterfactual-comparison-display"].innerText == g.BLIND_HIDDEN_NOTE
    assert "hidden" in els["gauge-range-display"].innerText and "Baseline:" not in els["gauge-range-display"].innerText
    assert "plan-line--base" not in els["plan-chart"].innerHTML and "(B, dotted)" not in els["plan-chart"].innerHTML
    assert "pure-growth" not in els["plan-table"].innerHTML
    assert "baseline" not in els["plan-summary"].innerText
    report = g.report_card_html()
    assert "hidden during your blind run" in report
    assert "vs. pure-growth baseline" not in report and "points behind" not in report and "points ahead" not in report
    assert "avoided" not in report.replace("hidden", "")
    assert base not in els["counterfactual-comparison-display"].innerText
    fields = g.copy_result_fields()
    assert "blind run" in fields["stats"] and not any("avoided" in s for s in fields["stats"])


def test_record_marker_is_hidden_while_blind(game_env):
    g = game_env.module
    g.record_coupling_ratio = 0.5
    turn_on(game_env)
    g.render()
    assert game_env.elements["coupling-gauge-record-display"].hidden is True
    assert "Best ever" not in game_env.elements["coupling-gauge"].innerHTML
    g.reveal_blind_run()
    g.render()
    assert game_env.elements["coupling-gauge-record-display"].hidden is False


def test_blind_run_never_changes_the_simulation(game_env):
    plain = play(game_env, 4)
    plain_state = {k: v for k, v in plain.get_state().items() if k not in ("blind_run", "summary")}
    # the same plays with the blind run on
    game_env.reload()
    g2 = game_env.module
    turn_on(game_env)
    play(game_env, 4)
    env2_state = {k: v for k, v in g2.get_state().items() if k not in ("blind_run", "summary")}
    assert plain_state == env2_state


def test_reveal_button_ends_it_and_spells_out_the_comparison(game_env):
    g = game_env.module
    turn_on(game_env)
    play(game_env, 5)
    assert game_env.elements["blind-reveal-button"].hidden is False
    game_env.elements["blind-reveal-button"].dispatch("click")
    assert g.blind_hidden() is False and g.farm.blind_revealed is True
    text = game_env.elements["blind-reveal-text"].innerText
    assert "Blind run revealed" in text and ("ahead" in text or "behind" in text)
    assert f"{g.farm.counterfactual_score():.0f}" in text
    assert "points" in game_env.elements["counterfactual-comparison-display"].innerText
    assert game_env.elements["blind-reveal-button"].hidden is True
    assert game_env.elements["blind-run-checkbox"].disabled is True
    g.set_blind_run(False)
    assert g.farm.blind_run is True, "a revealed run cannot be hidden again or switched off"


def test_filing_the_farm_or_a_handover_also_reveals(game_env):
    g = game_env.module
    turn_on(game_env)
    play(game_env, 2)
    assert "reveals the blind run" in game_env.elements["ledger-add-button"].innerText
    game_env.elements["ledger-add-button"].dispatch("click")
    assert g.blind_hidden() is False
    assert game_env.elements["ledger-add-button"].innerText == "File this farm now"
    g2 = game_env.reload()
    turn_on(game_env)
    g2.farm.certified = True
    g2.hand_over_farm()
    assert g2.farm.blind_run is False, "the next generation starts a normal farm"


def test_saved_only_when_set_and_validated(game_env):
    g = game_env.module
    assert "blind_run" not in g.get_state()
    turn_on(game_env)
    state = json.loads(json.dumps(g.get_state()))
    assert state["blind_run"] is True and "blind_revealed" not in state
    g.reveal_blind_run()
    state = json.loads(json.dumps(g.get_state()))
    assert state["blind_run"] is True and state["blind_revealed"] is True
    g.farm.blind_run = False
    g.farm.blind_revealed = False
    assert g.load_state(state)
    assert g.farm.blind_run and g.farm.blind_revealed
    base = g.get_state()
    for bad in ({"blind_run": "yes"}, {"blind_run": 1}, {"blind_revealed": True}, {"blind_run": None, "blind_revealed": True}):
        data = dict(base)
        data.pop("blind_run", None)
        data.pop("blind_revealed", None)
        data.update(bad)
        assert g.load_state(data)
        assert g.farm.blind_run is False and g.farm.blind_revealed is False


def test_an_old_save_loads_and_a_hidden_save_stays_hidden(game_env):
    g = game_env.module
    turn_on(game_env)
    play(game_env, 2)
    saved = json.loads(json.dumps(g.get_state()))
    g.farm.blind_run = False
    assert g.load_state(saved)
    assert g.blind_hidden() is True
    assert game_env.elements["counterfactual-comparison-display"].innerText == g.BLIND_HIDDEN_NOTE


def test_both_pages_have_the_ids():
    for page in ("index.html", "pc.html"):
        text = page_text(page)
        for ident in ("blind-run-checkbox", "blind-run-note", "blind-run-panel", "blind-reveal-text", "blind-reveal-button"):
            assert f'id="{ident}"' in text, (page, ident)
