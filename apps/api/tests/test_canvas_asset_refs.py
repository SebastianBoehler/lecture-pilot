import pytest

from lecturepilot.canvas_asset_refs import parsed_asset_target


def test_relative_course_asset_builds_an_authenticated_route() -> None:
    asset_path, asset_url = parsed_asset_target(
        "asset:generated-slides/exercise/slide-001.png",
        course_id="software-quality",
        lecture_id="lecture-01",
    )

    assert asset_path == "generated-slides/exercise/slide-001.png"
    assert asset_url == (
        "/course-assets/software-quality/lecture-01/generated-slides/exercise/slide-001.png"
    )


@pytest.mark.parametrize(
    "target",
    [
        "",
        "asset:",
        "asset:/course-assets/software-quality/lecture-01/",
        "asset:generated-slides/exercise/",
        "asset:../private/answer.png",
    ],
)
def test_invalid_course_asset_targets_are_not_renderable(target: str) -> None:
    assert parsed_asset_target(
        target,
        course_id="software-quality",
        lecture_id="lecture-01",
    ) == (None, "")
