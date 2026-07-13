from lecturepilot.university_course_search import alma_term_key


def test_alma_term_key_matches_lecturepilot_and_alma_labels() -> None:
    assert alma_term_key("Sommer 2026") == alma_term_key("Sommersemester 2026")
    assert alma_term_key("Winter 2025/26") == alma_term_key("Wintersemester 2025")
