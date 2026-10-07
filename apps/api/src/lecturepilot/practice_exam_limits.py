"""Fixed request and token bounds for one student-triggered exam generation."""

from contextlib import contextmanager

from lecturepilot.authoring_limits import authoring_budget

EXAM_REQUEST_LIMIT = 24
EXAM_INPUT_TOKEN_LIMIT = 500_000
EXAM_OUTPUT_TOKEN_LIMIT = 80_000
EXAM_RESERVED_TOKENS = EXAM_INPUT_TOKEN_LIMIT + EXAM_OUTPUT_TOKEN_LIMIT
EXAM_DEADLINE_SECONDS = 15 * 60


@contextmanager
def practice_exam_budget():
    with authoring_budget(
        request_limit=EXAM_REQUEST_LIMIT,
        input_tokens_limit=EXAM_INPUT_TOKEN_LIMIT,
        output_tokens_limit=EXAM_OUTPUT_TOKEN_LIMIT,
    ) as budget:
        yield budget
