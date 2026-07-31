from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.ppi_exam_source_service import PpiCredentialsError, PpiExamSourceService
from lecturepilot.ppi_exam_source_store import PpiExamSourceStore


def test_cached_sources_are_private_and_listed_without_credentials(tmp_path: Path) -> None:
    client, store, _factory = _client(tmp_path)
    store.import_archive(
        user_id="student-a",
        course_id="martius-ml",
        lecture_id=42,
        title="Machine Learning",
        protocol_count=7,
        filename="protocols.zip",
        archive=_archive(),
    )

    own = client.get("/courses/martius-ml/ppi-exam-sources", headers=student_headers("student-a"))
    other = client.get("/courses/martius-ml/ppi-exam-sources", headers=student_headers("student-b"))

    assert own.status_code == 200
    assert [item["id"] for item in own.json()] == ["ppi-42"]
    assert other.json() == []


def test_catalog_rejects_invalid_credentials_without_leaking_secret(tmp_path: Path) -> None:
    client, _store, factory = _client(tmp_path)
    factory.error = PpiCredentialsError("rejected")

    response = client.post(
        "/courses/martius-ml/ppi-exam-sources/catalog",
        headers=student_headers("student-a"),
        json={"username": "zxabc12", "password": "ppi-secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "PPI rejected the username or PPI-specific password."
    assert "ppi-secret" not in response.text


def test_already_borrowed_lecture_downloads_without_spending_token(tmp_path: Path) -> None:
    client, _store, factory = _client(tmp_path)
    factory.client = _FakePpiClient(borrowed=True)

    response = _import(client, confirm=False)

    assert response.status_code == 200
    assert response.json()["token_spent"] is False
    assert response.json()["source"]["id"] == "ppi-42"
    assert factory.client.borrow_calls == 0
    assert factory.client.download_calls == 1


def test_new_borrow_requires_exact_confirmation_and_available_token(tmp_path: Path) -> None:
    client, _store, factory = _client(tmp_path)
    factory.client = _FakePpiClient(borrowed=False)
    unconfirmed = _import(client, confirm=False)

    assert unconfirmed.status_code == 409
    assert "confirm_token_spend" in unconfirmed.json()["detail"]
    assert factory.client.borrow_calls == 0

    confirmed = _import(client, confirm=True)
    assert confirmed.status_code == 200
    assert confirmed.json()["token_spent"] is True
    assert factory.client.borrow_calls == 1


def test_fresh_state_recheck_avoids_stale_token_spend(tmp_path: Path) -> None:
    client, _store, factory = _client(tmp_path)
    factory.client = _FakePpiClient(borrowed=False, become_borrowed_on_recheck=True)

    response = _import(client, confirm=True)

    assert response.status_code == 200
    assert response.json()["token_spent"] is False
    assert factory.client.borrow_calls == 0


def test_import_reports_no_tokens_and_allows_exact_deletion(tmp_path: Path) -> None:
    client, _store, factory = _client(tmp_path)
    factory.client = _FakePpiClient(borrowed=False, tokens=0)
    unavailable = _import(client, confirm=True)
    assert unavailable.status_code == 409
    assert unavailable.json()["detail"] == "No PPI tokens are available."

    factory.client = _FakePpiClient(borrowed=True)
    assert _import(client, confirm=False).status_code == 200
    deleted = client.delete(
        "/courses/martius-ml/ppi-exam-sources/ppi-42",
        headers=student_headers("student-a"),
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}


def test_import_reports_unsupported_archive_members_as_validation_errors(tmp_path: Path) -> None:
    client, _store, factory = _client(tmp_path)
    factory.client = _FakePpiClient(borrowed=True, archive=_archive("questions.exe"))

    response = _import(client, confirm=False)

    assert response.status_code == 422
    assert response.json()["detail"] == "PPI archive contains an unsupported file type."


def test_ppi_sources_deny_professors_and_require_course_enrollment(tmp_path: Path) -> None:
    client, _store, _factory = _client(tmp_path)
    professor = client.get("/courses/martius-ml/ppi-exam-sources", headers=professor_headers())
    unenrolled = client.get(
        "/courses/martius-ml/ppi-exam-sources",
        headers=student_headers("student-a", course_ids=[]),
    )

    assert professor.status_code == 403
    assert unenrolled.status_code in {403, 404}


def _import(client: TestClient, *, confirm: bool):
    return client.post(
        "/courses/martius-ml/ppi-exam-sources/imports",
        headers=student_headers("student-a"),
        json={
            "username": "zxabc12",
            "password": "ppi-secret",
            "ppi_lecture_id": 42,
            "confirm_token_spend": confirm,
        },
    )


def _client(tmp_path: Path) -> tuple[TestClient, PpiExamSourceStore, "_ClientFactory"]:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    store = PpiExamSourceStore(app.state.canvas_workspace.layout)
    factory = _ClientFactory()
    app.state.ppi_exam_source_store = store
    app.state.ppi_exam_source_service = PpiExamSourceService(store, client_factory=factory)
    return TestClient(app), store, factory


class _ClientFactory:
    def __init__(self) -> None:
        self.client = _FakePpiClient(borrowed=True)
        self.error: Exception | None = None

    def __call__(self, username: str, password: str):
        assert username == "zxabc12"
        assert password == "ppi-secret"
        if self.error:
            raise self.error
        return self.client


class _FakePpiClient:
    def __init__(
        self,
        *,
        borrowed: bool,
        tokens: int = 2,
        become_borrowed_on_recheck: bool = False,
        archive: bytes | None = None,
    ) -> None:
        self.borrowed = borrowed
        self.tokens = tokens
        self.become_borrowed_on_recheck = become_borrowed_on_recheck
        self.catalog_calls = 0
        self.borrow_calls = 0
        self.download_calls = 0
        self.archive = archive or _archive()

    def fetch_lecture_catalog(self) -> "_Catalog":
        self.catalog_calls += 1
        if self.become_borrowed_on_recheck and self.catalog_calls > 1:
            self.borrowed = True
        return _Catalog(
            tokens=self.tokens,
            source_url="https://ppi.example/lectures.php",
            lectures=[
                _Lecture(
                    id=42,
                    title="Machine Learning",
                    protocol_count=7,
                    borrowed=self.borrowed,
                    can_borrow=not self.borrowed and self.tokens > 0,
                )
            ],
        )

    def fetch_borrowed_lectures(self) -> "_BorrowedPage":
        return _BorrowedPage(
            tokens=self.tokens,
            source_url="https://ppi.example/download.php",
            lectures=(
                [_BorrowedLecture(42, "Machine Learning", "4 weeks", True)] if self.borrowed else []
            ),
        )

    def borrow_lecture(self, lecture_id: int) -> "_Lecture":
        self.borrow_calls += 1
        self.borrowed = True
        return self.fetch_lecture_catalog().lectures[0]

    def download_lecture(self, lecture_id: int) -> "_Download":
        self.download_calls += 1
        return _Download(lecture_id, "protocols.zip", "application/zip", self.archive)

    def close(self) -> None:
        return None


def _archive(filename: str = "questions.txt") -> bytes:
    content = BytesIO()
    with ZipFile(content, "w") as bundle:
        bundle.writestr(filename, "Explain empirical risk minimization.")
    return content.getvalue()


@dataclass
class _Lecture:
    id: int
    title: str
    protocol_count: int
    borrowed: bool
    can_borrow: bool


@dataclass
class _Catalog:
    tokens: int
    source_url: str
    lectures: list[_Lecture]


@dataclass
class _BorrowedLecture:
    id: int
    title: str
    borrowed_until: str
    download_available: bool


@dataclass
class _BorrowedPage:
    tokens: int
    source_url: str
    lectures: list[_BorrowedLecture]


@dataclass
class _Download:
    lecture_id: int
    filename: str
    content_type: str
    data: bytes
