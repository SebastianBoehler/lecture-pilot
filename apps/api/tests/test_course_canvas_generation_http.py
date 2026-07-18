from types import SimpleNamespace
from typing import NoReturn

from fastapi import HTTPException
import pytest

from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_generation_http import run_canvas_generation_request
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_service import CANVAS_GENERATION_LEASE_SECONDS
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.tenancy import TenantContext


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_repairable"),
    [
        (CanvasGenerationRepairableError("Generated math is invalid."), True),
        (ProviderConfigurationError("Provider API key is missing."), False),
    ],
)
async def test_only_generated_content_failures_are_repairable(
    tmp_path, error: Exception, expected_repairable: bool
) -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(
        StorageLayout(tmp_path), lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
    )

    async def fail_generation(_generation_id: str, _attempt: int) -> NoReturn:
        raise error

    with pytest.raises(HTTPException) as caught:
        await run_canvas_generation_request(
            app=app,
            store=store,
            course_id="course-1",
            lecture_id="lecture-01",
            context=TenantContext(tenant_id="tenant-1", user_id="professor-1", roles=frozenset()),
            request_key=f"request-key-{expected_repairable!s:>16}".replace(" ", "0"),
            generate=fail_generation,
        )

    assert (caught.value.headers or {}).get("X-Generation-Repairable") == (
        "true" if expected_repairable else None
    )
