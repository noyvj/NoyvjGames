"""Real-browser bug found in the site-wide bug-check pass: showing a second
toast while the first one's setTimeout was still pending destroyed the first
timer's proxy, so when the browser later fired it Pyodide threw "Object has
already been destroyed" (an uncaught console error). The fake proxy now raises
on a destroyed call like the real one, so flushing timers after back-to-back
toasts must not throw, and the toast must still end up hidden."""


def test_back_to_back_toasts_do_not_call_destroyed_proxy(game_env):
    game_env.module.show_achievement_toast("first")
    game_env.module.show_achievement_toast("second")
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False

    game_env.timers.flush()  # would raise before the fix

    assert toast.hidden is True
