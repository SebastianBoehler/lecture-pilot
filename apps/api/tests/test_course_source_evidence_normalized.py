import json
from pathlib import Path

from lecturepilot.course_source_evidence import selection_detail_files, source_file_excerpt
from lecturepilot.source_index_models import IndexedSourceFile


def test_routing_evidence_reads_normalized_office_text_and_inert_code(tmp_path: Path) -> None:
    office = _indexed("slides/lecture.pptx", "presentation", "a")
    code = _indexed("examples/solver.cpp", "code", "b")
    revision = tmp_path / "normalized" / office.sha256
    revision.mkdir(parents=True)
    (revision / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_path": office.path,
                "source_sha256": office.sha256,
                "media_type": (
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                ),
                "blocks": [
                    {
                        "kind": "heading",
                        "text": "Bayesian model selection",
                        "locator": {"slide": 3},
                        "extraction": "native",
                    }
                ],
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )

    selected = selection_detail_files([office, code], set())

    assert {item.path for item in selected} == {office.path, code.path}
    assert source_file_excerpt(office, [tmp_path / "normalized"]) == ("Bayesian model selection")


def _indexed(path: str, kind: str, prefix: str) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=path,
        kind=kind,
        size_bytes=10,
        sha256=prefix * 64,
        modified_ns=1,
    )
