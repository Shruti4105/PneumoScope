from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.image_validation import ImageValidationError, validate_upload
from tests.conftest import make_xray_png


def _jpeg(w=300, h=300) -> bytes:
    b = io.BytesIO()
    Image.new("L", (w, h), 120).save(b, format="JPEG")
    return b.getvalue()


def test_accepts_png_and_jpeg():
    assert validate_upload("x.png", "image/png", make_xray_png()).size == (320, 300)
    assert validate_upload("x.JPG", "image/jpeg", _jpeg()).size == (300, 300)


@pytest.mark.parametrize("name,ctype,data,code", [
    ("x.png", "image/png", b"", 422),
    ("x.gif", "image/gif", b"GIF89a....", 415),
    ("x.png", "image/png", b"not an image at all", 415),
    ("x.png", "text/html", b"\x89PNG\r\n\x1a\n", 415),
    ("x.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, 422),
])
def test_rejects_invalid(name, ctype, data, code):
    with pytest.raises(ImageValidationError) as e:
        validate_upload(name, ctype, data)
    assert e.value.status_code == code


def test_rejects_too_small():
    with pytest.raises(ImageValidationError, match="too small"):
        validate_upload("x.jpg", "image/jpeg", _jpeg(64, 64))


def test_rejects_oversized_file():
    with pytest.raises(ImageValidationError) as e:
        validate_upload("x.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"0" * (11 * 1024 * 1024))
    assert e.value.status_code == 413


def test_extension_mismatch_rejected():
    with pytest.raises(ImageValidationError):
        validate_upload("x.exe", "image/png", make_xray_png())
