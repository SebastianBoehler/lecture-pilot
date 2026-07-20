from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.client_contract import CLIENT_CONTRACT_HEADER, CLIENT_CONTRACT_VERSION
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError


def test_ai_repair_replaces_only_the_failed_block_and_preserves_neighboring_sections(
    tmp_path: Path,
) -> None:
    client = _course_client(tmp_path)
    planner = _TargetedRepairPlanner()
    client.app.state.course_planner = planner
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"

    failed = client.post(
        path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-repair-failure-0001",
        },
    )
    repaired = client.post(
        f"{path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-repair-success-0001",
        },
    )

    assert failed.status_code == 503
    assert failed.headers["X-Generation-Repairable"] == "true"
    assert repaired.status_code == 200
    assert planner.full_repair_called is False
    assert planner.targeted_repair_calls == [
        (
            "learning-optimization",
            "optimization-math",
            "Math block optimization-math in Optimization contains explanatory prose; "
            "move that text to a paragraph or callout block.",
        )
    ]
    assert planner.repaired_document is not None
    assert planner.repaired_document.sections[1] == planner.candidate.sections[1]
    payload = repaired.json()
    repaired_blocks = payload["sections"][0]["blocks"]
    assert [block["type"] for block in repaired_blocks[1:3]] == ["paragraph", "math"]
    assert repaired_blocks[2]["text"] == r"w^\top x"


def test_ai_repair_refuses_a_candidate_from_an_older_source_revision(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    planner = _TargetedRepairPlanner()
    client.app.state.course_planner = planner
    path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"
    failed = client.post(
        path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-repair-stale-failure-0001",
        },
    )
    update = client.post(
        "/admin/courses/targeted-repair/updates",
        headers=professor_headers(),
    )
    assert update.status_code == 200
    update_id = update.json()["update_id"]
    staged = client.post(
        f"/admin/courses/targeted-repair/updates/{update_id}/materials",
        data={"path": "Lecture01.tex"},
        files={
            "file": (
                "Lecture01.tex",
                b"""
\\title{Targeted repair revised}
\\begin{frame}{Optimization revised}
The revised source changes the formula evidence used by this lecture.
\\end{frame}
""",
            )
        },
        headers=professor_headers(),
    )
    assert staged.status_code == 200
    analysis = client.get(
        f"/admin/courses/targeted-repair/updates/{update_id}",
        headers=professor_headers(),
    )
    assert analysis.status_code == 200
    updated = client.post(
        f"/admin/courses/targeted-repair/updates/{update_id}/apply",
        headers=professor_headers(),
        json={
            "lectures": [
                {
                    "lecture_id": "lecture-01",
                    "number": "01",
                    "title": "Optimization revised",
                    "date": "2026-05-06",
                    "file_paths": ["Lecture01.tex"],
                }
            ]
        },
    )
    repaired = client.post(
        f"{path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-repair-stale-attempt-0001",
        },
    )

    assert failed.status_code == 503
    assert updated.status_code == 200
    assert repaired.status_code == 409
    assert repaired.json()["detail"] == (
        "Lecture source changed after this failure. Generate a new draft before repairing it."
    )
    assert planner.targeted_repair_calls == []


class _TargetedRepairPlanner:
    def __init__(self) -> None:
        self.candidate: CanvasDocument | None = None
        self.repaired_document: CanvasDocument | None = None
        self.full_repair_called = False
        self.targeted_repair_calls: list[tuple[str, str | None, str]] = []

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        repair_context: str | None = None,
        output_language: str,
    ) -> CanvasDocument:
        if repair_context is not None:
            self.full_repair_called = True
            raise AssertionError("A block-addressable failure must not regenerate the full draft.")
        self.candidate = _invalid_candidate(source_document)
        error = CanvasGenerationRepairableError(
            "Math block optimization-math in Optimization contains explanatory prose; "
            "move that text to a paragraph or callout block."
        )
        error.candidate = self.candidate
        error.section_id = "learning-optimization"
        error.block_id = "optimization-math"
        raise error

    async def repair_section(
        self,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
        *,
        section_id: str,
        block_id: str | None,
        failure_context: str,
        output_language: str,
    ) -> CanvasDocument:
        self.targeted_repair_calls.append((section_id, block_id, failure_context))
        section = candidate_document.sections[0]
        blocks = [
            section.blocks[0],
            CanvasBlock(
                id="optimization-math-explanation",
                type="paragraph",
                text="The transpose turns the weight vector into the matching row vector.",
            ),
            CanvasBlock(id="optimization-math", type="math", text=r"w^\top x"),
            *section.blocks[2:],
        ]
        repaired = section.model_copy(update={"blocks": blocks})
        self.repaired_document = candidate_document.model_copy(
            update={"sections": [repaired, candidate_document.sections[1]]}
        )
        return self.repaired_document


def _invalid_candidate(source_document: CanvasDocument) -> CanvasDocument:
    detail = (
        "This source-grounded explanation connects the definition to the optimization "
        "procedure, its assumptions, and the practical consequence for model training. "
    )
    first = CanvasSection(
        id="learning-optimization",
        title="Optimization",
        source_ref="Lecture01.tex frame 1",
        blocks=[
            CanvasBlock(id="optimization-intro", type="paragraph", text=detail * 2),
            CanvasBlock(
                id="optimization-math",
                type="math",
                text=r"The score is computed as w^\top x.",
            ),
            CanvasBlock(id="optimization-example", type="callout", text=detail * 2),
            CanvasBlock(id="optimization-steps", type="paragraph", text=detail * 2),
            CanvasBlock(
                id="optimization-check",
                type="quiz",
                text="What does the transpose accomplish?",
                items=["It aligns dimensions", "It removes the weights"],
                answer_index=0,
            ),
        ],
    )
    second = CanvasSection(
        id="learning-summary",
        title="Summary",
        source_ref="Lecture01.tex frame 1",
        blocks=[
            CanvasBlock(id="summary-1", type="paragraph", text=detail * 2),
            CanvasBlock(id="summary-2", type="paragraph", text=detail * 2),
            CanvasBlock(id="summary-3", type="callout", text=detail * 2),
            CanvasBlock(id="summary-4", type="paragraph", text=detail * 2),
            CanvasBlock(
                id="summary-quiz",
                type="quiz",
                text="Which expression is dimensionally valid?",
                items=[r"w^\top x", "wx"],
                answer_index=0,
            ),
        ],
    )
    return source_document.model_copy(
        update={
            "source_kind": "generated",
            "source_ref": "Lecture01.tex",
            "sections": [first, second],
        }
    )


def _course_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    client = TestClient(app)
    created = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Targeted Repair",
            "lecture_number": "01",
            "lecture_title": "Optimization",
        },
        headers=professor_headers(),
    )
    assert created.status_code == 200
    upload = client.post(
        "/admin/courses/targeted-repair/materials",
        data={"path": "Lecture01.tex"},
        files={
            "file": (
                "Lecture01.tex",
                b"""
\\title{Targeted repair}
\\begin{frame}{Optimization}
The score is the inner product of the transposed weight vector and the input.
\\end{frame}
""",
            )
        },
        headers=professor_headers(),
    )
    assert upload.status_code == 200
    return client


def _client_contract_headers() -> dict[str, str]:
    return {CLIENT_CONTRACT_HEADER: CLIENT_CONTRACT_VERSION}
