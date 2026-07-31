from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lecturepilot.ppi_exam_source_models import (
    PpiCatalogLecture,
    PpiCatalogResponse,
    PpiCredentials,
    PpiImportInput,
    PpiImportResult,
)
from lecturepilot.ppi_exam_source_store import PpiExamSourceStore


class PpiServiceError(RuntimeError):
    pass


class PpiCredentialsError(PpiServiceError):
    pass


class PpiAccessError(PpiServiceError):
    pass


class PpiIntegrationUnavailable(PpiServiceError):
    pass


class PpiExamSourceService:
    def __init__(
        self,
        store: PpiExamSourceStore,
        *,
        client_factory: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.store = store
        self.client_factory = client_factory or _authenticated_client

    def catalog(
        self, *, user_id: str, course_id: str, credentials: PpiCredentials
    ) -> PpiCatalogResponse:
        client = self._client(credentials)
        try:
            catalog = client.fetch_lecture_catalog()
            borrowed = client.fetch_borrowed_lectures()
            cached = self.store.list(user_id=user_id, course_id=course_id)
            cached_by_lecture = {item.ppi_lecture_id: item.id for item in cached}
            borrowed_by_id = {item.id: item for item in borrowed.lectures if item.id is not None}
            lectures = []
            for item in catalog.lectures:
                if item.id is None:
                    continue
                entitlement = borrowed_by_id.get(item.id)
                lectures.append(
                    PpiCatalogLecture(
                        id=item.id,
                        title=item.title,
                        protocol_count=item.protocol_count,
                        borrowed=item.borrowed or entitlement is not None,
                        can_borrow=item.can_borrow,
                        download_available=bool(entitlement and entitlement.download_available),
                        borrowed_until=(entitlement.borrowed_until if entitlement else None),
                        cached_source_id=cached_by_lecture.get(item.id),
                    )
                )
            return PpiCatalogResponse(
                tokens=catalog.tokens, lectures=lectures, cached_sources=cached
            )
        except Exception as exc:
            _raise_service_error(exc)
        finally:
            client.close()

    def import_source(
        self, *, user_id: str, course_id: str, input_data: PpiImportInput
    ) -> PpiImportResult:
        source_id = f"ppi-{input_data.ppi_lecture_id}"
        try:
            cached = self.store.read(user_id=user_id, course_id=course_id, source_id=source_id)
            return PpiImportResult(source=cached, token_spent=False, reused=True)
        except FileNotFoundError:
            pass
        client = self._client(input_data)
        try:
            lecture, entitlement, tokens = _remote_state(client, input_data.ppi_lecture_id)
            token_spent = False
            if entitlement is None:
                if not input_data.confirm_token_spend:
                    raise PpiAccessError(
                        "Set confirm_token_spend=true to borrow this lecture for one PPI token."
                    )
                lecture, entitlement, tokens = _remote_state(client, input_data.ppi_lecture_id)
                if entitlement is None:
                    if tokens <= 0:
                        raise PpiAccessError("No PPI tokens are available.")
                    if not lecture.can_borrow:
                        raise PpiAccessError("This PPI lecture cannot currently be borrowed.")
                    client.borrow_lecture(input_data.ppi_lecture_id)
                    token_spent = True
                    lecture, entitlement, _tokens = _remote_state(client, input_data.ppi_lecture_id)
            if entitlement is None or not entitlement.download_available:
                raise PpiAccessError("The PPI lecture is not currently available for download.")
            download = client.download_lecture(input_data.ppi_lecture_id)
            source = self.store.import_archive(
                user_id=user_id,
                course_id=course_id,
                lecture_id=input_data.ppi_lecture_id,
                title=lecture.title,
                protocol_count=lecture.protocol_count,
                filename=download.filename,
                archive=download.data,
                borrowed_until=entitlement.borrowed_until,
            )
            return PpiImportResult(source=source, token_spent=token_spent, reused=False)
        except PpiServiceError:
            raise
        except Exception as exc:
            _raise_service_error(exc)
        finally:
            client.close()

    def _client(self, credentials: PpiCredentials):
        try:
            return self.client_factory(
                credentials.username, credentials.password.get_secret_value()
            )
        except PpiServiceError:
            raise
        except Exception as exc:
            _raise_service_error(exc)


def _remote_state(client: Any, lecture_id: int) -> tuple[Any, Any | None, int]:
    catalog = client.fetch_lecture_catalog()
    lecture = next((item for item in catalog.lectures if item.id == lecture_id), None)
    if lecture is None:
        raise PpiAccessError("The selected PPI lecture was not found.")
    borrowed = client.fetch_borrowed_lectures()
    entitlement = next((item for item in borrowed.lectures if item.id == lecture_id), None)
    return lecture, entitlement, catalog.tokens


def _authenticated_client(username: str, password: str):
    try:
        from tue_api_wrapper import PpiClient
    except ImportError as exc:
        raise PpiIntegrationUnavailable(
            "PPI support is unavailable. Install the API with the tuebingen extra."
        ) from exc
    try:
        client = PpiClient()
    except Exception as exc:
        _raise_service_error(exc)
    try:
        client.login(username, password)
        return client
    except Exception as exc:
        try:
            client.close()
        finally:
            _raise_service_error(exc)


def _raise_service_error(exc: Exception) -> None:
    name = type(exc).__name__
    if name == "PpiAuthenticationError":
        raise PpiCredentialsError("PPI credentials were rejected.") from exc
    if name in {"PpiAccessError", "PpiValidationError"}:
        raise PpiAccessError("PPI rejected the requested operation.") from exc
    if isinstance(exc, PpiServiceError):
        raise exc
    raise PpiIntegrationUnavailable("PPI is temporarily unavailable. Please retry.") from exc
