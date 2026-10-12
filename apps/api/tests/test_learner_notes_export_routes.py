from auth_helpers import professor_headers, student_headers
from learner_study_test_helpers import COURSE_ID, learner, study_client
from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.learner.learner_notes_export import notes_filename

URL = f"/courses/{COURSE_ID}/lectures/lecture-open/notes.md"


def _write_notes(client, user_id: str = "student-a", lecture_id: str = "lecture-open") -> None:
    client.app.state.canvas_workspace.apply_sections(
        course_id=COURSE_ID,
        lecture_id=lecture_id,
        user_id=user_id,
        sections=[
            CanvasSection(
                id="zz-summary",
                title="My summary",
                blocks=[CanvasBlock(id="summary-p", type="paragraph", text="Summary text.")],
            ),
            CanvasSection(
                id="aa-example",
                title="Worked example",
                blocks=[CanvasBlock(id="example-p", type="paragraph", text="Example text.")],
            ),
        ],
        placements={"zz-summary": {"mode": "before_section", "section_id": "intro"}},
    )


def test_notes_export_concatenates_own_notes_in_placement_order(tmp_path) -> None:
    client = study_client(tmp_path)
    _write_notes(client)

    response = client.get(URL, headers=learner())

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["cache-control"] == "no-store"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="lecturepilot-notes-lecture-open.md"'
    )
    body = response.text
    assert body.startswith("# Published lecture\n")
    assert body.index("## My summary") < body.index("## Worked example")
    assert "Summary text." in body and "Example text." in body
    assert "placement_mode" not in body
    assert "<!-- block" not in body
    assert "Published." not in body  # official sections are not part of the learner export


def test_notes_export_is_scoped_to_session_learner_and_unlocked_lectures(tmp_path) -> None:
    client = study_client(tmp_path)
    _write_notes(client)
    _write_notes(client, lecture_id="lecture-locked")

    other = client.get(f"{URL}?user_id=student-a", headers=learner("student-b"))
    assert other.status_code == 404
    assert "Summary text." not in other.text
    assert client.get(URL).status_code == 401
    outsider = student_headers("outsider", course_ids=[])
    assert client.get(URL, headers=outsider).status_code == 404
    locked = client.get(f"/courses/{COURSE_ID}/lectures/lecture-locked/notes.md", headers=learner())
    assert locked.status_code == 403
    hidden = client.get(f"/courses/{COURSE_ID}/lectures/lecture-hidden/notes.md", headers=learner())
    assert hidden.status_code == 404
    traversal = client.get(
        f"/courses/{COURSE_ID}/lectures/..%2Flecture-open/notes.md", headers=learner()
    )
    assert traversal.status_code == 404
    assert client.get(URL, headers=professor_headers()).status_code == 403


def test_notes_filename_is_safe() -> None:
    assert notes_filename('../evil"name') == "lecturepilot-notes-evil-name.md"
    assert notes_filename("...") == "lecturepilot-notes-lecture.md"
