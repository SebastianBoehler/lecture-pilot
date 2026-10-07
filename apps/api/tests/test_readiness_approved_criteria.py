from lecturepilot.exam_readiness import build_exam_readiness_check, public_exam_readiness_check
from lecturepilot.learning_map_models import LearningMap, LearningMapGate, LearningMapNode
from test_exam_readiness import _document


def map_for_document(document):
    gates = [
        LearningMapGate.create(
            id=block.id,
            concept_id=section.id,
            title=section.title,
            prompt=block.text,
            section_id=section.id,
            source_ref=section.source_ref,
            evidence_criteria=[
                {"id": "required", "description": "Explains the evidence-to-decision link."},
                {"id": "extra", "description": "Optional enrichment.", "required": False},
            ],
            transfer_prompt="SECRET transfer task",
            independent_exit_task="SECRET exit task",
            review_after_days=2,
        )
        for section in document.sections
        for block in section.blocks
        if block.type == "checkpoint"
    ]
    return LearningMap.create(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        title=document.title,
        objective="Explain decisions.",
        gates=gates,
        nodes=[
            LearningMapNode(
                id=section.id,
                title=section.title,
                lecture_id=document.lecture_id,
                section_id=section.id,
                prerequisites=[],
                quiz_ids=[],
                gate_ids=[gate.id for gate in gates if gate.section_id == section.id],
            )
            for section in document.sections
        ],
    )


def test_readiness_uses_published_required_criteria_without_exposing_hidden_tasks():
    document = _document("lecture-01", "Evidence", with_quiz=False)
    check = build_exam_readiness_check(
        course_id=document.course_id,
        documents=[document],
        lectures=[],
        learning_maps=[map_for_document(document)],
    )
    assert check.questions[0].rubric == ["Explains the evidence-to-decision link."]
    assert "connects evidence" in check.questions[0].source_excerpt
    public = public_exam_readiness_check(check).model_dump_json()
    assert "source_excerpt" not in public
    assert "required" not in public and "SECRET" not in public
