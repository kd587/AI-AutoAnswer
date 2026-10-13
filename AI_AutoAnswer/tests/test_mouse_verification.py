import numpy as np

from app.automation.mouse_controller import _visual_changed


def test_small_checkmark_change_is_detected():
    before = np.zeros((80, 200, 3), dtype=np.uint8)
    after = before.copy()
    after[10:15, 10:15] = 255
    assert _visual_changed(before, after)
