from notebook import LexisState, Notebook
from pulse import PULSE, spell_number


def test_the_notebook_stores_guesses_without_judging_them():
    nb = Notebook()
    nb.write("1000", "  Bread ")
    assert nb.entries == {"1000": "bread"}
    nb.write("1000", "")
    assert nb.entries == {}


def test_confirm_reports_how_many_are_right_not_which():
    nb = Notebook()
    nb.write("1000", "lamp")
    nb.write("1001", "window")        # wrong
    nb.write(spell_number(3), "3")
    assert nb.confirm(["1000", "1001", spell_number(3)]) == 2
    assert nb.confirm(["1000"]) == 1
    assert nb.confirm(["1010"]) == 0   # nothing written for it: not counted, not revealed


def test_numbers_are_judged_by_their_value():
    nb = Notebook()
    nb.write(spell_number(5), "five")   # words for numbers are not the digits: not accepted as written
    nb.write(spell_number(6), "6")
    assert nb.confirm([spell_number(5), spell_number(6)]) == 1


def test_state_round_trips_and_ignores_garbage():
    state = LexisState()
    state.notebook.write("1000", "lamp")
    state.see_next_scene(6)
    state.spoken = ["10000001" + "1111"]
    again = LexisState.from_dict(state.to_dict())
    assert again.to_dict() == state.to_dict()
    junk = LexisState.from_dict({"scenes_seen": -4, "spoken": ["hello", "0101"], "notebook": {"entries": {"1000": "x"}}})
    assert junk.scenes_seen == 0 and junk.spoken == ["0101"] and junk.notebook.entries == {"1000": "x"}
    assert LexisState.from_dict(None).to_dict()["scenes_seen"] == 0


def test_scenes_seen_never_exceeds_the_total():
    state = LexisState()
    for _ in range(20):
        state.see_next_scene(6)
    assert state.scenes_seen == 6
