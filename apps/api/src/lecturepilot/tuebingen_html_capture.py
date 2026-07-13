from __future__ import annotations

from typing import Any, Callable

from lecturepilot.auth_diagnostics import AuthDiagnostics


def prepare_alma_html_capture(api: Any, diagnostics: AuthDiagnostics) -> None:
    if not diagnostics.html_capture_enabled:
        return
    from tue_api_wrapper.client import AlmaClient

    _prepare_authenticated_client(api, AlmaClient, "alma", diagnostics)


def prepare_ilias_html_capture(api: Any, diagnostics: AuthDiagnostics) -> None:
    if not diagnostics.html_capture_enabled:
        return
    from tue_api_wrapper.ilias_client import IliasClient

    _prepare_authenticated_client(api, IliasClient, "ilias", diagnostics)


def _prepare_authenticated_client(
    api: Any,
    client_factory: Callable[[], Any],
    provider: str,
    diagnostics: AuthDiagnostics,
) -> None:
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
