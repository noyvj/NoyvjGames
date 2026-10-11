"""The pictures are proved here, one by one: each has exactly ONE solution, line logic alone finishes it (nobody has to guess),
its stored bitmap equals the solved grid, its clues match the picture, and none of it depends on a clock or a random source."""

import pytest

import nonogram as n
import pictures

ALL = pictures.ALL


def ids():
    return [p.id for p in ALL]


def test_each_gallery_has_ten_pictures_and_the_sizes_the_plan_gives():
    assert len(pictures.GALLERIES) >= 3
    assert [len(g["pictures"]) for g in pictures.GALLERIES[:3]] == [10, 10, 10]
    assert {p.size for p in pictures.GALLERIES[0]["pictures"]} == {"5x5"}
    assert {p.size for p in pictures.GALLERIES[1]["pictures"]} == {"8x8"}
    assert {p.size for p in pictures.GALLERIES[2]["pictures"]} == {"10x10"}
    assert [g["name"] for g in pictures.GALLERIES[:3]] == ["Instruments", "Small Machines", "Robots"]


def test_ids_are_unique_stable_words_and_every_picture_has_text():
    assert len(ids()) == len(set(ids())) and set(ids()) == set(pictures.BY_ID)
    for p in ALL:
        assert p.id.isidentifier() and p.id == p.id.lower()
        assert p.title.strip() and p.caption.strip().endswith(".") and len(p.caption) <= 90
        assert p.tint in pictures.TINTS
    assert len({p.title for p in ALL}) == len(ALL)
    assert pictures.ORDER == ids()
    # numbers run 1..n inside each gallery
    for g in pictures.GALLERIES:
        assert [p.number for p in g["pictures"]] == list(range(1, len(g["pictures"]) + 1))


def test_every_bitmap_is_a_clean_rectangle_with_something_in_it():
    for p in ALL:
        assert n.bitmap_ok(p.rows), p.id
        assert 5 <= p.width <= 15 and 5 <= p.height <= 15 and p.width == p.height, p.id
        filled = sum(row.count("#") for row in p.rows)
        assert filled >= p.width and filled <= p.width * p.height * 0.8, p.id        # a real picture, not a blank or a solid block


def test_no_two_pictures_are_the_same_drawing():
    assert len({p.rows for p in ALL}) == len(ALL)


@pytest.mark.parametrize("pid", ids())
def test_a_picture_has_exactly_one_solution(pid):
    p = pictures.BY_ID[pid]
    assert n.count_solutions(p.row_clues, p.col_clues, 2) == 1, pid


@pytest.mark.parametrize("pid", ids())
def test_a_picture_is_solved_by_line_logic_alone_and_equals_its_bitmap(pid):
    p = pictures.BY_ID[pid]
    grid, solved = n.solve_lines(p.row_clues, p.col_clues)
    assert solved, "%s needs guessing" % pid
    assert n.bitmap_of(grid) == list(p.rows)
    assert n.count_of_unknown(grid) == 0


@pytest.mark.parametrize("pid", ids())
def test_the_independent_counter_agrees(pid):
    p = pictures.BY_ID[pid]
    assert n.count_by_rows(p.row_clues, p.col_clues, 2) == 1, pid


@pytest.mark.parametrize("pid", ids())
def test_clues_match_the_picture_row_by_row_and_column_by_column(pid):
    p = pictures.BY_ID[pid]
    for r, row in enumerate(p.rows):
        runs = [len(part) for part in row.split(".") if part]
        assert p.row_clues[r] == runs
    for c in range(p.width):
        column = "".join(row[c] for row in p.rows)
        assert p.col_clues[c] == [len(part) for part in column.split(".") if part]
    assert sum(sum(clue) for clue in p.row_clues) == sum(sum(clue) for clue in p.col_clues) == sum(row.count("#") for row in p.rows)


def test_solving_and_clues_are_deterministic():
    for p in ALL[:6]:
        again = pictures.Picture({"id": p.id, "title": p.title, "caption": p.caption, "tint": p.tint, "rows": list(p.rows)}, p.gallery, p.number)
        assert again.row_clues == p.row_clues and again.col_clues == p.col_clues
        assert n.solve_lines(p.row_clues, p.col_clues) == n.solve_lines(again.row_clues, again.col_clues)


def test_the_proof_tool_passes_the_whole_set():
    import check_pictures
    assert check_pictures.main([]) == 0


def test_the_proof_tool_can_repair_a_draft_that_needs_guessing():
    """A symmetric draft is ambiguous (the tool must say so), and the tool offers an edit that is not."""
    import check_pictures
    draft = ["#..#", ".##.", ".##.", "#..#"]
    assert not check_pictures.passes(draft)
    fixes = list(check_pictures.suggest_fixes(draft))
    assert fixes and all(check_pictures.passes(rows) for _combo, rows in fixes)


def test_gating_opens_the_next_gallery_at_six_hung():
    first = pictures.GALLERIES[0]["pictures"]
    assert pictures.gallery_open(set(), 0) and not pictures.gallery_open(set(), 1) and not pictures.gallery_open(set(), 2)
    five = {p.id for p in first[:5]}
    six = {p.id for p in first[:6]}
    assert not pictures.gallery_open(five, 1) and pictures.gallery_open(six, 1)
    assert not pictures.gallery_open(six, 2)
    # any six of the ten will do: the order inside a gallery is free
    assert pictures.gallery_open({p.id for p in first[4:]}, 1)
    second = pictures.GALLERIES[1]["pictures"]
    assert pictures.gallery_open(six | {p.id for p in second[:6]}, 2)
    # a gallery cannot be open without the one before it
    assert not pictures.gallery_open({p.id for p in second}, 2)
    assert pictures.picture_open(six, second[0].id) and not pictures.picture_open(five, second[0].id)
    assert not pictures.picture_open(set(), "nothing")
    assert pictures.galleries_done({p.id for p in first}) == 1 and pictures.galleries_done(set()) == 0
