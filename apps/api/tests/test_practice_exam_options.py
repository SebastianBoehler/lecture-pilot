import pytest

from lecturepilot.practice_exam_validation import (
    PracticeExamValidationError,
    validate_practice_exam,
)
from test_practice_exam_review import _review, _validate
from test_practice_exam_validation import _exam


@pytest.mark.parametrize(
    "options",
    [
        ["2/10", "3/15", "3/10", "1/4"],
        [r"$\frac{2}{10}$", r"$\dfrac{3}{15}$", "3/10", "1/4"],
        ["0.2", ".20", "0.3", "0.4"],
        ["-1/2", "-0.5", "1/2", "0"],
    ],
)
def test_exam_rejects_equivalent_numeric_choices(options):
    exam = _exam()
    exam.questions[0].options = options
    with pytest.raises(PracticeExamValidationError, match="numerically equivalent"):
        validate_practice_exam(
            exam,
            authoritative_source_ids={"lecture-01:risk"},
            question_count=20,
            selected_ppi_source_ids={"ppi-42"},
        )


def test_exam_accepts_distinct_numeric_choices():
    exam = _exam()
    exam.questions[0].options = ["2/15", "3/15", "3/10", "1/4"]
    validate_practice_exam(
        exam,
        authoritative_source_ids={"lecture-01:risk"},
        question_count=20,
        selected_ppi_source_ids={"ppi-42"},
    )


def test_review_cannot_pass_equivalent_numeric_choices(monkeypatch):
    exam = _exam()
    exam.questions[0].options = ["2/10", "3/15", "3/10", "1/4"]
    monkeypatch.setattr("test_practice_exam_review._exam", lambda: exam)
    with pytest.raises(PracticeExamValidationError, match="numerically equivalent"):
        _validate(_review())
