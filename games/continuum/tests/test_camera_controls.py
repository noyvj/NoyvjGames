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


def test_pan_camera_function_exists():
    """Test that panCamera function is defined."""
    src = render3d_source()
    assert "function panCamera(dx, dy)" in src


def test_look_at_uses_target_coordinates():
    """Test that camera.lookAt uses targetX and targetZ."""
    src = render3d_source()
    assert "camera.lookAt(targetX, 0.4, targetZ)" in src


def test_max_pan_constant_exists():
    """Test that MAX_PAN constant is defined."""
    src = render3d_source()
    assert "const MAX_PAN = 6;" in src


def test_contextmenu_listener_exists():
    """Test that contextmenu event listener is attached."""
    src = render3d_source()
    assert 'addEventListener("contextmenu"' in src
