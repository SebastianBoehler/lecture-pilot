DEFAULT_STUDENT_COURSE_IDS = (
    "martius-ml",
    "demo-ml-course",
    "mixed-source-course",
    "demo-course",
    "c1",
)


def student_headers(
    user_id: str = "student01",
    *,
    course_ids: tuple[str, ...] | list[str] = DEFAULT_STUDENT_COURSE_IDS,
) -> dict[str, str]:
    return {
        "X-Course-Ids": ",".join(course_ids),
        "X-Tenant-Id": "tenant-tuebingen",
        "X-User-Id": user_id,
        "X-User-Role": "student",
    }


def professor_headers(user_id: str = "prof01") -> dict[str, str]:
    return {
        "X-Tenant-Id": "tenant-tuebingen",
        "X-User-Id": user_id,
        "X-User-Role": "professor",
    }
