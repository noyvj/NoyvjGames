"""The engine's handle(json) -> json entry point: playing the timeline builder, learning, locking, sections."""

import json

import puzzle as pz


def test_boot_starts_the_first_section_first_round(p):
    v = p.call("boot")["view"]
    assert v["puzzle"]["id"] == "presidents-sample/s1/0"
    assert v["puzzle"]["status"] == "playing" and v["puzzle"]["size"] == 3
    assert [s["unlocked"] for s in v["sections"]] == [True, False, False, False]
    assert v["set"]["draft"] and v["set"]["total"] == 64 and v["set"]["found"] == 0
    assert v["first_run"] is True


def test_the_view_never_contains_the_answer_or_the_dates_before_the_puzzle_is_done(p):
    r = p.call("boot")
    text = json.dumps(r["view"])
    puz = p.puzzle()
    assert r["view"]["result"] is None
    assert "1789" not in text and "date_label" not in text
    assert "answer" not in r["view"]["puzzle"]
    # the tray order is not the answer order
    assert r["view"]["puzzle"]["tray"] != puz.answer


def test_handle_takes_and_returns_json_strings(g):
    out = json.loads(g.handle(json.dumps({"action": "boot"})))
    assert out["ok"] and out["view"]["puzzle"]["size"] == 3
    assert json.loads(g.handle("{not json"))["ok"] is False
    assert json.loads(g.handle(json.dumps({"action": "nope"})))["ok"] is False
    assert json.loads(g.handle(json.dumps([1, 2])))["ok"] is False


def test_place_moves_swaps_and_unplaces(p):
    puz = p.puzzle()
    a, b, c = puz.tray
    assert p.call("place", event=a, slot=0)["ok"]
    assert p.call("place", event=b, slot=0)["ok"]                      # b replaces a, a returns to the tray
    v = p.call("boot")["view"]["puzzle"]
    assert [s["card"] for s in v["slots"]] == [b, None, None] and set(v["tray"]) == {a, c}
    assert p.call("place", event=a, slot=2)["ok"]
    assert p.call("place", event=a, slot=0)["ok"]                      # a moves from slot 2 and swaps with b
    v = p.call("boot")["view"]["puzzle"]
    assert [s["card"] for s in v["slots"]] == [a, None, b]
    assert p.call("unplace", slot=0)["ok"] and p.call("boot")["view"]["puzzle"]["slots"][0]["card"] is None


def test_bad_placements_are_refused_with_a_message_and_change_nothing(p):
    before = p.m.get_state()["session"]
    for kwargs in ({"event": "e-nope", "slot": 0}, {"event": p.puzzle().tray[0], "slot": 9}, {"event": p.puzzle().tray[0], "slot": -1},
                   {"event": p.puzzle().tray[0], "slot": "0"}, {"event": 7, "slot": 0}, {"slot": 0}):
        r = p.call("place", **kwargs)
        assert r["ok"] is False and r["error"]
    assert p.m.get_state()["session"] == before


def test_check_needs_every_slot_filled(p):
    r = p.call("check")
    assert r["ok"] is False and "all 3 cards" in r["error"]


def test_a_wrong_check_locks_only_the_right_cards_and_hints_at_direction(p):
    puz = p.puzzle()
    a = puz.answer
    for i, e in enumerate([a[0], a[2], a[1]]):                       # first right, other two swapped
        p.call("place", event=e, slot=i)
    r = p.call("check")
    v = r["view"]["puzzle"]
    assert r["ok"] and v["status"] == "playing" and v["checks"] == 1
    assert [s["locked"] for s in v["slots"]] == [True, False, False]
    assert v["slots"][1]["direction"] == "later" and v["slots"][2]["direction"] == "earlier"
    assert "1 of 3" in v["message"]
    assert r["view"]["set"]["found"] > 0
    # the locked card cannot be moved or swapped over
    assert p.call("unplace", slot=0)["ok"] is False
    assert p.call("place", event=a[1], slot=0)["ok"] is False
    assert p.call("place", event=a[0], slot=1)["ok"] is False
    # fixing the other two solves it
    p.call("place", event=a[1], slot=1)
    p.call("place", event=a[2], slot=2)
    done = p.call("check")["view"]
    assert done["puzzle"]["status"] == "solved" and done["puzzle"]["checks"] == 2
    assert done["result"]["solved"] and [e["id"] for e in done["result"]["reveal"]] == a


def test_solving_learns_the_events_and_the_nuance_events_and_never_twice(p):
    r = p.solve()
    learned = set(p.m.S["sets"]["presidents-sample"]["learned"])
    puz = p.puzzle()
    assert set(puz.answer) <= learned
    assert {"c-bastille", "c-waterloo"} <= learned
    assert r["view"]["result"]["new_count"] == 5
    again = p.m.S["session"]["new"]
    assert len(again) == len(set(again))


