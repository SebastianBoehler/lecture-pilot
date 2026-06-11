def student_headers(user_id: str = "student01") -> dict[str, str]:
    return {
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
