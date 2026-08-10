from datetime import date

import pytest

from lecturepilot.course_source_routing_planner import (
    _read_selected_routes,
    _routing_evidence,
    _routing_messages,
)
from lecturepilot.agent_response_schema import source_routing_response_format
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.course_source_routing_review import (
    apply_review_corrections,
    routing_review_messages,
)
from lecturepilot.models import Lecture
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.course_source_evidence import selection_detail_files
from lecturepilot.source_index_models import IndexedSourceFile


def test_source_selection_builds_complete_least_privilege_manifest() -> None:
    files = [_indexed_file(number) for number in range(1525)]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
        material_path=files[0].path,
    )

    routes = _read_selected_routes(
        {
            "selections": [
                {
                    "path": files[1].path,
                    "role": "course_wide",
                    "lecture_id": None,
                }
            ]
        },
        files,
        [lecture],
    )

    assert len(routes) == len(files)
    assert routes[0].role == SourceRouteRole.LECTURE
    assert routes[0].lecture_id == lecture.id
    assert routes[1].role == SourceRouteRole.COURSE_WIDE
    assert all(route.role == SourceRouteRole.EXCLUDED for route in routes[2:])


def test_source_routing_schema_binds_role_to_lecture_id_shape() -> None:
    schema = source_routing_response_format()["json_schema"]["schema"]
    variants = schema["properties"]["selections"]["items"]["anyOf"]

    by_role = {
        variant["properties"]["role"]["const"]: variant["properties"]["lecture_id"]
        for variant in variants
    }
    assert by_role["lecture"]["type"] == "string"
    assert by_role["course_wide"] == {"type": "null"}
    assert "excluded" not in by_role


def test_source_selection_sees_complete_inventory_and_bounded_detail() -> None:
    files = [_indexed_file(number) for number in range(3)]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
    )

    evidence = _routing_evidence("course", files, [lecture], [])

    assert "Complete course inventory (3 files)" in evidence
    assert "Candidate content evidence" in evidence
    for item in files:
        assert item.path in evidence


def test_source_routing_agent_excludes_assignments_when_lecture_material_exists() -> None:
    files = [_indexed_file(0)]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
    )

    messages = _routing_messages("course", files, [lecture], [])

    assert "Return only additional selected sources" in messages[0]["content"]
    assert "assignment sheets" in messages[0]["content"]
    assert "exam-preparation guidance" in messages[0]["content"]
    assert "applicable to every lecture" in messages[0]["content"]
    assert "derived text conversions" in messages[0]["content"]
    assert (
        "complementary examples, code demos, readings, or standalone diagrams"
        in messages[0]["content"]
    )
    assert "generated slide-page images" in messages[0]["content"]


def test_source_selection_detail_sample_represents_each_material_kind() -> None:
    files = [_indexed_file(number) for number in range(60)]
    files.extend(
        [
            _indexed_kind("deep/examples/demo.ipynb", "notebook", 1, "a"),
            _indexed_kind("notes/overview.md", "markdown", 2, "b"),
        ]
    )

    details = selection_detail_files(files, set())

    assert len(details) == 60
    assert {item.kind for item in details} >= {"pdf", "notebook", "markdown"}


def test_source_selection_rejects_primary_reassignment() -> None:
    files = [_indexed_file(0)]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
        material_path=files[0].path,
    )

    with pytest.raises(ProviderConfigurationError, match="primary source"):
        _read_selected_routes(
            {
                "selections": [
                    {
                        "path": files[0].path,
                        "role": "course_wide",
                        "lecture_id": None,
                    }
                ]
            },
            files,
            [lecture],
        )


def test_global_reviewer_sees_every_proposal_and_selected_side_source(tmp_path) -> None:
    primary = tmp_path / "lecture.pdf"
    primary.write_text("Primary lecture material", encoding="utf-8")
    side = tmp_path / "opaque.dat"
    side.write_text("Submit your graded answers to this assignment.", encoding="utf-8")
    files = [
        _indexed_path(primary, "pdf", "a"),
        _indexed_path(side, "text", "b"),
    ]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
        material_path=primary.name,
    )
    routes = [
        _route(files[0], SourceRouteRole.LECTURE, lecture.id),
        _route(files[1], SourceRouteRole.LECTURE, lecture.id),
    ]

    messages = routing_review_messages("course", files, [lecture], [tmp_path], routes)
    evidence = messages[1]["content"]

    assert "exam protocols" in messages[0]["content"]
    assert "applicable to every lecture" in messages[0]["content"]
    assert primary.name in evidence
    assert side.name in evidence
    assert "Submit your graded answers" in evidence


def test_global_reviewer_applies_only_known_unique_corrections() -> None:
    files = [_indexed_file(0), _indexed_file(1)]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
    )
    routes = [
        _route(files[0], SourceRouteRole.LECTURE, lecture.id),
        _route(files[1], SourceRouteRole.LECTURE, lecture.id),
    ]

    reviewed = apply_review_corrections(
        {"corrections": [{"path": files[1].path, "role": "excluded", "lecture_id": None}]},
        routes,
        [lecture],
    )

    assert reviewed[0].role == SourceRouteRole.LECTURE
    assert reviewed[1].role == SourceRouteRole.EXCLUDED
    with pytest.raises(ProviderConfigurationError, match="Unknown correction path"):
        apply_review_corrections(
            {"corrections": [{"path": "not-uploaded.pdf", "role": "excluded", "lecture_id": None}]},
            routes,
            [lecture],
        )


def test_global_reviewer_rejects_duplicate_corrections() -> None:
    item = _indexed_file(0)
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Introduction",
        date=date(2026, 4, 13),
    )
    route = _route(item, SourceRouteRole.LECTURE, lecture.id)
    correction = {"path": item.path, "role": "excluded", "lecture_id": None}

    with pytest.raises(ProviderConfigurationError, match="Duplicate correction path"):
        apply_review_corrections({"corrections": [correction, correction]}, [route], [lecture])


def _indexed_file(number: int) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=f"uploads/course/material-{number:03d}.pdf",
        kind="pdf",
        size_bytes=number,
        sha256=f"{number:064x}",
        modified_ns=number,
    )


def _indexed_path(path, kind: str, digest: str) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=path.name,
        kind=kind,
        size_bytes=path.stat().st_size,
        sha256=digest * 64,
        modified_ns=path.stat().st_mtime_ns,
    )


def _indexed_kind(path: str, kind: str, size: int, digest: str) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=path,
        kind=kind,
        size_bytes=size,
        sha256=digest * 64,
        modified_ns=size,
    )


def _route(
    item: IndexedSourceFile, role: SourceRouteRole, lecture_id: str | None
) -> CourseSourceRoute:
    return CourseSourceRoute(
        path=item.path,
        kind=item.kind,
        sha256=item.sha256,
        role=role,
        lecture_id=lecture_id,
    )
