from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class AnswerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_question: bool
    question_type: Literal["single", "multiple", "unknown"]
    answers: list[str]
    can_answer: bool

    @model_validator(mode="after")
    def valid_shape(self):
        self.answers = [answer.upper().strip() for answer in self.answers]
        if self.question_type == "single" and len(self.answers) > 1:
            raise ValueError("Single choice answer has multiple labels")
        if self.question_type == "multiple" and self.can_answer and len(self.answers) < 2:
            raise ValueError("Multiple choice requires at least two labels")
        if len(self.answers) != len(set(self.answers)):
            raise ValueError("Duplicate answer labels")
        if not self.can_answer and self.answers:
            raise ValueError("Unanswerable question cannot contain answers")
        return self


def validate_answer(payload: AnswerPayload, observed_options: dict[str, str]) -> list[str]:
    if not payload.is_question or not payload.can_answer or not payload.answers:
        raise ValueError("Question cannot be answered safely")
    if payload.question_type == "unknown":
        raise ValueError("Unknown question type")
    observed = {key.upper(): value.strip() for key, value in observed_options.items()}
    for label in payload.answers:
        if label not in observed:
            raise ValueError(f"Answer {label} is absent from observed options")
    return payload.answers
