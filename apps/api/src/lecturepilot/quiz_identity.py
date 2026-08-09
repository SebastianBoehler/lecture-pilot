from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument


class DuplicateCanonicalQuizIdError(ValueError):
    def __init__(self, quiz_id: str) -> None:
        self.quiz_id = quiz_id
        super().__init__(f"Duplicate canonical quiz ID '{quiz_id}'.")


def canonical_quiz_id(block: CanvasBlock) -> str:
    return block.component_id or block.id


def is_quiz_block(block: CanvasBlock) -> bool:
    return block.type == "quiz" or (
        block.type == "component" and block.component_type == "single_choice_quiz"
    )


def validate_unique_quiz_ids(document: CanvasDocument) -> None:
    seen: set[str] = set()
    for section in document.sections:
        for block in section.blocks:
            if not is_quiz_block(block):
                continue
            quiz_id = canonical_quiz_id(block)
            if quiz_id in seen:
                raise DuplicateCanonicalQuizIdError(quiz_id)
            seen.add(quiz_id)
