from __future__ import annotations

from fastapi import Depends, FastAPI, Query

from lecturepilot.api_auth import request_context, require_professor, require_same_tenant
from lecturepilot.tenancy import TenantContext
from lecturepilot.usage_models import ProfessorUsageSummary


def register_professor_usage_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.get("/admin/usage", response_model=ProfessorUsageSummary)
    def professor_usage(
        days: int = Query(default=30, ge=7, le=90),
        context: TenantContext = Depends(request_context),
    ) -> ProfessorUsageSummary:
        require_professor(context)
        require_same_tenant(context, course_tenant_id=course_tenant_id)
        return app.state.professor_usage.summary(
            actor_user_id=context.user_id,
            tenant_id=course_tenant_id,
            days=days,
        )
