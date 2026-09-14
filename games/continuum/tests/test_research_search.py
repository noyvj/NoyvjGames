"""Milestone 17 -- K14: a search/filter box on the research tree panel.

The tree runs 14 tiers across 3 branches and ~45 nodes (see CLAUDE.md's
Phase 1 build notes on research.py's structure) -- this adds a plain text
input above the panel that filters rows by name/blurb/branch label,
case-insensitively, without touching the tree's own unlock/availability
logic at all (this is a rendering-layer filter, not a tree query).
"""

import research


def _dispatch_search(game_env, query):
    game_env.elements["research-search-input"].value = query
    game_env.elements["research-search-input"].dispatch("input", None)


def _rendered_node_names(game_env):
    container = game_env.elements["research-list"]
    names = []
    for row in container.children:
        # Each row's first child is .row-top, whose first child is the
        # name span (see render_research()) -- walk the same structure the
        # real DOM has rather than re-deriving it from the tree directly.
        if not row.children:
            continue
        top = row.children[0]
        if top.children:
            names.append(top.children[0].innerText)
    return names


def test_no_query_shows_every_visible_node(game_env):
    tree = game_env.module.tree
    names = _rendered_node_names(game_env)
    assert len(names) == len(tree.visible_nodes())


def test_filtering_by_a_partial_node_name(game_env):
    tree = game_env.module.tree
    total = len(tree.visible_nodes())
    _dispatch_search(game_env, "fire-keeping")  # matches by name specifically
    names = _rendered_node_names(game_env)
    assert "Fire-Keeping" in names
    # Matching is name-OR-blurb-OR-branch (see _research_node_matches()), so
    # a query this specific narrows the list rather than showing everything.
    assert len(names) < total


def test_filtering_is_case_insensitive(game_env):
    _dispatch_search(game_env, "FIRE-KEEPING")
    names = _rendered_node_names(game_env)
    assert any("Fire-Keeping" in n for n in names)


def test_filtering_by_branch_label(game_env):
    _dispatch_search(game_env, "provision")
    tree = game_env.module.tree
    visible_provision = [n for n in tree.visible_nodes() if n.branch == "provision"]
    names = _rendered_node_names(game_env)
    assert len(names) == len(visible_provision)


def test_filtering_by_blurb_text(game_env):
    tree = game_env.module.tree
    node = next(n for n in tree.visible_nodes())
    # Pick a distinctive word straight out of that node's own blurb rather
    # than assuming one -- keeps this test valid even if blurb text is
    # edited later.
    word = node.blurb.split()[0].strip(".,").lower()
    if len(word) < 4:
        word = node.blurb.split()[1].strip(".,").lower()
    _dispatch_search(game_env, word)
    names = _rendered_node_names(game_env)
    assert node.name in names


def test_a_query_matching_nothing_shows_a_message_not_an_empty_panel(game_env):
    _dispatch_search(game_env, "xyzzy-not-a-real-node-nqqrst")
    container = game_env.elements["research-list"]
    assert len(container.children) == 1
    assert "no research nodes match" in container.children[0].innerText.lower()


def test_clearing_the_query_restores_the_full_list(game_env):
    _dispatch_search(game_env, "fire")
    filtered = _rendered_node_names(game_env)
    assert len(filtered) < len(game_env.module.tree.visible_nodes())

    _dispatch_search(game_env, "")
    restored = _rendered_node_names(game_env)
    assert len(restored) == len(game_env.module.tree.visible_nodes())


def test_a_filtered_out_unresearched_node_never_gets_a_button_proxy(game_env):
    # Search for something that matches only a subset of nodes, then
    # confirm every node NOT shown has no live proxy tracked for it --
    # render_research() must skip minting a Study-button proxy for a row
    # it never draws, or a filtered-out node would leak a live but
    # invisible click listener.
    tree = game_env.module.tree
    _dispatch_search(game_env, "fire")
    shown_ids = {
        node.node_id
        for node in tree.visible_nodes()
        if game_env.module._research_node_matches(node, "fire")
    }
    tracked_ids = set(game_env.module._research_button_proxies.keys())
    assert tracked_ids <= shown_ids


def test_locked_node_reasons_still_show_while_filtered(game_env):
    # A player searching for a node they haven't unlocked yet should still
    # see why it's locked -- filtering only hides ROWS that don't match,
    # it doesn't change what a shown row displays.
    tree = game_env.module.tree
    locked = next(
        n for n in tree.visible_nodes() if not tree.is_researched(n.node_id) and not tree.is_available(n.node_id)
    )
    _dispatch_search(game_env, locked.name)
    container = game_env.elements["research-list"]
    all_text = " ".join(row.innerText if hasattr(row, "innerText") else "" for row in container.children)
    # Rows are built via createElement, not innerHTML, so check the
    # dedicated locked-reason child text instead of a flattened innerText.
    found_reason = False
    for row in container.children:
        for child in row.children:
            if getattr(child, "className", "") == "research-locked-reason":
                found_reason = True
    assert found_reason


def test_research_branch_label_import_is_used_correctly():
    # Sanity check the module this filter reads from -- BRANCH_LABEL must
    # cover every branch the filter can be asked to match against.
    assert set(research.BRANCH_LABEL.keys()) == set(research.BRANCHES)
