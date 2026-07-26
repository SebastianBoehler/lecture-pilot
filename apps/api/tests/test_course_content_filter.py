from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_content_filter import filter_source_document_for_planning
from lecturepilot.course_content_filter import is_learning_section


def test_global_german_course_admin_sections_are_not_repeated_in_lecture_canvas() -> None:
    document = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture-03",
        title="White Box Testing",
        source_kind="generated",
        source_ref="uploads",
        workspace_path="source.json",
        sections=[
            _section("white-box", "White Box Testing"),
            _section("exercise", "Exercise Sheet 3"),
            _section("course-info", "Offizielle Kursinfo"),
            _section("exam-info", "Prüfungsinfo"),
            _section("materials", "Themen und Materialien"),
        ],
    )

    filtered = filter_source_document_for_planning(document)

    assert [section.id for section in filtered.sections] == ["white-box", "exercise"]


def test_learning_topic_is_not_filtered_because_its_content_mentions_requirements() -> None:
    section = _section("model-based", "Model-Based Testing")
    section.blocks[
        0
    ].text = "The method derives tests from requirements and checks the resulting behavior."

    assert is_learning_section(section) is True


def _section(section_id: str, title: str) -> CanvasSection:
    return CanvasSection(
        id=section_id,
        title=title,
        source_ref=f"{title}.md",
        blocks=[
            CanvasBlock(
                id=f"{section_id}-text",
                type="paragraph",
                text=f"Source evidence for {title}.",
            )
        ],
    )
