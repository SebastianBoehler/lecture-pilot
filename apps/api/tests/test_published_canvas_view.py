from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from auth_helpers import student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from test_quiz_attempt_review_fixes import COURSE_ID, LECTURE_ID, _client, _document, _publish


def test_rendered_canvas_version_remains_submission_authority_after_republish(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    canvas = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=headers,
    )
    first_context = client.app.state.canvas_workspace.course_canvas_store.read_analytics_context(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    )

    assert canvas.status_code == 200
    view = canvas.json()
    assert view["publication_version"] == 1
    assert view["learning_map_revision"] == first_context.learning_map_revision
    assert view["document"]["sections"][0]["blocks"][0]["text"] == ("What should be minimized?")
    assert "answer_index" not in view["document"]["sections"][0]["blocks"][0]

    _publish(client, version_two=True)
    current_state = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=headers,
    )
    stale = client.post(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer",
        headers=headers,
        json={
            "attendance": "present",
            "attempt_id": "rendered-version-one-attempt",
            "block_id": "risk-quiz",
            "option_index": 1,
            "publication_version": view["publication_version"],
        },
    )

    assert current_state.status_code == 200
    assert current_state.json()["publication_version"] == 2
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "stale_quiz_publication"
    refreshed_state = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=headers,
    ).json()
    assert refreshed_state["quiz_states"] == {}
    assert (
        client.app.state.analytics_store.events(
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
        )
        == []
    )


def test_concurrent_published_gets_are_coherent_and_never_mutate_learner_canvas(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    odd_revision = workspace.course_canvas_store.read_analytics_context(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    ).learning_map_revision
    _publish(client, version_two=True)
    even_revision = workspace.course_canvas_store.read_analytics_context(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    ).learning_map_revision
    workspace.apply_sections(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id="student-a",
        sections=[
            CanvasSection(
                id="student-transfer-note",
                title="Transfer note",
                source_ref="student workspace",
                blocks=[
                    CanvasBlock(
                        id="student-transfer-note-p",
                        type="paragraph",
                        text="Learner-owned note.",
                    )
                ],
            )
        ],
    )
    before = _learner_canvas_files(workspace)
    rounds = range(3, 11)
    rendezvous = Barrier(5)

    def republish() -> None:
        for version in rounds:
            rendezvous.wait()
            try:
                published = publish_course_canvas(
                    workspace,
                    _document(version_two=version % 2 == 0),
                )
                assert published["version"] == version
            finally:
                rendezvous.wait()

    def read_views() -> list[object]:
        results: list[object] = []
        for _ in rounds:
            rendezvous.wait()
            try:
                results.append(
                    client.get(
                        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
                        headers=headers,
                    )
                )
            except Exception as exc:  # captured so all real workers can leave the barrier
                results.append(exc)
            finally:
                rendezvous.wait()
        return results

    with ThreadPoolExecutor(max_workers=5) as executor:
        publishing = executor.submit(republish)
        readers = [executor.submit(read_views) for _ in range(4)]
        responses = [response for reader in readers for response in reader.result(timeout=20)]
        publishing.result(timeout=20)

    assert _learner_canvas_files(workspace) == before
    assert len(responses) == 32
    for response in responses:
        assert not isinstance(response, Exception), response
        assert response.status_code == 200
        view = response.json()
        version = view["publication_version"]
        assert view["learning_map_revision"] == (
            even_revision if version % 2 == 0 else odd_revision
        )
        quiz = view["document"]["sections"][0]["blocks"][0]
        expected = (
            "What should be minimized now?" if version % 2 == 0 else "What should be minimized?"
        )
        assert quiz["text"] == expected
        assert any(
            section["id"] == "student-transfer-note" for section in view["document"]["sections"]
        )


def _learner_canvas_files(workspace) -> dict[str, bytes]:
    lecture_root = workspace.layout.user_lecture_root("student-a", COURSE_ID, LECTURE_ID)
    paths = list((lecture_root / "canvas").rglob("*"))
    compiled = lecture_root / "canvas.json"
    if compiled.exists():
        paths.append(compiled)
    return {
        str(path.relative_to(lecture_root)): path.read_bytes() for path in paths if path.is_file()
    }
