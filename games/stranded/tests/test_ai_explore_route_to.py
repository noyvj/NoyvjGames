"""Tests for explore.route_to() function."""

import explore
import walker


def test_route_to_finds_path_to_reachable_scene():
    """Test that route_to finds a path to a reachable scene using allowed edges."""
    # Get initial state
    start, _ = walker.initial()

    # Find a simple path (e.g., first choice from start)
    first_choice = 0
    target_scene = walker.destination(start, first_choice)

    # Create taken edges set with just the first edge
    taken = {(start[0], first_choice, target_scene)}

    # route_to should find the path
    path = explore.route_to(taken, target_scene)
    assert path is not None
    assert path == "0"  # Should be just choice 0


def test_route_to_returns_none_for_unreachable_scene():
    """Test that route_to returns None when target is unreachable with given edges."""
    # Get initial state
    start, _ = walker.initial()

    # Try to reach a scene that's not reachable from start with no edges
    # (This is an edge case - in practice, we'd need to know an unreachable scene)
    # For now, test with empty taken set and a scene that's not the start
    taken = set()
    path = explore.route_to(taken, "s1b")  # Assuming s1b is not reachable from start
    assert path is None
