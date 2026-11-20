"""Validation of uploaded image files (type, size, integrity, dimensions)."""
from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.ml.preprocessing import decode_image

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_FORMATS = {"JPEG", "PNG"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/octet-stream", ""}


class ImageValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _magic_ok(data: bytes) -> bool:
    return data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")


def validate_upload(filename: str | None, content_type: str | None, data: bytes) -> Image.Image:
    s = get_settings()
    if not data:
        raise ImageValidationError("The uploaded file is empty.")
    if len(data) > s.max_upload_bytes:
        raise ImageValidationError(f"File exceeds the {s.max_upload_mb:g} MB limit.", 413)
    name = (filename or "").lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError("Unsupported file type. Upload a JPG, JPEG or PNG image.", 415)
    if (content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise ImageValidationError("Unsupported content type. Upload a JPG, JPEG or PNG image.", 415)
    if not _magic_ok(data):
        raise ImageValidationError("File content is not a valid JPEG or PNG image.", 415)
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise ImageValidationError("The image could not be decoded. It may be corrupted.")
    if fmt not in ALLOWED_FORMATS:
        raise ImageValidationError("Only JPEG and PNG images are supported.", 415)
    try:
        img = decode_image(data)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ImageValidationError("The image could not be decoded. It may be corrupted.")
    w, h = img.size
    if min(w, h) < s.min_image_side:
        raise ImageValidationError(f"Image is too small ({w}×{h}). Minimum side is {s.min_image_side} px.")
    if max(w, h) > s.max_image_side:
        raise ImageValidationError(f"Image is too large ({w}×{h}). Maximum side is {s.max_image_side} px.")
    return img
