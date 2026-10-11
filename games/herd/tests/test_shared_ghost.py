"""Z-3e: Herd opts in to the shared best-farm ghost (shared/ghost.py). Two numbers per round (score and methane) are
kept for the best farm filed in each mode, the methane chart gets a faint dashed line, the shared sentences say who is
ahead, an off switch hides it, saves are unchanged and hostile data is dropped."""
import copy
import json
import xml.etree.ElementTree as ET


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _play(env, rounds, invest=True):
    env.farm.funds = 2000.0
    env.grow_herd()
    for i in range(rounds):
        if invest and i < 3:
            env.invest_decoupling("capture")
        env.advance_round()


def _stored(env):
    raw = env.local_storage.getItem(env.module.GHOST_STORAGE_KEY)
    return None if raw is None else json.loads(raw)


def test_no_ghost_and_no_stored_key_on_a_fresh_install(game_env):
    m = game_env.module
    assert _stored(game_env) is None and m.load_ghosts() == {} and m.ghost_graph_data() is None
    assert "hand a farm over, or file one" in game_env.elements["ghost-note"].innerText
    assert game_env.elements["ghost-toggle-wrap"].hidden is True        # nothing to switch off yet
    assert "ghost" not in "".join(m.get_state().keys())                  # the save is unchanged


def test_filing_a_farm_keeps_two_recorder_traces(game_env):
    m = game_env.module
    _play(game_env, 5)
    series = m.farm_series()
    _click(game_env, "ledger-add-button")
    entry = _stored(game_env)["plain"]
    assert entry["gen"] == 1 and entry["result"] == m.ghost_lib.clean_number(m.farm.score() - m.farm.counterfactual_score())
    assert entry["score"]["turns"] == 5 and entry["score"]["values"] == [m.ghost_lib.clean_number(v) for v in series[0]]
    assert entry["methane"]["values"] == [m.ghost_lib.clean_number(v) for v in series[1]]
    assert entry["score"]["label"] == "Farm 1" and m.ghost_lib.load(entry["methane"]) == entry["methane"]
    assert game_env.elements["ghost-toggle-wrap"].hidden is False


def test_a_farm_that_played_fewer_than_four_rounds_is_not_kept(game_env):
    _play(game_env, 3)
    _click(game_env, "ledger-add-button")
    assert _stored(game_env) is None


def test_a_handover_keeps_the_ghost_and_a_worse_farm_does_not_replace_it(game_env):
    m = game_env.module
    _play(game_env, 6)
    game_env.farm.certified = True
    best = m.farm.score() - m.farm.counterfactual_score()
    m.hand_over_farm()
    first = copy.deepcopy(_stored(game_env)["plain"])
    assert first["result"] == m.ghost_lib.clean_number(best) and first["gen"] == 1
    stored = _stored(game_env)
    stored["plain"]["result"] = first["result"] + 500                  # pretend the kept farm was far better
    game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, json.dumps(stored))
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    assert _stored(game_env)["plain"]["result"] == first["result"] + 500 and _stored(game_env)["plain"]["gen"] == 1
    stored["plain"]["result"] = first["result"]                        # equal result: the latest wins
    game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, json.dumps(stored))
    _click(game_env, "ledger-add-button")
    assert _stored(game_env)["plain"]["gen"] == 2


def test_each_farm_mode_has_its_own_ghost(game_env):
    m = game_env.module
    _play(game_env, 5)
    _click(game_env, "ledger-add-button")
    m.farm.variation_enabled = True
    assert m.ghost_mode_key() == "seasons" and m.ghost_entry() is None
    assert "hand a farm over" in m.ghost_note_text()


def test_the_next_farm_is_compared_every_round_in_the_shared_words(game_env):
    m = game_env.module
    _play(game_env, 6)
    game_env.farm.certified = True
    m.hand_over_farm()
    m.render()
    assert "ran 6 rounds" in game_env.elements["ghost-note"].innerText
    game_env.farm.funds = 2000.0
    game_env.grow_herd()
    game_env.advance_round()
    text = game_env.elements["ghost-note"].innerText
    entry = m.ghost_entry()
    series = m.farm_series()
    score = m.ghost_lib.summary(m._rounded_result(m.ghost_lib.compare(series[0], entry["score"]), 0), label="your best farm (Farm 1)")
    assert text.startswith(score.replace("ghost: ", "Ghost: ", 1) + ". Methane (lower is better): ") and text.endswith(" at turn 1.")
    assert "your best farm (Farm 1)" in text and text.count("host:") == 1


