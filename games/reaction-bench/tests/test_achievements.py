"""Milestone 6: the 14 achievements (manifest, pure checks over saved state, panel and toast wiring, reachability on every level)."""

import json
import re
from pathlib import Path

import achievements
import game
import reactions
from .helpers import call, open_chapter, solve

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
BY_ID = {a[0]: a for a in achievements.ACHIEVEMENTS}


def fresh():
    game.game.__init__()


def earned_ids():
    return {a["id"] for a in call(action="open")["achievements"] if a["earned"]}


def have(aid):
    return [a for a in call(action="open")["achievements"] if a["id"] == aid][0]["have"]


def ids_of(chapter):
    return [r.id for r in reactions.CHAPTERS[chapter]["reactions"]]


# ---- the manifest ------------------------------------------------------------------------------------------------------------------
def test_manifest_matches_the_engine_table_and_has_fourteen():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for entry, row in zip(manifest, achievements.ACHIEVEMENTS):
        assert entry == {"id": row[0], "label": row[1], "description": row[2]}
    assert len(set(achievements.IDS)) == 14


def test_the_plans_fourteen_names_are_all_there():
    labels = {a[1] for a in achievements.ACHIEVEMENTS}
    assert labels == {"First Balance", "Ten on the Shelf", "Twenty Shelved", "Every Flask", "Fire Starter", "Salt of the Earth", "Acid Test",
                      "The Works", "Quarter Table", "Half Table", "Full Table", "Oxygen Everywhere", "Straight Through", "Right Product"}


def test_every_achievement_has_a_visible_number_and_none_is_hidden_or_timed():
    fresh()
    for a in call(action="open")["achievements"]:
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"]
        assert a["label"].strip() and a["description"].strip() and a["description"].endswith(".")
    text = (GAME_DIR / "achievements.json").read_text(encoding="utf-8").lower()
    assert "hidden" not in text
    for _i, label, description, fact, _n in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck", "fast", "speed", "difficulty", "hard", "easy"):
            assert word not in description.lower().replace(".", "").split(), (label, word)
        assert fact in achievements.FACTS


def test_the_numbers_follow_the_size_of_the_game():
    assert BY_ID["every_flask"][4] == len(reactions.ORDER) == 40
    assert BY_ID["first_balance"][4] < BY_ID["ten_on_the_shelf"][4] < BY_ID["twenty_shelved"][4] < BY_ID["every_flask"][4]
    assert BY_ID["fire_starter"][4] == len(reactions.CHAPTERS[1]["reactions"])
    assert BY_ID["acid_test"][4] == len(reactions.CHAPTERS[3]["reactions"])
    assert BY_ID["the_works"][4] == len(reactions.CHAPTERS[4]["reactions"])
    assert reactions.CHAPTERS[1]["name"] in BY_ID["fire_starter"][2] and reactions.CHAPTERS[3]["name"] in BY_ID["acid_test"][2]
    assert reactions.CHAPTERS[4]["name"] in BY_ID["the_works"][2]
    assert BY_ID["oxygen_everywhere"][4] == 15 and BY_ID["straight_through"][4] == 10 and BY_ID["right_product"][4] == 10
    assert len(achievements.OXYGEN_ORDERS) >= 15 and len([r for r in reactions.ALL if r.is_round]) >= 10


def test_the_table_achievements_are_scaled_to_the_fifteen_elements_the_bench_reaches():
    """The plan said 9, 18 and 36 of 36 elements. The 40 safe orders reach 15, so the three scale to 4, 8 and all 15 (CLAUDE.md says so)."""
    assert len(reactions.BENCH_ELEMENTS) == 15
    assert [BY_ID[i][4] for i in ("quarter_table", "half_table", "full_table")] == [4, 8, 15]
    assert BY_ID["full_table"][4] == len(reactions.BENCH_ELEMENTS)
    text = (GAME_DIR / "CLAUDE.md").read_text(encoding="utf-8")
    assert "4, 8 and" in text and "15 elements" in text


def test_the_salt_list_is_every_product_that_is_a_salt_and_nothing_else():
    products = {f for r in reactions.ALL for f in r.products}
    named = {f for f in products if re.search(r"chloride|sulfate|carbonate|nitrate|phosphate", reactions.name_of(f)) and "acid" not in reactions.name_of(f)}
    assert named == set(achievements.SALT_FORMULAS)
    assert set(achievements.SALT_ORDERS) == {r.id for r in reactions.ALL if set(r.products) & named}
    assert len(achievements.SALT_ORDERS) == 15 and BY_ID["salt_of_the_earth"][4] == 15
    for rid in achievements.SALT_ORDERS:
        assert reactions.BY_ID[rid].products[0] in achievements.SALT_FORMULAS or len(reactions.BY_ID[rid].products) > 1


