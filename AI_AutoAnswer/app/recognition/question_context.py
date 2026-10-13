"""Select the active question without page headers or progress summaries."""
import re


STEM = re.compile(r"^\s*\d{1,3}\s*[.、．:：)）]\s*\S+")
HEADING = re.compile(r"^\s*(?:模拟练习|练习)\s*第\s*\d+\s*题")
TYPE_TAG = re.compile(r"^\s*(单选题|多选题|单选|多选)\s*$")
MULTIPLE = re.compile(r"多选|选择所有|至少两|选择两|选择三")


def current_question(lines: list[tuple[int, str]]) -> tuple[str, str]:
    """Return (stem, locally displayed type), with the last numbered stem winning."""
    ordered = sorted((y, value.strip()) for y, value in lines if value.strip())
    if not ordered:
        return "", "unknown"
    candidates = [index for index, (_, value) in enumerate(ordered)
                  if STEM.match(value) or HEADING.match(value)]
    if candidates:
        index = candidates[-1]
    else:
        candidates = [index for index, (_, value) in enumerate(ordered)
                      if not TYPE_TAG.fullmatch(value)]
        if not candidates:
            return "", "unknown"
        index = candidates[-1]
    chunks = [ordered[index][1]]
    last_y = ordered[index][0]
    for y, value in ordered[index + 1:]:
        if y - last_y > 50 or TYPE_TAG.fullmatch(value):
            break
        chunks.append(value)
        last_y = y
    question = "\n".join(chunks)
    # A type chip immediately above the stem belongs to this question. A
    # distant page summary (for example "20 单选 + 10 多选") does not.
    nearby = [value for y, value in ordered[:index]
              if ordered[index][0] - y <= 100 and TYPE_TAG.fullmatch(value)]
    tag = nearby[-1] if nearby else ""
    if tag:
        kind = "multiple" if "多选" in tag else "single"
    elif MULTIPLE.search(question):
        kind = "multiple"
    elif "单选" in question:
        kind = "single"
    else:
        kind = "unknown"
    return question, kind