def test_the_methane_chart_gets_a_dashed_labelled_ghost_line(game_env):
    m = game_env.module
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    game_env.advance_round()
    game_env.advance_round()                                             # the live farm is now longer than the ghost's run
    svg = game_env.elements["methane-trend-graph"].innerHTML
    ET.fromstring(svg)
    assert 'data-testid="ghost-line"' in svg and 'stroke-dasharray="4 3"' in svg and "Ghost: best farm (dashed)" in svg
    assert 'role="img"' in svg and "your best farm (Farm 1)" in svg
    ghost_points = svg.split('<polyline points="')[1].split('"')[0].split()
    assert len(ghost_points) == 6                                        # the ghost's six rounds; none invented beyond its end
    # the old call shape still draws exactly the old chart
    assert 'data-testid="ghost-line"' not in m.methane_trend_graph_svg(m.farm.methane_history)
    assert m.methane_trend_graph_svg(m.farm.methane_history, None) == m.methane_trend_graph_svg(m.farm.methane_history)


def test_the_off_switch_hides_line_and_note_but_keeps_the_ghost(game_env):
    m = game_env.module
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    game_env.advance_round()
    toggle = game_env.elements["ghost-toggle"]
    toggle.checked = False
    toggle.dispatch("change", None)
    assert game_env.local_storage.getItem(m.GHOST_PREF_KEY) == "0"
    assert 'data-testid="ghost-line"' not in game_env.elements["methane-trend-graph"].innerHTML
    assert game_env.elements["ghost-note"].hidden is True and game_env.elements["ghost-note"].innerText == ""
    assert _stored(game_env) is not None
    toggle.checked = True
    toggle.dispatch("change", None)
    assert 'data-testid="ghost-line"' in game_env.elements["methane-trend-graph"].innerHTML


def test_sandbox_and_custom_rules_farms_are_never_a_ghost_or_race_one(game_env):
    m = game_env.module
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    before = _stored(game_env)
    m.farm.custom_rules_used = True
    assert not m.ghost_eligible() and "never ranked" in m.ghost_note_text()
    assert m.file_ghost() is False and m.ghost_graph_data() is None
    assert _stored(game_env) == before


def test_a_blind_run_shows_nothing_until_it_is_revealed(game_env):
    m = game_env.module
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    m.farm.blind_run = True
    assert m.ghost_note_text() == "" and m.ghost_graph_data() is None
    m.farm.blind_revealed = True
    assert m.ghost_note_text() != ""


def test_a_save_from_before_the_funds_history_has_no_comparison_and_no_crash(game_env):
    m = game_env.module
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    state = copy.deepcopy(m.get_state())
    state.pop("funds_history")                                          # an older save
    m.load_state(state)
    assert m.farm_series() is None and m.ghost_sentences() is None and m.ghost_graph_data() is None
    assert "This farm is compared with it after every round" in game_env.elements["ghost-note"].innerText
    assert m.file_ghost() is False                                      # its unknown rounds cannot make a trace


def test_hostile_stored_ghosts_are_dropped_or_cleaned(game_env):
    m = game_env.module
    good = {"v": 1, "turns": 5, "values": [10, 20, 30, 40, 50], "label": "Farm 2"}
    entry = {"gen": 2, "result": 12.5, "score": good, "methane": good}
    for blob in ["junk", "[]", "5", '{"plain": "x"}', json.dumps({"plain": dict(entry, result="big")}),
                 json.dumps({"plain": dict(entry, score={"turns": 5, "values": [1]})}),
                 json.dumps({"plain": dict(entry, methane=dict(good, turns=9))}),         # lengths disagree
                 json.dumps({"plain": dict(entry, score=dict(good, values=[1.0] * 9000))}),
                 json.dumps({"plain": dict(entry, methane=dict(good, values=["a", None, True, [1], float("nan")]))}),
                 json.dumps({"hacked": entry, "../x": entry})]:
        game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, blob)
        assert m.load_ghosts() == {}, blob
        m.render()
    game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, json.dumps({"plain": dict(entry, gen="x", result=1e99, score=dict(good, label="<b>" * 30))}))
    clean = m.load_ghosts()["plain"]
    assert clean["gen"] == 1 and clean["result"] == 1e12 and len(clean["score"]["label"]) <= 40


def test_the_ghost_survives_a_page_reload(game_env):
    _play(game_env, 6)
    _click(game_env, "ledger-add-button")
    module = game_env.reload()
    assert module.ghost_entry()["score"]["turns"] == 6


def test_when_the_ghosts_run_has_ended_one_sentence_covers_both_numbers(game_env):
    m = game_env.module
    _play(game_env, 5)
    _click(game_env, "ledger-add-button")
    game_env.advance_round()
    assert m.ghost_note_text() == "Ghost: your best farm (Farm 1) ended before turn 6."


def test_gaps_are_read_in_whole_funds_and_a_tiny_one_is_level(game_env):
    m = game_env.module
    assert m._rounded_result({"status": "ahead", "lead": 39.35, "turn": 3}, 0)["lead"] == 39
    assert m._rounded_result({"status": "behind", "lead": 0.3, "turn": 3}, 0)["status"] == "level"
    assert m._rounded_result(None, 0) is None
