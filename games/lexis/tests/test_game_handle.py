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
