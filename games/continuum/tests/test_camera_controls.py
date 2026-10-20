from .pagefiles import render3d_source


def test_camera_zoom_constants():
    """Test that MIN_DISTANCE and MAX_DISTANCE constants are defined."""
    src = render3d_source()
    assert "const MIN_DISTANCE = 3.5;" in src
    assert "const MAX_DISTANCE = 16;" in src


def test_zoom_camera_function():
    """Test that zoomCamera function is defined with deltaY parameter."""
    src = render3d_source()
    assert "function zoomCamera(deltaY)" in src


def test_wheel_event_listener():
    """Test that the wheel event listener is attached with passive: false."""
    src = render3d_source()
    assert 'addEventListener("wheel"' in src
    assert "passive: false" in src


def test_camera_state_accessor():
    """Test that cameraState accessor is added to ContinuumScene."""
    src = render3d_source()
    assert "cameraState: function" in src
