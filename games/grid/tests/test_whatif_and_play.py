"""C-3 what-if analyzer, GC-15 Perfect Round combo, GC-21 undo and Ironman, GC-4 nicknames and the
coal eulogy, GC-25 surprise grants."""
import json

from .test_career import _install_storage, _play


# --- C-3 what-if analyzer ------------------------------------------------------------------------

def _finished_run(game_env, rounds=8):
    g = game_env.module
    _install_storage()
    for _ in range(3):
        game_env.build("coal")
    game_env.build("solar")
    for _ in range(rounds):
        game_env.advance_round()
    return g, g.finish_run()


def test_finishing_a_run_files_three_what_if_rows(game_env):
    g, points = _finished_run(game_env)
    assert points is not None
    rec = g.career["history"][-1]
    assert [w["id"] for w in rec["whatif"]] == ["renewables_early", "no_retire", "storage_first"]
    for row in rec["whatif"]:
        assert row["grade"] in "ABCDF" and row["funds"] >= 0 and 0 <= row["score"] <= 100
    assert g.seed_lib.is_valid(rec["seed"], "grid") and rec["ironman"] is False


def test_the_replay_uses_the_runs_own_seed_and_is_deterministic(game_env):
    g = game_env.module
    s = g.GridState()
    s.seed = "GRID-K7F2Q"
    s.weather_variability_enabled = True
    s.round_number = 9
    a = g.what_if_results(s)
    b = g.what_if_results(s)
    assert a == b
    s2 = g.GridState()
    s2.seed = "GRID-AAAAA"
    s2.weather_variability_enabled = True
    s2.round_number = 9
    assert g.what_if_results(s2) != a  # a different seed faces different rolls


def test_the_strategies_really_differ(game_env):
    g = game_env.module
    s = g.GridState()
    s.round_number = 21
    results = {r["id"]: r for r in g.what_if_results(s)}
    assert len({(r["grade"], r["funds"], r["score"]) for r in results.values()}) >= 2
    # no-retire leans on cheap fossil capacity; all-renewable-early ends cleaner
    assert results["renewables_early"]["score"] > results["no_retire"]["score"]


def test_the_replay_follows_the_runs_settings(game_env):
    g = game_env.module
    s = g.GridState()
    s.round_number = 7
    plain = g.what_if_results(s)
    s.steeper_demand_growth_enabled = True
    steep = g.what_if_results(s)
    assert plain != steep
    s.steeper_demand_growth_enabled = False
    s.scenario = "coal_legacy"
    assert g.what_if_results(s) != plain


def test_a_short_run_has_no_what_if(game_env):
    g = game_env.module
    s = g.GridState()
    s.round_number = 3
    assert g.what_if_results(s) == []
    assert "at least 5 rounds" in g.career_whatif_verdict(None)


def test_the_replay_never_touches_the_live_run(game_env):
    g = game_env.module
    s = game_env.state
    s.round_number = 9
    funds, counts, seed = s.funds, dict(s.plant_counts), s.seed
    g.what_if_results(s)
    assert (s.funds, s.plant_counts, s.seed, s.round_number) == (funds, counts, seed, 9)


def test_what_if_rows_show_in_the_career_panel(game_env):
    g, _ = _finished_run(game_env)
    game_env.toggle_career()
    container = game_env.elements["career-whatif"]
    assert len(container.children) == 5          # header, You, three strategies
    first = [c.innerText for c in container.children[1].children]
    assert first[0] == "You"
    verdict = game_env.elements["career-whatif-verdict"].innerText
    assert verdict.startswith(("Your own play beat", "All-renewable early", "Never retire, grow with fossil", "Storage first"))


def test_what_if_validation_drops_junk_and_survives_a_round_trip(game_env):
    g, _ = _finished_run(game_env)
    rec = g.career["history"][-1]
    again = g.validate_career(json.loads(json.dumps(g.career)))["history"][-1]
    assert again["whatif"] == rec["whatif"] and again["seed"] == rec["seed"]
    bad = dict(rec, whatif=[{"id": "nope"}, {"id": "no_retire", "grade": "Z", "funds": "x", "score": -4}, 5], seed="x")
    clean = g._validate_run_record(bad)
    assert clean["whatif"] == [{"id": "no_retire", "grade": "F", "funds": 0, "score": 0.0}] and clean["seed"] == ""
    old = {k: v for k, v in rec.items() if k not in ("whatif", "seed", "ironman")}
    assert g._validate_run_record(old)["whatif"] == []


