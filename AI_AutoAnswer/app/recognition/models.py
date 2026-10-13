from dataclasses import dataclass, field
import hashlib

from app.automation.coordinate_mapper import Rect


@dataclass
class LocatedOption:
    label: str
    text: str
    rect: Rect
    control: object | None = None
    selected: bool | None = None


@dataclass
class ObservedQuestion:
    question: str
    question_type: str
    options: dict[str, LocatedOption] = field(default_factory=dict)
    next_rect: Rect | None = None
    next_control: object | None = None
    source: str = "unknown"
    finished: bool = False

    @property
    def fingerprint(self) -> str:
        content = self.question + "|" + "|".join(
            f"{label}:{opt.text}" for label, opt in sorted(self.options.items()))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @property
    def option_text(self) -> dict[str, str]:
        return {label: option.text for label, option in self.options.items()}