def test_the_achievement_text_never_names_an_order_that_is_not_shelved_yet():
    fresh()
    text = json.dumps(call(action="open")["achievements"])
    for r in reactions.ALL:
        assert r.title not in text and r.blurb not in text


# ---- the pure checks ---------------------------------------------------------------------------------------------------------------
def test_each_achievement_needs_what_it_says_and_not_less():
    facts = achievements.facts_of({}, 0, {}, set())
    assert achievements.earned(facts) == []
    assert achievements.earned(dict(facts, shelved=10)) == ["first_balance", "ten_on_the_shelf"]
    assert "twenty_shelved" not in achievements.earned(dict(facts, shelved=19)) and "twenty_shelved" in achievements.earned(dict(facts, shelved=20))
    assert "every_flask" not in achievements.earned(dict(facts, shelved=39)) and "every_flask" in achievements.earned(dict(facts, shelved=40))
    for aid, fact in (("fire_starter", "ch1"), ("acid_test", "ch3"), ("the_works", "ch4")):
        assert aid not in achievements.earned(dict(facts, **{fact: 7})) and aid in achievements.earned(dict(facts, **{fact: 8}))
    assert "salt_of_the_earth" not in achievements.earned(dict(facts, salts=14)) and "salt_of_the_earth" in achievements.earned(dict(facts, salts=15))
    for aid, n in (("quarter_table", 4), ("half_table", 8), ("full_table", 15)):
        assert aid not in achievements.earned(dict(facts, found=n - 1)) and aid in achievements.earned(dict(facts, found=n))
    assert "oxygen_everywhere" not in achievements.earned(dict(facts, oxygen=14)) and "oxygen_everywhere" in achievements.earned(dict(facts, oxygen=15))
    assert "straight_through" not in achievements.earned(dict(facts, clean=9)) and "straight_through" in achievements.earned(dict(facts, clean=10))
    assert "right_product" not in achievements.earned(dict(facts, first=9)) and "right_product" in achievements.earned(dict(facts, first=10))


def test_facts_count_chapters_salts_oxygen_and_clean_from_the_shelf():
    shelf = {"table-salt": 1, "carbon-dioxide": 1, "methane": 1, "fizz": 2, "iron-chloride": 1}
    facts = achievements.facts_of(shelf, 6, {"methane": 2, "fizz": 1}, {"methane"})
    assert facts["shelved"] == 5 and facts["found"] == 6 and facts["first"] == 1
    assert facts["salts"] == 3                                      # table salt, fizz (it makes table salt) and iron chloride
    assert facts["oxygen"] == 3                                     # carbon dioxide, methane, fizz
    assert facts["clean"] == 3                                      # table salt, carbon dioxide, iron chloride
    assert facts["ch0"] == 2 and facts["ch1"] == 1 and facts["ch3"] == 1 and facts["ch4"] == 1 and facts["ch2"] == 0


# ---- earned ids in the save, and never read back ---------------------------------------------------------------------------------
def test_earned_ids_are_written_to_the_save_and_never_read_back():
    assert "achievements_earned" not in game.get_state()
    solve("carbon-dioxide")
    state = game.get_state()
    assert state["achievements_earned"] == ["first_balance"]
    assert json.loads(json.dumps(state)) == state
    fresh()
    game.load_state({"schema": 1, "achievements_earned": list(achievements.IDS)})
    v = call(action="open")
    assert v["totals"]["shelved"] == 0 and not any(a["earned"] for a in v["achievements"]) and "achievements_earned" not in game.get_state()


def test_a_loaded_save_and_a_played_game_agree_on_what_is_earned():
    for rid in reactions.ORDER[:11]:
        solve(rid)
    played = earned_ids()
    state = json.loads(json.dumps(game.get_state()))
    fresh()
    game.load_state(state)
    assert earned_ids() == played
    assert {"first_balance", "ten_on_the_shelf", "quarter_table", "half_table"} <= played
    assert game.get_state()["achievements_earned"] == state["achievements_earned"]


