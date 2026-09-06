from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_review_models import (
    PracticeDesignQualityReview,
    PracticeDesignReviewResult,
)


def with_quality_review(
    design: PracticeDesign, result: PracticeDesignReviewResult
) -> PracticeDesign:
    review = PracticeDesignQualityReview.bind(
        result,
        source_revision=design.source_revision,
        practice_design_revision=design.revision,
    )
    return PracticeDesign.model_validate(
        {**design.model_dump(mode="python"), "quality_review": review.model_dump(mode="python")}
    )