def test_the_reveal_carries_dates_claims_confidence_and_three_sources_each(p):
    res = p.solve()["view"]["result"]
    for e in res["reveal"] + res["nuance"]:
        assert e["date_label"] and e["claim"]["text"]
        assert e["claim"]["confidence"] == "documented" and e["claim"]["symbol"] == "✔"
        assert len(e["claim"]["sources"]) >= 3
        for s in e["claim"]["sources"]:
            assert s["url"].startswith("https://") and s["read"] == "2026-10-07" and s["institution"] and s["note"]
    assert res["reveal"][0]["date_label"] == "30 April 1789"
    assert res["span"] == [1789, 1814]


def test_show_answer_reveals_but_learns_nothing_and_next_moves_on(p):
    r = p.call("show_answer")
    assert r["ok"] and r["view"]["puzzle"]["status"] == "revealed"
    assert r["view"]["set"]["found"] == 0 and r["view"]["result"]["solved"] is False
    assert p.m.S["sets"]["presidents-sample"]["solved"] == {}
    assert p.call("place", event=p.puzzle().tray[0], slot=0)["ok"] is False
    r2 = p.call("next")
    assert r2["view"]["puzzle"]["round"] == 1 and r2["view"]["puzzle"]["status"] == "playing"


def test_next_skips_solved_rounds_and_start_picks_the_first_unsolved(p):
    p.solve()
    r = p.call("next")["view"]["puzzle"]
    assert r["round"] == 1
    p.solve()
    assert p.call("start", section="s1")["view"]["puzzle"]["round"] == 2


def test_sections_unlock_when_their_requirements_are_cleared(p):
    assert p.call("start", section="s2")["ok"] is False
    for _ in range(12):
        v = p.call("boot")["view"]
        if v["sections"][0]["cleared"]:
            break
        p.solve()
        p.call("next")
    v = p.call("boot")["view"]
    assert v["sections"][0]["cleared"] and v["sections"][1]["unlocked"] and v["sections"][2]["unlocked"]
    assert v["sections"][3]["unlocked"] is False
    assert p.call("start", section="s2")["view"]["puzzle"]["section"] == "s2"
    assert p.call("start", section="s4")["ok"] is False
    assert p.call("start", section="nope")["ok"] is False


def test_a_cleared_section_shows_its_reading_once(p):
    res = None
    for _ in range(12):
        res = p.solve()["view"]["result"]
        if res["section_cleared"]:
            break
        p.call("next")
    assert res["section_cleared"] and res["readings"][0]["id"] == "r-s1"
    assert all(len(c["sources"]) >= 3 for c in res["readings"][0]["claims"])


def test_the_archive_fills_in_and_locked_entries_hide_their_titles(p):
    a = p.call("archive")["archive"]
    assert a["found"] == 0 and a["total"] == 64 and a["percent"] == 0
    assert [g["id"] for g in a["groups"]] == ["events", "elsewhere", "people", "places", "connections", "records", "sources", "choices"]
    assert all(e["title"] is None and not e["found"] and e["hint"] for g in a["groups"] for e in g["entries"])
    p.solve()
    a = p.call("archive")["archive"]
    assert a["found"] == 12 and a["percent"] == 18                  # 3 moments, 2 elsewhere, 3 people, 4 places
    titles = {e["id"]: e["title"] for g in a["groups"] for e in g["entries"] if e["found"]}
    assert titles["washington"] == "George Washington" and titles["paris"] == "Paris"
    assert "madison" in titles and "e-removal-act" not in titles


def test_entries_are_openable_only_once_found_and_show_their_claims(p):
    assert p.call("entry", id="e-washington-oath")["ok"] is False
    assert p.call("entry", id="washington")["ok"] is False
    p.solve()
    e = p.call("entry", id="e-washington-oath")["entry"]
    assert e["date_label"] == "30 April 1789" and len(e["claim"]["sources"]) == 3
    person = p.call("entry", id="washington")["entry"]
    assert person["kind"] == "person" and [x["id"] for x in person["events"]] == ["e-washington-oath"]
    place = p.call("entry", id="paris")["entry"]
    assert {x["id"] for x in place["events"]} == {"c-bastille"} | ({"e-louisiana"} if False else set())
    assert p.call("entry", id="nope")["ok"] is False


