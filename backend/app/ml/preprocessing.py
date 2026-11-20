"""Image decoding, preprocessing and image descriptors.

The same functions are used by the training pipeline, the inference API and
the drift monitor, so the reference statistics and live statistics are
computed identically.
"""
from __future__ import annotations

import io

import numpy as np
import torch
from PIL import Image, ImageOps

IMAGE_SIZE = 224
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
HIST_BINS = 32

Image.MAX_IMAGE_PIXELS = 80_000_000  # decompression-bomb guard


def decode_image(data: bytes) -> Image.Image:
    """Decode bytes into an RGB PIL image with EXIF orientation applied."""
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    if img.mode in ("I;16", "I;16B", "I"):
        arr = np.asarray(img, dtype=np.float64)
        arr = (255 * (arr - arr.min()) / max(arr.max() - arr.min(), 1)).astype(np.uint8)
        img = Image.fromarray(arr)
    return img.convert("RGB")


def to_grayscale_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.uint8)


def to_model_tensor(img: Image.Image) -> torch.Tensor:
    """Grayscale radiograph -> 3-channel, 224×224, ImageNet-normalised tensor [3,H,W].

    The whole image is resized (no centre crop) so peripheral lung fields are
    never cropped away.
    """
    gray = img.convert("L").resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)
    arr = np.asarray(gray, dtype=np.float32) / 255.0
    t = torch.from_numpy(arr).unsqueeze(0).repeat(3, 1, 1)
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    return (t - mean) / std


def display_image(img: Image.Image, size: int = IMAGE_SIZE) -> np.ndarray:
    """Grayscale uint8 [size,size] matching the model's spatial view (for Grad-CAM overlays)."""
    return np.asarray(img.convert("L").resize((size, size), Image.BILINEAR), dtype=np.uint8)


def colourfulness(img: Image.Image) -> float:
    """Hasler & Süsstrunk colourfulness, scaled to ~[0,1]. Radiographs are ~0."""
    small = img.convert("RGB").resize((128, 128))
    a = np.asarray(small, dtype=np.float64) / 255.0
    rg = a[..., 0] - a[..., 1]
    yb = 0.5 * (a[..., 0] + a[..., 1]) - a[..., 2]
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def image_descriptors(img: Image.Image) -> dict:
    """Input descriptors monitored for drift."""
    gray = to_grayscale_array(img)
    h, w = gray.shape
    hist256 = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    p = hist256 / hist256.sum()
    nz = p[p > 0]
    entropy = float(-(nz * np.log2(nz)).sum())
    hist = np.histogram(gray, bins=HIST_BINS, range=(0, 256))[0].astype(np.float64)
    hist = (hist / hist.sum()).round(6).tolist()
    return {
        "width": int(w),
        "height": int(h),
        "brightness": float(gray.mean() / 255.0),
        "contrast": float(gray.std() / 255.0),
        "intensity_entropy": entropy,
        "intensity_hist": hist,
    }


def quality_flags(img: Image.Image, desc: dict) -> tuple[list[str], list[str]]:
    """Return (blocking_flags, warnings). Blocking flags force a REFER decision."""
    blocking, warnings = [], []
    c = colourfulness(img)
    if c > 0.12:
        blocking.append(f"image contains significant colour (colourfulness {c:.2f}); it may not be a radiograph")
    if desc["contrast"] < 0.03:
        blocking.append("image has almost no contrast")
    aspect = desc["width"] / desc["height"]
    if aspect > 2.5 or aspect < 0.4:
        blocking.append(f"unusual aspect ratio {aspect:.2f}")
    if min(desc["width"], desc["height"]) < 256:
        warnings.append("low resolution (shorter side < 256 px)")
    if desc["brightness"] > 0.85 or desc["brightness"] < 0.1:
        warnings.append("extreme overall brightness")
    return blocking, warnings
