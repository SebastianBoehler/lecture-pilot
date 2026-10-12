from __future__ import annotations


CLIENT_CONTRACT_HEADER = "X-LecturePilot-Client-Contract"
CLIENT_CONTRACT_VERSION = "1"
CLIENT_UPDATE_REQUIRED_CODE = "client_update_required"
CLIENT_UPDATE_REQUIRED_DETAIL = "LecturePilot was updated. Reload this page to continue."


class ClientUpdateRequiredError(RuntimeError):
    pass


def require_current_client_contract(value: str | None) -> None:
    if value != CLIENT_CONTRACT_VERSION:
        raise ClientUpdateRequiredError(CLIENT_UPDATE_REQUIRED_DETAIL)
