from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.audit import record_audit_event
from lecturepilot.canvas_language_generation import generate_language_variant
from lecturepilot.canvas_language_store import CanvasLanguageStore
from lecturepilot.canvas_language_variants import Language, publish_variant, teaching_texts
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from lecturepilot.tenancy import TenantContext


class LanguageApproval(BaseModel):
    assessment_language: Language
    model_config = ConfigDict(extra="forbid")
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def register_canvas_language_routes(app: FastAPI, *, course_tenant_id, seeded_course, lectures):
    def store():
        return CanvasLanguageStore(app.state.canvas_workspace.layout)

    def manager(request, context, course_id):
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/languages/{language}/generate"
    )
    async def generate(
        course_id: str,
        lecture_id: str,
        language: Language,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        manager(request, context, course_id)
        try:
            snapshot = store().snapshot(course_id, lecture_id)
            with model_usage_scope(
                actor_user_id=context.user_id, course_id=course_id, workload="canvas_language"
            ):
                variant = await generate_language_variant(
                    app.state.practice_design_planner, snapshot, language
                )
            with locked_course_state(store().layout.course_root(course_id)):
                store().write(course_id, lecture_id, variant)
            return variant
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ModelExecutionError, ProviderConfigurationError, UnexpectedModelBehavior) as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/admin/courses/{course_id}/lectures/{lecture_id}/canvas/languages/{language}")
    def preview(
        course_id: str,
        lecture_id: str,
        language: Language,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        manager(request, context, course_id)
        try:
            with locked_course_state(store().layout.course_root(course_id)):
                snapshot = store().snapshot(course_id, lecture_id)
                variant = store().read(course_id, lecture_id, language, snapshot=snapshot)
                return {
                    "draft": variant,
                    "originals": teaching_texts(snapshot.document),
                    "assessment_language": store().assessment_language(
                        course_id, lecture_id, snapshot
                    ),
                    "assessments": [
                        block.text
                        for section in snapshot.document.sections
                        for block in section.blocks
                        if block.type in {"checkpoint", "quiz", "component"} and block.text
                    ],
                }
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/languages/{language}/publish"
    )
    def publish(
        course_id: str,
        lecture_id: str,
        language: Language,
        approval: LanguageApproval,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        manager(request, context, course_id)
        try:
            with locked_course_state(store().layout.course_root(course_id)):
                variant = store().read(course_id, lecture_id, language)
                if variant is None:
                    raise ValueError("Generate and preview the language draft first.")
                snapshot = store().snapshot(course_id, lecture_id)
                variant = publish_variant(
                    variant,
                    snapshot,
                    approval.digest,
                    context.user_id,
                )
                store().declare_assessment_language(
                    course_id, lecture_id, snapshot, approval.assessment_language, context.user_id
                )
                store().write(course_id, lecture_id, variant, published=True)
            record_audit_event(
                app.state.database,
                context,
                event_type="course.language_published",
                target_type="lecture",
                target_id=f"{course_id}:{lecture_id}",
            )
            return variant
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/courses/{course_id}/lectures/{lecture_id}/canvas/languages")
    def languages(
        course_id: str, lecture_id: str, context: TenantContext = Depends(request_context)
    ):
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=lectures,
        )
        current, stale = [], []
        with locked_course_state(store().layout.course_root(course_id)):
            snapshot = store().snapshot(course_id, lecture_id)
            for language in ("de", "en"):
                try:
                    variant = store().read(
                        course_id, lecture_id, language, published=True, snapshot=snapshot
                    )
                    if variant:
                        current.append(variant.model_dump(exclude={"published_by"}))
                except ValueError:
                    stale.append(language)
        return {
            "variants": current,
            "unavailable_languages": stale,
            "originals": teaching_texts(snapshot.document),
            "canonical_language": store().assessment_language(course_id, lecture_id, snapshot),
        }
