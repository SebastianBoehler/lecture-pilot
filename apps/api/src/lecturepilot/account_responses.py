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
        email=account.email,
        term=term,
        tenant_id=account.tenant_id,
        account_type=account.account_type,
        university_role=account.university_role,
        roles=sorted(account.roles, key=lambda role: role.value),
        professor_status=account.professor_status,
        csrf_token=csrf_token,
        courses=list(account.courses),
    )


def account_response(account: AccountView) -> AccountResponse:
    return AccountResponse(
        user_id=account.user_id,
        username=account.username,
        email=account.email,
        tenant_id=account.tenant_id,
        account_type=account.account_type,
        university_role=account.university_role,
        roles=sorted(account.roles, key=lambda role: role.value),
        professor_status=account.professor_status,
        courses=list(account.courses),
    )
