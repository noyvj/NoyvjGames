"""shared/skill-tree.js in headless Chromium (Playwright): the pure rules match
shared/skill_tree.py result for result, and the renderer is keyboard and screen
reader operable. Skipped when Playwright or Chromium is not installed."""

import mimetypes
import sys
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))
import skill_tree as st  # noqa: E402

ORIGIN = "http://harness.test"

TREE = {
    "id": "charter", "title": "Charter perks", "currency": "charter points",
    "branches": [{"id": "routes", "title": "Routes"}, {"id": "automation", "title": "Automation"}],
    "nodes": [
        {"id": "lanes", "branch": "routes", "cost": 1, "label": "Surveyed Lanes", "description": "+1 cargo on every load.", "requires": []},
        {"id": "waystation", "branch": "routes", "cost": 2, "label": "Waystation", "description": "Posts cheaper.", "requires": ["lanes"], "effect": "post_discount"},
        {"id": "convoy", "branch": "routes", "cost": 3, "label": "Standing Convoy", "description": "Ship 1 automated.", "requires": ["waystation", "orders"]},
        {"id": "orders", "branch": "automation", "cost": 1, "label": "Standing Orders", "description": "Automation 20% cheaper."},
        {"id": "lab", "branch": "automation", "cost": 2, "label": "Lab <b>Automation</b>", "description": "Research faster.", "requires": ["orders"]},
    ],
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/shared/skill-tree.css">
<style>body{margin:0;padding:12px;font-family:system-ui;background:var(--page-bg,#12162a);color:var(--st-fg)}
html[data-theme="light"] body{--page-bg:#eef2fc}</style></head>
<body><div id="mount"></div><button id="after">after</button>
<script src="/shared/skill-tree.js"></script></body></html>"""


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield b
        b.close()


def open_page(browser, size=(1440, 900), theme=None):
    context = browser.new_context(viewport={"width": size[0], "height": size[1]})
    page = context.new_page()

    def serve(route, request):
        url = request.url[len(ORIGIN):].split("?")[0]
        if url == "/t.html":
            return route.fulfill(status=200, content_type="text/html", body=PAGE)
        file = ROOT / url.lstrip("/")
        if file.is_file():
            return route.fulfill(status=200, content_type=mimetypes.guess_type(file.name)[0] or "text/plain", body=file.read_bytes())
        return route.fulfill(status=404, body="")

    page.route(f"{ORIGIN}/**", serve)
    page.goto(f"{ORIGIN}/t.html")
    if theme:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
    return context, page


def mount(page, owned=(), earned=5, refund_nodes=False):
    page.evaluate(
        """([tree, owned, earned, refundNodes]) => {
          window.calls = { buy: [], refund: [], refundAll: 0 };
          window.ctl = NoyvjSkillTree.render(document.getElementById('mount'), {
            tree, owned, earned, refundNodes,
            onBuy: (id) => window.calls.buy.push(id),
            onRefund: (id) => window.calls.refund.push(id),
            onRefundAll: () => { window.calls.refundAll++; },
          });
        }""",
        [TREE, list(owned), earned, refund_nodes],
    )


def test_js_rules_match_python_rules(browser):
    context, page = open_page(browser)
    scenarios = [
        [], ["lanes"], ["lanes", "waystation"], ["orders"], ["lanes", "waystation", "orders"],
        ["waystation"], ["lanes", "ghost", "lanes", 4], ["lanes", "waystation", "orders", "lab", "convoy"],
    ]
    for earned in (None, 0, 1, 3, 9):
        for owned in scenarios:
            js = page.evaluate(
                """([tree, owned, earned]) => {
                  const T = NoyvjSkillTree;
                  const ids = tree.nodes.map((n) => n.id).concat(['ghost']);
                  const out = { status: {}, canBuy: {}, buy: {}, refund: {}, canRefund: {}, missing: {} };
                  ids.forEach((id) => {
                    out.status[id] = T.status(tree, owned, id, earned);
                    out.canBuy[id] = T.canBuy(tree, owned, id, earned);
                    const b = T.buy(tree, owned, id, earned);
                    out.buy[id] = [b.ok, b.owned, b.spent, b.pointsLeft, b.reason];
                    const r = T.refund(tree, owned, id);
                    out.refund[id] = [r.ok, r.owned, r.refunded, r.reason];
                    out.canRefund[id] = T.canRefund(tree, owned, id);
                    out.missing[id] = T.missingRequirements(tree, owned, id);
                  });
                  const t = T.totals(tree, owned, earned);
                  return { out, spent: T.spent(tree, owned), left: T.pointsLeft(tree, owned, earned),
                    effects: T.effects(tree, owned), sanitized: T.sanitizeOwned(tree, owned, earned),
                    trimmed: T.sanitizeOwned(tree, owned, earned, 'trim'), refundAll: T.refundAll(tree, owned),
                    totals: [t.ownedCount, t.nodeCount, t.spent, t.totalCost, t.remainingCost, t.pointsLeft, t.complete, t.byBranch],
                    tiers: ids.map((i) => T.tierOf(tree, i)), validate: T.validate(tree) };
                }""",
                [TREE, owned, earned],
            )
            ids = [n["id"] for n in TREE["nodes"]] + ["ghost"]
            for i in ids:
                assert js["out"]["status"][i] == st.status(TREE, owned, i, earned), (owned, earned, i)
                assert js["out"]["canBuy"][i] == st.can_buy(TREE, owned, i, earned)
                b = st.buy(TREE, owned, i, earned)
                assert js["out"]["buy"][i] == [b["ok"], b["owned"], b["spent"], b["points_left"], b["reason"]], (owned, earned, i)
                r = st.refund(TREE, owned, i)
                assert js["out"]["refund"][i] == [r["ok"], r["owned"], r["refunded"], r["reason"]]
                assert js["out"]["canRefund"][i] == st.can_refund(TREE, owned, i)
                assert js["out"]["missing"][i] == st.missing_requirements(TREE, owned, i)
            assert js["spent"] == st.spent(TREE, owned)
            assert js["left"] == st.points_left(TREE, owned, earned)
            assert js["effects"] == st.effects(TREE, owned)
            assert js["sanitized"] == st.sanitize_owned(TREE, owned, earned)
            assert js["trimmed"] == st.sanitize_owned(TREE, owned, earned, overspend="trim")
            ra = st.refund_all(TREE, owned)
            assert js["refundAll"] == {"ok": ra["ok"], "owned": ra["owned"], "refunded": ra["refunded"], "reason": ra["reason"]}
            t = st.totals(TREE, owned, earned)
            assert js["totals"] == [t["owned_count"], t["node_count"], t["spent"], t["total_cost"], t["remaining_cost"],
                                    t["points_left"], t["complete"], t["by_branch"]]
            assert js["tiers"] == [st.tier_of(TREE, i) for i in ids]
            assert js["validate"] == st.validate(TREE) == []
    context.close()


def test_js_validate_matches_python_on_bad_trees(browser):
    context, page = open_page(browser)
    bad_trees = [
        {"nodes": []},
        {"nodes": [{"id": "a", "cost": 0, "label": "A"}, {"id": "a", "cost": 1, "label": "A"}]},
        {"nodes": [{"id": "x", "cost": 1, "label": "X", "requires": ["y"]}, {"id": "y", "cost": 1, "label": "Y", "requires": ["x"]}]},
        {"nodes": [{"id": "b", "cost": 1, "label": "B", "requires": ["ghost"]}, {"id": "c", "cost": 1, "label": "C", "requires": ["c"]}]},
    ]
    for tree in bad_trees:
        assert page.evaluate("(t) => NoyvjSkillTree.validate(t)", tree) == st.validate(tree)
    context.close()


def test_renderer_shows_state_by_text_and_shape_not_colour_alone(browser):
    context, page = open_page(browser)
    mount(page, owned=["lanes"], earned=3)
    rows = page.evaluate("""() => [...document.querySelectorAll('.noyvj-st-node')].map((li) => ({
      id: li.dataset.node, status: li.dataset.status,
      glyph: li.querySelector('.noyvj-st-glyph').textContent,
      glyphHidden: li.querySelector('.noyvj-st-glyph').getAttribute('aria-hidden'),
      state: li.querySelector('.noyvj-st-state').textContent,
      meta: li.querySelector('.noyvj-st-meta').textContent,
      desc: li.querySelector('.noyvj-st-desc').textContent,
      needs: (li.querySelector('.noyvj-st-needs') || {}).textContent || '',
      border: getComputedStyle(li).borderStyle, disabled: li.querySelector('.noyvj-st-btn').getAttribute('aria-disabled'),
    }))""")
    by = {r["id"]: r for r in rows}
    assert by["lanes"]["status"] == "owned" and by["lanes"]["state"] == "Owned" and by["lanes"]["glyph"] == "✓"
    assert by["waystation"]["status"] == "available" and "buy for 2 charter points" in by["waystation"]["state"]
    assert by["orders"]["status"] == "available" and "buy for 1 charter point" in by["orders"]["state"]
    assert by["convoy"]["status"] == "locked" and by["convoy"]["state"] == "Locked: needs Waystation and Standing Orders"
    assert by["convoy"]["needs"] == "Needs: Waystation, Standing Orders"
    assert by["lab"]["state"] == "Locked: needs Standing Orders"
    # distinct glyphs and distinct border styles per state
    assert len({by[i]["glyph"] for i in ("lanes", "waystation", "convoy")}) == 3
    assert {by["lanes"]["border"], by["waystation"]["border"], by["convoy"]["border"]} == {"solid", "dotted"}
    assert by["lanes"]["glyphHidden"] == "true"
    assert by["waystation"]["meta"] == "Tier 2 · Cost 2 charter points"
    assert by["waystation"]["desc"] == "Posts cheaper."
    assert by["lanes"]["disabled"] == "true", "an owned perk cannot be bought again"
    # budget line
    assert page.locator(".noyvj-st-points").inner_text() == "2 charter points left of 3"
    # unaffordable: spend down so only 1 point remains and waystation costs 2
    page.evaluate("ctl.update({ owned: ['lanes'], earned: 2 })")
    assert page.locator('[data-node="waystation"] .noyvj-st-state').inner_text() == "Not enough points: 1 more charter point needed"
    assert page.locator('li[data-node="waystation"]').get_attribute("data-status") == "unaffordable"
    assert page.evaluate("getComputedStyle(document.querySelector('[data-node=\"waystation\"]')).borderStyle") == "dashed"
    context.close()


def test_labels_are_written_as_text_not_html(browser):
    context, page = open_page(browser)
    mount(page)
    assert page.locator('[data-node="lab"] .noyvj-st-label').inner_text() == "Lab <b>Automation</b>"
    assert page.locator(".noyvj-st b").count() == 0
    context.close()


def test_keyboard_navigation_is_one_tab_stop_with_arrow_movement(browser):
    context, page = open_page(browser)
    mount(page)
    tab_stops = page.evaluate("[...document.querySelectorAll('.noyvj-st-btn')].filter((b) => b.tabIndex === 0).map((b) => b.dataset.node)")
    assert tab_stops == ["lanes"]
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "noyvj-st-refund-all", "the header button comes first"
    page.keyboard.press("Tab")
    focused = lambda: page.evaluate("document.activeElement.dataset.node")  # noqa: E731
    assert focused() == "lanes"
    page.keyboard.press("ArrowDown")
    assert focused() == "waystation"
    page.keyboard.press("ArrowDown")
    assert focused() == "convoy"
    page.keyboard.press("ArrowDown")
    assert focused() == "convoy", "stays at the end of the branch"
    page.keyboard.press("ArrowRight")
    assert focused() == "lab", "the next branch, same row clamped to its length"
    page.keyboard.press("ArrowLeft")
    assert focused() == "waystation"
    page.keyboard.press("Home")
    assert focused() == "lanes"
    page.keyboard.press("End")
    assert focused() == "convoy"
    page.keyboard.press("Control+Home")
    assert focused() == "lanes"
    page.keyboard.press("Control+End")
    assert focused() == "lab"
    # the roving stop followed the focus; Tab leaves the tree
    assert page.evaluate("[...document.querySelectorAll('.noyvj-st-btn')].filter((b) => b.tabIndex === 0).map((b) => b.dataset.node)") == ["lab"]
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") == "after"
    context.close()


def test_enter_buys_an_available_perk_and_a_locked_one_explains_why(browser):
    context, page = open_page(browser)
    mount(page)
    page.locator('[data-node="lanes"] .noyvj-st-btn').focus()
    page.keyboard.press("Enter")
    assert page.evaluate("calls.buy") == ["lanes"]
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")  # convoy (locked)
    page.keyboard.press("Space")
    assert page.evaluate("calls.buy") == ["lanes"], "a locked perk never reaches onBuy"
    page.wait_for_timeout(80)
    assert "Locked: needs Waystation and Standing Orders" in page.locator(".noyvj-st-live").inner_text()
    # the renderer never changed state by itself
    assert page.locator('li[data-node="lanes"]').get_attribute("data-status") == "available"
    context.close()


def test_update_keeps_focus_and_announces_the_purchase(browser):
    context, page = open_page(browser)
    mount(page)
    page.locator('[data-node="lanes"] .noyvj-st-btn').focus()
    page.keyboard.press("Enter")
    page.evaluate("ctl.update({ owned: ['lanes'] })")
    assert page.evaluate("document.activeElement.dataset.node") == "lanes", "an in-place update must not steal focus"
    page.wait_for_timeout(80)
    assert page.locator(".noyvj-st-live").inner_text() == "Bought Surveyed Lanes. 4 charter points left."
    assert page.locator('li[data-node="lanes"]').get_attribute("data-status") == "owned"
    assert page.locator('li[data-node="waystation"]').get_attribute("data-status") == "available"
    # a periodic re-render with identical data is silent and harmless
    page.evaluate("ctl.update({ owned: ['lanes'], earned: 5 })")
    assert page.evaluate("document.activeElement.dataset.node") == "lanes"
    context.close()


def test_refund_all_and_single_refund_go_through_callbacks(browser):
    context, page = open_page(browser)
    mount(page, owned=["lanes", "waystation"], earned=5, refund_nodes=True)
    assert page.locator(".noyvj-st-refund-all").get_attribute("aria-disabled") == "false"
    page.locator(".noyvj-st-refund-all").click(force=True)
    assert page.evaluate("calls.refundAll") == 1
    # a perk another owned perk needs cannot be refunded; its dependent can
    page.locator('[data-node="lanes"] .noyvj-st-btn').focus()
    page.keyboard.press("r")
    assert page.evaluate("calls.refund") == []
    page.wait_for_timeout(80)
    assert "cannot be refunded" in page.locator(".noyvj-st-live").inner_text()
    page.locator('[data-node="waystation"] .noyvj-st-btn').focus()
    page.keyboard.press("r")
    assert page.evaluate("calls.refund") == ["waystation"]
    page.evaluate("ctl.update({ owned: [] })")
    assert page.locator(".noyvj-st-refund-all").get_attribute("aria-disabled") == "true"
    page.locator(".noyvj-st-refund-all").click(force=True)
    assert page.evaluate("calls.refundAll") == 1, "nothing to refund: no callback"
    context.close()


def test_roles_and_names_for_assistive_tech(browser):
    context, page = open_page(browser)
    mount(page)
    info = page.evaluate("""() => {
      const group = document.querySelector('.noyvj-st-branches');
      const b = document.querySelector('[data-node="convoy"] .noyvj-st-btn');
      return {
        groupName: document.getElementById(group.getAttribute('aria-labelledby')).textContent,
        groupDesc: document.getElementById(group.getAttribute('aria-describedby')).textContent,
        lists: [...document.querySelectorAll('ol.noyvj-st-nodes')].map((ol) => document.getElementById(ol.getAttribute('aria-labelledby')).textContent.replace(/\\s+/g, ' ').trim()),
        described: b.getAttribute('aria-describedby').split(' ').map((id) => document.getElementById(id).textContent),
        liveRole: document.querySelector('.noyvj-st-live').getAttribute('role'),
      };
    }""")
    assert info["groupName"] == "Charter perks"
    assert info["groupDesc"].startswith("Up and down move within a branch")
    assert info["lists"] == ["Routes (0/3)", "Automation (0/2)"]
    assert info["described"] == ["Ship 1 automated.", "Needs: Waystation, Standing Orders", "Locked: needs Waystation and Standing Orders"]
    assert info["liveRole"] == "status"
    context.close()


@pytest.mark.parametrize("size", [(1440, 900), (360, 740)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_layout_fits_the_viewport_in_both_themes(browser, size, theme):
    context, page = open_page(browser, size=size, theme=theme)
    mount(page, owned=["lanes", "orders"], earned=5, refund_nodes=True)
    geo = page.evaluate("""() => ({ sw: document.documentElement.scrollWidth, vw: innerWidth,
      small: [...document.querySelectorAll('.noyvj-st-btn')].map((b) => b.getBoundingClientRect().height).filter((h) => h < 40).length,
      fg: getComputedStyle(document.querySelector('.noyvj-st-desc')).color, theme: document.documentElement.dataset.theme })""")
    assert geo["theme"] == theme
    assert geo["sw"] <= geo["vw"], "no horizontal page scroll"
    assert geo["small"] == 0, "tap targets are at least 40px tall"
    dark_text = geo["fg"].startswith("rgb(232")
    assert dark_text == (theme == "dark")
    context.close()
