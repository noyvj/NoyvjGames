import json

import game
from pulse import say_door, say_lamps


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def setup_function():
    call(action="reset")


def test_open_starts_with_no_scenes_and_nothing_settled():
    view = call(action="open")
    assert view["scenes"] == [] and view["scenes_total"] == 6 and view["settled"] is False
    assert view["station"] == {"lamps": 0, "door": "shut"}


def test_scenes_are_revealed_one_at_a_time_and_the_language_becomes_settled():
    seen_settled = []
    for k in range(1, 7):
        view = call(action="next_scene")
        assert len(view["scenes"]) == k
        seen_settled.append(view["settled"])
    assert seen_settled[0] is False and seen_settled[-1] is True
    assert call(action="next_scene")["scenes"].__len__() == 6      # no-op at the end


def test_notebook_entries_are_stored_never_judged_and_can_be_cleared():
    view = call(action="write", form="1000", gloss=" Lamp ")
    assert view["notebook"] == {"1000": "lamp"}
    assert call(action="write", form="1000", gloss="")["notebook"] == {}
    assert call(action="write", form="12", gloss="x")["notebook"] == {}       # not a token: ignored


def test_confirm_reports_a_count_only():
    call(action="write", form="1000", gloss="lamp")
    call(action="write", form="1001", gloss="wrong")
    result = call(action="confirm", forms=["1000", "1001"])
    assert result == {"right": 1, "chosen": 2}


def test_speaking_changes_the_station_and_answers_in_world():
    view = call(action="speak", marks=say_lamps(3))
    assert view["reaction"]["understood"] and view["station"]["lamps"] == 3
    view = call(action="speak", marks=say_door("open"))
    assert view["station"] == {"lamps": 3, "door": "open"}
    failed = call(action="speak", marks="1000" + "1010" + "1111")
    assert not failed["reaction"]["understood"] and failed["reaction"]["reason"] == "lamp_needs_number"
    assert failed["station"] == {"lamps": 3, "door": "open"}
    assert failed["spoken"][-1] == "1000" + "1010" + "1111"


def test_bad_requests_get_an_error_not_a_crash():
    assert "error" in json.loads(game.handle("not json"))
    assert "error" in call(action="nonsense")


def test_save_round_trip_merges_instead_of_replacing():
    call(action="write", form="1000", gloss="lamp")
    call(action="next_scene")
    saved = game.get_state()
    call(action="reset")
    call(action="write", form="1001", gloss="door")
    game.load_state(saved)
    view = call(action="open")
    assert view["notebook"] == {"1000": "lamp", "1001": "door"}
    assert len(view["scenes"]) == 1
    game.load_state(None)                       # garbage in never raises
    game.load_state({"station": {"lamps": "x"}})


# --- planets and contact ---------------------------------------------------------------------------

def test_planet_two_is_locked_until_planet_one_is_contacted():
    assert "error" in call(action="open", planet="compound")
    call(action="speak", marks=say_door("open"))
    call(action="speak", marks=say_lamps(5))
    view = call(action="open")
    assert view["planets"]["pulse"]["contact"] is True and view["planets"]["compound"]["unlocked"] is True
    assert call(action="open", planet="compound")["planet"] == "compound"


def _contact_with_planet_one():
    call(action="speak", marks=say_door("open"))
    call(action="speak", marks=say_lamps(5))


def test_unknown_planets_and_actions_are_errors_not_crashes():
    assert "error" in call(action="open", planet="narnia")


def test_the_compound_planet_plays_end_to_end():
    _contact_with_planet_one()
    view = call(action="open", planet="compound")
    assert view["scenes"] == [] and view["components"].keys() == {"k", "m", "t", "o", "u"} and view["tray"] == []
    for k in range(1, 5):
        view = call(action="next_scene", planet="compound")
        assert len(view["scenes"]) == k
    assert view["settled"] is True and view["letters"] == ["k", "o", "m", "u", "t"]
    bad = call(action="speak", planet="compound", glyph="ok")
    assert not bad["reaction"]["understood"] and bad["reaction"]["reason"] == "order"
    call(action="speak", planet="compound", glyph="ku")
    assert call(action="open", planet="compound")["planets"]["compound"]["contact"] is False
    done = call(action="speak", planet="compound", glyph="tu")
    assert done["tray"] == ["big water", "big fire"] and done["planets"]["compound"]["contact"] is True


def test_compound_notebook_is_separate_and_confirm_counts_only():
    _contact_with_planet_one()
    call(action="write", planet="compound", form="k", gloss="Water")
    call(action="write", planet="compound", form="u", gloss="small")      # wrong
    call(action="write", planet="compound", form="zz", gloss="ignored")
    assert call(action="open", planet="compound")["notebook"] == {"k": "water", "u": "small"}
    assert call(action="open")["notebook"] == {}                           # planet 1's notebook is untouched
    assert call(action="confirm", planet="compound", forms=["k", "u"]) == {"right": 1, "chosen": 2}


