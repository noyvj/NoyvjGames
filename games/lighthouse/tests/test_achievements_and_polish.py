"""Achievements (computed from the state, never luck-gated, manifest in step), the copy lint over every shipped string,
the worst-case timing ceiling and the balance bots."""

import ast
import json
import re
import time
from pathlib import Path

import achievements
import data
import game
import harness
import lore
import mysteries
import sim
import story
from state import Keep

from .test_story_data import BANNED

GAME_DIR = Path(__file__).resolve().parent.parent


def played(seed, nights, style="careful", quiet=False, eerie=True):
    k = Keep(seed)
    k.quiet = quiet
    k._eerie = eerie
    sim.to_evening(k)
    harness.play(k, nights, style)
    achievements.refresh(k)
    return k


# ---- the framework --------------------------------------------------------------------------------
def test_the_manifest_matches_the_code_exactly():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))
    assert manifest == achievements.manifest()
    ids = [a["id"] for a in manifest["achievements"]]
    assert len(ids) == len(set(ids)) == len(achievements.ACHIEVEMENTS) == 21
    assert all(re.match(r"^[a-z_]+$", i) and a["label"] and a["description"] for i, a in zip(ids, manifest["achievements"]))


def test_a_fresh_keeper_has_earned_nothing_and_every_id_has_a_checker():
    k = Keep(1)
    assert achievements.earned_ids(k) == [] and achievements.refresh(k) == []
    assert set(achievements._checks(k)) == {a[0] for a in achievements.ACHIEVEMENTS}


def test_a_quiet_year_can_reach_every_keeping_achievement_and_none_of_the_story_ones():
    import day
    keeping = {a[0] for a in achievements.ACHIEVEMENTS if not a[3]}
    story_ids = {a[0] for a in achievements.ACHIEVEMENTS if a[3]}
    assert len(keeping) == 11
    got = set()
    for seed in range(1, 12):
        k = played(seed, 41, "careful", quiet=True)
        got |= set(k.meta["achievements_earned"])
    k = Keep(3)
    k.quiet = True
    sim.to_evening(k)
    k.phase, k.day_slots = "day", 5
    k.structure = {p: 20 for p in data.PARTS}
    k.supplies = {s: 20 for s in data.SUPPLIES}
    for part in data.PARTS:
        assert day.repair(k, part)[0]
    achievements.refresh(k)
    got |= set(k.meta["achievements_earned"])
    assert keeping <= got, keeping - got
    assert not (got & story_ids)


def test_a_full_story_year_earns_the_mysteries_the_cast_and_the_gifts():
    k = Keep(5)
    k._eerie = True
    sim.to_evening(k)

    def read_all(keep):
        for item in list(keep.story["inbox"]):
            story.read_letter(keep, item["id"])
    harness.play(k, 40, "careful", on_morning=read_all)
    read_all(k)
    achievements.refresh(k)
    earned = set(k.meta["achievements_earned"])
    assert {"second_light", "square_to_the_floor", "the_drummer", "two_cups", "return_to_sender", "twelve_windows"} <= earned
    assert {"reading_by_lamplight", "good_neighbour", "year_at_the_rock"} <= earned
    assert len(k.meta["story"]["met"]) >= 8


def test_bravery_is_optional_needs_forty_nights_of_eerie_off_in_a_row_and_resets_when_it_is_on():
    k = played(7, 41, "careful", eerie=False)
    assert k.meta["counters"]["eerie_off_streak"] >= 40 and "bravery_optional" in k.meta["achievements_earned"]
    k2 = Keep(7)
    sim.to_evening(k2)
    k2._eerie = False
    harness.play(k2, 30, "careful")
    k2._eerie = True
    harness.play(k2, 12, "careful")
    assert k2.meta["counters"]["eerie_off_streak"] == 0 or k2.meta["counters"]["eerie_off_streak"] < 40
    assert "bravery_optional" not in k2.meta["achievements_earned"]


def test_hidden_mystery_achievements_show_only_a_mystery_until_earned():
    k = Keep(1)
    view = achievements.view(k)
    hidden = [a for a in view if a["hidden"]]
    assert len(hidden) == 6 and all(a["label"] == "A mystery" for a in hidden)
    for name in ("Second Light", "Twelve Windows", "Two Cups"):
        assert name not in json.dumps(hidden)
    k.meta["achievements_earned"].append("two_cups")
    assert [a["label"] for a in achievements.view(k) if a["id"] == "two_cups"] == ["Two Cups"]


def test_earned_achievements_survive_a_save_and_the_save_lists_them_for_the_hub():
    k = played(2, 3)
    d = json.loads(json.dumps(k.to_dict()))
    assert Keep.from_dict(d).meta["achievements_earned"] == k.meta["achievements_earned"]
    game.keep = k
    assert game.get_state()["achievements_earned"] == achievements.earned_ids(k)


