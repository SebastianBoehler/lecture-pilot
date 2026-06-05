from __future__ import annotations

from datetime import date

from lecturepilot.models import AttendanceStatus, Course, Lecture, LectureView
from lecturepilot.policies import is_lecture_unlocked


COURSE = Course(
    id="martius-ml",
    title="Grundlagen des Maschinellen Lernens",
    professor="Prof. Georg Martius",
    term="Sommer 2026",
)

LECTURES = [
    Lecture(
        id="lecture-01",
        course_id=COURSE.id,
        title="Introduction and Learning Setup",
        date=date(2026, 5, 6),
        material_path="courses/martius-ml/lectures/01/source.tex",
    ),
    Lecture(
        id="lecture-02",
        course_id=COURSE.id,
        title="Linear Models and Generalization",
        date=date(2026, 5, 13),
        material_path="courses/martius-ml/lectures/02/source.tex",
    ),
    Lecture(
        id="lecture-03",
        course_id=COURSE.id,
        title="Kernels and Feature Maps",
        date=date(2026, 6, 4),
        material_path="courses/martius-ml/lectures/03/source.tex",
    ),
]


def unlocked_lectures(today: date | None = None) -> list[LectureView]:
    return [
        LectureView(
            lecture=lecture,
            unlocked=is_lecture_unlocked(lecture, today=today),
            attendance=AttendanceStatus.UNKNOWN,
        )
        for lecture in LECTURES
        if is_lecture_unlocked(lecture, today=today)
    ]

