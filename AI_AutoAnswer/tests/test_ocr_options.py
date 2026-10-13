from app.automation.coordinate_mapper import Rect
from app.recognition.ocr_engine import OPTION, merge_split_option_boxes


def test_separate_letter_badges_join_adjacent_option_text_only():
    items = [
        (20, "A", Rect(20, 20, 24, 24)),
        (20, "AI AutoAnswer 模拟题库", Rect(65, 20, 210, 24)),
        (150, "A", Rect(100, 150, 20, 24)),
        (151, "栈", Rect(145, 151, 30, 22)),
        (220, "B", Rect(101, 220, 20, 24)),
        (221, "队列", Rect(146, 221, 46, 22)),
    ]
    merged = merge_split_option_boxes(items)
    options = [(text, rect) for _, text, rect in merged if OPTION.match(text)]
    assert [text for text, _ in options] == ["A. 栈", "B. 队列"]
    assert options[0][1].contains((155, 160))
    assert (20, "A", Rect(20, 20, 24, 24)) in merged
