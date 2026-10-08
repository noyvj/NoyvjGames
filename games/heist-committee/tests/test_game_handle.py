import json


def to_plan(g, crew=("dot", "pip", "bea", "tomasz", "hank")):
    g(action="take_job", target="pigeon_museum")
    g(action="to_recruit")
    job = g.module.career.job
    job["offer"] = list(crew) + [c for c in job["offer"] if c not in crew][:3]
    chosen = list(crew)
    for cid in chosen:
        g(action="hire", crew=cid)
    return g(action="confirm_crew")


def test_starts_on_the_board(g):
    view = g(action="open")["view"]
    assert view["phase"] == "board" and view["cash"] == 300
    assert view["board"][0]["id"] == "pigeon_museum"


def test_unknown_action_and_bad_json_do_not_crash(g):
    assert "error" in g(action="nonsense")
    assert "error" in json.loads(g.module.handle("not json"))
    assert "error" in json.loads(g.module.handle("[1,2]"))


def test_take_job_goes_to_scout_with_the_free_top_complication(g):
    view = g(action="take_job", target="pigeon_museum")["view"]
    assert view["phase"] == "scout"
    assert len(view["scout"]["complications"]) >= 1
    assert view["scout"]["details"]


def test_scouting_costs_cash_and_reveals_more(g):
    g(action="take_job", target="pigeon_museum")
    before = g(action="open")["view"]
    after = g(action="scout", level=1)["view"]
    assert after["cash"] < before["cash"]
    assert len(after["scout"]["complications"]) > len(before["scout"]["complications"])
    again = g(action="scout", level=1)["view"]
    assert again["cash"] == after["cash"]            # no double charge


def test_offer_has_eight_candidates_covering_all_roles(g):
    g(action="take_job", target="pigeon_museum")
    view = g(action="to_recruit")["view"]
    assert len(view["offer"]) == 8
    assert {c["role"] for c in view["offer"]} == {"charmer", "locksmith", "driver", "lookout", "hauler"}


def test_hire_toggles_and_caps_at_five(g):
    g(action="take_job", target="pigeon_museum")
    offer = [c["id"] for c in g(action="to_recruit")["view"]["offer"]]
    for cid in offer:
        g(action="hire", crew=cid)
    assert len(g(action="open")["view"]["crew_ids"]) == 5
    g(action="hire", crew=offer[0])
    assert offer[0] not in g(action="open")["view"]["crew_ids"]


def test_confirm_needs_five_and_charges_fees(g):
    g(action="take_job", target="pigeon_museum")
    offer = [c["id"] for c in g(action="to_recruit")["view"]["offer"]]
    out = g(action="confirm_crew")
    assert "five" in out["view"]["note"] and out["view"]["phase"] == "recruit"
    for cid in offer[:5]:
        g(action="hire", crew=cid)
    cash = g(action="open")["view"]["cash"]
    view = g(action="confirm_crew")["view"]
    assert view["phase"] == "plan" and view["cash"] == cash - view["fees"]


def test_unaffordable_crew_cannot_be_confirmed(g):
    g.module.career.cash = 20
    g(action="take_job", target="pigeon_museum")
    offer = [c["id"] for c in g(action="to_recruit")["view"]["offer"]]
    for cid in offer[:5]:
        g(action="hire", crew=cid)
    out = g(action="confirm_crew")
    assert out["view"]["phase"] == "recruit" and "committee has" in out["view"]["note"]


def test_background_check_reveals_a_quirk_for_a_fee(g):
    g(action="take_job", target="pigeon_museum")
    offer = g(action="to_recruit")["view"]["offer"]
    first = offer[0]
    assert first["quirk"] is None
    view = g(action="background", crew=first["id"])["view"]
    card = next(c for c in view["offer"] if c["id"] == first["id"])
    assert card["quirk"] and view["cash"] == 300 - 10


def test_gear_limit(g):
    g(action="take_job", target="pigeon_museum")
    g(action="to_recruit")
    g(action="gear", gear="earplugs")
    g(action="gear", gear="cat_treats")
    out = g(action="gear", gear="lucky_coin")
    assert "fit in the van" in out["view"]["note"]


def test_plan_phase_view_has_lanes_tray_and_validation(g):
    view = to_plan(g)["view"]
    assert view["phase"] == "plan"
    assert len(view["plan"]["lanes"]) == 5 and len(view["plan"]["lanes"][0]) == 6
    assert any(a["id"] == "lockpick" for a in view["tray"])
    assert any(m["level"] == "warn" for m in view["plan"]["messages"])


def test_place_clear_undo_redo(g):
    to_plan(g)
    view = g(action="place", lane=0, beat=0, cell="sweet_talk")["view"]
    assert view["plan"]["lanes"][0][0]["action"] == "sweet_talk"
    assert view["plan"]["lanes"][0][0]["odds"]["word"] == "solid"
    view = g(action="undo")["view"]
    assert view["plan"]["lanes"][0][0]["cell"] is None and view["plan"]["can_redo"]
    view = g(action="redo")["view"]
    assert view["plan"]["lanes"][0][0]["action"] == "sweet_talk"
    view = g(action="clear", lane=0, beat=0)["view"]
    assert view["plan"]["lanes"][0][0]["cell"] is None


def test_two_beat_action_covers_the_next_cell_and_overwrites(g):
    to_plan(g)
    g(action="place", lane=1, beat=2, cell="hack")
    view = g(action="place", lane=1, beat=1, cell="lockpick")["view"]
    row = view["plan"]["lanes"][1]
    assert row[1]["span"] == 2 and row[2]["role"] == "cont" and row[2]["cell"] is None
    view = g(action="place", lane=1, beat=2, cell="carry")["view"]       # lands on the second half: removes the lockpick
    assert view["plan"]["lanes"][1][1]["cell"] is None and view["plan"]["lanes"][1][2]["action"] == "carry"


