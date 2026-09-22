"""Tests for the tracker's X-section feature batch: data-age readout,
progress bars, blocking summary, priority sort, shopping list, copy buttons,
toast, confirm-gated reset, notes, archive/search/sort, grindy flag,
visited Wiki links, and backward-compatible saves."""

from datetime import date

from .test_tracker import _find_row, _reset_to_known_state


def _texts(node):
    return node.textContent


def _rows(tbody):
    return [c.attributes["data-part"] for c in tbody.children if "data-part" in c.attributes]


# --- 1. data age -----------------------------------------------------------


def test_days_since_counts_whole_days(game_env):
    m = game_env.module
    assert m.days_since("2026-09-20", today=date(2026, 9, 25)) == 5
    assert m.days_since("2026-09-20", today=date(2026, 9, 20)) == 0
    assert m.days_since("2030-01-01", today=date(2026, 9, 20)) == 0  # never negative


def test_days_since_rejects_bad_dates(game_env):
    assert game_env.module.days_since("not-a-date") is None
    assert game_env.module.days_since(None) is None


def test_data_updated_readout_rendered(game_env):
    text = game_env.elements["data-updated"].textContent
    assert game_env.module.DATA_UPDATED in text
    assert "Recipe data last updated" in text


# --- 2. progress bars ------------------------------------------------------


def test_category_progress_counts(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}, "Balla Strike": {"owned": 0}})
    comps, _ = m.calculate()
    prog = m.category_progress(comps)
    assert prog["amp"] == (11, 12)
    assert prog["zaw"] == (12, 13)
    assert prog["kitgun"] == (8, 8)


def test_category_bars_rendered(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    m.render()
    bars = game_env.elements["category-progress"].children
    assert len(bars) == 3
    counts = [b.children[2].textContent for b in bars]
    assert counts == ["11/12 parts complete", "13/13 parts complete", "8/8 parts complete"]
    assert bars[0].children[1].attributes["aria-valuenow"] == "11"


def test_overall_percentage_in_readout(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    m.render()
    assert game_env.elements["component-progress"].textContent == "33 / 33 complete · 100%"


# --- 3. blocking -----------------------------------------------------------


def test_blocking_resource_is_short_for_most_builds(game_env):
    m = game_env.module
    # Raplak and Shwaak both need Iradite; Balla doesn't. Nothing in stock.
    _reset_to_known_state(m, parts={
        "Raplak Prism": {"owned": 0}, "Shwaak Prism": {"owned": 0}, "Granmu Prism": {"owned": 0},
    })
    comps, _ = m.calculate()
    resource, count, names = m.whats_blocking(comps)
    assert count >= 2
    assert resource in ("Marquise Veridos", "Iradite")  # both shared; tie-break is deterministic
    assert set(names) <= {"Raplak Prism", "Shwaak Prism", "Granmu Prism"}
    assert "What's blocking me" in game_env.elements["blocking-summary"].textContent


def test_blocking_none_when_everything_buildable_or_done(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    comps, _ = m.calculate()
    assert m.whats_blocking(comps) is None
    m.render()
    assert "Every part is built" in game_env.elements["blocking-summary"].textContent


def test_blocking_ignores_covered_resources(game_env):
    m = game_env.module
    ing = m.RECIPES["Raplak Prism"]["ingredients"]
    inv = {r: {"built": q, "raw": 0} for r, q in ing.items()}
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}}, inventory=inv)
    comps, _ = m.calculate()
    assert m.whats_blocking(comps) is None


# --- 4 / 9. priority sort, search, archive ---------------------------------


def _two_part_setup(m):
    """Raplak is fully stocked (0 short); Shwaak has nothing (all short)."""
    ing = m.RECIPES["Raplak Prism"]["ingredients"]
    inv = {r: {"built": q, "raw": 0} for r, q in ing.items()}
    _reset_to_known_state(
        m, parts={"Shwaak Prism": {"owned": 0}, "Raplak Prism": {"owned": 0}}, inventory=inv)


def test_priority_sort_ranks_closest_first(game_env):
    m = game_env.module
    _two_part_setup(m)
    comps, _ = m.calculate()
    ordered = [p["name"] for p in m.arrange_components(comps, "priority")]
    assert ordered[:2] == ["Raplak Prism", "Shwaak Prism"]
    assert ordered[2] == "Granmu Prism"  # finished parts sink to the bottom, fixed order


def test_priority_sort_ranks_by_fewest_missing_resources(game_env):
    m = game_env.module
    _two_part_setup(m)
    # Give Shwaak everything except one resource: fewer short than Granmu.
    ing = m.RECIPES["Shwaak Prism"]["ingredients"]
    first = next(iter(ing))
    for r, q in ing.items():
        if r != first:
            m.state["inventory"][r] = {"built": q, "raw": 0}
    m.state["parts"]["Granmu Prism"]["owned"] = 0
    comps, _ = m.calculate()
    ordered = [p["name"] for p in m.arrange_components(comps, "priority") if not p["complete"]]
    assert ordered.index("Shwaak Prism") < ordered.index("Granmu Prism")


