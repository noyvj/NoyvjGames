"""Every authored reaction is PROVED: one balancing setting, equal to the stored answer, by three independent routes; product-choice
rounds have exactly one balanceable list; the data is clean, safe, deterministic and every word the player reads is accounted for."""

import itertools
import re

import pytest

import chem
import elements
import reactions
from balance import brute_force, check

ALL = reactions.ALL


def test_the_bench_has_five_chapters_of_eight():
    assert [len(c["reactions"]) for c in reactions.CHAPTERS] == [8, 8, 8, 8, 8] and len(ALL) == 40
    assert [r.number for r in ALL] == list(range(1, 41))
    assert len({r.id for r in ALL}) == 40 and len({r.title for r in ALL}) == 40


@pytest.mark.parametrize("r", ALL, ids=lambda r: r.id)
def test_the_nullspace_has_exactly_one_dimension_and_its_smallest_solution_is_the_stored_answer(r):
    assert len(chem.nullspace(r.reactants, r.products)) == 1
    assert chem.smallest(r.reactants, r.products) == r.answer
    solutions = chem.solutions(r.reactants, r.products)
    assert [s for s in solutions if chem.lowest_terms(s)] == [r.answer]
    assert all(s == [k * a for a in r.answer] for s in solutions for k in [s[0] // r.answer[0]])      # every other setting is a multiple


@pytest.mark.parametrize("r", ALL, ids=lambda r: r.id)
def test_the_stored_answer_passes_the_same_ledger_the_player_uses(r):
    rows = chem.ledger(r.reactants, r.products, r.answer)
    assert chem.is_balanced(rows) and chem.lowest_terms(r.answer)
    assert len(r.answer) == r.size and all(chem.MIN_COEF <= c <= chem.MAX_COEF for c in r.answer)


@pytest.mark.parametrize("r", [r for r in ALL if r.size <= 5], ids=lambda r: r.id)
def test_a_brute_force_search_finds_no_other_setting(r):
    """Independent of the nullspace code: try every setting from 1 to 12."""
    assert [s for s in brute_force(r.reactants, r.products) if chem.lowest_terms(s)] == [r.answer]


@pytest.mark.parametrize("r", ALL, ids=lambda r: r.id)
def test_mass_is_conserved_to_two_decimals(r):
    n = len(r.reactants)
    left = chem.side_mass(r.reactants, r.answer[:n], elements.MASSES)
    right = chem.side_mass(r.products, r.answer[n:], elements.MASSES)
    assert abs(float(left) - float(right)) < 0.01 and left == right


@pytest.mark.parametrize("r", ALL, ids=lambda r: r.id)
def test_tools_balance_agrees(r):
    assert check(r)[0]


def test_every_product_choice_round_has_exactly_one_balanceable_list():
    rounds = [r for r in ALL if r.is_round]
    assert [r.chapter for r in rounds] == [1] * 8 + [2] * 8 + [3] * 8 + [4] * 8 and not any(r.is_round for r in reactions.CHAPTERS[0]["reactions"])
    for r in rounds:
        assert len(r.choices) == 4 and r.choices[r.right] == r.products
        balanceable = [i for i, c in enumerate(r.choices) if chem.can_balance(r.reactants, c)]
        assert balanceable == [r.right], r.id
        assert len({tuple(c) for c in r.choices}) == 4
        for i, cand in enumerate(r.choices):
            if i != r.right:
                assert chem.why_not(r.reactants, cand)


def test_the_right_list_is_not_always_in_the_same_place():
    positions = {r.right for r in ALL if r.is_round}
    assert positions == {0, 1, 2, 3}


def test_every_wrong_list_gives_a_reason_of_a_known_kind():
    kinds = set()
    for r in ALL:
        for i, cand in enumerate(r.choices or []):
            if i == r.right:
                continue
            why = chem.why_not(r.reactants, cand)
            kinds.add("extra" if "appear from nowhere" in why else "missing" if "nowhere to go" in why else "contradiction")
    assert kinds == {"extra", "missing", "contradiction"}


def test_chapter_three_formulas_use_bracket_groups_and_earlier_ones_do_not():
    assert any(r.has_group for r in reactions.CHAPTERS[2]["reactions"])
    assert not any(r.has_group for r in reactions.CHAPTERS[0]["reactions"] + reactions.CHAPTERS[1]["reactions"])
    assert sum(1 for r in reactions.CHAPTERS[2]["reactions"] if r.has_group) >= 4


def test_every_formula_has_a_name_and_every_element_a_use_and_a_mass():
    for r in ALL:
        for f in r.formulas() + [x for c in (r.choices or []) for x in c]:
            assert f in reactions.NAMES, f
            assert reactions.NAMES[f][0].islower()                  # names read as plain lower case words
    used = set()
    for r in ALL:
        used.update(r.elements)
    assert used == set(elements.BENCH) == set(reactions.BENCH_ELEMENTS)
    for sym, info in elements.BENCH.items():
        assert sym in elements.BY_SYMBOL and info["use"].endswith(".") and len(info["use"]) < 140
        assert re.fullmatch(r"\d+(\.\d+)?", info["mass"]) and info["kind"] and info["state"] in ("gas", "solid", "liquid")


def test_the_banned_list_lint_finds_nothing_in_any_reaction():
    for r in ALL:
        texts = [r.title, r.blurb, r.fennel] + [reactions.NAMES[f] for f in r.formulas()]
        formulas = r.formulas() + [x for c in (r.choices or []) for x in c]
        assert chem.lint(texts, formulas) == [], r.id
    for sym, info in elements.BENCH.items():
        assert chem.lint([info["use"]], []) == []


def test_atomic_masses_are_the_snapshot_values():
    assert elements.MASSES["H"] == "1.0080" and elements.MASSES["O"] == "15.999" and elements.MASSES["C"] == "12.011"
    assert elements.SNAPSHOT_DATE == "2026-10-12"


def test_text_is_short_one_line_each():
    for r in ALL:
        assert len(r.fennel) <= 130 and len(r.blurb) <= 260 and r.fennel.count(".") <= 4


def test_gating_opens_the_next_chapter_after_five_of_the_one_before():
    shelf = {}
    assert reactions.chapter_open(shelf, 0) and not reactions.chapter_open(shelf, 1) and not reactions.chapter_open(shelf, 2)
    for r in reactions.CHAPTERS[0]["reactions"][:4]:
        shelf[r.id] = 1
    assert not reactions.chapter_open(shelf, 1)
    shelf[reactions.CHAPTERS[0]["reactions"][6].id] = 1               # any fifth one
    assert reactions.chapter_open(shelf, 1) and not reactions.chapter_open(shelf, 2)
    for r in reactions.CHAPTERS[1]["reactions"][3:]:
        shelf[r.id] = 1
    assert reactions.chapter_open(shelf, 2)
    assert reactions.chapters_done(shelf) == 0


def test_the_bench_elements_are_in_atomic_number_order():
    nums = [elements.number_of(s) for s in reactions.BENCH_ELEMENTS]
    assert nums == sorted(nums) and len(nums) == 15


def test_no_clock_and_no_randomness_in_any_engine_module():
    from pathlib import Path
    for path in Path(reactions.__file__).parent.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M), path.name
        assert "shuffle(" not in text and "sample(" not in text and "random" not in re.sub(r"\"\"\".*?\"\"\"", "", text, flags=re.S).replace("randomness", "")


def test_the_periodic_layout_has_118_unique_places_and_the_right_shape():
    cells = {}
    for z, sym, name in elements.ELEMENTS:
        pos = elements.position(z)[:2]
        assert pos not in cells
        cells[pos] = z
    assert len(cells) == 118 and len(elements.ELEMENTS) == 118
    assert elements.position(1) == (1, 1, "body") and elements.position(2) == (1, 18, "body")
    assert elements.position(26) == (4, 8, "body") and elements.position(17) == (3, 17, "body") and elements.position(20) == (4, 2, "body")
    assert elements.position(57)[0] == 9 and elements.position(89)[0] == 10 and elements.position(72) == (6, 4, "body")
    assert elements.group_of(11) == 1 and elements.group_of(17) == 17 and elements.group_of(57) == 0 and elements.period_of(26) == 4
    assert [s for _z, s, _n in elements.ELEMENTS[:10]] == ["H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne"]
    assert elements.ELEMENTS[-1][1:] == ("Og", "Oganesson") and elements.BY_SYMBOL["Fe"][2] == "Iron"
