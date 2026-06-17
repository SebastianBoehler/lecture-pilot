from types import SimpleNamespace

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_media import (
    add_course_youtube_selection,
    add_youtube_selection,
    apply_course_media,
    course_media_evidence,
)
from lecturepilot.models import YoutubeSearchResponse, YoutubeSelectionInput, YoutubeVideoCandidate


HEADERS = {
    "X-Tenant-Id": "tenant-tuebingen",
    "X-User-Id": "professor-1",
    "X-User-Role": "professor",
}


def test_professor_can_search_and_include_youtube_video(tmp_path) -> None:
    app = create_app()
    app.state.youtube_discovery = _FakeYoutubeDiscovery()
    app.state.canvas_workspace = SimpleNamespace(material_root=tmp_path)
    client = TestClient(app)

    search = client.get(
        "/admin/courses/martius-ml/media/youtube/search",
        params={"q": "bayesian decision theory"},
        headers=HEADERS,
    )
    assert search.status_code == 200
    candidate = search.json()["items"][0]

    include = client.post(
        "/admin/courses/martius-ml/media/youtube",
        headers=HEADERS,
        json={"video": candidate},
    )

    assert include.status_code == 200
    payload = include.json()
    assert payload["block_id"] == "youtube-abc123abc12"
    assert (tmp_path / "canvas" / "media" / "martius-ml-__course__.json").exists()

    listed = client.get("/admin/courses/martius-ml/media/youtube", headers=HEADERS)
    assert listed.status_code == 200
    assert listed.json()[0]["video"]["url"] == "https://www.youtube.com/watch?v=abc123abc12"


def test_students_cannot_manage_youtube_course_media(tmp_path) -> None:
    app = create_app()
    app.state.youtube_discovery = _FakeYoutubeDiscovery()
    app.state.canvas_workspace = SimpleNamespace(material_root=tmp_path)
    client = TestClient(app)

    response = client.get(
        "/admin/courses/martius-ml/media/youtube/search",
        params={"q": "bayesian decision theory"},
        headers={**HEADERS, "X-User-Role": "student"},
    )

    assert response.status_code == 403


def test_professor_can_clear_course_youtube_media(tmp_path) -> None:
    app = create_app()
    app.state.canvas_workspace = SimpleNamespace(material_root=tmp_path)
    client = TestClient(app)
    add_course_youtube_selection(
        material_root=tmp_path,
        course_id="martius-ml",
        selection=YoutubeSelectionInput(section_id="bayes-formula", video=_candidate()),
        approved_by="professor-1",
    )

    response = client.delete("/admin/courses/martius-ml/media/youtube", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert not (tmp_path / "canvas" / "media" / "martius-ml-__course__.json").exists()


def test_approved_youtube_selection_merges_into_canvas_section(tmp_path) -> None:
    video = _candidate()
    add_youtube_selection(
        material_root=tmp_path,
        course_id="martius-ml",
        lecture_id="lecture-03",
        selection=YoutubeSelectionInput(section_id="bayes-formula", video=video),
        approved_by="professor-1",
    )
    document = CanvasDocument(
        id="martius-ml-lecture-03",
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Bayesian Decision Theory",
        source_kind="latex",
        source_ref="Lecture03-eng.tex",
        workspace_path="canvas/index.md",
        sections=[CanvasSection(id="bayes-formula", title="Bayes formula")],
    )

    merged = apply_course_media(document, tmp_path)

    assert merged.sections[0].blocks[0].type == "video"
    assert merged.sections[0].blocks[0].asset_url == "https://www.youtube.com/watch?v=abc123abc12"


def test_course_youtube_selection_becomes_planner_evidence(tmp_path) -> None:
    add_course_youtube_selection(
        material_root=tmp_path,
        course_id="martius-ml",
        selection=YoutubeSelectionInput(video=_candidate()),
        approved_by="professor-1",
    )
    document = CanvasDocument(
        id="martius-ml-lecture-03",
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Bayesian Decision Theory",
        source_kind="latex",
        source_ref="Lecture03-eng.tex",
        workspace_path="canvas/index.md",
        sections=[CanvasSection(id="bayes-formula", title="Bayes formula")],
    )

    with_media = course_media_evidence(document, tmp_path)

    evidence = with_media.sections[-1]
    assert evidence.id == "professor-approved-video-evidence"
    assert evidence.blocks[0].type == "video"
    assert evidence.blocks[0].asset_path == "https://www.youtube.com/watch?v=abc123abc12"


class _FakeYoutubeDiscovery:
    def search(self, query: str, *, max_results: int = 5) -> YoutubeSearchResponse:
        return YoutubeSearchResponse(query=query, items=[_candidate()])


def _candidate() -> YoutubeVideoCandidate:
    return YoutubeVideoCandidate(
        video_id="abc123abc12",
        title="Bayesian decision theory",
        channel_title="ML Course",
        description="Posterior probabilities and risk.",
        url="https://www.youtube.com/watch?v=abc123abc12",
    )
