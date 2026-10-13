import pytest

from app.ai.schema import AnswerPayload, validate_answer
from app.automation.coordinate_mapper import Rect, screenshot_to_screen
from app.core.state_machine import RunState, StateMachine


def test_coordinate_mapping_handles_negative_monitor_origin_and_scaling():
    assert screenshot_to_screen((100, 50), Rect(-1800, 120, 800, 600), (1600, 1200)) == (-1750, 145)


def test_answer_must_match_observed_options():
    payload = AnswerPayload.model_validate({
        "is_question": True, "question_type": "single", "answers": ["C"],
        "can_answer": True,
    })
    with pytest.raises(ValueError):
        validate_answer(payload, {"A": "one", "B": "two"})


def test_single_answer_rejects_multiple_choices():
    with pytest.raises(ValueError):
        AnswerPayload.model_validate({
            "is_question": True, "question_type": "single", "answers": ["A", "B"],
            "can_answer": True,
        })


def test_state_machine_rejects_unsafe_transition():
    machine = StateMachine()
    machine.advance(RunState.RECOGNIZE)
    with pytest.raises(ValueError):
        machine.advance(RunState.SELECT)
