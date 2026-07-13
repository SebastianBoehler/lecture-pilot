from dataclasses import dataclass

from lecturepilot.university_models import UniversityLoginResult


DEFAULT_STUDENT_COURSE_IDS = (
    "martius-ml",
    "demo-ml-course",
    "mixed-source-course",
    "demo-course",
    "c1",
)


@dataclass(frozen=True)
class FakePendingUniversityLogin:
    initial_identity: UniversityLoginResult
    synchronized_identity: UniversityLoginResult

    def synchronize(self) -> UniversityLoginResult:
        return self.synchronized_identity


def pending_university_login(
    identity: UniversityLoginResult,
    *,
    preload_profile: bool = True,
) -> FakePendingUniversityLogin:
    initial = identity.model_copy(
        update={
            "courses": [],
            "sources_checked": set(),
            "warnings": [],
            **({} if preload_profile else {"display_name": None, "email": None}),
        }
    )
    return FakePendingUniversityLogin(initial, identity)


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
