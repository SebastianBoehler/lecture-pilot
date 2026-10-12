from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import (
    configure_canvas_workspace,
    publish_course_canvas,
    published_course_canvas,
)
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.lecture_access_models import LectureAccessRule
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture

COURSE_ID = "study-course"
PAST = date(2020, 1, 1)
FUTURE = date(2099, 1, 1)
HIDDEN_EVIDENCE = "zebracheckpointevidence"
HIDDEN_QUIZ = "zebraquizoption"


def learner(user_id: str = "student-a") -> dict[str, str]:
    return student_headers(user_id, course_ids=[COURSE_ID])


def study_client(tmp_path: Path) -> TestClient:
    app = create_app()
    configure_canvas_workspace(
        app,
        CanvasWorkspace(
            workspace_root=tmp_path / "workspaces",
            material_root=tmp_path / "materials",
        ),
    )
    lectures = [
        Lecture(id="lecture-open", course_id=COURSE_ID, title="Bayes basics", date=PAST),
        Lecture(id="lecture-two", course_id=COURSE_ID, title="Risk", date=PAST),
        Lecture(id="lecture-locked", course_id=COURSE_ID, title="Future", date=FUTURE),
        Lecture(
            id="lecture-hidden",
            course_id=COURSE_ID,
            title="Hidden",
            date=PAST,
            access_override=LectureAccessRule(publication_mode="hidden"),
        ),
        Lecture(id="lecture-unpublished", course_id=COURSE_ID, title="Draft", date=PAST),
    ]
    write_course_workspace(
        app.state.canvas_workspace.course_media_root(COURSE_ID),
        CourseWorkspaceResult(
            course=Course(id=COURSE_ID, title="Study", professor="Professor", term="2026"),
            lectures=lectures,
            active_lecture_id="lecture-open",
        ),
    )
    for lecture_id in ("lecture-open", "lecture-two", "lecture-locked", "lecture-hidden"):
        document = published_course_canvas(COURSE_ID, lecture_id)
        document.sections[0].blocks = [
            CanvasBlock(
                id="intro-p",
                type="paragraph",
                text=f"The **posterior** combines prior and likelihood in {lecture_id}.",
            ),
            CanvasBlock(id="risk-check", type="checkpoint", text=f"Name {HIDDEN_EVIDENCE}."),
            CanvasBlock(
                id="intro-quiz",
                type="quiz",
                text="Pick one.",
                items=[HIDDEN_QUIZ, "Other"],
                answer_index=0,
            ),
        ]
        if lecture_id == "lecture-two":
            document.sections.append(
                CanvasSection(
                    id="posterior-risk",
                    title="Posterior risk",
                    source_ref="test fixture",
                    blocks=[CanvasBlock(id="risk-p", type="paragraph", text="Expected loss.")],
                )
            )
        publish_course_canvas(app.state.canvas_workspace, document)
    return TestClient(app)
