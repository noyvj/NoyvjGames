from report import build


class MockNotebook:
    def __init__(self, entries=None, confirm_result=0):
        self.entries = entries or []
        self.confirm_result = confirm_result
        self.truth = lambda x: x  # dummy truth function

    def confirm(self, entries, truth=None):
        return self.confirm_result


class MockState:
    def __init__(self, contact=None, scenes_seen=0, compound_scenes_seen=0, bridge_scenes_seen=0,
                 spoken=None, compound_spoken=None, bridge_spoken=None):
        self.contact = contact or {}
        self.notebook = MockNotebook()
        self.compound_notebook = MockNotebook()
        self.bridge_notebook = MockNotebook()
        self.scenes_seen = scenes_seen
        self.compound_scenes_seen = compound_scenes_seen
        self.bridge_scenes_seen = bridge_scenes_seen
        self.spoken = spoken or []
        self.compound_spoken = compound_spoken or []
        self.bridge_spoken = bridge_spoken or []


def test_build_returns_none_without_bridge_contact():
    """build should return None if contact with planet 3 has not happened."""
    state = MockState(contact={})
    assert build(state, [], {}) is None


def test_build_handles_zero_scenes_and_entries():
    """build should correctly compute totals when everything is zero."""
    state = MockState(contact={"bridge": True}, scenes_seen=0, compound_scenes_seen=0, bridge_scenes_seen=0,
                      spoken=[], compound_spoken=[], bridge_spoken=[])
    result = build(state, [], {"pulse": 0, "compound": 0, "bridge": 0})
    assert result is not None
    assert result["totals"]["transmissions"] == 0
    assert result["totals"]["sent"] == 0
    assert result["totals"]["written"] == 0
    assert result["totals"]["right"] == 0


def test_build_handles_max_scenes():
    """build should correctly sum large scene counts."""
    state = MockState(contact={"bridge": True}, scenes_seen=10, compound_scenes_seen=20, bridge_scenes_seen=30,
                      spoken=[1] * 5, compound_spoken=[1] * 15, bridge_spoken=[1] * 25)
    result = build(state, [], {"pulse": 10, "compound": 20, "bridge": 30})
    assert result["totals"]["transmissions"] == 60
    assert result["totals"]["sent"] == 45


def test_build_handles_empty_achievements():
    """build should return empty achievements list and zero total when none are earned."""
    state = MockState(contact={"bridge": True})
    result = build(state, [], {"pulse": 1, "compound": 1, "bridge": 1})
    assert result["achievements"] == []
    assert result["achievements_total"] == 0


def test_build_handles_mixed_achievements():
    """build should only include earned achievements and report the correct total."""
    state = MockState(contact={"bridge": True})
    achievements_view = [
        {"label": "A", "description": "Desc A", "earned": True},
        {"label": "B", "description": "Desc B", "earned": False},
        {"label": "C", "description": "Desc C", "earned": True},
    ]
    result = build(state, achievements_view, {"pulse": 1, "compound": 1, "bridge": 1})
    assert len(result["achievements"]) == 2
    assert result["achievements_total"] == 3
    labels = [a["label"] for a in result["achievements"]]
    assert "A" in labels and "C" in labels and "B" not in labels


def test_build_propagates_notebook_counts():
    """build should correctly pass through written and right counts from notebooks."""
    state = MockState(contact={"bridge": True}, scenes_seen=1, compound_scenes_seen=1, bridge_scenes_seen=1,
                      spoken=[1], compound_spoken=[1], bridge_spoken=[1])
    state.notebook.entries = ["a", "b"]
    state.notebook.confirm_result = 2
    state.compound_notebook.entries = ["x"]
    state.compound_notebook.confirm_result = 1
    state.bridge_notebook.entries = []
    state.bridge_notebook.confirm_result = 0

    result = build(state, [], {"pulse": 5, "compound": 5, "bridge": 5})

    pulse_row = next(p for p in result["planets"] if p["planet"] == "pulse")
    assert pulse_row["written"] == 2
    assert pulse_row["right"] == 2

    compound_row = next(p for p in result["planets"] if p["planet"] == "compound")
    assert compound_row["written"] == 1
    assert compound_row["right"] == 1

    bridge_row = next(p for p in result["planets"] if p["planet"] == "bridge")
    assert bridge_row["written"] == 0
    assert bridge_row["right"] == 0
