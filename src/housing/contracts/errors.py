from typing import Literal

type ErrorCode = Literal[
    "DATA_INVALID",
    "DATA_INCOMPLETE",
    "AGENT_OUTPUT_INVALID",
    "AGENT_POLICY_ERROR",
    "BUDGET_EXCEEDED",
    "REPLAY_MISS",
    "TOOL_ERROR",
    "MODEL_UNAVAILABLE",
]


class HousingError(Exception):
    def __init__(self, code: ErrorCode, message: str, stage: str = "validation"):
        self.code = code
        self.message = message
        self.stage = stage
        super().__init__(f"{code}: {message}")