# ---- copy lint -----------------------------------------------------------------------------------------
def _strings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                doc_nodes.add(id(body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes]


def test_no_banned_word_in_any_string_of_the_game_modules():
    techniques = {b["technique"] for m in mysteries.MYSTERIES.values() for b in m["beats"]} | {t["technique"] for t in mysteries.TRIFLES.values()}
    for name in ("lore", "mysteries", "info", "sim", "day", "story", "view", "game", "goals", "achievements", "unease", "cast", "ships", "weather", "data"):
        for text in _strings(GAME_DIR / f"{name}.py"):
            if text in techniques:
                continue
            assert not BANNED.search(text), (name, text)


def test_no_dashes_and_calm_punctuation_in_player_facing_files():
    for name in ("app.js", "index.html", "changelog.json", "achievements.json", "lore.py", "mysteries.py", "info.py", "sim.py", "story.py", "day.py", "view.py"):
        text = (GAME_DIR / name).read_text(encoding="utf-8")
        text = text.replace("Advertisement — not part of the game", "")
        assert "—" not in text and "–" not in text, name
    for name in ("sim.py", "day.py", "story.py", "info.py", "mysteries.py"):
        assert not re.search(r"!!|\?!|!\?", (GAME_DIR / name).read_text(encoding="utf-8")), name


def test_the_story_keeps_its_promises_in_plain_words():
    text = " ".join(list(_strings(GAME_DIR / "mysteries.py")) + list(_strings(GAME_DIR / "lore.py"))).lower()
    for must_not in ("you die", "you are dead", "kill", "blood", "corpse", "screams"):
        assert must_not not in text
    assert "everyone aboard is safe" in " ".join(_strings(GAME_DIR / "sim.py")).lower()


# ---- timing --------------------------------------------------------------------------------------------
def test_the_worst_night_runs_well_inside_the_step_ceiling():
    """A winter storm night at the most ships and events, with every upgrade, the story on and the keeper watching: the whole
    night in one call and each single tick must stay far below what the page's timer could notice (Pyodide is a few times
    slower than this machine, so the ceilings are generous)."""
    from view import build
    worst_whole = worst_tick = worst_view = 0.0
    storms = [(s, n) for s in range(1, 40) for n in range(31, 41) if sim.weather(s, n).severity == 3][:25]
    assert storms
    for seed, night in storms:
        k = Keep(seed)
        k.night = night
        sim.to_evening(k)
        k.upgrades = [u["id"] for u in data.UPGRADES]
        k.tasks = {"wind": True, "watch": True, "repair": True}
        k.supplies = {s: 20 for s in data.SUPPLIES}
        sim.begin_night(k)
        t0 = time.perf_counter()
        while k.phase == "night":
            t1 = time.perf_counter()
            sim.step(k, 1)
            worst_tick = max(worst_tick, time.perf_counter() - t1)
        worst_whole = max(worst_whole, time.perf_counter() - t0)
        t2 = time.perf_counter()
        build(k, {"eerie": True})
        worst_view = max(worst_view, time.perf_counter() - t2)
    assert worst_whole < 0.25, worst_whole
    assert worst_tick < 0.04, worst_tick
    assert worst_view < 0.04, worst_view


def test_handle_step_stays_fast_over_a_whole_year():
    game._begin_run(3, False)
    import json as _json
    t0 = time.perf_counter()
    slowest = 0.0
    for _ in range(20):
        game.handle(_json.dumps({"action": "start_night"}))
        while True:
            t1 = time.perf_counter()
            v = _json.loads(game.handle(_json.dumps({"action": "step", "n": 1})))
            slowest = max(slowest, time.perf_counter() - t1)
            if v["phase"] != "night":
                break
        game.handle(_json.dumps({"action": "end_morning"}))
        game.handle(_json.dumps({"action": "end_day"}))
    assert slowest < 0.06 and time.perf_counter() - t0 < 10


# ---- balance bots -----------------------------------------------------------------------------------------
def _rate(k):
    m = k.meta
    return m["ships_passed"] / float(max(1, m["ships_passed"] + m["ships_delayed"] + m["ships_damaged"]))


def test_the_balance_bots_show_planning_pays_and_neglect_never_ends_the_game():
    results = {}
    for style in ("careful", "idle", "miser"):
        rates, reps = [], []
        for seed in range(1, 21):
            k = played(seed, 40, style, quiet=True)
            rates.append(_rate(k))
            reps.append(k.reputation)
            assert k.phase in ("evening", "day", "yearend") and k.meta["nights_kept"] == 40
        results[style] = (sum(rates) / len(rates), sum(reps) / len(reps))
    careful, idle, miser = results["careful"], results["idle"], results["miser"]
    assert careful[0] > idle[0] > miser[0]
    assert careful[0] >= 0.9 and 0.4 <= idle[0] <= 0.85 and miser[0] < 0.3
    assert careful[1] > idle[1] > miser[1]
    assert idle[1] >= data.REP_TITLES[1][0]          # even the idle bot becomes Noted within a year


def test_the_oil_economy_is_tight_but_a_sensible_plan_rarely_hits_the_reserve_flask():
    flask_nights = total = 0
    for seed in range(1, 16):
        k = Keep(seed)
        k.quiet = True
        sim.to_evening(k)
        for _ in range(40):
            if k.oil <= 0:
                flask_nights += 1
            harness.play(k, 1, "careful")
            total += 1
    assert flask_nights / float(total) < 0.05


def test_lore_and_mysteries_ids_are_what_the_achievements_expect():
    assert set(achievements.MYSTERY_ACHIEVEMENTS) == set(mysteries.MYSTERIES)
    assert len(lore.SAILORS) == 10
