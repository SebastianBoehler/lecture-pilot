from __future__ import annotations

from lecturepilot.api_auth import require_learner_workspace_access
from lecturepilot.models import AgentTurnInput
from lecturepilot.tenancy import TenantContext


def authorize_agent_turn(
    context: TenantContext,
    *,
    course_tenant_id: str,
    turn: AgentTurnInput,
) -> None:
    require_learner_workspace_access(
        context,
        learner_user_id=turn.user_id,
        course_tenant_id=course_tenant_id,
    )
