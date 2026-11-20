"""Secure storage for uploaded images and generated visualisations.

* filenames are random IDs — user-supplied names are never used or stored
* images are re-encoded as PNG, which strips EXIF / embedded metadata
* every read resolves the path and checks it stays inside the storage root
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from app.config import get_settings


def _safe(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise PermissionError("Path escapes storage root")
    return p


def save_upload(analysis_id: str, img: Image.Image) -> str:
    s = get_settings()
    rel = f"{analysis_id}.png"
    clean = Image.fromarray(np.asarray(img.convert("L"), dtype=np.uint8), "L")  # pixels only — no metadata
    clean.save(_safe(s.uploads_dir, rel), format="PNG", optimize=True)
    return rel


def upload_path(rel: str) -> Path:
    return _safe(get_settings().uploads_dir, rel)


def load_upload(rel: str) -> Image.Image:
    with Image.open(upload_path(rel)) as im:
        im.load()
        return im.convert("RGB")


def save_gradcam(analysis_id: str, cam: np.ndarray, heat_rgba: np.ndarray, overlay_rgb: np.ndarray,
                 base_gray: np.ndarray) -> str:
    s = get_settings()
    rel = analysis_id
    d = _safe(s.gradcam_dir, rel)
    d.mkdir(parents=True, exist_ok=True)
    Image.fromarray(heat_rgba, "RGBA").save(d / "heatmap.png")
    Image.fromarray(overlay_rgb, "RGB").save(d / "overlay.png")
    Image.fromarray(base_gray, "L").save(d / "original.png")
    np.save(d / "cam.npy", cam.astype(np.float16))
    return rel


def gradcam_file(rel: str, kind: str) -> Path:
    if kind not in {"heatmap", "overlay", "original"}:
        raise ValueError("unknown kind")
    return _safe(get_settings().gradcam_dir, f"{rel}/{kind}.png")


def delete_analysis_files(image_rel: str | None, gradcam_rel: str | None) -> None:
    s = get_settings()
    if image_rel:
        p = _safe(s.uploads_dir, image_rel)
        p.unlink(missing_ok=True)
        p.with_suffix(".thumb.webp").unlink(missing_ok=True)
    if gradcam_rel:
        d = _safe(s.gradcam_dir, gradcam_rel)
        if d.exists():
            for f in d.iterdir():
                f.unlink(missing_ok=True)
            d.rmdir()
