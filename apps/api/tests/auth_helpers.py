from dataclasses import dataclass

from lecturepilot.course_source_partition import is_course_wide_source, select_lecture_source_files
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
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


def confirm_source_routing(
    client,
    course_id: str,
    route_overrides: dict[str, tuple[str, str | None]] | None = None,
) -> dict:
    install_test_source_routing_planner(client)
    response = client.post(
        f"/admin/courses/{course_id}/source-routing/proposal",
        headers=professor_headers(),
    )
    assert response.status_code == 200
    routing = response.json()
    for route in routing["routes"]:
        override = (route_overrides or {}).get(route["path"])
        if override:
            route.update({"role": override[0], "lecture_id": override[1]})
    confirmed = client.put(
        f"/admin/courses/{course_id}/source-routing",
        json={"source_revision": routing["source_revision"], "routes": routing["routes"]},
        headers=professor_headers(),
    )
    assert confirmed.status_code == 200
    return confirmed.json()


def install_test_source_routing_planner(client) -> None:
    client.app.state.source_routing_planner = DeterministicTestSourceRoutingPlanner()


class DeterministicTestSourceRoutingPlanner:
    async def propose_routes(self, *, files, lectures, **_kwargs):
        bundle_files = [item.as_bundle_file() for item in files]
        paths_by_lecture = {
            lecture.id: {
                item.path
                for item in select_lecture_source_files(
                    files=bundle_files,
                    lectures=lectures,
                    lecture_id=lecture.id,
                )
            }
            for lecture in lectures
        }
        routes = []
        for item in files:
            matches = [
                lecture.id for lecture in lectures if item.path in paths_by_lecture[lecture.id]
            ]
            lowered = item.path.casefold()
            if "exam-protocol" in lowered or lowered.startswith(("build/", "uploads/build/")):
                role, lecture_id = SourceRouteRole.EXCLUDED, None
            elif is_course_wide_source(item.path):
                role, lecture_id = SourceRouteRole.COURSE_WIDE, None
            elif len(matches) == 1:
                role, lecture_id = SourceRouteRole.LECTURE, matches[0]
            else:
                role, lecture_id = SourceRouteRole.EXCLUDED, None
            routes.append(
                CourseSourceRoute(
                    path=item.path,
                    kind=item.kind,
                    sha256=item.sha256,
                    role=role,
                    lecture_id=lecture_id,
                )
            )
        return routes
