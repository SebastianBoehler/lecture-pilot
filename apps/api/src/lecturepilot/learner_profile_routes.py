from __future__ import annotations

import re

from fastapi import Depends, FastAPI, HTTPException, Query, Response

from lecturepilot.api_auth import request_context, require_learner_workspace_access
from lecturepilot.audit import record_audit_event
from lecturepilot.learner_profile import (
    LearnerProfileResponse,
    LearnerProfileUpdate,
    read_learner_profile,
)
from lecturepilot.tenancy import TenantContext


_PREFERENCE_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def register_learner_profile_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.get("/me/learning-profile", response_model=LearnerProfileResponse)
    def get_learning_profile(
        context: TenantContext = Depends(request_context),
    ) -> LearnerProfileResponse:
        _require_student(context, course_tenant_id)
        return read_learner_profile(app.state.user_memory_store, context.user_id)

    @app.post("/me/learning-profile", response_model=LearnerProfileResponse)
    def update_learning_profile(
        update: LearnerProfileUpdate,
        context: TenantContext = Depends(request_context),
    ) -> LearnerProfileResponse:
        _require_student(context, course_tenant_id)
        app.state.user_memory_store.update_preferences(
            context.user_id,
            update.model_dump(mode="json"),
        )
        record_audit_event(
            app.state.database,
            context,
            event_type="learner.profile_updated",
            target_type="user",
            target_id=context.user_id,
            details={"learning_goal": update.learning_goal},
        )
        return read_learner_profile(app.state.user_memory_store, context.user_id)

    @app.delete("/me/learning-profile/preferences/{key}", status_code=204)
    def delete_learning_preference(
        key: str,
        context: TenantContext = Depends(request_context),
    ) -> Response:
        _require_student(context, course_tenant_id)
        if key == "onboarding_completed" or not _PREFERENCE_KEY.fullmatch(key):
            raise HTTPException(status_code=400, detail="Preference key is not removable.")
        app.state.user_memory_store.delete_preference(context.user_id, key)
        return Response(status_code=204)

    @app.delete("/me/learning-profile/memory", status_code=204)
    def clear_learning_memory(
        course_id: str | None = Query(default=None, min_length=1, max_length=120),
        context: TenantContext = Depends(request_context),
    ) -> Response:
        _require_student(context, course_tenant_id)
        app.state.user_memory_store.clear_notes(context.user_id, course_id)
        record_audit_event(
            app.state.database,
            context,
            event_type="learner.memory_cleared",
            target_type="course" if course_id else "user",
            target_id=course_id or context.user_id,
        )
        return Response(status_code=204)


def _require_student(context: TenantContext, course_tenant_id: str) -> None:
    require_learner_workspace_access(
        context,
        learner_user_id=context.user_id,
        course_tenant_id=course_tenant_id,
    )