def test_the_hint_and_first_right_records_survive_a_save_and_reload():
    open_chapter(1)
    call(action="pick", reaction="methane")
    call(action="hint")
    solve("methane")
    call(action="pick", reaction="propane")
    call(action="choose", option=reactions.BY_ID["propane"].right)
    state = json.loads(json.dumps(game.get_state()))
    assert state["hints"] == {"methane": 1} and "propane" in state["first"]
    fresh()
    game.load_state(state)
    assert game.game.hinted == {"methane": 1} and "propane" in game.game.first
    assert have("straight_through") == len(reactions.CHAPTERS[0]["reactions"][:5])      # the five chapter-one orders, not methane


# ---- how each input is counted -----------------------------------------------------------------------------------------------------
def test_chapter_achievements_come_with_the_last_order_of_the_chapter():
    open_chapter(1)
    ids = ids_of(1)
    for rid in ids[:-1]:
        solve(rid)
    assert "fire_starter" not in earned_ids() and have("fire_starter") == 7
    solve(ids[-1])
    assert "fire_starter" in earned_ids()


def test_the_table_achievements_follow_the_tiles_lit_not_the_orders_shelved():
    solve("carbon-dioxide")                                      # carbon, oxygen
    assert have("quarter_table") == 2 and "quarter_table" not in earned_ids()
    solve("table-salt")                                          # sodium, chlorine: four tiles
    assert "quarter_table" in earned_ids() and "half_table" not in earned_ids()
    solve("carbon-dioxide")                                      # running an order again lights nothing new
    assert have("half_table") == 4
    for rid in ("water", "magnesium-oxide", "rust"):             # hydrogen, magnesium, iron: seven
        solve(rid)
    assert have("half_table") == 7
    solve("aluminium-oxide")                                     # aluminium: eight
    assert "half_table" in earned_ids() and "full_table" not in earned_ids()


def test_oxygen_everywhere_counts_orders_not_runs():
    for rid in reactions.ORDER[:5]:
        solve(rid)
    assert have("oxygen_everywhere") == 4                        # table salt has no oxygen
    solve("carbon-dioxide")
    solve("carbon-dioxide")
    assert have("oxygen_everywhere") == 4


def test_salt_of_the_earth_needs_every_order_that_makes_a_salt():
    last = max(reactions.ORDER.index(rid) for rid in achievements.SALT_ORDERS)
    for n, rid in enumerate(reactions.ORDER):
        solve(rid)
        assert ("salt_of_the_earth" in earned_ids()) == (n >= last), rid
    assert have("salt_of_the_earth") == 15


def test_straight_through_counts_only_orders_shelved_without_pressing_the_ladder():
    call(action="pick", reaction="water")
    call(action="hint")                                           # a nudge is a suggestion: this order is no longer clean
    for rid in reactions.ORDER[:10]:
        solve(rid)
    assert have("straight_through") == 9 and "straight_through" not in earned_ids()
    # a suggestion cannot be asked on a shelved order, so it cannot change the record afterwards
    call(action="pick", reaction="table-salt")
    assert call(action="hint")["ok"] is False
    assert have("straight_through") == 9
    solve(reactions.ORDER[10])
    assert "straight_through" in earned_ids() and game.game.hinted == {"water": 1}


def test_straight_through_is_still_earnable_after_using_the_ladder_on_other_orders():
    solve(reactions.ORDER[0])                                     # carbon dioxide starts balanced, so it never offers a suggestion
    for rid in reactions.ORDER[1:31]:
        call(action="pick", reaction=rid)
        call(action="hint")
        solve(rid)
    assert have("straight_through") == 1 and game.game.tally["hints"] == 30
    for rid in reactions.ORDER[31:]:
        solve(rid)
    assert "straight_through" in earned_ids() and have("straight_through") == 10


def test_right_product_counts_only_rounds_chosen_right_on_the_first_try():
    open_chapter(1)
    rounds = [r for r in reactions.ALL if r.is_round and r.chapter == 1]
    wrong = next(i for i in range(4) if i != rounds[0].right)
    call(action="pick", reaction=rounds[0].id)
    call(action="choose", option=wrong)                           # tried and wrong first: not "first time"
    call(action="choose", option=rounds[0].right)
    assert have("right_product") == 0
    call(action="pick", reaction=rounds[1].id)
    call(action="choose", option=rounds[1].right)
    assert have("right_product") == 1
    call(action="pick", reaction=rounds[2].id)
    for _ in range(3):
        call(action="hint", confirm=True)                         # nudge, hint, then the right list chosen for you: not "first time"
    assert rounds[2].id in game.game.picked and have("right_product") == 1


