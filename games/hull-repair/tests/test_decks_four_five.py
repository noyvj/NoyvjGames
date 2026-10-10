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


def test_the_whole_station_is_forty_four_boards_in_five_decks():
    """AN-2: Life Support and The Core each start with two practice boards, so decks are 8, 8, 8, 10, 10."""
    assert [len(c["rooms"]) for c in boards.CHAPTER_LIST] == [8, 8, 8, 10, 10] and len(boards.ORDER) == 44
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


def test_a_perfect_player_restores_all_forty_four_rooms():
    import progress
    game.game.__init__()
    for bid in boards.ORDER:
        assert progress.board_open(game.game.st, bid), bid
        call(action="pick", board=bid)
        game.game.draw.load_answer(boards.BY_ID[bid].solution)
        game.game._record()
    v = call(action="open")
    assert v["totals"]["patched"] == v["totals"]["restored"] == 44 and v["totals"]["decks_restored"] == 5
    assert all(a["earned"] for a in v["achievements"] if a["id"] not in ("second_thoughts", "second_opinion", "pipe_layer"))


PRACTICE_VALVE = ("spare-valve-closet", "vent-stack")
PRACTICE_MIXER = ("junction-closet", "relay-alcove")


def test_practice_boards_come_before_the_first_valve_and_the_first_mixer_board():
    """AN-2 (owner question Hr5): the new parts are not moved earlier; two gentle boards of each sit just before the old first one."""
    life, core = boards.CHAPTER_LIST[3]["rooms"], boards.CHAPTER_LIST[4]["rooms"]
    assert tuple(life[:2]) == PRACTICE_VALVE and life[2] == "air-scrubbers"
    assert tuple(core[:2]) == PRACTICE_MIXER and core[2] == "power-core"
    first_valve = min(i for i, bid in enumerate(boards.ORDER) if boards.BY_ID[bid].valves)
    first_mixer = min(i for i, bid in enumerate(boards.ORDER) if boards.BY_ID[bid].mixers)
    assert boards.ORDER[first_valve] == PRACTICE_VALVE[0] and boards.ORDER[first_mixer] == PRACTICE_MIXER[0]
    assert first_valve < first_mixer


def test_practice_boards_are_gentle_and_teach_exactly_one_new_part():
    for bid in PRACTICE_VALVE + PRACTICE_MIXER:
        b = boards.BY_ID[bid]
        assert b.w == b.h and b.w <= 6 and len(b.lines) <= 5, bid
        assert not b.holes and not b.bridges, bid
    for bid in PRACTICE_VALVE:
        b = boards.BY_ID[bid]
        assert len(b.valves) == 1 and not b.mixers and "valve" in rules.flags_of(b, b.solution), bid
    for bid in PRACTICE_MIXER:
        b = boards.BY_ID[bid]
        assert len(b.mixers) == 1 and not b.valves and "mix" in rules.flags_of(b, b.solution), bid
    # each pair gets a little harder: the second board is bigger than the first
    assert boards.BY_ID["vent-stack"].w > boards.BY_ID["spare-valve-closet"].w
    assert boards.BY_ID["relay-alcove"].w > boards.BY_ID["junction-closet"].w


def test_practice_boards_have_exactly_one_restored_layout_and_a_log_line():
    for bid in PRACTICE_VALVE + PRACTICE_MIXER:
        b = boards.BY_ID[bid]
        sols = solver.solve(b, 2, node_limit=400000)
        assert len(sols) == 1 and rules.status(b, sols[0]) == rules.RESTORED
        assert logbook.LOGS[bid].strip() and len(logbook.LOGS[bid]) < 220


def test_the_map_fits_ten_rooms_in_a_deck_and_every_room_is_clickable():
    svg = render.station_svg(game.game._rooms_view())
    assert svg.count("data-id=") == 44 and svg.count("hr-room-empty") == 0
    for deck_index in (3, 4):
        assert len(boards.CHAPTER_LIST[deck_index]["rooms"]) == 10
    widths = render._widths(10, 3)
    assert len(widths) == 10 and sum(widths) + 4 * 9 == render.ROW_SPAN and min(widths) >= 40
    assert render._widths(8, 0) == list(render.ROOM_WIDTHS)       # the eight-room decks are drawn exactly as before


def test_old_saves_without_the_practice_boards_still_load_and_keep_their_rooms():
    game.game.__init__()
    old = boards.BY_ID["air-scrubbers"]
    game.load_state({"cur": "air-scrubbers", "best": {"air-scrubbers": rules.encode(old.solution)}})
    v = call(action="open")
    assert v["board"]["id"] == "air-scrubbers" and v["totals"]["restored"] == 1 and v["totals"]["rooms"] == 44
    assert v["board"]["new"] == "" and boards.BY_ID["spare-valve-closet"].number == 1
    assert call(action="pick", board="spare-valve-closet")["board"]["new"].startswith("Valves")
