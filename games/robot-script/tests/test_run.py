import dsl
import room
import run
from room import Layout


def go(rows, text, **kw):
    return run.run(Layout(rows, **kw), dsl.from_text(text))


def test_forward_and_exit():
    r = go([">..E"], "main: F F F")
    assert r.status == "cleared" and r.actions == 3 and r.state[:3] == (3, 0, 1)
    assert len(r.frames) == 4 and r.frames[0][-1] == "" and r.frames[1][-1] == "main/0"


def test_short_list_is_not_cleared_and_says_what_is_left():
    r = go([">..E"], "main: F F")
    assert r.status == "short" and "exit pad" in r.message
    assert not r.cleared


def test_wall_halts_with_a_plain_reason_and_the_robot_stays():
    r = go([">.#E"], "main: F F F")
    assert r.status == "halt" and r.actions == 2 and r.state[0] == 1
    assert "wall" in r.message and r.at == "main/1"


def test_edge_of_the_room_halts():
    r = go([">E"], "main: F F")
    assert r.status == "halt" and "edge" in r.message


def test_door_opens_only_after_its_switch():
    rows = [">1AE"]
    assert go(rows, "main: F F").status == "halt"
    assert go(rows, "main: F S F F").status == "cleared"
    assert "Light switch 1" in go(rows, "main: F F").message


def test_turning_changes_heading_and_cycles():
    r = go([">..", "..."], "main: R F L F")
    assert r.state[:3] == (1, 1, 1)
    r = go([">..", "..."], "main: L L L L")
    assert r.state[2] == 1


def test_grab_and_place_rules():
    rows = [">poE"]
    assert go(rows, "main: F G F P F").status == "cleared"
    assert "no part" in go(rows, "main: G").message
    assert "hands are full" in go([">ppo"], "main: F G F G").message
    assert "not carrying" in go(rows, "main: F F P").message
    assert "no empty socket" in go([">poo"], "main: F G P F P", strict=False).message


def test_no_socket_means_a_part_goal():
    r = go([">pE"], "main: F G F")
    assert r.status == "cleared"
    assert go([">pE"], "main: F F").status == "short"


def test_switch_rules_and_idempotence():
    assert go([">1"], "main: F S").status == "cleared"
    assert go([">1"], "main: F S S").status == "cleared"     # lighting a lit switch is harmless
    assert go([">1"], "main: S").status == "halt"


def test_rep_until_if_call():
    assert go([">...E"], "main: rep 4 { F }").status == "cleared"
    assert go([">....#"], "main: until blocked { F }").state[0] == 4
    assert go([">.p..E"], "main: until part { F }").state[0] == 2
    assert go([">.p.E"], "main: F F if part { G } else { R } F F").status == "cleared"
    r = go([">...E"], "main: A A A A\nA: F")
    assert r.status == "cleared"
    r = go([">....E"], "main: B F\nB: A A\nA: F F")
    assert r.status == "cleared"


def test_frames_carry_the_address_of_calls_and_nested_blocks():
    r = go([">...E"], "main: rep 3 { F } \nA: F")
    assert [f[-1] for f in r.frames[1:]] == ["main/0/2/0"] * 3
    r = go([">..E"], "main: A F F\nA: F")
    assert r.frames[1][-1] == "A/0"


def test_endless_loop_is_stopped_safely_not_punished():
    r = go([">..."], "main: until blocked { L L L L }")
    assert r.status == "loop" and r.actions == run.ACTION_LIMIT and "Nothing is lost" in r.message
    r = go([">..."], "main: until blocked { }")
    assert r.status == "loop"


def test_run_is_deterministic():
    rows = [">p.1A.oE"]
    a = go(rows, "main: F G F S F F P F")
    b = go(rows, "main: F G F S F F P F")
    assert a.frames == b.frames and a.status == b.status


def test_goal_list_labels():
    layout = Layout([">p1AoE", "......"])
    g = room.goals(layout, layout.initial())
    assert [x["id"] for x in g] == ["exit", "sockets", "switches"]
    assert not any(x["met"] for x in g)


def test_layout_validation():
    for rows in (["...."], [">>"], [">a"], [">oo"], [">pp"], [">A"], [">11"], [">" + "." * 10], ["." * 9, ">" * 9][:1] + ["x" * 9]):
        try:
            Layout(rows)
        except room.LayoutError:
            continue
        raise AssertionError(rows)
