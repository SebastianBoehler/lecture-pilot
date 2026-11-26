"""Validate the bounded transport envelope without decoding image pixels."""

import base64
from typing import Annotated

from pydantic import BeforeValidator

MAX_CAMERA_BASE64_LENGTH = 640_000


def decode_camera_frame(value: object) -> bytes:
    if not isinstance(value, str) or len(value) > MAX_CAMERA_BASE64_LENGTH:
        raise ValueError("Camera frame must be a base64 JPEG of at most 480 KB.")
    try:
        image = base64.b64decode(value, validate=True)
    except ValueError:
        raise ValueError("Camera frame must be a base64 JPEG.") from None
    if not image.startswith(b"\xff\xd8\xff") or not image.endswith(b"\xff\xd9"):
        raise ValueError("Camera frame must be a JPEG.")
    return image


CameraFrame = Annotated[bytes, BeforeValidator(decode_camera_frame, json_schema_input_type=str)]
