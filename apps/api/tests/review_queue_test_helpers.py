from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import CoachingProgress, DelayedReview
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.exam_revision_plan import ExamRevisionTask
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture

COURSE_ID = "review-course"
NOW = datetime.now(UTC)


def review_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    lectures = [
        Lecture(id="lecture-a", course_id=COURSE_ID, title="Lecture A", date=date(2020, 1, 1)),
        Lecture(id="lecture-b", course_id=COURSE_ID, title="Lecture B", date=date(2020, 1, 2)),
        Lecture(id="lecture-locked", course_id=COURSE_ID, title="Locked", date=date(2099, 1, 1)),
        Lecture(
            id="lecture-unpublished",
            course_id=COURSE_ID,
            title="Unpublished",
            date=date(2020, 1, 3),
        ),
    ]
    write_course_workspace(
        app.state.canvas_workspace.course_media_root(COURSE_ID),
        CourseWorkspaceResult(
            course=Course(id=COURSE_ID, title="Review", professor="Professor", term="2026"),
            lectures=lectures,
            active_lecture_id="lecture-a",
        ),
    )
    for lecture_id, section_id, gate_id, label in (
        ("lecture-a", "section-a", "gate-a", "A"),
        ("lecture-b", "section-b", "gate-b", "B"),
        ("lecture-locked", "section-locked", "gate-locked", "Locked"),
    ):
        document = published_course_canvas(COURSE_ID, lecture_id)
        blocks = [CanvasBlock(id=gate_id, type="checkpoint", text=f"Explain {label}.")]
        if lecture_id == "lecture-a":
            blocks.append(CanvasBlock(id="gate-c", type="checkpoint", text="Explain C."))
        document.sections[0] = document.sections[0].model_copy(
            update={
                "id": section_id,
                "title": f"Section {label}",
                "blocks": blocks,
            }
        )
        app.state.canvas_workspace.write_course_canvas(document)
        path = app.state.canvas_workspace.course_canvas_store.path(COURSE_ID, lecture_id)
        learning_map = app.state.canvas_workspace.course_canvas_store.learning_map(
            course_id=COURSE_ID, lecture_id=lecture_id
        )
        assert learning_map is not None
        for index, gate in enumerate(learning_map.gates):
            gate_label = "C" if gate.id == "gate-c" else label
            learning_map.gates[index] = gate.model_copy(
                update={"transfer_prompt": f"Apply {gate_label} to an unfamiliar case."}
            )
        (path / "learning-map.json").write_text(
            learning_map.model_dump_json(indent=2), encoding="utf-8"
        )
    return TestClient(app)


def write_review(
    client: TestClient, user_id: str, lecture_id: str, gate_id: str, due_at: datetime
) -> None:
    progress = read_progress(client, user_id, lecture_id)
    progress.delayed_reviews[gate_id] = DelayedReview(
        gate_id=gate_id,
        gate_revision=gate_revision(client, lecture_id, gate_id),
        scheduled_at=(due_at - timedelta(days=2)).isoformat(),
        due_at=due_at.isoformat(),
    )
    write_progress(client, user_id, lecture_id, progress)


def write_readiness_task(client: TestClient, user_id: str, course_id: str = COURSE_ID) -> None:
    task = ExamRevisionTask(
        id="repair-risk",
        question_id="question-risk",
        kind="review_wrong_mc",
        guidance_level="standard",
        lecture_id="lecture-a",
        lecture_title="Lecture A",
        section_id="section-a",
        section_title="Section A",
        prompt="Which hidden option was correct?",
        rubric=["Name the hidden answer."],
        expected_evidence="Name the hidden answer.",
        next_action="Revisit Section A and explain the choice.",
    )
    path = client.app.state.canvas_workspace.layout.user_course_root(user_id, course_id)
    atomic_write_json(
        path / "progress.json",
        {
            "attempts": [],
            "active_tasks": [task.model_dump(mode="json")],
            "updated_at": NOW.isoformat(),
        },
    )


def gate_revision(client: TestClient, lecture_id: str, gate_id: str) -> str:
    learning_map = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id=COURSE_ID, lecture_id=lecture_id
    )
    assert learning_map is not None
    return next(gate.revision for gate in learning_map.gates if gate.id == gate_id)


def read_progress(client: TestClient, user_id: str, lecture_id: str) -> CoachingProgress:
    return CoachingProgressStore(client.app.state.canvas_workspace.layout).read(
        user_id=user_id, course_id=COURSE_ID, lecture_id=lecture_id
    )


def write_progress(
    client: TestClient, user_id: str, lecture_id: str, progress: CoachingProgress
) -> None:
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(user_id, COURSE_ID, lecture_id)
        / "tutor-state.json"
    )
    atomic_write_json(path, progress.model_dump(mode="json"))
