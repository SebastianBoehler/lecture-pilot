from __future__ import annotations

import shutil

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.storage_layout import StorageLayout, StorageLayoutError, safe_id
from lecturepilot.tenancy import TenantContext


class CourseDeletionResult(BaseModel):
    course_id: str = Field(min_length=1)
    deleted: bool
    deleted_path: str


def delete_course_workspace(*, layout: StorageLayout, course_id: str) -> CourseDeletionResult | None:
    course_root = layout.course_root(course_id)
    if not course_root.exists():
        return None
    shutil.rmtree(course_root)
    return CourseDeletionResult(
        course_id=course_id,
        deleted=True,
        deleted_path=str(course_root),
    )


def register_course_deletion_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.delete("/admin/courses/{course_id}", response_model=CourseDeletionResult)
    def delete_course(
        course_id: str,
        context: TenantContext = Depends(request_context),
    ) -> CourseDeletionResult:
        require_course_manager(context, course_tenant_id=course_tenant_id)
        if not _is_canonical_course_id(course_id):
            raise HTTPException(status_code=400, detail="Invalid course id.")
        result = delete_course_workspace(
            layout=app.state.canvas_workspace.layout,
            course_id=course_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Course workspace not found.")
        return result


def _is_canonical_course_id(course_id: str) -> bool:
    try:
        return safe_id(course_id) == course_id
    except StorageLayoutError:
        return False