def test_sort_dropdown_switches_mode_and_hides_category_rows(game_env):
    m = game_env.module
    _two_part_setup(m)
    game_env.elements["sort-select"].value = "priority"
    game_env.elements["sort-select"].dispatch("change", None)
    assert m.state["prefs"]["sort"] == "priority"
    body = game_env.elements["components-body"]
    assert _rows(body)[0] == "Raplak Prism"
    assert not any("category-row" in c.className for c in body.children)
    game_env.elements["sort-select"].value = "category"
    game_env.elements["sort-select"].dispatch("change", None)
    assert any("category-row" in c.className for c in body.children)


def test_invalid_sort_value_ignored(game_env):
    game_env.elements["sort-select"].value = "bogus"
    game_env.elements["sort-select"].dispatch("change", None)
    assert game_env.module.state["prefs"]["sort"] == "category"


def test_name_and_remaining_sorts(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Shtung Grip": {"owned": 0}, "Balla Strike": {"owned": 0}})
    comps, _ = m.calculate()
    assert m.arrange_components(comps, "name")[0]["name"] == "Balla Strike"
    assert m.arrange_components(comps, "remaining")[0]["name"] == "Shtung Grip"  # 11 left


def test_search_filters_case_insensitively(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    game_env.elements["search-input"].value = "PRISM"
    game_env.elements["search-input"].dispatch("input", None)
    rows = _rows(game_env.elements["components-body"])
    assert rows and all("Prism" in r for r in rows)
    game_env.elements["search-input"].value = "zzz-nothing"
    game_env.elements["search-input"].dispatch("input", None)
    body = game_env.elements["components-body"]
    assert _rows(body) == []
    assert "No parts match" in body.children[0].children[0].textContent


def test_archive_toggle_hides_completed_parts(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    game_env.elements["hide-complete-toggle"].checked = True
    game_env.elements["hide-complete-toggle"].dispatch("change", None)
    assert m.state["prefs"]["hide_complete"] is True
    assert _rows(game_env.elements["components-body"]) == ["Raplak Prism"]
    game_env.elements["hide-complete-toggle"].checked = False
    game_env.elements["hide-complete-toggle"].dispatch("change", None)
    assert len(_rows(game_env.elements["components-body"])) == 33


def test_archive_does_not_change_overall_progress(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    game_env.elements["hide-complete-toggle"].checked = True
    game_env.elements["hide-complete-toggle"].dispatch("change", None)
    assert game_env.elements["component-progress"].textContent.startswith("32 / 33")


# --- 5. shopping list ------------------------------------------------------


def test_shopping_list_text_lists_only_short_resources(game_env):
    m = game_env.module
    _reset_to_known_state(
        m, parts={"Raplak Prism": {"owned": 0}},
        inventory={"Iradite": {"built": 15, "raw": 5}, "Esher Devar": {"built": 10, "raw": 0}})
    _, res = m.calculate()
    text = m.shopping_list_text(res)
    assert "Iradite x25" in text
    assert "5 raw on hand" in text
    assert "Esher Devar" not in text  # already covered
    assert "Tear Azurite x10" in text


def test_shopping_list_empty_message(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    _, res = m.calculate()
    assert "Nothing left to farm" in m.shopping_list_text(res)


def test_shopping_textarea_populated_and_copy_button(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    m.render()
    text = game_env.elements["shopping-text"].value
    assert "Iradite x40" in text
    game_env.elements["copy-shopping-button"].dispatch("click", None)
    assert game_env.js.navigator.clipboard.written[-1] == text
    assert game_env.elements["toast"].textContent == "Copied shopping list!"
    assert game_env.elements["toast"].hidden is False


def test_copy_failure_shows_fallback_message(game_env):
    game_env.js.navigator.clipboard.fail = True
    game_env.elements["copy-shopping-button"].dispatch("click", None)
    assert "Couldn't copy" in game_env.elements["toast"].textContent


def test_toast_auto_hides(game_env):
    game_env.elements["copy-shopping-button"].dispatch("click", None)
    assert game_env.elements["toast"].hidden is False
    game_env.js.timers.fire_all()
    assert game_env.elements["toast"].hidden is True


# --- 6. copy resource + inline remaining -----------------------------------


def _resource_row(game_env, name):
    return _find_row(game_env.elements["resources-body"], "data-resource", name)


def _find(node, pred):
    if pred(node):
        return node
    for child in node.children:
        found = _find(child, pred)
        if found:
            return found
    return None


def test_copy_resource_name_button(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    m.render()
    name_cell = _resource_row(game_env, "Iradite").children[0]
    btn = _find(name_cell, lambda n: "copy-btn" in n.className)
    assert btn.attributes["aria-label"] == "Copy resource name Iradite"
    btn.dispatch("click", None)
    assert game_env.js.navigator.clipboard.written[-1] == "Iradite"


def test_used_in_shows_remaining_needed(game_env):
    m = game_env.module
    _reset_to_known_state(
        m, parts={"Raplak Prism": {"owned": 0}}, inventory={"Iradite": {"built": 15, "raw": 0}})
    m.render()
    name_cell = _resource_row(game_env, "Iradite").children[0]
    summary = _find(name_cell, lambda n: n.tag == "summary")
    assert "25 still needed" in summary.textContent
    _reset_to_known_state(
        m, parts={"Raplak Prism": {"owned": 0}}, inventory={"Iradite": {"built": 40, "raw": 0}})
    m.render()
    summary = _find(_resource_row(game_env, "Iradite").children[0], lambda n: n.tag == "summary")
    assert "covered" in summary.textContent


# --- 6b. location icon -----------------------------------------------------


def test_location_icon_matches_each_known_region(game_env):
    m = game_env.module
    assert m.location_icon("Plains of Eidolon (Earth)") == "\U0001F33E"
    assert m.location_icon("Orb Vallis (Venus) -- Heist reward") == "❄️"
    assert m.location_icon("Cambion Drift (Deimos)") == "\U0001F9EC"
    assert m.location_icon("Refined from Auron (see Auron's own Wiki page)") == "\U0001F504"
    assert m.location_icon("Venus, Phobos, Ceres, Jupiter, Pluto, and Sedna") == "\U0001FA90"


def test_resource_location_div_is_prefixed_with_the_matching_icon(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    m.render()
    # Iradite -> "Plains of Eidolon (Earth)" -> the Cetus open-world icon.
    loc_div = _find(
        _resource_row(game_env, "Iradite").children[0],
        lambda n: n.className == "resource-location",
    )
    assert loc_div.textContent.startswith("\U0001F33E ")
    assert "Plains of Eidolon" in loc_div.textContent
    # Esher Devar -> a "Refined from ..." entry -> the refined-chain icon.
    # (Also one of Raplak Prism's own ingredients, so it's guaranteed to be
    # a rendered row under the same reset-to-known-state fixture above.)
    loc_div = _find(
        _resource_row(game_env, "Esher Devar").children[0],
        lambda n: n.className == "resource-location",
    )
    assert loc_div.textContent.startswith("\U0001F504 ")


# --- 7. toast + reset dialog ----------------------------------------------


def test_build_click_shows_built_toast(game_env):
    m = game_env.module
    ing = m.RECIPES["Raplak Prism"]["ingredients"]
    _reset_to_known_state(
        m, parts={"Raplak Prism": {"owned": 0}},
        inventory={r: {"built": q, "raw": 0} for r, q in ing.items()})
    m.render()
    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    btn = _find(row, lambda n: "build-btn" in n.className)
    btn.dispatch("click", None)
    assert game_env.elements["toast"].textContent == "Built! Raplak Prism"
    assert game_env.elements["toast"].hidden is False


class _FakeDialog:
    def __init__(self):
        self.calls = []

    def ask(self, id, message, confirmLabel, onConfirm):  # noqa: A002
        self.calls.append((id, message, confirmLabel, onConfirm))


def test_reset_uses_shared_confirm_dialog_when_present(game_env):
    m = game_env.module
    _reset_to_known_state(
        m, parts={"Raplak Prism": {"owned": 1}}, inventory={"Iradite": {"built": 40, "raw": 0}})
    dialog = _FakeDialog()
    game_env.js.window = type("W", (), {"ConfirmDialog": dialog})()
    game_env.reset()
    # Not reset until confirmed; the browser confirm() isn't used.
    assert m.state["inventory"] != {}
    assert game_env.confirm.last_message is None
    assert dialog.calls[0][0] == "warframe-tracker-reset-inventory"
    dialog.calls[0][3]()
    assert m.state["inventory"] == {}
    assert m.state["parts"]["Raplak Prism"]["owned"] == 0
    assert game_env.elements["toast"].textContent == "Inventory reset to zero."


def test_reset_keeps_notes(game_env):
    m = game_env.module
    m.state["notes"]["Raplak Prism"] = "farm on Earth"
    game_env.confirm.next_result = True
    game_env.reset()
    assert m.state["notes"]["Raplak Prism"] == "farm on Earth"


# --- 8. notes --------------------------------------------------------------


def _note_box(game_env, part):
    row = _find_row(game_env.elements["components-body"], "data-part", part)
    return _find(row, lambda n: n.tag == "textarea"), row


def test_note_saved_on_change_and_round_trips(game_env):
    m = game_env.module
    box, _ = _note_box(game_env, "Raplak Prism")
    box.value = "need Iradite from Eidolon runs"
    box.dispatch("change", None)
    assert m.get_state()["notes"] == {"Raplak Prism": "need Iradite from Eidolon runs"}
    m.state["notes"] = {}
    m.load_state({"notes": {"Raplak Prism": "restored"}})
    box, _ = _note_box(game_env, "Raplak Prism")
    assert box.value == "restored"


def test_note_html_is_never_interpreted(game_env):
    m = game_env.module
    evil = '<img src=x onerror="alert(1)"><script>x</script>'
    box, _ = _note_box(game_env, "Raplak Prism")
    box.value = evil
    box.dispatch("change", None)
    assert m.state["notes"]["Raplak Prism"] == evil
    m.render()
    box, row = _note_box(game_env, "Raplak Prism")
    assert box.value == evil  # via .value / textContent only
    assert "onerror" not in row.children[0].innerHTML


def test_blank_note_is_removed_and_length_capped(game_env):
    m = game_env.module
    box, _ = _note_box(game_env, "Raplak Prism")
    box.value = "x" * 900
    box.dispatch("change", None)
    assert len(m.state["notes"]["Raplak Prism"]) == m.NOTE_MAX_LEN
    box.value = "   "
    box.dispatch("change", None)
    assert "Raplak Prism" not in m.state["notes"]


def test_load_state_drops_malformed_notes(game_env):
    m = game_env.module
    m.load_state({"notes": {"Raplak Prism": 5, "Bogus Part": "hi", "Shwaak Prism": "ok"}})
    assert m.state["notes"] == {"Shwaak Prism": "ok"}
    m.load_state({"notes": "garbage"})
    assert m.state["notes"] == {"Shwaak Prism": "ok"}


# --- 10. grindy + visited --------------------------------------------------


def test_grindy_flag_uses_single_threshold(game_env):
    m = game_env.module
    _reset_to_known_state(m, parts={"Shtung Grip": {"owned": 0}, "Raplak Prism": {"owned": 0}})
    _, res = m.calculate()
    by_name = {r["name"]: r for r in res}
    for r in res:
        assert r["grindy"] == (r["needed"] >= m.GRINDY_THRESHOLD)
    m.GRINDY_THRESHOLD = 1
    _, res = m.calculate()
    assert all(r["grindy"] for r in res)
    assert by_name  # sanity


def test_grindy_flag_rendered_only_when_unfinished(game_env):
    m = game_env.module
    m.GRINDY_THRESHOLD = 10
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0}})
    m.render()
    cell = _resource_row(game_env, "Iradite").children[0]
    assert "grindy-flag" in cell.innerHTML
    m.state["inventory"]["Iradite"] = {"built": 40, "raw": 0}
    m.render()
    assert "grindy-flag" not in _resource_row(game_env, "Iradite").children[0].innerHTML


def test_visited_wiki_link_class_survives_rerender(game_env):
    m = game_env.module
    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    link = _find(row, lambda n: n.tag == "a")
    assert "visited-session" not in link.className
    link.dispatch("click", None)
    assert "visited-session" in link.className
    m.render()
    row = _find_row(game_env.elements["components-body"], "data-part", "Raplak Prism")
    assert "visited-session" in _find(row, lambda n: n.tag == "a").className


# --- backward compatibility ------------------------------------------------


def test_old_save_without_notes_or_prefs_loads(game_env):
    m = game_env.module
    m.load_state({"parts": {"Raplak Prism": {"target": 2, "owned": 1}},
                  "inventory": {"Iradite": {"raw": 1, "built": 2}}})
    assert m.state["parts"]["Raplak Prism"]["target"] == 2
    assert m.state["prefs"] == {"sort": "category", "hide_complete": False}
    assert m.get_state()["notes"] == {}


def test_prefs_validated_and_round_trip(game_env):
    m = game_env.module
    m.load_state({"prefs": {"sort": "priority", "hide_complete": True}})
    assert m.get_state()["prefs"] == {"sort": "priority", "hide_complete": True}
    assert game_env.elements["sort-select"].value == "priority"
    assert game_env.elements["hide-complete-toggle"].checked is True
    m.load_state({"prefs": {"sort": "nonsense", "hide_complete": "yes"}})
    assert m.get_state()["prefs"] == {"sort": "priority", "hide_complete": True}
    m.load_state({"prefs": 7})
    assert m.get_state()["prefs"]["sort"] == "priority"


def test_get_state_is_a_copy(game_env):
    m = game_env.module
    st = m.get_state()
    st["notes"]["x"] = "y"
    st["prefs"]["sort"] = "name"
    assert m.state["notes"] == {}
    assert m.state["prefs"]["sort"] == "category"