def test_two_beat_action_at_the_last_beat_is_refused(g):
    to_plan(g)
    out = g(action="place", lane=1, beat=5, cell="lockpick")
    assert "2 beats" in out["view"]["note"]
    assert out["view"]["plan"]["lanes"][1][5]["cell"] is None


def test_standby_needs_a_kind_and_defaults_to_the_first_option(g):
    to_plan(g)
    view = g(action="place", lane=2, beat=1, cell="standby")["view"]
    assert view["plan"]["lanes"][2][1]["arg"] == view["plan"]["cover"][0]["id"]
    view = g(action="place", lane=2, beat=2, cell="standby:cat")["view"]
    assert view["plan"]["lanes"][2][2]["arg"] == "cat"


def test_move_lane_swaps_crew_and_cells(g):
    to_plan(g)
    ids = g(action="open")["view"]["crew_ids"]
    g(action="place", lane=0, beat=0, cell="sweet_talk")
    view = g(action="move_lane", lane=0, dir=1)["view"]
    assert view["crew_ids"][0] == ids[1] and view["crew_ids"][1] == ids[0]
    assert view["plan"]["lanes"][1][0]["action"] == "sweet_talk"


def test_validation_tracks_the_requirements(g):
    to_plan(g, crew=("dot", "pip", "bea", "tomasz", "hank"))
    ids = g(action="open")["view"]["crew_ids"]
    lock, look = ids.index("pip"), ids.index("tomasz")
    g(action="place", lane=ids.index("dot"), beat=0, cell="sweet_talk")
    g(action="place", lane=lock, beat=2, cell="lockpick")
    view = g(action="open")["view"]
    texts = [m["text"] for m in view["plan"]["messages"]]
    assert any("Get past the front desk" in t and "Dot" in t for t in texts)
    assert any("needs a clear corridor in beats 3 and 4" in t for t in texts)
    g(action="place", lane=look, beat=2, cell="lookout")
    g(action="place", lane=look, beat=3, cell="lookout")
    texts = [m["text"] for m in g(action="open")["view"]["plan"]["messages"]]
    assert not any("needs a clear corridor" in t for t in texts)


def test_save_round_trip_in_every_phase(g):
    for stage in ("board", "scout", "recruit", "plan"):
        if stage == "scout":
            g(action="take_job", target="pigeon_museum")
        elif stage == "recruit":
            g(action="to_recruit")
        elif stage == "plan":
            offer = [c["id"] for c in g(action="open")["view"]["offer"]]
            for cid in offer[:5]:
                g(action="hire", crew=cid)
            g(action="confirm_crew")
            g(action="place", lane=0, beat=0, cell="sweet_talk")
        data = g.module.get_state()
        json.dumps(data)
        before = g(action="open")["view"]
        g.module.load_state(json.loads(json.dumps(data)))
        after = g(action="open")["view"]
        for view in (before, after):
            if "plan" in view:
                view["plan"].pop("can_undo")        # the undo history is session-only
        assert after == before


def test_get_state_omits_defaults(g):
    assert g.module.get_state() == {"schema": 1, "career_seed": 77}


def test_load_state_survives_junk(g):
    for junk in (None, 5, "x", [], {"job": 7}, {"job": {"phase": "plan", "target": "nope"}},
                 {"cash": "lots", "job": {"phase": "plan", "target": "pigeon_museum", "crew": ["a"] * 9}},
                 {"career_seed": -4, "meta": {"known_quirks": "dot", "jobs_done": -3}},
                 {"job": {"phase": "recruit", "target": "pigeon_museum", "offer": ["dot"], "crew": ["zzz", "dot", "dot"]}}):
        g.module.load_state(junk)
        view = g(action="open")["view"]
        assert view["phase"] in ("board", "scout", "recruit")


def test_load_state_replaces_the_current_career(g):
    to_plan(g)
    g.module.load_state({"career_seed": 5, "cash": 123})
    view = g(action="open")["view"]
    assert view["phase"] == "board" and view["cash"] == 123


def test_abandon_returns_to_the_board(g):
    to_plan(g)
    view = g(action="abandon")["view"]
    assert view["phase"] == "board" and "fees are gone" in view["note"]


def test_move_cell_moves_between_lanes_in_one_undo_step(g):
    to_plan(g)
    g(action="place", lane=0, beat=0, cell="sweet_talk")
    view = g(action="move_cell", lane=0, beat=0, to_lane=3, to_beat=1)["view"]
    assert view["plan"]["lanes"][0][0]["cell"] is None
    assert view["plan"]["lanes"][3][1]["action"] == "sweet_talk"
    view = g(action="undo")["view"]
    assert view["plan"]["lanes"][0][0]["action"] == "sweet_talk" and view["plan"]["lanes"][3][1]["cell"] is None


def test_move_cell_refuses_a_two_beat_action_at_the_edge(g):
    to_plan(g)
    g(action="place", lane=1, beat=0, cell="lockpick")
    out = g(action="move_cell", lane=1, beat=0, to_lane=2, to_beat=5)
    assert "2 beats" in out["view"]["note"]
    assert out["view"]["plan"]["lanes"][1][0]["action"] == "lockpick"


def test_one_slot_never_satisfies_two_requirements_in_the_checklist(g):
    to_plan(g)
    ids = g(action="open")["view"]["crew_ids"]
    g(action="place", lane=ids.index("hank"), beat=4, cell="carry")
    texts = [m["text"] for m in g(action="open")["view"]["plan"]["messages"]]
    assert not any("Pocket the gift shop till" in t and "Hank" in t for t in texts)
