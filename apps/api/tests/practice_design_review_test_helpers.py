from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_review_models import (
    REVIEW_DIMENSIONS,
    PracticeDesignReviewResult,
)


def source_document(
    source_path: str = "lecture-01.md", *, text: str = "Source evidence."
) -> CanvasDocument:
    return CanvasDocument(
        id="course-01-lecture-01",
        course_id="course-01",
        lecture_id="lecture-01",
        title="Source evidence",
        source_kind="markdown",
        source_ref=source_path,
        workspace_path="source.json",
        sections=[
            {
                "id": "source-evidence",
                "title": "Source evidence",
                "source_ref": source_path,
                "blocks": [{"id": "evidence", "type": "paragraph", "text": text}],
            }
        ],
    )


def passing_review() -> PracticeDesignReviewResult:
    return PracticeDesignReviewResult(
        checks=[
            {
                "dimension": dimension,
                "severity": "pass",
                "summary": f"No material {dimension} issue found.",
                "target_ids": [],
                "supporting_anchors": [],
            }
            for dimension in REVIEW_DIMENSIONS
        ]
    )
