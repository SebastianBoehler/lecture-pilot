from typing import Literal

MAX_APPROVED_TASK_LENGTH = 2_000
AssistanceLevel = Literal["none", "prompt", "cue", "faded_example", "worked_step"]
AssessmentStage = Literal[
    "diagnostic",
    "diagnostic_support",
    "independent_exit",
    "exit_support",
    "delayed_transfer",
    "delayed_support",
]
HintLevel = Literal["prompt", "cue", "faded_example", "worked_step"]
