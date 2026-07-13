from __future__ import annotations

from lecturepilot.account_models import AccountResponse, LoginResult
from lecturepilot.identity_repository import AccountView


def login_result(
    account: AccountView,
    *,
    term: str,
    csrf_token: str,
) -> LoginResult:
    return LoginResult(
        username=account.username,
        display_name=account.display_name,
        email=account.email,
        term=term,
        tenant_id=account.tenant_id,
        account_type=account.account_type,
        university_role=account.university_role,
        roles=sorted(account.roles, key=lambda role: role.value),
        csrf_token=csrf_token,
        courses=list(account.courses),
        university_courses=list(account.university_courses),
        university_course_sync_status=account.university_course_sync_status,
    )


def account_response(account: AccountView) -> AccountResponse:
    return AccountResponse(
        user_id=account.user_id,
        username=account.username,
        display_name=account.display_name,
        email=account.email,
        tenant_id=account.tenant_id,
        account_type=account.account_type,
        university_role=account.university_role,
        roles=sorted(account.roles, key=lambda role: role.value),
        courses=list(account.courses),
        university_courses=list(account.university_courses),
        university_course_sync_status=account.university_course_sync_status,
    )
