from enum import Enum


class RunState(str, Enum):
    IDLE = "IDLE"
    CAPTURE = "CAPTURE"
    RECOGNIZE = "RECOGNIZE"
    REQUEST_AI = "REQUEST_AI"
    ANALYZE = "REQUEST_AI"
    LOCATE = "LOCATE"
    CLICK = "CLICK"
    SELECT = "CLICK"
    VERIFY = "VERIFY"
    NEXT = "NEXT"
    WAIT = "WAIT"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


ORDER = [RunState.CAPTURE, RunState.RECOGNIZE, RunState.ANALYZE,
         RunState.LOCATE, RunState.SELECT, RunState.VERIFY,
         RunState.NEXT, RunState.WAIT]


class StateMachine:
    def __init__(self):
        self.state = RunState.CAPTURE

    def advance(self, next_state: RunState) -> None:
        if next_state in (RunState.PAUSED, RunState.STOPPED, RunState.ERROR, RunState.FINISHED):
            self.state = next_state
            return
        if self.state in (RunState.PAUSED, RunState.STOPPED):
            if next_state != RunState.CAPTURE:
                raise ValueError("Resume must revalidate from capture")
        elif ORDER[(ORDER.index(self.state) + 1) % len(ORDER)] != next_state:
            raise ValueError(f"Unsafe state transition: {self.state} -> {next_state}")
        self.state = next_state
