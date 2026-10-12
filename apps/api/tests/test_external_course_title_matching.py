from lecturepilot.courses.external_course_sync import course_title_key


def test_title_key_ignores_leading_alma_module_code() -> None:
    assert course_title_key(
        "INFO4222 Softwarequalität in Theorie und Industrieller Praxis"
    ) == course_title_key("Softwarequalität in Theorie und Industrieller Praxis")


def test_title_key_keeps_numbers_inside_the_actual_title() -> None:
    assert course_title_key("Studio 54 Softwarequalität") != course_title_key("Softwarequalität")
