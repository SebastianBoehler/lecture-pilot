from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import configure_canvas_workspace, publish_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_canvas_endpoint_loads_private_course_source_for_student(tmp_path: Path) -> None:
    app = create_app()
    configure_canvas_workspace(app, _workspace(tmp_path))
    response = TestClient(app).get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["publication_version"] == 1
    assert payload["learning_map_revision"]
    assert payload["document"]["title"] == "Bayesian Decision Theory"
    assert payload["document"]["source_ref"] == "Lecture03-eng.tex"
    assert payload["document"]["sections"][0]["id"] == "bayesian-decision-theory-the-aim"
    assert "workspace_path" not in payload["document"]


def test_canvas_endpoint_requires_authenticated_learner_identity(tmp_path: Path) -> None:
    app = create_app()
    configure_canvas_workspace(app, _workspace(tmp_path))

    response = TestClient(app).get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01"
    )

    assert response.status_code == 401


def _workspace(tmp_path: Path) -> CanvasWorkspace:
    material_root = tmp_path / "course"
    material_root.mkdir()
    (material_root / "Lecture03-eng.tex").write_text(
        r"""
\mytitle[29 April, 2025]{3}{Bayesian Decision Theory}
\begin{frame}{Bayesian Decision Theory: The Aim}
Bayesian decision theory connects evidence, posterior probabilities, and decisions.
\end{frame}
""",
        encoding="utf-8",
    )
    workspace = CanvasWorkspace(workspace_root=tmp_path / "workspaces", material_root=material_root)
    document = workspace.source_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        workspace_path=str(tmp_path / "published" / "index.md"),
    )
    section = document.sections[0]
    document = document.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            *section.blocks,
                            CanvasBlock(
                                id="demo-gate",
                                type="checkpoint",
                                text="Explain one concrete Bayesian decision.",
                            ),
                        ]
                    }
                ),
                *document.sections[1:],
            ]
        }
    )
    publish_course_canvas(workspace, document)
    return workspace