def test_save_round_trip_keeps_both_planets():
    _contact_with_planet_one()
    call(action="next_scene", planet="compound")
    call(action="write", planet="compound", form="k", gloss="water")
    call(action="speak", planet="compound", glyph="ku")
    saved = json.loads(json.dumps(game.get_state()))
    call(action="reset")
    game.load_state(saved)
    pulse_view = call(action="open")
    comp = call(action="open", planet="compound")
    assert pulse_view["planets"]["pulse"]["contact"] is True
    assert comp["notebook"] == {"k": "water"} and len(comp["scenes"]) == 1 and comp["tray"] == ["big water"]
    game.load_state({"tray": ["nonsense", "big nothing"], "compound": {"spoken": ["ku", "1"]}})   # garbage never raises


# --- planet 3: the bridge language ------------------------------------------------------------------

def _contact_with_planet_two():
    _contact_with_planet_one()
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")


def test_planet_three_is_locked_until_planet_two_is_contacted():
    assert "error" in call(action="open", planet="bridge")
    _contact_with_planet_one()
    assert "error" in call(action="open", planet="bridge")          # planet 1 alone is not enough
    assert call(action="open")["planets"]["bridge"]["unlocked"] is False
    call(action="speak", planet="compound", glyph="ku")
    call(action="speak", planet="compound", glyph="tu")
    view = call(action="open", planet="bridge")
    assert view["planet"] == "bridge" and call(action="open")["planets"]["bridge"]["unlocked"] is True
    assert view["planets"]["bridge"]["contact"] is False


def test_the_bridge_planet_starts_empty_and_reveals_scenes_in_order():
    _contact_with_planet_two()
    view = call(action="open", planet="bridge")
    assert view["scenes"] == [] and view["scenes_total"] == 5 and view["stock"] == [] and view["settled"] is False
    assert view["stock_text"] == "The counter is empty." and view["markers"] == [] and "tu" in view["nouns"]
    assert view["numbers"][0] == "0000" and view["numbers"][5] == "0101" and len(view["numbers"]) == 8
    assert view["components"].keys() >= {"k", "m", "t", "o", "u", "p", "n", "q"}
    assert "five big fire" in view["goal"] and "ask" in view["goal"]
    settled = []
    for k in range(1, 6):
        view = call(action="next_scene", planet="bridge")
        assert len(view["scenes"]) == k
        settled.append(view["settled"])
    assert settled == [False] * 4 + [True]
    assert view["markers"] == ["p", "n", "q"]
    assert view["scenes"][1] == {"id": "ku-p-3", "message": "ku p 0011", "reply": "",
                                 "before": {"items": [{"label": "big water", "count": 1}]},
                                 "after": {"items": [{"label": "big water", "count": 4}]}}
    assert view["scenes"][4]["reply"] == "The station shows 2 small grain."
    assert len(call(action="next_scene", planet="bridge")["scenes"]) == 5          # no-op at the end


def test_bridge_notebook_is_separate_and_confirm_counts_only_with_the_role_word():
    _contact_with_planet_two()
    for letter, gloss in (("p", "Plural"), ("n", "ask"), ("q", "ask"), ("k", "water"), ("zz", "x")):
        call(action="write", planet="bridge", form=letter, gloss=gloss)
    view = call(action="open", planet="bridge")
    assert view["notebook"] == {"p": "plural", "n": "ask", "q": "ask"}     # only markers; stored, never judged
    assert call(action="open", planet="compound")["notebook"] == {}
    assert call(action="confirm", planet="bridge", forms=["p", "n", "q"]) == {"right": 2, "chosen": 3}
    assert call(action="confirm", planet="bridge", forms=["z"]) == {"right": 0, "chosen": 1}
    call(action="write", planet="bridge", form="p", gloss="")
    assert "p" not in call(action="open", planet="bridge")["notebook"]


def test_speaking_on_planet_three_changes_the_counter_and_errors_stay_in_world():
    _contact_with_planet_two()
    view = call(action="speak", planet="bridge", message="ku p 0011")
    assert view["reaction"]["understood"] and view["stock"] == [{"label": "big water", "count": 3}]
    bad = call(action="speak", planet="bridge", message="ku p")
    assert not bad["reaction"]["understood"] and bad["reaction"]["reason"] == "plural_needs_count"
    assert bad["reaction"]["text"] and bad["stock"] == view["stock"]            # nothing changed
    for message, reason in (("", "silence"), ("zz", "no_thing"), ("ku x", "unknown_marker"), ("ku n 0011", "extra")):
        out = call(action="speak", planet="bridge", message=message)
        assert out["reaction"]["reason"] == reason and "error" not in out
    asked = call(action="speak", planet="bridge", message="ku q")
    assert asked["reaction"]["reply"] == "The station shows 3 big water." and asked["stock"] == view["stock"]
    gone = call(action="speak", planet="bridge", message="  ku   n ")      # spacing is forgiven
    assert gone["stock"] == []
    assert gone["spoken"][-2:] == ["ku q", "ku n"]
    assert "zz" in gone["spoken"]


