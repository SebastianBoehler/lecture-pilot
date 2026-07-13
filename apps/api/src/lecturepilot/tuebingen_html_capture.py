from __future__ import annotations

from typing import Any, Callable

from lecturepilot.auth_diagnostics import current_auth_diagnostics


def prepare_alma_html_capture(api: Any) -> None:
    diagnostics = current_auth_diagnostics()
    if not diagnostics.html_capture_enabled:
        return
    from tue_api_wrapper.client import AlmaClient

    _prepare_authenticated_client(api, AlmaClient, "alma")


def prepare_ilias_html_capture(api: Any) -> None:
    diagnostics = current_auth_diagnostics()
    if not diagnostics.html_capture_enabled:
        return
    from tue_api_wrapper.ilias_client import IliasClient

    _prepare_authenticated_client(api, IliasClient, "ilias")


def _prepare_authenticated_client(
    api: Any,
    client_factory: Callable[[], Any],
    provider: str,
) -> None:
    diagnostics = current_auth_diagnostics()
    existing = getattr(api, "_client", None)
    if existing is not None:
        _install_hook(existing, diagnostics.response_hook(provider))
        return

    client = client_factory()
    _install_hook(client, diagnostics.response_hook(provider))
    try:
        client.login(api.credentials.username, api.credentials.password)
    except Exception:
        client.session.close()
        raise
    api._client = client


def _install_hook(client: Any, hook: Callable[..., None]) -> None:
    client.session.hooks.setdefault("response", []).append(hook)
