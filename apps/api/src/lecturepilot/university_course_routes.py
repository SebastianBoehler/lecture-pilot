from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from lecturepilot.api_auth import request_context, require_professor, require_same_tenant
from lecturepilot.tenancy import TenantContext
from lecturepilot.university_course_search import (
    UniversityCourseSearchError,
    UniversityCourseSuggestionResult,
)


def register_university_course_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.get(
        "/admin/university-courses/search",
        response_model=UniversityCourseSuggestionResult,
    )
    def search_university_courses(
        q: Annotated[str, Query(min_length=3, max_length=120)],
        term: Annotated[str, Query(min_length=1, max_length=80)],
        limit: Annotated[int, Query(ge=1, le=10)] = 8,
        context: TenantContext = Depends(request_context),
    ) -> UniversityCourseSuggestionResult:
        require_professor(context)
        require_same_tenant(context, course_tenant_id=course_tenant_id)
        query = q.strip()
        resolved_term = term.strip()
        if len(query) < 3 or not resolved_term:
            raise HTTPException(status_code=422, detail="A course query and term are required.")
        try:
            items = app.state.university_course_search.search(
                query=query,
                term=resolved_term,
                limit=limit,
            )
        except UniversityCourseSearchError as exc:
            raise HTTPException(
                status_code=502,
                detail="Alma course search is temporarily unavailable.",
            ) from exc
        return UniversityCourseSuggestionResult(items=items)
