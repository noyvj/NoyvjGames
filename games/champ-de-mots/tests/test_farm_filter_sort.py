"""L-24: the farm grid's filter ("show") and sort controls."""

import re
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def _select_options(select_id):
    block = re.search(rf'<select id="{select_id}">(.*?)</select>', HTML, flags=re.S).group(1)
    return re.findall(r'<option value="([^"]+)"', block)


def _row_plot_ids(env, sequence):
    container = env.elements[f"row-plots-{sequence}"]
    return [child.id[len("plot-"):] for child in container.children]


def _row_order(env):
    return [child.id for child in env.elements["farm"].children]


def _visible_ids(env):
    return {
        plot.plot_id
        for plot in env.state.plots
        if not env.module.plot_cells[plot.plot_id].hidden
    }


def test_the_markup_options_match_the_game_constants(game_env):
    module = game_env.module
    assert _select_options("farm-filter-select") == list(module.FARM_FILTERS)
    assert _select_options("farm-sort-select") == list(module.FARM_SORTS)


def test_by_default_everything_shows_in_syllabus_order(game_env):
    module = game_env.module
    module.render()
    assert module.farm_filter == "all" and module.farm_sort == "syllabus"
    assert len(_visible_ids(game_env)) == len(game_env.state.plots)
    assert game_env.elements["farm-filter-count"].innerText == ""
    assert _row_order(game_env) == [f"row-{r.sequence}" for r in game_env.state.rows]


def test_due_filter_hides_what_is_not_due(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    state.review(plot.plot_id, True)  # now due tomorrow, not today
    module.set_farm_filter("due")
    shown = _visible_ids(game_env)
    assert plot.plot_id not in shown
    assert len(shown) == len(state.plots) - 1
    assert game_env.elements["farm-filter-count"].innerText == f"Showing {len(state.plots) - 1} of {len(state.plots)} plots"
    state.advance_day()
    module.render()
    assert plot.plot_id in _visible_ids(game_env)


def test_weeds_filter_shows_only_weeds_and_hides_empty_rows(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[5]
    plot.in_weeds = True
    module.set_farm_filter("weeds")
    assert _visible_ids(game_env) == {plot.plot_id}
    for row in state.rows:
        assert game_env.elements[f"row-{row.sequence}"].hidden is (row.sequence != plot.sequence)
    module.set_farm_filter("all")
    assert all(game_env.elements[f"row-{r.sequence}"].hidden is False for r in state.rows)


def test_type_filters_split_the_farm(game_env):
    module, state = game_env.module, game_env.state
    seen = set()
    for kind in ("vocab", "phrase", "grammar", "phonetic"):
        module.set_farm_filter(kind)
        shown = _visible_ids(game_env)
        assert shown == {p.plot_id for p in state.plots if p.topic_type == kind}
        assert shown and not (shown & seen)
        seen |= shown
    assert seen == {p.plot_id for p in state.plots}


def test_unwatered_filter_follows_watering(game_env):
    module, state = game_env.module, game_env.state
    module.set_farm_filter("unwatered")
    assert len(_visible_ids(game_env)) == len(state.plots)
    state.review(state.plots[0].plot_id, False)  # even a wrong answer counts as watered
    module.render()
    assert state.plots[0].plot_id not in _visible_ids(game_env)


def test_unknown_filter_or_sort_falls_back(game_env):
    module = game_env.module
    assert module.set_farm_filter("nonsense") == "all"
    assert module.set_farm_sort("nonsense") == "syllabus"
    assert module.set_farm_filter(None) == "all"
    assert module.set_farm_sort(7) == "syllabus"


def test_select_change_events_drive_the_filter_and_sort(game_env):
    module = game_env.module
    game_env.elements["farm-filter-select"].value = "grammar"
    game_env.elements["farm-filter-select"].dispatch("change", None)
    assert module.farm_filter == "grammar"
    game_env.elements["farm-sort-select"].value = "type"
    game_env.elements["farm-sort-select"].dispatch("change", None)
    assert module.farm_sort == "type"


def test_weakest_first_puts_the_shakiest_plot_first_in_its_row(game_env):
    module, state = game_env.module, game_env.state
    row = state.rows[3]
    plots = state.row_plots(row.sequence)
    target = plots[-1]
    state.review(target.plot_id, False)  # lowers its ease below the untouched ones
    module.set_farm_sort("weakest")
    assert _row_plot_ids(game_env, row.sequence)[0] == target.plot_id
    module.set_farm_sort("syllabus")
    assert _row_plot_ids(game_env, row.sequence) == [p.plot_id for p in plots]


def test_weakest_first_sends_the_strongest_week_last(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(1):
        plot.stage = module.STAGE_AUTOMATED
    module.set_farm_sort("weakest")
    order = _row_order(game_env)
    assert order[-1] == "row-1"
    assert order[0] == "row-2"


def test_overdue_sort_leads_with_the_longest_overdue(game_env):
    module, state = game_env.module, game_env.state
    row = state.rows[2]
    plots = state.row_plots(row.sequence)
    a, b = plots[4], plots[9]
    state.review(a.plot_id, True)
    state.review(b.plot_id, True)
    a.next_due, b.next_due = 1, 3
    module.set_farm_sort("overdue")
    state.current_day = 10
    module.on_next_day()  # day 11, both overdue, a more so; the next day re-applies the sort
    ids = _row_plot_ids(game_env, row.sequence)
    assert ids[:2] == [a.plot_id, b.plot_id]
    assert _row_order(game_env)[0] == f"row-{row.sequence}"  # most overdue plots live here


def test_type_sort_groups_by_type_without_losing_any_plot(game_env):
    module, state = game_env.module, game_env.state
    module.set_farm_sort("type")
    for row in state.rows:
        kinds = [state.plots_by_id[pid].topic_type for pid in _row_plot_ids(game_env, row.sequence)]
        ranks = [module.FARM_TYPE_ORDER.index(k) for k in kinds]
        assert ranks == sorted(ranks)


def test_reordering_moves_nodes_it_never_duplicates_them(game_env):
    module, state = game_env.module, game_env.state
    for key in ("weakest", "overdue", "type", "syllabus"):
        module.set_farm_sort(key)
        rows = game_env.elements["farm"].children
        assert len(rows) == len(state.rows) == len({r.id for r in rows})
        total = 0
        seen = set()
        for row in state.rows:
            ids = _row_plot_ids(game_env, row.sequence)
            assert sorted(ids) == sorted(row.plot_ids)
            total += len(ids)
            seen |= set(ids)
        assert total == len(state.plots) == len(seen)


def test_filter_and_sort_never_touch_srs_state_or_the_save(game_env):
    module, state = game_env.module, game_env.state
    state.review(state.plots[1].plot_id, True)
    before = [(p.plot_id, p.stage, p.interval_days, p.next_due, p.ease_factor) for p in state.plots]
    saved = module.get_state()
    for key in module.FARM_FILTERS:
        module.set_farm_filter(key)
    for key in module.FARM_SORTS:
        module.set_farm_sort(key)
    assert [(p.plot_id, p.stage, p.interval_days, p.next_due, p.ease_factor) for p in state.plots] == before
    assert module.get_state() == saved
    assert "farm_filter" not in str(saved) and "farm_sort" not in str(saved)


def test_loading_a_save_reapplies_the_current_order(game_env):
    module, state = game_env.module, game_env.state
    module.set_farm_sort("weakest")
    module.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert module.farm_sort == "weakest"  # a display preference, not part of a save
    assert len(_row_order(game_env)) == len(state.rows)
