from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.storage_layout import StorageLayout


class CanvasContextWorkspace:
    def __init__(self, root) -> None:
        self.layout = StorageLayout(root)

    def has_published_course_canvas(self, *, course_id: str, lecture_id: str) -> bool:
        return course_id == "martius-ml" and lecture_id == "lecture-03"

    def read_document(self, *, course_id: str, lecture_id: str, user_id: str) -> CanvasDocument:
        return CanvasDocument(
            id="martius-ml-lecture-03",
            course_id=course_id,
            lecture_id=lecture_id,
            title="Bayesian Decision Theory",
            source_kind="latex",
            source_ref="Lecture03-eng.tex",
            workspace_path=".lecturepilot/workspaces/test/canvas/index.md",
            sections=[CanvasSection(id="bayes-formula", title="Bayes formula")],
        )


class _PublishedCanvasAccessStub:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def has_published_course_canvas(self, *, course_id: str, lecture_id: str) -> bool:
        return course_id == "martius-ml" and lecture_id == "lecture-01"

    def read_document(self, *, course_id: str, lecture_id: str, user_id: str) -> CanvasDocument:
        raise CanvasWorkspaceError("Canvas loading is outside these harness tests.")


def agent_client(harness: object) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = _PublishedCanvasAccessStub(app.state.canvas_workspace.layout)
    app.state.agent_harness = harness
    return TestClient(app)
