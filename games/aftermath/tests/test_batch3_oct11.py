"""Batch 3 (2026-10-11): GE-20 mood strip, GE-25 settlement looks, GE-14 hit effects, GE-26 countdown pulse,
GE-23 run timer, E-31 achievements strip, E-7 settlement chronicle, E-26 tap targets."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------------------------------ GE-20
def test_mood_is_cheerful_for_a_comfortable_sheltered_settlement_and_grim_for_a_bare_one(game_env):
    m = game_env.module
    m.run.resources = 200.0
    m.run.resilience_capacity = 17  # 85% mitigation
    faces, label = m.mood_summary(m.run)
    assert faces[-1] == m.MOOD_FACES[0] and set(faces) <= set(m.MOOD_FACES[:2])
    assert "cheerful" in label and "citizens are smiling" in label
    m.run.resources = 0.0
    m.run.resilience_capacity = 0
    faces, label = m.mood_summary(m.run)
    assert faces[0] == m.MOOD_FACES[4] and faces[-1] == m.MOOD_FACES[4] and "frightened" in label and "0 of 5" in label


def test_mood_moves_one_face_at_a_time_and_never_leaves_the_face_range(game_env):
    m = game_env.module
    seen = set()
    for resources in range(0, 400, 10):
        for resilience in (0, 4, 9, 17, 40):
            m.run.resources = float(resources)
            m.run.resilience_capacity = resilience
            levels = m.mood_levels(m.settlement_mood_score(m.run))
            assert len(levels) == 5 and all(0 <= level < len(m.MOOD_FACES) for level in levels)
            assert levels == sorted(levels, reverse=True)  # the strip reads from the gloomiest citizen to the most hopeful, always in that order
            seen.update(levels)
    assert seen == {0, 1, 2, 3, 4}


def test_every_allocation_click_redraws_the_strip_and_its_words(game_env):
    m, e = game_env.module, game_env.elements
    before = e["mood-caption"].innerText
    assert before.startswith("Settlement mood:") and e["mood-strip"].getAttribute("aria-label") == before
    assert len(e["mood-strip"].children) == 5 and all(c.getAttribute("aria-hidden") == "true" for c in e["mood-strip"].children)
    m.run.resources = 25.0
    game_env.invest_resilience()
    after = e["mood-caption"].innerText
    assert after != before and e["mood-strip"].getAttribute("aria-label") == after
    assert len(e["mood-strip"].children) == 5  # built once, then updated in place


def test_a_page_without_the_strip_still_renders(game_env):
    m = game_env.module
    m._mood_parts.clear()
    m._el = lambda element_id: None
    m.render_mood_strip()  # no error


# ------------------------------------------------------------------------------------------ GE-25
def _finish_run(game_env):
    for _ in range(len(game_env.module.run.schedule)):
        game_env.resolve_event()


def test_look_thresholds_follow_the_real_size_of_the_tree(game_env):
    m = game_env.module
    assert len(m.SKILLS) == 7
    assert m.look_thresholds() == {"thatched": 0, "timber": 4, "concrete": 7}
    assert m.look_thresholds(10) == {"thatched": 0, "timber": 5, "concrete": 10}  # the TODO's "5, 10 and all" for a ten-skill tree
    assert [m.look_for_skill_count(n) for n in range(8)] == ["thatched"] * 4 + ["timber"] * 3 + ["concrete"]


def test_a_run_gets_its_look_when_it_starts_and_keeps_it(game_env):
    m = game_env.module
    assert m.run.look == "thatched"
    m.skill_tree.unlocked = set(list(m.SKILLS)[:4])
    m.run = m.RunState()
    assert m.run.look == "timber"
    m.skill_tree.unlocked = set()
    assert m.run.look == "timber"  # fixed at the start of the run
    m.skill_tree.unlocked = set(m.SKILLS)
    assert m.RunState().look == "concrete"
    assert m.RunState(normalised=True).look == "thatched"  # a friend's challenge run ignores your tree


def test_the_look_changes_no_number(game_env):
    m = game_env.module
    base = m.RunState()
    m.skill_tree.unlocked = set()
    plain = m.RunState()
    assert (plain.resources, plain.resilience_capacity, plain.growth_capacity) == (base.resources, base.resilience_capacity, base.growth_capacity)
    assert "look" not in json.dumps(m.get_state())  # nothing new in the run save


def test_history_records_a_non_default_look_only_and_old_runs_read_as_default(game_env):
    m = game_env.module
    _finish_run(game_env)
    assert "look" not in m.run_log_history[-1]
    game_env.start_new_run()
    m.skill_tree.unlocked = set(list(m.SKILLS)[:5])
    m.run = m.RunState(run_number=2)
    _finish_run(game_env)
    assert m.run_log_history[-1]["look"] == "timber"
    assert m.entry_look(m.run_log_history[0]) == "thatched" and m.entry_look({"look": "marble"}) == "thatched" and m.entry_look(None) == "thatched"
    assert m.looks_seen() == {"thatched", "timber"}


def test_the_look_shows_in_the_status_the_art_class_and_past_runs(game_env):
    m, e = game_env.module, game_env.elements
    text = e["settlement-look-display"].innerText
    assert "Thatched huts" in text and "Timber halls at 4" in text and "Looks seen: 1 of 3" in text
    assert e["settlement-visual"].classList.contains("settlement-visual--thatched")
    m.skill_tree.unlocked = set(m.SKILLS)
    m.run = m.RunState(run_number=5)
    m.render()
    assert e["settlement-visual"].classList.contains("settlement-visual--concrete")
    assert not e["settlement-visual"].classList.contains("settlement-visual--thatched")
    assert "Concrete and glass" in e["settlement-look-display"].innerText and "7 of 7 skills owned" in e["settlement-look-display"].innerText
    _finish_run(game_env)
    card = m._past_run_card(0, m.run_log_history[-1], False)
    assert "Concrete and glass" in card.children[0].innerText


def test_a_cached_page_without_the_look_elements_still_renders(game_env):
    m = game_env.module
    m._el = lambda element_id: None
    m.render_settlement_look()


# ------------------------------------------------------------------------------------------ GE-14
def _set(game_env, key, value):
    game_env.local_storage.setItem(key, value)


def test_every_event_type_has_an_effect_and_a_distinct_enough_class(game_env):
    m = game_env.module
    assert set(m.EVENT_HIT_EFFECT) == set(m.EVENT_LABEL)  # a future event type must pick its effect
    assert {m.hit_effect_class(t) for t in m.EVENT_LABEL} == set(m.HIT_EFFECT_CLASSES)
    assert len(m.HIT_EFFECT_CLASSES) >= 5
    assert m.hit_effect_class("flood") == "hit-ripple" and m.hit_effect_class("civil_unrest") == "hit-shudder"
    assert m.hit_effect_class("not_an_event") == "hit-dim"


def test_effects_default_on_switch_off_and_reduce_motion_always_wins(game_env):
    m = game_env.module
    assert m.effects_enabled() is True
    _set(game_env, "aftermath-effects", "false")
    assert m.effects_enabled() is False
    _set(game_env, "aftermath-effects", "true")
    assert m.effects_enabled() is True
    _set(game_env, "aftermath-reduced-motion", "true")
    assert m.effects_enabled() is False  # even with the switch on
    _set(game_env, "aftermath-reduced-motion", "false")
    assert m.effects_enabled() is True


def test_resolving_an_event_plays_its_effect_class_then_removes_it(game_env):
    m, e = game_env.module, game_env.elements
    assert m.run.next_event_type() == "flood"
    game_env.resolve_event()
    assert e["settlement-visual"].classList.contains("hit-ripple")
    assert e["hit-number"].classList.contains("hit-number--pop")
    delays = [d for _cb, d in game_env.timers.pending]
    assert m.HIT_EFFECT_MS in delays
    game_env.timers.flush()
    assert not e["settlement-visual"].classList.contains("hit-ripple")
    assert not e["hit-number"].classList.contains("hit-number--pop")


def test_effects_off_means_no_class_is_ever_added(game_env):
    e = game_env.elements
    _set(game_env, "aftermath-effects", "false")
    game_env.resolve_event()
    assert not any(e["settlement-visual"].classList.contains(c) for c in game_env.module.HIT_EFFECT_CLASSES)
    assert not e["hit-number"].classList.contains("hit-number--pop")
    assert e["hit-number"].innerText  # the large number itself is plain text and stays


def test_hit_number_is_words_and_icon_not_just_colour_and_follows_the_last_event(game_env):
    m, e = game_env.module, game_env.elements
    assert e["hit-number"].hidden is True and e["hit-number"].innerText == ""
    game_env.resolve_event()
    entry = m.run.event_log[-1]
    text = e["hit-number"].innerText
    assert m.EVENT_ICON[entry["type"]] in text and f"{entry['damage']:.0f}" in text and "damage" in text
    assert e["hit-number"].hidden is False and "event-category--weather" in e["hit-number"].className
    game_env.module.run = m.RunState(run_number=2)
    m.render()
    assert e["hit-number"].hidden is True


def test_a_page_without_the_hit_elements_still_resolves_events(game_env):
    m = game_env.module
    real = m._el
    m._el = lambda element_id: None if element_id in ("hit-number", "settlement-visual") else real(element_id)
    game_env.resolve_event()
    assert len(m.run.event_log) == 1


# ------------------------------------------------------------------------------------------ GE-26
def test_countdown_stages_follow_what_the_resources_can_still_buy(game_env):
    m = game_env.module
    stage = {}
    for resources in (200, 80, 79, 60, 59, 40, 20, 19, 0):
        m.run.resources = float(resources)
        stage[resources] = m.countdown_stage(m.run)
    assert stage == {200: 1, 80: 1, 79: 2, 60: 2, 59: 2, 40: 2, 20: 2, 19: 3, 0: 3}
    m.run.event_index = len(m.run.schedule)
    assert m.countdown_stage(m.run) == 0 and m.countdown_note_text(m.run) == ""


def test_the_strip_carries_the_stage_and_a_hint_in_words(game_env):
    m, e = game_env.module, game_env.elements
    assert e["schedule-strip"].getAttribute("data-countdown") == "1"
    assert "up to 10 units" in e["countdown-note"].innerText and "Flood" in e["countdown-note"].innerText
    m.run.resources = 20.0
    m.render()
    assert e["schedule-strip"].getAttribute("data-countdown") == "2" and "up to 1 unit " in e["countdown-note"].innerText
    m.run.resources = 5.0
    m.render()
    assert e["schedule-strip"].getAttribute("data-countdown") == "3"
    assert e["countdown-note"].innerText == "Nothing left you can afford: Flood is the next step." and e["countdown-note"].hidden is False
    for _ in range(len(m.run.schedule)):
        game_env.resolve_event()
    assert e["schedule-strip"].getAttribute("data-countdown") == "0" and e["countdown-note"].hidden is True


def test_the_pulse_is_css_only_and_guarded_by_both_switches():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert 'html[data-effects="false"] .schedule-strip .schedule-chip--next' in css
    block = css[css.index("GE-26: the countdown pulse"):css.index("BATCH3-END")]
    assert "prefers-reduced-motion: reduce" in block and "animation: none" in block
    assert "data-countdown" not in (GAME_DIR / "ui.js").read_text(encoding="utf-8")


def test_a_cached_page_without_the_countdown_note_still_renders(game_env):
    m = game_env.module
    real = m._el
    m._el = lambda element_id: None if element_id == "countdown-note" else real(element_id)
    m.render_schedule_strip()


# ------------------------------------------------------------------------------------------ GE-23
class _Clock:
    def __init__(self, start=1000.0):
        self.t = start

    def __call__(self):
        return self.t


def _timer(game_env, on=True, start=1000.0):
    m = game_env.module
    clock = _Clock(start)
    m._now = clock
    if on:
        game_env.local_storage.setItem("aftermath-run-timer", "true")
    return clock


def test_timer_is_off_by_default_hidden_and_adds_nothing_anywhere(game_env):
    m, e = game_env.module, game_env.elements
    clock = _timer(game_env, on=False)
    assert m.run_timer_enabled() is False and e["run-timer-display"].hidden is True
    game_env.invest_growth()
    clock.t += 3
    for _ in range(len(m.run.schedule)):
        game_env.resolve_event()
    assert "seconds" not in m.run_log_history[-1] and "timer_seconds" not in m.get_state()
    assert m.run.timed is False and m.fastest_run_number() is None
    assert m.run_log_history[-1]["score"] == m.run.run_score()


def test_time_runs_from_the_first_action_to_the_last_event_and_is_logged(game_env):
    m, e = game_env.module, game_env.elements
    clock = _timer(game_env)
    m.render()
    assert e["run-timer-display"].hidden is False and "starts with your first move" in e["run-timer-display"].innerText
    clock.t += 100
    assert m.run.elapsed == 0  # waiting before the first move costs nothing
    game_env.invest_growth()  # the first action starts the clock
    assert m.run.timed is True
    clock.t += 4
    game_env.resolve_event()
    assert m.run.elapsed == 4
    for _ in range(len(m.run.schedule) - 1):
        clock.t += 2
        game_env.resolve_event()
    assert m.run.is_complete() and m.run.elapsed == 4 + 2 * 6
    assert m.run_log_history[-1]["seconds"] == 16
    assert e["run-timer-display"].innerText == "Run time: 0:16 (final)"
    assert m.get_state().get("timer_seconds") is None or m.get_state()["timer_seconds"] == 16


def test_one_long_pause_counts_at_most_five_seconds(game_env):
    m = game_env.module
    clock = _timer(game_env)
    game_env.invest_growth()
    clock.t += 3600  # a tab left open for an hour
    game_env.resolve_event()
    assert m.run.elapsed == m.TIMER_MAX_STEP


def test_ticks_between_actions_keep_the_display_moving_and_chain_one_timeout(game_env):
    m, e = game_env.module, game_env.elements
    clock = _timer(game_env)
    game_env.invest_growth()
    before = len([d for _cb, d in game_env.timers.pending if d == 1000])
    assert before == 1
    m.render()
    assert len([d for _cb, d in game_env.timers.pending if d == 1000]) == 1  # never doubled
    clock.t += 1
    game_env.timers.flush()
    assert m.run.elapsed == 1 and e["run-timer-display"].innerText == "Run time: 0:01"
    assert len([d for _cb, d in game_env.timers.pending if d == 1000]) == 1  # and it re-armed itself


def test_a_run_that_began_untimed_stays_untimed_and_switching_off_ends_timing(game_env):
    m, e = game_env.module, game_env.elements
    clock = _timer(game_env, on=False)
    game_env.invest_growth()
    game_env.local_storage.setItem("aftermath-run-timer", "true")
    clock.t += 5
    game_env.resolve_event()
    assert m.run.timed is False and "not timed" in e["run-timer-display"].innerText
    game_env.start_new_run()
    game_env.invest_growth()
    assert m.run.timed is True
    game_env.local_storage.setItem("aftermath-run-timer", "false")
    e["run-timer-checkbox"].dispatch("change", None)
    assert m.run.timed is False and e["run-timer-display"].hidden is True


def test_a_challenge_run_is_never_timed(game_env):
    m = game_env.module
    _timer(game_env)
    run = m.RunState(normalised=True)
    m.run = run
    game_env.invest_growth()
    assert run.timed is False


def test_a_saved_run_keeps_its_seconds_and_a_bad_value_is_ignored(game_env):
    m = game_env.module
    clock = _timer(game_env)
    game_env.invest_growth()
    clock.t += 4
    game_env.resolve_event()
    state = m.get_state()
    assert state["timer_seconds"] == 4
    m.load_state(dict(state))
    assert m.run.timed is True and m.run.elapsed == 4
    for bad in (True, "9", -3, 0, 10 ** 9, None, [1]):
        broken = dict(state, timer_seconds=bad)
        m.load_state(broken)
        assert m.run.timed is None and m.run.elapsed == 0
    m.load_state({k: v for k, v in state.items() if k != "timer_seconds"})  # an older save has no key
    assert m.run.timed is None
    game_env.local_storage.setItem("aftermath-run-timer", "false")
    m.load_state(dict(state))
    assert m.run.timed is None  # the switch is off now: the loaded run is simply untimed


def test_past_runs_show_the_time_mark_the_fastest_and_sort_by_it(game_env):
    m = game_env.module
    clock = _timer(game_env)
    for number, per_step in ((1, 3), (2, 1), (3, 2)):
        m.run = m.RunState(run_number=number)
        game_env.invest_growth()
        for _ in range(len(m.run.schedule)):
            clock.t += per_step
            game_env.resolve_event()
    assert [e.get("seconds") for e in m.run_log_history] == [21, 7, 14]
    assert m.fastest_run_number() == 2
    card = m._past_run_card(1, m.run_log_history[1], False)
    assert "⏱ 0:07 (fastest)" in card.children[0].innerText
    card = m._past_run_card(0, m.run_log_history[0], False)
    assert "⏱ 0:21" in card.children[0].innerText and "fastest" not in card.children[0].innerText
    m.past_runs_sort = "fastest"
    order = [entry["run_number"] for _i, entry in m.past_runs_view()]
    assert order == [2, 3, 1]
    m.run_log_history.append({"run_number": 4, "score": 5, "resilience_capacity": 0, "growth_capacity": 0, "damage_taken": 1, "knowledge_earned": 1, "event_log": []})
    assert [entry["run_number"] for _i, entry in m.past_runs_view()] == [2, 3, 1, 4]  # untimed runs follow
    assert m.entry_seconds({"seconds": "9"}) is None and m.entry_seconds({"seconds": 0}) is None and m.entry_seconds({"seconds": True}) is None
    assert m.format_duration(59) == "0:59" and m.format_duration(3725) == "1:02:05"


# ------------------------------------------------------------------------------------------ E-31
def test_every_achievement_sits_on_exactly_one_branch_in_catalog_order(game_env):
    m = game_env.module
    branches = m.achievement_tree_branches()
    placed = [entry["id"] for _label, entries in branches for entry in entries]
    assert sorted(placed) == sorted(a["id"] for a in m.ACHIEVEMENTS) and len(placed) == len(set(placed))
    assert [label for label, _e in branches][0] == "Getting started" and len(branches) == 6
    listed = {i for _label, ids in m.ACHIEVEMENT_BRANCHES for i in ids}
    assert listed <= {a["id"] for a in m.ACHIEVEMENTS}  # no typo in a branch list
    assert not any(label == "More" for label, _e in branches)  # nothing fell through today


def test_an_achievement_nobody_listed_lands_on_a_more_branch(game_env):
    m = game_env.module
    summary = m.achievements_summary() + [{"id": "future_one", "label": "Future", "description": "d", "earned": False, "progress": None}]
    branches = m.achievement_tree_branches(summary)
    assert branches[-1][0] == "More" and [e["id"] for e in branches[-1][1]] == ["future_one"]


def test_the_strip_lights_earned_nodes_in_words_and_shape_and_redraws_only_on_change(game_env):
    m, e = game_env.module, game_env.elements
    strip = e["achievement-strip"]
    assert e["achievement-strip-summary"].innerText.endswith("Achievements: 0 of 26 earned")
    assert len(strip.children) == 6
    assert sum(len(branch.children[1].children) for branch in strip.children) == 26
    before = strip.children
    m.render()
    assert strip.children is before  # same drawing: nothing earned in between
    game_env.invest_resilience()
    game_env.invest_growth()
    game_env.resolve_event()
    assert "earned" in e["achievement-strip-summary"].innerText and "0 of 26" not in e["achievement-strip-summary"].innerText
    first = strip.children[0]
    assert first.children[0].innerText.startswith("Getting started 3/4")
    nodes = first.children[1].children
    lit = [n for n in nodes if "achievement-node--earned" in n.className]
    assert len(lit) == 3 and all(n.innerText == "✓" for n in lit)  # a check mark, not only a colour
    assert all(n.innerText == "" for n in nodes if n not in lit)
    assert "Facing It Head-On: earned" in [n.getAttribute("aria-label") for n in nodes]
    assert any(n.getAttribute("aria-label").endswith("not earned yet") for n in nodes)
    assert first.getAttribute("aria-label") == "Getting started: 3 of 4 earned"


def test_a_cached_page_without_the_strip_still_renders(game_env):
    m = game_env.module
    real = m._el
    m._el = lambda element_id: None if element_id.startswith("achievement-strip") else real(element_id)
    m._achievement_strip_signature = None
    m.render_achievement_strip()


# ------------------------------------------------------------------------------------------ E-26
def test_the_dock_line_repeats_resources_resilience_and_growth_and_follows_clicks(game_env):
    e = game_env.elements
    assert e["dock-resources"].innerText == "Resources 200 · Resilience 0 · Growth 0"
    game_env.invest_resilience()
    game_env.invest_growth()
    assert e["dock-resources"].innerText == "Resources 155 · Resilience 1 · Growth 1"


def test_the_dock_line_is_shown_only_while_the_bar_is_docked_and_phone_rules_exist():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    assert ".dock-resources { display: none; margin: 0; }" in css
    assert "#actions-dock.mobile-docked .dock-resources" in css
    block = css[css.index("E-26: phone tap targets"):css.index("BATCH3-END")]
    for needle in (".achievement-node::after", "min-height: 44px", "min-width: 44px", "(max-width: 640px)"):
        assert needle in block
    page = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="dock-resources" class="dock-resources" aria-hidden="true"' in page and page.index('id="actions-dock"') < page.index('id="dock-resources"') < page.index('id="resolve-event-button"')


def test_a_cached_page_without_the_dock_line_still_renders(game_env):
    m = game_env.module
    real = m._el
    m._el = lambda element_id: None if element_id == "dock-resources" else real(element_id)
    m.render_dock_resources()
