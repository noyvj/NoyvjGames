"""The whole book can be finished from a clean save: every case Clean by following the hint ladder, every spirit page completed by
a thorough replay, every keepsake returned, and the guide full."""

import game
import progress
from tests.helpers import call, solve_thoroughly, solve_with_hints


def test_all_forty_cases_come_out_clean_by_following_the_hints_and_the_guide_can_be_filled():
    game.game.__init__()
    call(action="open")
    for cid in progress.ORDER:
        v = call(action="pick", case=cid)
        assert v["ok"], "case %s should be open by now" % cid
        v = solve_with_hints()
        assert v["result"]["grade_name"] == "Clean", cid
    t = call(action="open")["totals"]
    assert t["done"] == 40 and t["clean"] == 40 and t["chapters_done"] == 5
    # a player who knows the answers confirms every piece of evidence, one thorough replay per case
    for cid in progress.ORDER:
        solve_thoroughly(cid)
        if game.compiled(cid).keep_room >= 0:
            assert call(action="return")["ok"], cid
    v = call(action="open")
    assert v["guide"]["complete"] == 12, [e["title"] + " " + e["lines"][0] for s in v["guide"]["sections"] if s["id"] == "spirits" for e in s["entries"] if "complete" not in e["title"]]
    assert v["guide"]["found"] == v["guide"]["total"] == 37
    assert all(s["found"] == s["total"] for s in v["guide"]["sections"])
    assert game.game.best == {cid: 3 for cid in progress.ORDER}
