"""Create the website's images from the Kermany dataset (CC BY 4.0) and the trained model.

  python -m scripts.make_site_images

Writes to frontend/public/images/:
  hero-xray.webp     chest X-ray with a soft radial fade (home hero)
  login-bg.webp      wide, blue-toned X-ray background (login page)
  thumb-1..3.webp    small round thumbnails
  gradcam.webp       a real Grad-CAM overlay produced by the trained model
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import PROJECT_ROOT, get_settings  # noqa: E402

DATA = PROJECT_ROOT / "data" / "kermany" / "chest_xray" / "test"
OUT = PROJECT_ROOT / "frontend" / "public" / "images"


def load(path: Path) -> Image.Image:
    with Image.open(path) as im:
        return ImageOps.autocontrast(im.convert("L"), cutoff=1)


def square_crop(img: Image.Image, top_bias: float = 0.42) -> Image.Image:
    w, h = img.size
    s = min(w, h)
    left = (w - s) // 2
    top = int((h - s) * top_bias)
    return img.crop((left, top, left + s, top + s))


def radial_alpha(size: int, inner: float = 0.52, outer: float = 0.98) -> Image.Image:
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    a = np.clip((outer - r) / (outer - inner), 0, 1) ** 1.6
    return Image.fromarray((a * 255).astype(np.uint8), "L")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    normals = sorted((DATA / "NORMAL").glob("*.jpeg"))
    pneumonia = sorted((DATA / "PNEUMONIA").glob("*.jpeg"))

    # Hero: clean normal radiograph, faded edges, slightly cool silver tone.
    src_hero = load(normals[10])
    k = 860 / max(src_hero.size)
    src_hero = src_hero.resize((int(src_hero.width * k), int(src_hero.height * k)), Image.LANCZOS)
    hero = Image.new("L", (900, 900), 0)
    hero.paste(src_hero, ((900 - src_hero.width) // 2, (900 - src_hero.height) // 2))
    hero = ImageEnhance.Contrast(hero).enhance(1.1)
    # warm, slightly amber silver to match the dark/orange theme
    tint = Image.merge("RGB", [hero, hero.point(lambda v: int(v * 0.9)), hero.point(lambda v: int(v * 0.78))])
    rgba = tint.convert("RGBA")
    # fade both radially and at the image's own edges so no hard border shows
    content = Image.new("L", (900, 900), 0)
    content.paste(255, ((900 - src_hero.width) // 2 + 40, (900 - src_hero.height) // 2 + 30,
                        (900 + src_hero.width) // 2 - 40, (900 + src_hero.height) // 2 - 30))
    content = content.filter(ImageFilter.GaussianBlur(45))
    alpha = np.asarray(radial_alpha(900, inner=0.55, outer=1.0), dtype=np.float32) * np.asarray(content, dtype=np.float32) / 255
    rgba.putalpha(Image.fromarray(alpha.astype(np.uint8), "L"))
    rgba.save(OUT / "hero-xray.webp", quality=86, method=6)

    # Login background: a landscape chest X-ray cropped to 16:9 so it fills the
    # whole page with no empty sides, warm-toned with a soft vignette.
    wide = load(DATA / "NORMAL" / "NORMAL2-IM-0123-0001.jpeg")
    w0, h0 = wide.size
    wide = wide.crop((int(w0 * 0.035), int(h0 * 0.02), int(w0 * 0.965), h0))  # trim scanner border
    wide = ImageOps.fit(wide, (1920, 1080), method=Image.LANCZOS, centering=(0.5, 0.42))
    wide = wide.filter(ImageFilter.GaussianBlur(0.8))
    yy, xx = np.mgrid[0:1080, 0:1920]
    vig = np.clip(1.25 - np.sqrt(((xx - 960) / 1100) ** 2 + ((yy - 520) / 760) ** 2), 0.35, 1.0)
    wide = Image.fromarray((np.asarray(wide, dtype=np.float32) * vig).astype(np.uint8))
    duo = ImageOps.colorize(wide, black="#0A0807", mid="#4A2E1C", white="#F0C9A0", midpoint=115)
    duo.save(OUT / "login-bg.webp", quality=84, method=6)

    # App background: warm, dark, cinematic X-ray with a strong vignette.
    ab = load(normals[10])
    scale = 1150 / ab.height
    ab = ab.resize((int(ab.width * scale), int(ab.height * scale)), Image.LANCZOS)
    canvas = Image.new("L", (1920, 1200), 0)
    canvas.paste(ab, ((1920 - ab.width) // 2, -40))
    canvas = canvas.filter(ImageFilter.GaussianBlur(2.2))
    yy, xx = np.mgrid[0:1200, 0:1920]
    r = np.sqrt(((xx - 960) / 960) ** 2 + ((yy - 430) / 760) ** 2)
    vignette = np.clip(1.15 - r, 0, 1) ** 1.4
    edge = Image.new("L", (1920, 1200), 0)
    edge.paste(255, ((1920 - ab.width) // 2 + 70, 0, (1920 + ab.width) // 2 - 70, 1200))
    vignette = vignette * np.asarray(edge.filter(ImageFilter.GaussianBlur(70)), dtype=np.float32) / 255
    canvas = Image.fromarray((np.asarray(canvas, dtype=np.float32) * vignette * 0.85).astype(np.uint8))
    warm = ImageOps.colorize(canvas, black="#0A0807", mid="#3A2618", white="#E6B98A", midpoint=120)
    warm.save(OUT / "app-bg.webp", quality=80, method=6)

    # Small round thumbnails.
    for i, p in enumerate([normals[20], pneumonia[5], pneumonia[40]], start=1):
        t = square_crop(load(p)).resize((128, 128), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (128, 128), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).ellipse((0, 0, 127, 127), fill=255)
        t.putalpha(mask)
        t.save(OUT / f"thumb-{i}.webp", quality=85)

    # A real Grad-CAM overlay from the trained model.
    from app.ml.artifacts import load_bundle
    from app.ml.preprocessing import display_image, to_model_tensor
    from app.services.gradcam_service import compute_gradcam, overlay
    bundle = load_bundle(get_settings().model_dir)
    from app.services.gradcam_service import cam_statistics
    best = None
    for p in pneumonia[:30]:  # pick a case where attention sits on the lung fields
        im = Image.open(p).convert("RGB")
        c, _ = compute_gradcam(bundle.model, to_model_tensor(im), "PNEUMONIA")
        st = cam_statistics(c)
        score = st["central_energy_fraction"] - st["border_energy_fraction"]
        if best is None or score > best[0]:
            best = (score, im, c)
    _, src, cam = best
    over = overlay(display_image(src, cam.shape[0]), cam, 0.55)
    Image.fromarray(over).resize((360, 360), Image.LANCZOS).save(OUT / "gradcam.webp", quality=88)

    for f in sorted(OUT.iterdir()):
        print(f"{f.name:16} {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
