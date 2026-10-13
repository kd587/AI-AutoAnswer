import time

from app.automation.user_activity import MouseActivityGuard


def test_guard_remembers_mouse_movement_even_if_cursor_returns():
    position = [(10, 10)]
    with MouseActivityGuard(lambda: position[0], interval=0.005) as guard:
        position[0] = (20, 20)
        time.sleep(0.03)
        position[0] = (10, 10)
    assert guard.moved
