from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from lecturepilot.core.models import TenantRole
from lecturepilot.courses.course_support_demand import course_support_demand, course_support_match
from lecturepilot.courses.course_support_models import (
    CourseSupportDemand,
    CourseSupportKey,
    CourseSupportMatch,
    CourseSupportStatus,
    CourseSupportStatusList,
)
from lecturepilot.courses.course_support_requests import (
    CourseNotObservedError,
    CourseSupportRequests,
)
from lecturepilot.courses.professor_preview import PROFESSOR_PREVIEW_HEADER
from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity.api_auth import (
    request_context,
    require_platform_admin,
    require_professor,
)
from lecturepilot.identity.tenancy import TenantContext

T = TypeVar("T")
ROUTE = "/me/course-support-requests"


def register_course_support_routes(app: FastAPI) -> None:
    def requests() -> CourseSupportRequests:
        return CourseSupportRequests(app.state.database)

    @app.get(ROUTE, response_model=CourseSupportStatusList)
    def list_course_support_requests(
        request: Request, context: TenantContext = Depends(request_context)
    ) -> CourseSupportStatusList:
        user_id = _student_id(request, context)
        items = _database(lambda: requests().list(user_id=user_id, tenant_id=context.tenant_id))
        return CourseSupportStatusList(items=items)

    @app.put(ROUTE, response_model=CourseSupportStatus)
    def request_course_support(
        input_data: CourseSupportKey,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseSupportStatus:
        user_id = _student_id(request, context)
        return _database(
            lambda: requests().request(user_id=user_id, tenant_id=context.tenant_id, key=input_data)
        )

    @app.delete(ROUTE, response_model=CourseSupportStatus)
    def withdraw_course_support(
        input_data: CourseSupportKey,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseSupportStatus:
        user_id = _student_id(request, context)
        return _database(
            lambda: requests().withdraw(
                user_id=user_id, tenant_id=context.tenant_id, key=input_data
            )
        )

    @app.get("/platform/course-support-demand", response_model=CourseSupportDemand)
    def platform_course_support_demand(
        limit: Annotated[int, Query(ge=1, le=1000)] = 500,
        context: TenantContext = Depends(request_context),
    ) -> CourseSupportDemand:
        require_platform_admin(context)
        items = _database(
            lambda: course_support_demand(
                app.state.database, tenant_id=context.tenant_id, limit=limit
            )
        )
        return CourseSupportDemand(items=items)

    @app.get("/admin/course-support-demand/match", response_model=CourseSupportMatch)
    def professor_course_support_match(
        title: Annotated[str, Query(min_length=1, max_length=200)],
        term: Annotated[str | None, Query(max_length=80)] = None,
        context: TenantContext = Depends(request_context),
    ) -> CourseSupportMatch:
        require_professor(context)
        return _database(
            lambda: course_support_match(
                app.state.database, tenant_id=context.tenant_id, title=title, term=term
            )
        )


def _student_id(request: Request, context: TenantContext) -> UUID:
    if TenantRole.STUDENT not in context.roles:
        raise HTTPException(status_code=403, detail="Student access is required.")
    if request.headers.get(PROFESSOR_PREVIEW_HEADER) is not None:
        raise HTTPException(status_code=403, detail="Learner preview cannot request courses.")
    try:
        return UUID(context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Database account is required.") from exc


def _database(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except CourseNotObservedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatabaseConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
