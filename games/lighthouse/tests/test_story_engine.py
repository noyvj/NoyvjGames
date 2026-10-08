"""The story layer's engine: who is on the water, which letter arrives, what reading it does, and the promise that
the sim does not care whether the story is on."""

import copy
import json

import cast
import data
import day
import game
import harness
import lore
import ships
import sim
import story
from state import Keep


def new_keep(seed=3, quiet=False):
    k = Keep(seed)
    k.quiet = quiet
    sim.to_evening(k)
    return k


def sim_fields(k):
    d = k.to_dict()["run"]
    for key in ("story", "log", "report", "quiet"):
        d.pop(key, None)
    return d


def test_assignment_only_renames_and_labels_never_adds_or_moves_a_ship():
    for seed in (1, 2, 3):
        for night in range(1, 60):
            mail = ships.mail_scheduled(seed, night)
            labelled = ships.ships_for_night(seed, night, mail)
            bare = [dict(s) for s in labelled]
            for s in bare:
                s.pop("who", None)
            assert len(bare) == len(labelled)
            for a, b in zip(labelled, bare):
                assert (a["id"], a["kind"], a["arrive"], a["window"], a["need"]) == (b["id"], b["kind"], b["arrive"], b["window"], b["need"])


def test_a_sailors_own_boat_keeps_its_name_and_at_most_two_non_mail_sailors_a_night():
    seen = set()
    for seed in range(1, 15):
        for night in range(1, 60):
            night_ships = ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night))
            who = [s["who"] for s in night_ships if s.get("who") and s["who"] != "ilse"]
            assert len(who) <= cast.MAX_PER_NIGHT and len(who) == len(set(who))
            for s in night_ships:
                if s.get("who"):
                    seen.add(s["who"])
                    assert lore.SAILORS[s["who"]]["kind"] == s["kind"]
                    if lore.SAILORS[s["who"]]["ship"]:
                        assert s["name"] == lore.SAILORS[s["who"]]["ship"]
    assert seen == {sid for sid, s in lore.SAILORS.items() if s["kind"]}


def test_nobody_appears_before_their_first_night():
    for seed in range(1, 20):
        for night in range(1, 12):
            for s in ships.ships_for_night(seed, night, ships.mail_scheduled(seed, night)):
                if s.get("who"):
                    assert night >= lore.SAILORS[s["who"]]["min_night"]


def test_the_sim_is_identical_with_the_story_on_or_off_when_no_letter_is_read():
    for seed in (4, 9):
        on, off = new_keep(seed, False), new_keep(seed, True)
        harness.play(on, 45, "careful")
        harness.play(off, 45, "careful")
        assert sim_fields(on) == sim_fields(off)
        assert on.story["inbox"] and not off.story["inbox"]


def test_a_quiet_run_has_no_story_at_all():
    k = new_keep(5, True)
    harness.play(k, 40, "careful")
    assert k.story == {"met": {}, "inbox": [], "read": [], "gifts": [], "choices": {}, "buffs": {}}
    assert k.meta["story"] == {"met": [], "letters": [], "gifts": []}
    assert not story.read_letter(k, "il1")[0]
    from view import build
    v = build(k, {"eerie": True})
    assert v["story"]["on"] is False and v["story"]["inbox"] == [] and all(s["who"] is None for s in v["ships"])
    assert not any("(" in e[2] for e in k.log)


def test_a_safe_passage_meets_the_sailor_and_letters_arrive_one_a_night():
    k = new_keep(3)
    letters_by_night = {}

    def note(keep):
        fresh = [l["id"] for l in keep.report["letters"]]
        assert len(fresh) <= 1
        if fresh:
            letters_by_night[keep.report["night"]] = fresh[0]
    harness.play(k, 60, "careful", on_morning=note)
    assert len(letters_by_night) >= 8
    assert k.meta["story"]["met"]
    for lid in letters_by_night.values():
        gate = lore.LETTERS[lid]["gate"]
        after = gate.get("after")
        if after:
            assert after in story.delivered_ids(k)


def test_a_letter_needs_the_passes_the_reputation_and_the_letter_before_it():
    k = new_keep(3)
    k.night = 3
    ship = {"id": "x", "kind": "mail", "who": "ilse", "name": "Gannet", "arrive": 5, "window": 6, "need": 5, "rep": 1, "salvage": 1}
    k.progress["x"] = {"seen": 6, "danger": 0, "state": "passed"}
    assert story.after_night(k, [ship])["letters"] == ["il1"]           # one pass is enough for the first
    assert k.story["met"]["ilse"] == 1 and "ilse" in k.meta["story"]["met"]
    k.reputation = 0
    assert story.after_night(k, [ship])["letters"] == []                # the second needs two passes and a name
    k.reputation = 8
    assert story.after_night(k, [ship])["letters"] == ["il2"]
    k.story["met"]["ilse"] = 1
    k.story["inbox"] = [i for i in k.story["inbox"] if i["id"] != "il2"]
    assert "il2" not in story.after_night(k, [])["letters"]             # not without enough passes


def test_people_ashore_write_on_their_night_and_are_met_by_their_first_letter():
    k = new_keep(3)
    k.night = 3
    assert story.after_night(k, [])["letters"] == []
    k.night = 4
    out = story.after_night(k, [])
    assert out["letters"] == ["du1"] and out["met"] == ["dunstan"] and "dunstan" in k.meta["story"]["met"]


def test_a_delayed_ship_earns_no_pass():
    k = new_keep(3)
    ship = {"id": "x", "kind": "fisher", "who": "odd", "name": "Hopeful Pail", "arrive": 5, "window": 6, "need": 5, "rep": 1, "salvage": 1}
    k.progress["x"] = {"seen": 0, "danger": 0, "state": "delayed"}
    assert story.after_night(k, [ship])["letters"] == [] and k.story["met"].get("odd", 0) == 0


