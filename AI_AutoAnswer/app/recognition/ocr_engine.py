import re
import sys
import os
import hashlib
import shutil
from pathlib import Path

import numpy as np

from app.automation.coordinate_mapper import Rect
from app.capture.screen_capture import Capture, preprocess
from .models import LocatedOption, ObservedQuestion
from .question_context import current_question


OPTION = re.compile(r"^\s*.{0,2}?\s*([A-H])\s*[.、．:：)）]\s*(.+)$", re.I)
NEXT = re.compile(r"^(下一题|下一页|继续|Next)\s*[→›>]*$", re.I)
FINISH = re.compile(r"^\s*(答题完成|全部完成|练习完成|练习结束|任务完成|考试结束)")
SINGLE_LABEL = re.compile(r"^\s*([A-H])\s*[.、．:：)）]?\s*$", re.I)


def merge_split_option_boxes(items: list[tuple[int, str, Rect]]) -> list[tuple[int, str, Rect]]:
    """Join an OCR letter badge with the adjacent option text on the same row."""
    labels = [(index, item) for index, item in enumerate(items)
              if SINGLE_LABEL.fullmatch(item[1])]
    clusters: list[list[tuple[int, tuple[int, str, Rect]]]] = []
    for candidate in labels:
        left = candidate[1][2].left
        cluster = next((group for group in clusters
                        if abs(group[0][1][2].left - left) <= 35), None)
        if cluster is None:
            clusters.append([candidate])
        else:
            cluster.append(candidate)
    if not clusters:
        return items
    group = max(clusters, key=lambda entries: len({item[1][1].strip().upper().rstrip('.、．:：)）')
                                                   for item in entries}))
    if len(group) < 2:
        return items
    consumed = set()
    merged = []
    for label_index, (_, letter, box) in group:
        center_y = box.top + box.height / 2
        choices = []
        for text_index, (_, value, text_box) in enumerate(items):
            if text_index == label_index or text_index in consumed:
                continue
            if SINGLE_LABEL.fullmatch(value) or OPTION.match(value):
                continue
            gap = text_box.left - (box.left + box.width)
            if not 3 <= gap <= 130:
                continue
            if abs(text_box.top + text_box.height / 2 - center_y) > max(16, box.height * 0.7):
                continue
            choices.append((gap, text_index, value, text_box))
        if not choices:
            continue
        _, text_index, value, text_box = min(choices)
        consumed.update((label_index, text_index))
        right = max(box.left + box.width, text_box.left + text_box.width)
        bottom = max(box.top + box.height, text_box.top + text_box.height)
        merged.append((min(box.top, text_box.top),
                       f"{SINGLE_LABEL.fullmatch(letter).group(1).upper()}. {value}",
                       Rect(box.left, min(box.top, text_box.top), right - box.left,
                            bottom - min(box.top, text_box.top))))
    if len(merged) < 2:
        return items
    return sorted([item for index, item in enumerate(items) if index not in consumed] + merged,
                  key=lambda item: item[0])


class OCREngine:
    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from paddleocr import PaddleOCR
            options = {}
            bundle = Path(getattr(sys, "_MEIPASS", "")) / "ocr_models"
            if bundle.is_dir():
                # Paddle 2.x opens model files through a narrow Windows C++ path.
                # A PyInstaller bundle below a non-ASCII directory can therefore
                # contain valid files that Paddle cannot open.
                drive = os.environ.get("SystemDrive", "C:")
                cache_id = hashlib.sha256(str(Path(sys.executable).resolve()).encode("utf-8")).hexdigest()[:16]
                cache = Path(drive + "\\ProgramData") / "AI_AutoAnswer" / cache_id / "ocr_models"
                for kind in ("det", "rec", "cls"):
                    folder = bundle / kind
                    if not (folder / "inference.pdmodel").is_file():
                        raise RuntimeError(f"Bundled OCR {kind} model is missing")
                    target = cache / kind
                    if not (target / "inference.pdmodel").is_file():
                        try:
                            shutil.copytree(folder, target, dirs_exist_ok=True)
                        except OSError as exc:
                            raise RuntimeError(f"Cannot prepare OCR model cache at {target}: {exc}") from exc
                    options[f"{kind}_model_dir"] = str(target)
            self._engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False, **options)
        return self._engine

    def read(self, capture: Capture) -> ObservedQuestion | None:
        image = preprocess(capture.image)
        lines = self._get_engine().ocr(image, cls=True)
        if not lines or not lines[0]:
            return None
        items = []
        for box, (text, confidence) in lines[0]:
            if confidence < 0.55:
                continue
            xs, ys = zip(*box)
            local = Rect(int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys)))
            screen = Rect(capture.screen_rect.left + local.left,
                          capture.screen_rect.top + local.top, local.width, local.height)
            items.append((local.top, text.strip(), screen))
        items.sort(key=lambda item: item[0])
        items = merge_split_option_boxes(items)
        if any(FINISH.match(text) for _, text, _ in items) and not any(OPTION.match(text) for _, text, _ in items):
            return ObservedQuestion("", "unknown", source="ocr", finished=True)
        options = {}
        next_rect = None
        for _, text, rect in items:
            match = OPTION.match(text)
            if match:
                label, value = match.groups()
                options[label.upper()] = LocatedOption(label.upper(), value.strip(), rect)
            elif NEXT.match(text):
                next_rect = rect
        if len(options) < 2:
            return None
        first_top = min(option.rect.top for option in options.values())
        question, kind = current_question([(rect.top, text) for _, text, rect in items
                                           if rect.top < first_top and not FINISH.search(text)])
        if not question:
            return None
        return ObservedQuestion(question, kind, options, next_rect, source="ocr")