def test_right_product_is_earned_by_ten_rounds_without_a_single_wrong_try():
    open_chapter(1)
    for r in [r for r in reactions.ALL if r.is_round][:9]:
        solve(r.id)                                                # solve() chooses the right list at once
    assert have("right_product") == 9 and "right_product" not in earned_ids()
    solve([r for r in reactions.ALL if r.is_round][9].id)
    assert "right_product" in earned_ids()


# ---- reachability: a scripted player earns all fourteen on every difficulty, and the level never changes which are earned --------------
def play_everything(level):
    fresh()
    if level:
        call(action="difficulty", level=level)
    for rid in reactions.ORDER:                                   # chapter order opens each chapter in turn; step ones come before step twos
        solve(rid)
    return call(action="open")


def test_a_scripted_player_earns_every_achievement_on_normal_without_luck_hints_or_time():
    v = play_everything("normal")
    assert [a["id"] for a in v["achievements"] if not a["earned"]] == []
    assert set(game.get_state()["achievements_earned"]) == set(achievements.IDS)
    assert game.game.hinted == {} and v["tally"]["hints"] == 0 and v["totals"]["shelved"] == 40 and v["totals"]["elements"] == 15
    by = {a["id"]: a for a in v["achievements"]}
    assert by["straight_through"]["have"] == 10 and by["every_flask"]["have"] == 40 and by["full_table"]["have"] == 15
    assert by["right_product"]["have"] == 10 and by["salt_of_the_earth"]["have"] == 15 and by["oxygen_everywhere"]["have"] == 15
    game.difficulty = "normal"


def test_the_difficulty_level_never_gates_an_achievement():
    results = {}
    for level in (None, "easy", "normal", "hard"):
        v = play_everything(level)
        results[level] = ([(a["id"], a["earned"], a["have"]) for a in v["achievements"]], game.get_state()["achievements_earned"])
    assert results["easy"] == results["normal"] == results["hard"] == results[None]
    game.difficulty = "normal"


def test_every_achievement_is_earnable_in_pieces_in_the_order_the_board_opens_them():
    """Each one flips at a known point of a straight play-through, never earlier, and none is lost by playing more."""
    fresh()
    seen = {}
    for n, rid in enumerate(reactions.ORDER, 1):
        solve(rid)
        for aid in earned_ids():
            seen.setdefault(aid, n)
    assert set(seen) == set(achievements.IDS)
    assert seen["first_balance"] == 1 and seen["ten_on_the_shelf"] == 10 and seen["twenty_shelved"] == 20 and seen["every_flask"] == 40
    assert seen["straight_through"] == 10 and seen["fire_starter"] == 16 and seen["quarter_table"] == 2
    assert seen["the_works"] == 40 and seen["acid_test"] == 32
    assert earned_ids() == set(achievements.IDS)


def test_the_achievement_module_never_reads_the_difficulty_or_the_engine():
    code = "\n".join(line for line in (GAME_DIR / "achievements.py").read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#"))
    code = code.split('"""', 2)[2]                                # drop the module docstring: only the code is judged
    assert "import game" not in code and "difficulty" not in code and "hard" not in code.lower()


# ---- the page --------------------------------------------------------------------------------------------------------------------
def test_the_panel_toast_count_and_share_button_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'id="achievements-count"',
                   'data-game-name="Reaction Bench"', "achievement-share.js", 'panel: "achievements-panel"'):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP
    assert "ach-list" in CSS and 'wirePanelToggle("achievements-toggle-button", "achievements-panel")' in APP
    assert '"achievements.py"' in APP


def test_the_toast_only_fires_for_something_new_and_never_on_load():
    """app.js remembers what was earned before; null until the first view, and a loaded save resets it (so loading never toasts)."""
    assert "var knownEarned = null" in APP and "knownEarned = null; eqSig" in APP
    assert "knownEarned.indexOf(a.id) === -1" in APP
    assert "announce(text)" in APP


def test_the_count_is_text_and_the_earned_state_is_not_colour_alone():
    assert '" of " + items.length' in APP and 'a.earned ? "Earned"' in APP
    assert "border-style: double" in CSS
    assert "N of 14" not in APP and "achievements earned." in APP


def test_the_toolbar_button_exists_beside_the_table_and_the_panel_is_hidden_at_first():
    assert HTML.index("table-toggle-button") < HTML.index("achievements-toggle-button") < HTML.index("changelog-toggle-button")
    assert '<section id="achievements-panel" class="panel" hidden' in HTML