def test_reading_takes_the_gift_once_and_applies_its_effect():
    k = new_keep(3)
    k.story["inbox"].append({"id": "co2", "night": 5})
    f = k.supplies["food"]
    ok, msg = story.read_letter(k, "co2")
    assert ok and "pickled walnuts" in msg.lower() and k.supplies["food"] == f + 3 and "walnuts" in k.story["gifts"]
    assert not story.read_letter(k, "co2")[0] and k.supplies["food"] == f + 3
    assert not story.read_letter(k, "nope")[0] and not story.read_letter(k, "il1")[0]
    assert "co2" in k.meta["story"]["letters"] and "walnuts" in k.meta["story"]["gifts"]


def test_the_lens_cloth_lengthens_the_beam_for_seven_nights_only():
    k = new_keep(3)
    k.night = 20
    sim.to_evening(k)
    sim.begin_night(k)
    base = sim.effective_reach(k, 1, 0)
    k.story["inbox"].append({"id": "du2", "night": 16})
    story.read_letter(k, "du2")
    assert k.story["buffs"]["lens_cloth"] == 7 and sim.effective_reach(k, 1, 0) == base + 1
    for _ in range(7):
        story.after_night(k, [])
    assert sim.effective_reach(k, 1, 0) == base
    k.quiet = True
    k.story["buffs"]["lens_cloth"] = 3
    assert sim.effective_reach(k, 1, 0) == base


def test_replies_are_chosen_once_and_answered_after_the_next_night():
    k = new_keep(3)
    k.story["inbox"].append({"id": "il2", "night": 5})
    assert not story.reply(k, "il2", "gulls")[0]                 # read it first
    story.read_letter(k, "il2")
    assert not story.reply(k, "il2", "nonsense")[0]
    assert story.reply(k, "il2", "gulls")[0] and not story.reply(k, "il2", "count")[0]
    v = story.view(k)["inbox"][0]
    assert v["reply"] == "Between us and the gulls." and v["answer"] is None
    k.night += 1
    assert "gulls" in story.view(k)["inbox"][0]["answer"]


def test_the_story_view_hides_what_is_not_yet_earned():
    k = new_keep(3)
    v = story.view(k)
    assert v["unread"] == 0 and v["inbox"] == []
    assert all(not s["met"] and s["name"] == "Someone you have not met" and s["role"] == "" for s in v["sailors"])
    assert all(g["name"] == "A gift you have not found" and g["text"] == "" for g in v["gifts"])
    k.story["inbox"].append({"id": "il1", "night": 3})
    v = story.view(k)
    assert v["unread"] == 1 and v["inbox"][0]["text"] == ""      # the words wait until it is opened
    story.read_letter(k, "il1")
    assert "manifest" in story.view(k)["inbox"][0]["text"]


def test_story_progress_survives_a_save_and_garbage_in_it_is_dropped():
    k = new_keep(3)
    k.story["inbox"] = [{"id": "il1", "night": 3}, {"id": "co1", "night": 4}]
    k.story["read"] = ["il1"]
    k.story["met"] = {"ilse": 2}
    k.story["gifts"] = ["brass_key"]
    k.meta["story"]["met"] = ["ilse"]
    d = json.loads(json.dumps(k.to_dict()))
    assert Keep.from_dict(d).to_dict() == d
    bad = copy.deepcopy(d)
    bad["run"]["story"] = {"inbox": [{"id": "zz"}, {"id": "il1", "night": "x"}, 5], "read": ["zz", "il1", "co2"], "gifts": ["nope", "chart"],
                           "met": {"ilse": -5, "ghost": 3}, "choices": {"il2": ["gulls", 3]}, "buffs": {"lens_cloth": 999}}
    bad["meta"]["story"] = {"met": ["nobody", "odd"], "letters": ["x"], "gifts": 4}
    fixed = Keep.from_dict(bad)
    assert [i["id"] for i in fixed.story["inbox"]] == ["il1"] and fixed.story["read"] == ["il1"] and fixed.story["gifts"] == ["chart"]
    assert fixed.story["met"] == {"ilse": 0} and fixed.story["choices"] == {} and fixed.story["buffs"]["lens_cloth"] == 99
    assert fixed.meta["story"]["met"] == ["odd"]


def test_handle_reads_and_replies_and_the_report_lists_the_post():
    game._begin_run(7, False)
    game.keep.story["inbox"].append({"id": "il2", "night": 4})
    v = json.loads(game.handle(json.dumps({"action": "read_letter", "id": "il2"})))
    assert v["ok"] and v["story"]["unread"] == 0
    v = json.loads(game.handle(json.dumps({"action": "reply", "id": "il2", "reply": "count"})))
    assert v["ok"] and v["story"]["inbox"][0]["reply"].startswith("Nine times")
    v = json.loads(game.handle(json.dumps({"action": "read_letter", "id": "il2"})))
    assert v["ok"] is False
    k = new_keep(3)
    k.night = 4
    sim.to_evening(k)
    seen = []
    harness.play(k, 1, "careful", on_morning=lambda keep: seen.append(dict(keep.report)))
    assert seen[0]["letters"][0]["id"] == "du1" and "Dunstan Yarrow" in seen[0]["met"]
    assert day is not None


def test_every_letter_can_be_earned_within_two_years_by_a_decent_keeper():
    got = set()
    for seed in (2, 5, 8, 13):
        k = new_keep(seed)
        harness.play(k, 80, "careful")
        got |= set(story.delivered_ids(k))
        assert len(story.delivered_ids(k)) >= 12
    assert got >= {lid for lid in lore.LETTERS}
    assert data.NIGHTS_PER_YEAR == 40
