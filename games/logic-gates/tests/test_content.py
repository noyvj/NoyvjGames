"""Level text, the hint ladder's content and the claims the About page makes about the game."""

import re

import levels
import words
from chips import BASE
from net import parse_circuit
from sim import Prog, Sim, flatten


def test_every_level_has_goal_nudge_hint_and_log_text():
    for lv in levels.LEVELS:
        for key in ("goal", "nudge", "hint", "log"):
            assert isinstance(lv[key], str) and len(lv[key]) > 8, (lv["id"], key)
        assert lv["nudge"] != lv["hint"] and len(lv["name"]) >= 3


def test_the_answer_in_words_names_every_chip_and_every_lamp():
    for lv in levels.LEVELS:
        lines = words.describe(lv["ref"], lv["outs"])
        assert len(lines) == len(lv["ref"]["chips"]) + len(lv["outs"])
        assert all(line.endswith(".") for line in lines)


def test_no_nudge_or_hint_gives_the_whole_answer_away_before_the_answer_rung():
    # a hint may name chips but never prints the reference netlist text
    for lv in levels.LEVELS:
        assert lv["ref_text"] not in lv["hint"]
        assert not re.search(r"\w+\s*=\s*\w+\(", lv["hint"])


def test_story_lines_are_short_and_chapters_have_an_intro():
    assert all(len(lv["log"]) < 200 for lv in levels.LEVELS)
    assert len(levels.CHAPTERS) == 5 and all(len(c["intro"]) > 40 for c in levels.CHAPTERS)


def test_the_about_page_claim_that_nand_alone_makes_every_two_input_function_is_true():
    """Close the set of two-input truth tables (4-bit codes, row order 00 01 10 11) under NAND, starting from A and B."""
    a, b = 0b1100, 0b1010
    have = {a, b}
    grew = True
    while grew:
        grew = False
        for x in list(have):
            for y in list(have):
                n = (~(x & y)) & 0b1111
                if n not in have:
                    have.add(n)
                    grew = True
    assert len(have) == 16


def test_the_sr_latch_cell_matches_the_nor_loop_the_about_page_describes():
    reg = dict(BASE)
    loop = parse_circuit("q = nor(R, qn); qn = nor(S, q); Q := q", ["S", "R"], ["Q"], reg)
    cell = parse_circuit("c = sr(S, R); Q := c.Q", ["S", "R"], ["Q"], reg)
    a, b = Sim(Prog(flatten(loop, reg, ["S", "R"], ["Q"]), ["S", "R"])), Sim(Prog(flatten(cell, reg, ["S", "R"], ["Q"]), ["S", "R"]))
    for s, r in [(0, 1), (1, 0), (0, 0), (0, 1), (0, 0), (1, 0), (0, 0)]:
        a.step({"S": s, "R": r})
        b.step({"S": s, "R": r})
        assert a.out("Q") == b.out("Q")