def test_view_claim_requires_the_claim_to_be_found_and_marks_it_viewed(p):
    assert p.call("view_claim", claim="c-e-washington-oath-date")["ok"] is False
    p.solve()
    r = p.call("view_claim", claim="c-e-washington-oath-date")
    assert r["ok"] and r["dirty"] and r["claim"]["viewed"] is True and len(r["claim"]["sources"]) == 3
    assert p.call("view_claim", claim="c-e-washington-oath-date")["dirty"] is False
    assert p.call("view_claim", claim="c-e-removal-act-date")["ok"] is False


def test_a_revealed_puzzles_claims_can_be_viewed_for_the_sources(p):
    p.call("show_answer")
    first = p.puzzle().answer[0]
    assert p.call("view_claim", claim="c-%s-date" % first)["ok"]


def test_info_lists_found_claims_with_sources_and_the_legend(p):
    info = p.call("info")["info"]
    assert info["found_claims"] == [] and info["counts"]["claims"] == 47 and info["counts"]["sources"] == 84
    assert [l["id"] for l in info["legend"]] == ["documented", "disputed", "traditional-but-doubtful"]
    assert info["set"]["draft"] is True
    p.solve()
    info = p.call("info")["info"]
    assert len(info["found_claims"]) == 5 and all(len(c["sources"]) >= 3 for f in info["found_claims"] for c in f["claims"])


def test_report_builds_a_payload_and_sends_nothing(p):
    r = p.call("report", claim="c-e-washington-oath-date", reason="wrong_date", note="  Looks off to me.  ")
    assert r["ok"] and r["sent"] is False and "opens soon" in r["notice"]
    pay = r["report"]
    assert pay["kind"] == "chronicle-claim-report" and pay["note"] == "Looks off to me."
    assert pay["claim_id"] == "c-e-washington-oath-date" and pay["set_version"] == 1 and pay["set_status"] == "sample-draft"
    assert len(pay["source_urls"]) == 3 and all(u.startswith("https://") for u in pay["source_urls"])
    assert r["dirty"] is False


def test_report_rejects_bad_input(p):
    for kwargs in ({"claim": "nope", "reason": "wrong_date"}, {"claim": "c-e-washington-oath-date", "reason": "spite"},
                   {"claim": "c-e-washington-oath-date", "reason": "other", "note": "x" * 501}, {"reason": "other"}):
        assert p.call("report", **kwargs)["ok"] is False


def test_the_engine_module_never_imports_a_network_library():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for name in ("game.py", "setdata.py", "puzzle.py", "report.py", "achievements.py"):
        src = (root / name).read_text(encoding="utf-8")
        for banned in ("urllib.request", "requests", "http.client", "socket", "fetch(", "XMLHttpRequest"):
            assert banned not in src, (name, banned)


def test_settings_hints_toggle_is_saved_and_validated(p):
    assert p.call("settings", hints=False)["view"]["settings"]["hints"] is False
    assert p.call("settings", hints="yes")["ok"] is False
    assert p.m.get_state()["settings"]["hints"] is False


def test_choose_set_and_the_picker(p):
    v = p.call("choose_set", set="presidents-sample")["view"]
    assert [s["id"] for s in v["sets"]] == ["presidents-sample"] and v["sets"][0]["status"] == "sample-draft"
    assert p.call("choose_set", set="nope")["ok"] is False


def test_a_second_set_can_be_added_without_engine_changes(g, raw, sample):
    """The picker and every view are driven by data: register a renamed copy and both play."""
    import copy
    import setdata
    files = copy.deepcopy(raw)
    files["meta"]["id"], files["meta"]["title"] = "presidents-copy", "Copy of the sample"
    g.register_set(setdata.load_set_dict(files))
    v = g.handle_dict({"action": "choose_set", "set": "presidents-copy"})["view"]
    assert [s["id"] for s in v["sets"]] == ["presidents-sample", "presidents-copy"]
    assert v["puzzle"]["id"].startswith("presidents-copy/")
    assert g.handle_dict({"action": "archive", "set": "presidents-sample"})["archive"]["found"] == 0


def test_a_set_that_fails_validation_is_skipped_and_reported(tmp_path, g, raw):
    import shutil
    import game
    from pathlib import Path
    SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sets" / "presidents-sample"
    shutil.copytree(SAMPLE_DIR, tmp_path / "bad")
    claims = json.loads((tmp_path / "bad" / "claims.json").read_text())
    claims[0]["sources"] = claims[0]["sources"][:2]
    (tmp_path / "bad" / "claims.json").write_text(json.dumps(claims))
    (tmp_path / "index.json").write_text(json.dumps({"sets": [{"folder": "bad"}]}))
    game.load_sets(tmp_path)
    assert game.SETS == {} and game.LOAD_PROBLEMS and "E_CLAIM_SOURCES" in game.LOAD_PROBLEMS[0]
    view = game.handle_dict({"action": "boot"})["view"]
    assert view["empty"] is True and view["problems"]