def test_the_goal_needs_exactly_five_big_fire_and_the_ask_sign():
    _contact_with_planet_two()
    call(action="speak", planet="bridge", message="tu p 0101")
    state = call(action="open", planet="bridge")
    assert state["planets"]["bridge"]["contact"] is False                       # five, but never asked
    call(action="speak", planet="bridge", message="tu p 0001")                  # six now
    asked = call(action="speak", planet="bridge", message="tu q")
    assert asked["planets"]["bridge"]["contact"] is False and asked["stock"] == [{"label": "big fire", "count": 6}]
    call(action="speak", planet="bridge", message="tu n")
    call(action="speak", planet="bridge", message="tu p 0101")
    done = call(action="open", planet="bridge")
    assert done["planets"]["bridge"]["contact"] is True                          # the flag was set earlier
    assert "third_contact" in {a["id"] for a in done["achievements"] if a["earned"]}
    call(action="speak", planet="bridge", message="tu n")                        # contact is kept once earned
    assert call(action="open", planet="bridge")["planets"]["bridge"]["contact"] is True


def test_asking_first_then_building_up_also_makes_contact():
    _contact_with_planet_two()
    call(action="speak", planet="bridge", message="tu q")                        # "no big fire", but the ask sign was used
    assert call(action="open", planet="bridge")["planets"]["bridge"]["contact"] is False
    done = call(action="speak", planet="bridge", message="tu p 0101")
    assert done["planets"]["bridge"]["contact"] is True


def test_other_planets_reset_and_save_round_trip_keep_planet_three():
    _contact_with_planet_two()
    call(action="next_scene", planet="bridge")
    call(action="write", planet="bridge", form="p", gloss="plural")
    call(action="speak", planet="bridge", message="tu p 0101")
    call(action="speak", planet="bridge", message="tu q")
    saved = json.loads(json.dumps(game.get_state()))
    assert saved["version"] == 3 and saved["stock"] == [["big fire", 5]]
    call(action="reset")
    assert "error" in call(action="open", planet="bridge")
    assert game.get_state()["stock"] == [] and game.get_state()["contact"] == {"pulse": False, "compound": False, "bridge": False}
    game.load_state(saved)
    view = call(action="open", planet="bridge")
    assert view["planets"]["bridge"]["contact"] is True and view["notebook"] == {"p": "plural"}
    assert len(view["scenes"]) == 1 and view["stock"] == [{"label": "big fire", "count": 5}]
    assert view["spoken"] == ["tu p 0101", "tu q"]
    # a save made before planet 3 existed (version 2, no bridge keys) still loads
    old = {"version": 2, "contact": {"pulse": True, "compound": True}, "compound": {"scenes_seen": 2}}
    call(action="reset")
    game.load_state(old)
    view = call(action="open", planet="bridge")
    assert view["scenes"] == [] and view["stock"] == [] and view["planets"]["bridge"]["contact"] is False


def test_loading_garbage_for_planet_three_never_raises_and_loading_merges():
    game.load_state({"bridge": {"scenes_seen": "x"}})
    game.load_state({"bridge": "nonsense", "stock": "nonsense"})
    game.load_state({"bridge": {"notebook": {"entries": {"p": 5}}, "spoken": ["ku p 0011", "<script>", 7, None],
                                "scenes_seen": 99},
                     "stock": [["big nothing", 3], ["big fire", 99], ["tiny water", 2], ["small grain", True], 7, ["small water", 2]],
                     "contact": {"compound": True}})
    game.load_state(["not", "a", "dict"])
    view = call(action="open", planet="bridge")
    assert view["scenes_total"] == 5 and len(view["scenes"]) == 5
    assert view["stock"] == [{"label": "big fire", "count": 7}, {"label": "small water", "count": 2}]
    assert "<script>" not in view["spoken"]
    # loading merges: a saved guess never deletes a newer one
    call(action="write", planet="bridge", form="n", gloss="negate")
    game.load_state({"bridge": {"notebook": {"entries": {"n": "ask", "q": "ask"}}}})
    nb = call(action="open", planet="bridge")["notebook"]
    assert nb["n"] == "negate" and nb["q"] == "ask"
