from fastapi import HTTPException

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.quiz_identity import canonical_quiz_id, is_quiz_block, validate_unique_quiz_ids


def quiz_block(document: CanvasDocument, block_id: str) -> CanvasBlock:
    validate_unique_quiz_ids(document)
    matches = [
        block
        for section in document.sections
        for block in section.blocks
        if canonical_quiz_id(block) == block_id
    ]
    quizzes = [block for block in matches if is_quiz_block(block)]
    if quizzes:
        return quizzes[0]
    if matches:
        raise HTTPException(status_code=400, detail="Canvas block is not a quiz component.")
    raise HTTPException(status_code=404, detail="Quiz block not found.")


def quiz_feedback(correct: bool | None) -> str:
    if correct is True:
        return "Correct. Explain why this option fits the concept before moving on."
    if correct is False:
        return (
            "Review the explanation above, explain why your choice does not fit, "
            "then try a correction."
        )
    return "Your answer was stored. Discuss the reasoning with the tutor."
