import json

import boards
import game
import logbook
import play
import render
import rules
import solver


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def deck(index):
    return [boards.BY_ID[i] for i in boards.CHAPTER_LIST[index]["rooms"]]


def test_the_whole_station_is_forty_boards_in_five_decks_of_eight():
    assert [len(c["rooms"]) for c in boards.CHAPTER_LIST] == [8, 8, 8, 8, 8] and len(boards.ORDER) == 40
    assert set(logbook.LOGS) == set(boards.ORDER)
    sizes = [(b.w, b.h) for b in boards.ALL_BOARDS]
    assert min(w for w, _ in sizes) == 5 and max(max(s) for s in sizes) == 9 and all(w == h for w, h in sizes)


def test_deck_four_has_valves_and_deck_five_has_mixers():
    assert all(b.valves for b in deck(3)) and all(b.mixers for b in deck(4))
    assert all(len(b.lines) <= 8 for b in boards.ALL_BOARDS)
    for b in deck(3):
        assert "valve" in rules.flags_of(b, b.solution), b.id


def test_valves_matter_somewhere_in_deck_four():
    """Taking every valve off a board must leave more than one restored layout on at least some boards (valves are real clues)."""
    loadbearing = 0
    for b in deck(3):
        rows = [list(r) for r in b.rows]
        for (x, y) in b.valves:
            rows[y][x] = "."
        loose = rules.Board({"id": "l", "rows": ["".join(r) for r in rows], **({"mixers": b.spec["mixers"]} if "mixers" in b.spec else {})})
        if len(solver.solve(loose, 2, node_limit=400000)) > 1:
            loadbearing += 1
    assert loadbearing >= 3


def test_every_valve_and_mixer_board_can_be_laid_by_dragging_and_a_mixer_takes_both_lines():
    for b in deck(3) + deck(4):
        d = play.Drawing(b)
        for c in b.lines:
            path = b.solution[c]
            assert d.begin(path[0])[0]
            for cell in path[1:]:
                assert d.move(cell)[0], (b.id, c, cell)
            d.end()
        assert d.status() == rules.RESTORED
    for b in deck(4):
        for cell, pair in b.mixers.items():
            ends = [b.solution[c][-1] for c in pair]
            assert ends == [cell, cell] and b.solution[pair[0]][-2] != b.solution[pair[1]][-2]


def test_the_new_parts_are_drawn():
    for b in deck(3):
        assert "hr-valve-arrow" in render.board_svg(b)
    for b in deck(4):
        assert "hr-mixer-body" in render.board_svg(b) and ">M<" in render.board_svg(b)


def test_the_achievement_totals_match_the_station():
    import achievements
    by_id = {a[0]: a for a in achievements.ACHIEVEMENTS}
    assert by_id["station_lit"][4] == by_id["hull_whole"][4] == len(boards.ORDER)
    assert all(len(row) == 5 for row in achievements.ACHIEVEMENTS), "no per-deck gate on any achievement (AN-1)"


def test_a_perfect_player_restores_all_forty_rooms():
    import progress
    game.game.__init__()
    for bid in boards.ORDER:
        assert progress.board_open(game.game.st, bid), bid
        call(action="pick", board=bid)
        game.game.draw.load_answer(boards.BY_ID[bid].solution)
        game.game._record()
    v = call(action="open")
    assert v["totals"]["patched"] == v["totals"]["restored"] == 40 and v["totals"]["decks_restored"] == 5
    assert all(a["earned"] for a in v["achievements"] if a["id"] not in ("second_thoughts", "second_opinion", "pipe_layer"))
