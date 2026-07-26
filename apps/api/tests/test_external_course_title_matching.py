from lecturepilot.external_course_sync import _course_title_key


def test_title_key_ignores_leading_alma_module_code() -> None:
    assert _course_title_key(
        "INFO4222 Softwarequalität in Theorie und Industrieller Praxis"
    ) == _course_title_key("Softwarequalität in Theorie und Industrieller Praxis")


def test_title_key_keeps_numbers_inside_the_actual_title() -> None:
    assert _course_title_key("Studio 54 Softwarequalität") != _course_title_key("Softwarequalität")
