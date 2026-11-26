"""Short-lived, same-account handoff of one handwritten page."""

from base64 import b64encode
from dataclasses import dataclass
from secrets import token_urlsafe
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Response
from pydantic import BaseModel, ConfigDict

from lecturepilot.courses.course_access import require_lecture_id_access
from lecturepilot.identity.api_auth import request_context
from lecturepilot.identity.tenancy import TenantContext
from lecturepilot.tutor.camera_frame import CameraFrame

PAIR_LIFETIME_SECONDS = 15 * 60
MAX_PAIRS = 64
MAX_PAIRS_PER_ACCOUNT = 3
PairCode = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{32}$")]


class InkPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image: CameraFrame


@dataclass
class InkPair:
    owner: tuple[str, str, str, str]
    expires_at: float
    image: bytes | None = None


def register_ink_pairing_routes(app: FastAPI, **seeded) -> None:
    pairs: dict[str, InkPair] = {}
    lock = Lock()
    root = "/courses/{course_id}/lectures/{lecture_id}/ink-pair"

    def authorize(course_id: str, lecture_id: str, context: TenantContext):
        require_lecture_id_access(
            app, context, course_id=course_id, lecture_id=lecture_id, **seeded
        )

    def owner(course_id: str, lecture_id: str, context: TenantContext):
        return context.tenant_id, context.user_id, course_id, lecture_id

    def expire():
        now = monotonic()
        for key in [key for key, pair in pairs.items() if pair.expires_at <= now]:
            del pairs[key]

    def find(key, code):
        expire()
        pair = pairs.get(code)
        if pair is None or pair.owner != key:
            raise HTTPException(404, "This iPad pairing expired or belongs to another account.")
        return pair

    @app.post(root)
    def create(course_id: str, lecture_id: str, context: TenantContext = Depends(request_context)):
        authorize(course_id, lecture_id, context)
        key = owner(course_id, lecture_id, context)
        with lock:
            expire()
            if len(pairs) >= MAX_PAIRS:
                raise HTTPException(503, "Too many iPad pairings. Try again shortly.")
            if sum(pair.owner[:2] == key[:2] for pair in pairs.values()) >= MAX_PAIRS_PER_ACCOUNT:
                raise HTTPException(429, "Close an existing iPad pairing and try again.")
            code = token_urlsafe(24)
            pairs[code] = InkPair(key, monotonic() + PAIR_LIFETIME_SECONDS)
        return {"code": code, "expires_in": PAIR_LIFETIME_SECONDS}

    @app.get(root + "/{code}")
    def read(
        course_id: str,
        lecture_id: str,
        code: PairCode,
        response: Response,
        context: TenantContext = Depends(request_context),
    ):
        key = owner(course_id, lecture_id, context)
        response.headers["Cache-Control"] = "no-store"
        with lock:
            image = find(key, code).image
        if image is None:
            return {"image": None}
        authorize(course_id, lecture_id, context)
        return {"image": b64encode(image).decode("ascii")}

    @app.put(root + "/{code}")
    def upload(
        course_id: str,
        lecture_id: str,
        code: PairCode,
        page: InkPage,
        context: TenantContext = Depends(request_context),
    ):
        key = owner(course_id, lecture_id, context)
        authorize(course_id, lecture_id, context)
        with lock:
            pair = find(key, code)
            if pair.image is not None and pair.image != page.image:
                raise HTTPException(409, "This pairing already received a page.")
            pair.image = page.image
        return {"received": True}

    @app.delete(root + "/{code}", status_code=204)
    def close(
        course_id: str,
        lecture_id: str,
        code: PairCode,
        context: TenantContext = Depends(request_context),
    ):
        key = owner(course_id, lecture_id, context)
        with lock:
            expire()
            pair = pairs.get(code)
            if pair is not None and pair.owner == key:
                del pairs[code]
