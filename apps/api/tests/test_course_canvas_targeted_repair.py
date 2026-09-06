from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import confirm_source_routing, professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.client_contract import CLIENT_CONTRACT_HEADER, CLIENT_CONTRACT_VERSION
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from practice_design_test_helpers import save_approved_design, write_manifest
from targeted_repair_test_helpers import invalid_candidate
from authoring_test_helpers import assigned_drafts, install_author
from pydantic_ai.messages import ModelResponse, ToolCallPart


def test_ai_repair_replaces_only_the_failed_block_and_preserves_neighboring_sections(
    tmp_path: Path,
    monkeypatch,
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
    calls = 0

    class Reviewer:
        async def complete_review(self, **kwargs):
            return {"issues": []}

    def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "edit",
                        {
                            "path": assigned_drafts(info)[0],
                            "old": r"The score is computed as w^\top x.",
                            "new": r"w^\top x",
                        },
                    )
                ]
            )
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    install_author(client, monkeypatch, respond, Reviewer())
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
    assert repaired.status_code == 200, repaired.text
    assert calls == 2
    status = client.get(
        path + "/status",
        headers={
            **professor_headers(),
            "Idempotency-Key": "targeted-repair-success-0001",
        },
    )
    assert status.status_code == 200
    assert status.json()["authoring_metrics"]["repair_edits"] == 1
    other_owner = client.post(
        path + "/cancel",
        headers={
            **professor_headers("other-professor"),
            **_client_contract_headers(),
            "Idempotency-Key": "targeted-repair-success-0001",
        },
    )
    assert other_owner.status_code == 404
    payload = repaired.json()
    expected_blocks = [b.model_dump(mode="json") for b in planner.candidate.sections[1].blocks]
    for block in expected_blocks:
        if block["text"]:
            block["text"] = block["text"].strip()
    assert payload["sections"][1]["blocks"] == expected_blocks
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


class _TargetedRepairPlanner:
    def __init__(self) -> None:
        self.candidate: CanvasDocument | None = None

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        practice_design,
        repair_context: str | None = None,
        output_language: str,
    ) -> CanvasDocument:
        if repair_context is not None:
            raise AssertionError("A block-addressable failure must not regenerate the full draft.")
        self.candidate = _candidate_with_practice_design(
            invalid_candidate(source_document), practice_design
        )
        error = CanvasGenerationRepairableError(
            "Math block optimization-math in Optimization contains explanatory prose; "
            "move that text to a paragraph or callout block."
        )
        error.candidate = self.candidate
        error.section_id = "learning-optimization"
        error.block_id = "optimization-math"
        raise error


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
The evidence states that the score is the inner product of the transposed weight vector and the input.
\\end{frame}
\\begin{frame}{Summary}
The weight and input vectors must have matching dimensions for the inner product.
\\end{frame}
""",
            )
        },
        headers=professor_headers(),
    )
    assert upload.status_code == 200
    confirm_source_routing(client, "targeted-repair")
    write_manifest(
        client.app.state.canvas_workspace.layout,
        course_id="targeted-repair",
        lecture_id="lecture-01",
        source_path="Lecture01.tex",
    )
    save_approved_design(
        client.app.state.canvas_workspace.layout,
        course_id="targeted-repair",
        lecture_id="lecture-01",
        source_path="Lecture01.tex",
    )
    return client


def _client_contract_headers() -> dict[str, str]:
    return {CLIENT_CONTRACT_HEADER: CLIENT_CONTRACT_VERSION}


def _candidate_with_practice_design(candidate: CanvasDocument, practice_design) -> CanvasDocument:
    first = candidate.sections[0]
    checkpoints = [
        CanvasBlock(id=f"practice-{target.id}", type="checkpoint", text=target.baseline_task)
        for target in practice_design.targets
    ]
    return candidate.model_copy(
        update={
            "sections": [
                first.model_copy(update={"blocks": [*first.blocks, *checkpoints]}),
                *candidate.sections[1:],
            ]
        }
    )
