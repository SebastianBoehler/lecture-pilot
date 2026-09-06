from collections.abc import Sequence
import hashlib

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_canvas_approved_checkpoints import section_practice_targets
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_practice_design_evidence import target_source_anchors
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeTarget


def practice_support_evidence(targets: Sequence[PracticeTarget]) -> str:
    """Exact approved teaching evidence, never hidden task wording or model-authored answers."""
    anchors = {}
    for target in targets:
        for anchor in target_source_anchors(target):
            anchors[(anchor.source_path, anchor.excerpt)] = anchor
    packet = "\n\n".join(
        f"APPROVED TASK SUPPORTING SOURCE {anchor.source_path}\n{anchor.excerpt}"
        for anchor in anchors.values()
    )
    if len(packet) > 24_000:
        raise CanvasGenerationRepairableError(
            "Approved practice evidence exceeds the section context limit; review the target scope."
        )
    return packet


def source_for_practice_review(
    source: CanvasDocument, candidate: CanvasDocument, design: PracticeDesign
) -> CanvasDocument:
    """Add cross-section support to the critic's private evidence view, not course files."""
    supplements: dict[str, list[CanvasBlock]] = {}
    for section in candidate.sections:
        packet = practice_support_evidence(section_practice_targets(section, design))
        if not packet:
            continue
        matched = next(
            (
                item
                for item in source.sections
                if item.source_ref and item.source_ref in (section.source_ref or "")
            ),
            None,
        )
        if matched is None:
            raise CanvasGenerationRepairableError(
                "Practice review cannot match the generated section to its source evidence.",
                section_id=section.id,
            )
        block_id = "practice-support-" + hashlib.sha256(section.id.encode()).hexdigest()[:16]
        supplements.setdefault(matched.id, []).append(
            CanvasBlock(id=block_id, type="paragraph", text=packet)
        )
    return source.model_copy(
        update={
            "sections": [
                section.model_copy(update={"blocks": supplements[section.id] + section.blocks})
                if section.id in supplements
                else section
                for section in source.sections
            ]
        }
    )