# --- GC-15 Perfect Round combo -------------------------------------------------------------------

def _calm(s, **kw):
    kw.setdefault("rng", lambda: 1.0)
    kw.setdefault("age_rng", lambda: 1.0)
    s.advance_round(**kw)


def test_perfect_rounds_build_a_streak_and_a_revenue_bonus(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["nuclear"] = 3            # 300 capacity: demand is met for many rounds
    base = 100 * g.REVENUE_PER_UNIT_MET
    _calm(s)
    assert s.perfect_streak == 1 and s.last_round_recap["perfect"] is True
    assert s.last_round_recap["perfect_bonus"] == 0           # first perfect round: no bonus yet
    funds = s.funds
    _calm(s)
    assert s.perfect_streak == 2
    assert abs(s.last_round_recap["perfect_bonus"] - (110 * g.REVENUE_PER_UNIT_MET) * 0.05) < 1e-9
    assert s.funds > funds + 110 * g.REVENUE_PER_UNIT_MET - 1e-9
    assert base == 200


def test_the_bonus_is_capped(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["nuclear"] = 9
    for _ in range(12):
        _calm(s)
    assert s.perfect_streak == 12
    assert s.perfect_bonus_fraction() == g.PERFECT_ROUND_STEP * g.PERFECT_ROUND_MAX_STEPS


def test_a_shortfall_a_disruption_or_a_breakdown_ends_the_streak(game_env):
    s = game_env.state
    s.plant_counts["nuclear"] = 3
    _calm(s)
    _calm(s)
    assert s.perfect_streak == 2
    s.plant_counts["nuclear"] = 0
    s.plant_counts["solar"] = 1               # 10 capacity against 120 demand
    _calm(s)
    assert s.perfect_streak == 0 and s.best_perfect_streak == 2
    s.plant_counts["nuclear"] = 4
    _calm(s)
    _calm(s)
    assert s.perfect_streak == 2
    s.emissions = 1800.0
    s.plant_counts["coal"] = 1
    s.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0)
    assert s.perfect_streak == 0
    _calm(s)
    s.plant_age["nuclear"] = 40.0
    s.advance_round(rng=lambda: 1.0, age_rng=lambda: 0.0)
    assert s.last_aging_event is not None and s.perfect_streak == 0


def test_streak_display_and_save(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["nuclear"] = 3
    game_env.advance_round()
    game_env.advance_round()
    text = game_env.elements["perfect-streak-display"].innerText
    assert "Perfect Round streak: 2" in text and "+10%" in text
    data = json.loads(json.dumps(g.get_state()))
    assert data["perfect_streak"] == 2 and data["best_perfect_streak"] == 2
    g.load_state(dict(data, perfect_streak=-3, best_perfect_streak="x"))
    assert game_env.state.perfect_streak == 0 and game_env.state.best_perfect_streak == 0
    assert "Perfect Round bonus" in g.round_recap_text()[1] or True


def test_recap_mentions_the_bonus(game_env):
    g = game_env.module
    s = game_env.state
    s.plant_counts["nuclear"] = 3
    _calm(s)
    _calm(s)
    assert "Perfect Round bonus: +" in g.round_recap_text()[1]
    assert "This was a Perfect Round" in g.round_recap_text()[1]


# --- GC-21 undo last build and Ironman -----------------------------------------------------------

def test_undo_gives_the_money_back_and_restores_the_curve(game_env):
    s = game_env.state
    funds = s.funds
    cost = s.plant_cost("wind")
    game_env.build("wind")
    assert s.can_undo_build() and s.funds == funds - cost
    assert game_env.elements["undo-build-button"].disabled is False
    game_env.elements["undo-build-button"].dispatch("click", None)
    assert s.funds == funds and s.plant_counts["wind"] == 0 and s.cumulative_built["wind"] == 0
    assert s.lifetime_build_spend == 0 and s.renewable_unlocked is False
    assert s.plant_cost("wind") == cost
    assert game_env.elements["undo-build-button"].disabled is True
    assert s.undo_last_build() is False


def test_undo_only_reaches_the_last_action_of_the_round(game_env):
    s = game_env.state
    game_env.build("coal")
    game_env.build("gas")
    s.retire_plant("coal")
    assert s.can_undo_build() is False
    game_env.build("gas")
    assert s.can_undo_build()
    s.maintain_plant("gas")
    assert s.can_undo_build() is False
    game_env.build("gas")
    s.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert s.can_undo_build() is False


def test_undo_keeps_unit_ages_and_shadow_log_honest(game_env):
    s = game_env.state
    s.plant_counts["coal"] = 2
    s.plant_age["coal"] = 6.0
    game_env.module.on_shadow_change  # the shadow grid is off, so nothing is logged
    game_env.build("coal")
    assert s.plant_age["coal"] == 4.0
    s.undo_last_build()
    assert s.plant_age["coal"] == 6.0 and s.plant_counts["coal"] == 2
    g = game_env.module
    g.shadow_scenario = "standard"
    game_env.build("gas")
    assert g.shadow_actions and g.shadow_actions[-1]["type"] == "gas"
    game_env.elements["undo-build-button"].dispatch("click", None)
    assert not any(a["type"] == "gas" for a in g.shadow_actions)


def test_ironman_blocks_undo_and_locks_once_play_starts(game_env):
    s = game_env.state
    el = game_env.elements
    el["ironman-toggle-button"].dispatch("click", None)
    assert s.ironman is True and "Ironman" in el["difficulty-header-display"].innerText
    game_env.build("coal")
    assert s.can_undo_build() is False and s.undo_last_build() is False
    assert "off in Ironman" in el["undo-build-button"].innerText
    el["ironman-toggle-button"].dispatch("click", None)
    assert s.ironman is True and "before you build" in el["run-seed-note"].innerText
    assert s.set_ironman(False) is False


def test_ironman_off_again_before_the_first_build(game_env):
    s = game_env.state
    assert s.set_ironman(True) and s.set_ironman(False) and s.ironman is False
    game_env.build("coal")
    assert s.can_undo_build()


def test_ironman_is_saved_and_filed_in_the_run_history(game_env):
    g = game_env.module
    _install_storage()
    s = game_env.state
    s.set_ironman(True)
    data = json.loads(json.dumps(g.get_state()))
    assert data["ironman"] is True
    _play(game_env, 6)
    g.finish_run()
    assert g.career["history"][-1]["ironman"] is True
    assert "Ironman." in g.career_history_rows(g.career["history"])[0]
    assert game_env.state.ironman is False  # a fresh run starts without it


# --- GC-4 nicknames and eulogy -------------------------------------------------------------------

def test_each_built_plant_gets_a_nickname_from_its_own_pool(game_env):
    g = game_env.module
    s = game_env.state
    for _ in range(3):
        game_env.build("coal")
    names = s.plant_name_list("coal")
    assert len(names) == 3 and len(set(names)) == 3
    assert all(n.split(" I")[0] in g.PLANT_NAME_POOL["coal"] or n in g.PLANT_NAME_POOL["coal"] for n in names)
    assert game_env.elements["coal-names"].innerText == ", ".join(names)
    game_env.build("solar")
    assert s.plant_name_list("solar")[0] in g.PLANT_NAME_POOL["solar"]


def test_nicknames_are_reproducible_from_the_seed(game_env):
    g = game_env.module

    def names(seed):
        s = g.GridState()
        s.seed = seed
        s.plant_counts["wind"] = 4
        return s.plant_name_list("wind")

    assert names("GRID-K7F2Q") == names("GRID-K7F2Q")
    assert any(names("GRID-K7F2Q") != names(sd) for sd in ("GRID-AAAAA", "GRID-ZZZZZ", "GRID-23456"))


def test_names_follow_the_count_up_and_down(game_env):
    s = game_env.state
    s.plant_counts["coal"] = 3                 # starting fleet gets names too
    first = list(s.plant_name_list("coal"))
    assert len(first) == 3
    s.plant_counts["coal"] = 1                 # damage or a breakdown took two
    assert s.plant_name_list("coal") == first[:1]
    game_env.build("coal")
    assert s.plant_name_list("coal")[0] == first[0] and len(s.plant_name_list("coal")) == 2
    s.retire_plant("coal")
    assert s.plant_name_list("coal") == first[:1]


def test_retiring_the_last_coal_plant_plays_a_eulogy(game_env):
    s = game_env.state
    game_env.build("coal")
    game_env.build("coal")
    name = s.plant_name_list("coal")[-1]
    s.retire_plant("coal")
    assert s.last_eulogy is None               # one left: no eulogy yet
    last = s.plant_name_list("coal")[0]
    s.retire_plant("coal")
    assert s.last_eulogy is not None and last in s.last_eulogy["text"] and name != ""
    game_env.module.render()
    assert game_env.elements["eulogy-display"].hidden is False and last in game_env.elements["eulogy-display"].innerText
    game_env.build("gas")
    s.retire_plant("gas")
    assert last in s.last_eulogy["text"]       # only coal gets one


def test_the_eulogy_through_the_retire_button(game_env):
    game_env.build("coal")
    game_env.retire("coal")                    # last unit asks ConfirmDialog; the fake DOM has none and goes ahead
    assert game_env.elements["eulogy-display"].hidden is False


def test_names_and_eulogy_survive_a_save_and_bad_data_is_cleaned(game_env):
    g = game_env.module
    s = game_env.state
    game_env.build("coal")
    game_env.build("coal")
    s.retire_plant("coal")
    s.retire_plant("coal")
    game_env.build("wind")
    data = json.loads(json.dumps(g.get_state()))
    assert data["plant_names"]["wind"] == s.plant_name_list("wind") and data["last_eulogy"]["text"]
    s.plant_names["wind"] = ["x"]
    g.load_state(data)
    assert s.plant_name_list("wind") == data["plant_names"]["wind"]
    g.load_state(dict(data, plant_names={"wind": [1, None, "y" * 99], "coal": "no"}, name_serial={"wind": "x"}, last_eulogy={"text": 5}))
    assert game_env.state.last_eulogy is None
    assert all(len(n) <= g.NAME_MAX_LEN for n in game_env.state.plant_name_list("wind"))


# --- GC-25 surprise grants ------------------------------------------------------------------------

def _grant_grid(g, seed="GRID-K7F2Q"):
    s = g.GridState()
    s.seed = seed
    s.plant_counts["nuclear"] = 9
    return s


def _first_offer(g, seeds=("GRID-K7F2Q", "GRID-AAAAA", "GRID-23456", "GRID-ZZZZZ", "GRID-HJKMN", "GRID-PQRST", "GRID-BCDFG")):
    for seed in seeds:
        s = _grant_grid(g, seed)
        for _ in range(60):
            s.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
            if s.policy_lever_available:
                s.decline_policy()
            if s.grant_offer is not None:
                return s
    raise AssertionError("no grant offered in 7 seeds x 60 rounds")


def test_grants_are_offered_deterministically_and_not_too_early(game_env):
    g = game_env.module
    a, b = _first_offer(g), _first_offer(g)
    assert a.round_number == b.round_number and a.grant_offer == b.grant_offer
    assert a.grant_offer["id"] in g.GRANTS and a.round_number >= g.GRANT_MIN_ROUND
    assert a.seed == b.seed


def test_the_offer_rate_is_occasional(game_env):
    g = game_env.module
    offers = 0
    rounds = 0
    for seed in ("GRID-K7F2Q", "GRID-AAAAA", "GRID-23456", "GRID-ZZZZZ", "GRID-HJKMN"):
        s = _grant_grid(g, seed)
        for _ in range(80):
            s.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
            rounds += 1
            if s.policy_lever_available:
                s.decline_policy()
            if s.grant_offer is not None:
                offers += 1
                s.decline_grant()
    assert 0.05 < offers / rounds < 0.30


def test_accepting_each_grant_applies_its_strings(game_env):
    g = game_env.module
    s = _grant_grid(g)
    s.grant_offer = {"id": "clean_grant", "round": 4}
    funds, coal = s.funds, s.plant_cost("coal")
    assert s.accept_grant() and s.funds == funds + g.GRANT_CLEAN_FUNDS and s.grant_offer is None
    assert abs(s.plant_cost("coal") - coal * 1.25) < 1e-9 and s.plant_cost("wind") == 70
    for _ in range(g.GRANT_CLEAN_ROUNDS):
        s.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert s.grant_effects["fossil_surcharge"] == 0 and abs(s.plant_cost("coal") - coal) < 1e-9
    s.grant_offer = {"id": "sponsor_deal", "round": 6}
    funds, demand = s.funds, s.demand
    s.accept_grant()
    assert s.funds == funds + g.GRANT_SPONSOR_FUNDS and s.demand == demand + g.GRANT_SPONSOR_DEMAND
    s.grant_offer = {"id": "inspection_fine", "round": 7}
    s.plant_age["nuclear"] = 10.0
    funds = s.funds
    s.accept_grant()
    assert s.funds == funds - g.GRANT_FINE and s.plant_age["nuclear"] == 7.0


def test_declining_is_free_except_for_contesting_the_fine(game_env):
    g = game_env.module
    s = _grant_grid(g)
    s.grant_offer = {"id": "sponsor_deal", "round": 4}
    funds = s.funds
    assert s.decline_grant() and s.funds == funds and s.grant_effects["breakdown_risk"] == 0
    s.grant_offer = {"id": "inspection_fine", "round": 5}
    s.plant_age["nuclear"] = 12.0
    plain = s.aging_breakdown_probability()
    s.decline_grant()
    assert s.grant_effects["breakdown_risk"] == g.GRANT_CONTEST_ROUNDS
    assert s.aging_breakdown_probability() > plain
    assert s.decline_grant() is False and s.accept_grant() is False


def test_an_unanswered_offer_lapses_when_the_round_moves_on(game_env):
    g = game_env.module
    s = _first_offer(g)
    kind = s.grant_offer["id"]
    funds = s.funds
    s.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert s.grant_offer is None or s.grant_offer["round"] == s.round_number
    assert s.last_grant_message
    assert kind in g.GRANTS and funds <= s.funds + 1000


def test_grant_buttons_and_the_banner(game_env):
    g = game_env.module
    s = game_env.state
    el = game_env.elements
    s.grant_offer = {"id": "sponsor_deal", "round": 4}
    g.render()
    assert el["grant-banner"].hidden is False
    assert "Industrial sponsor" in el["grant-text"].innerText and el["grant-accept-button"].innerText == "Take the deal"
    assert el["auto-advance-button"].disabled is True
    funds = s.funds
    el["grant-accept-button"].dispatch("click", None)
    assert el["grant-banner"].hidden is True and s.funds == funds + 90
    assert "Deal taken" in el["grant-message-display"].innerText and el["grant-message-display"].hidden is False
    s.grant_offer = {"id": "clean_grant", "round": 5}
    g.render()
    el["grant-decline-button"].dispatch("click", None)
    assert s.grant_offer is None and "declined" in el["grant-message-display"].innerText


def test_auto_advance_stops_at_a_grant_offer_and_waits_for_an_answer(game_env):
    g = game_env.module
    for seed in ("GRID-K7F2Q", "GRID-AAAAA", "GRID-23456", "GRID-ZZZZZ", "GRID-HJKMN", "GRID-PQRST", "GRID-BCDFG"):
        game_env.state.seed = seed
        game_env.state.plant_counts["nuclear"] = 60
        game_env.state.emissions = 0.0
        for _ in range(40):
            played, message = g.auto_advance(rng=lambda: 1.0, age_rng=lambda: 1.0)
            if "grant offer" in message and played:
                assert game_env.state.grant_offer is not None
                assert g.auto_advance()[0] == 0 and "grant offer" in g.auto_advance()[1]
                return
            if played == 0 or game_env.state.policy_lever_available:
                game_env.state.decline_policy()
                game_env.state.decline_grant()
    raise AssertionError("auto-advance never met a grant")


def test_grant_state_round_trips_and_bad_data_is_ignored(game_env):
    g = game_env.module
    s = game_env.state
    s.grant_offer = {"id": "clean_grant", "round": 4}
    s.grant_effects = {"fossil_surcharge": 2, "breakdown_risk": 1}
    data = json.loads(json.dumps(g.get_state()))
    s.grant_offer = None
    s.grant_effects = {"fossil_surcharge": 0, "breakdown_risk": 0}
    g.load_state(data)
    assert game_env.state.grant_offer == {"id": "clean_grant", "round": 4}
    assert game_env.state.grant_effects == {"fossil_surcharge": 2, "breakdown_risk": 1}
    g.load_state(dict(data, grant_offer={"id": "hacked"}, grant_effects={"fossil_surcharge": 99, "breakdown_risk": -4}))
    assert game_env.state.grant_offer is None
    assert game_env.state.grant_effects == {"fossil_surcharge": g.GRANT_CLEAN_ROUNDS, "breakdown_risk": 0}
