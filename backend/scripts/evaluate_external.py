"""External validation on the RSNA Pneumonia Detection Challenge (domain-shift probe).

RSNA data require accepting the Kaggle competition terms, so they are supplied
by the researcher:

  python -m scripts.evaluate_external --images <stage_2_train_images> \
      --labels <stage_2_train_labels.csv> [--model v1.0.0] [--limit 2000]

Label mapping: an image is positive if any row for its patientId has Target=1
("Lung Opacity"), negative otherwise. This is not identical to Kermany's
pneumonia label and the difference is part of the measured domain shift.

The result is written into the bundle's evaluation.json under external.rsna,
and a dataset card is written to artifacts/datasets/rsna/dataset_card.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402
from app.ml.artifacts import load_bundle  # noqa: E402
from app.ml.mc_dropout import mc_head_logits  # noqa: E402
from app.ml.preprocessing import image_descriptors, to_model_tensor  # noqa: E402
from scripts.train_pipeline import evaluate_split  # noqa: E402


def load_image(path: Path) -> Image.Image:
    if path.suffix.lower() == ".dcm":
        try:
            import pydicom
        except ImportError:
            sys.exit("pydicom is required for DICOM input: pip install pydicom")
        ds = pydicom.dcmread(str(path))
        arr = ds.pixel_array.astype(np.float64)
        arr = (255 * (arr - arr.min()) / max(arr.max() - arr.min(), 1)).astype(np.uint8)
        if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
            arr = 255 - arr
        return Image.fromarray(arr).convert("RGB")
    with Image.open(path) as im:
        return im.convert("RGB")


def main() -> None:
    s = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--model", default=None, help="model version (default: newest bundle)")
    ap.add_argument("--limit", type=int, default=2000, help="balanced sample size (0 = all)")
    args = ap.parse_args()

    bundles = sorted(p for p in s.models_dir.iterdir() if (p / "config.json").exists())
    bdir = s.models_dir / args.model if args.model else bundles[-1]
    bundle = load_bundle(bdir)
    labels = pd.read_csv(args.labels).groupby("patientId")["Target"].max().reset_index()
    if args.limit:
        n = args.limit // 2
        labels = pd.concat([labels[labels.Target == 1].sample(min(n, (labels.Target == 1).sum()), random_state=0),
                            labels[labels.Target == 0].sample(min(n, (labels.Target == 0).sum()), random_state=0)])
    rows, logits, ys = [], [], []
    for i, r in enumerate(labels.itertuples()):
        p = next((args.images / f"{r.patientId}{ext}" for ext in (".dcm", ".png", ".jpg") if (args.images / f"{r.patientId}{ext}").exists()), None)
        if p is None:
            continue
        img = load_image(p)
        d = image_descriptors(img)
        rows.append({k: v for k, v in d.items() if k != "intensity_hist"})
        with torch.no_grad():
            f = bundle.model.features(to_model_tensor(img).unsqueeze(0))
            logits.append(mc_head_logits(bundle.model.head, f, bundle.mc_passes, bundle.config.get("mc_seed")).numpy()[:, 0])
        ys.append(int(r.Target))
        if i % 200 == 0:
            print(f"  {i}/{len(labels)}")
    if not ys:
        sys.exit("No images matched the label file.")
    y = np.array(ys)
    result = evaluate_split("rsna_external_probe", np.stack(logits, axis=1).astype(np.float64), y,
                            bundle.temperature, bundle.policy.refer_threshold)
    ev_path = bdir / "evaluation.json"
    ev = json.loads(ev_path.read_text())
    ev["external"] = {"rsna": result, "status": "evaluated", "evaluated_at": datetime.now(timezone.utc).isoformat(),
                      "note": "RSNA 'Lung Opacity' target used as positive label; balanced sample."}
    ev_path.write_text(json.dumps(ev), encoding="utf-8")
    # NOTE: evaluation.json is not part of the config hash, so the deployed policy is unchanged.

    df = pd.DataFrame(rows)
    card = {"key": "rsna", "generated_at": datetime.now(timezone.utc).isoformat(), "total_images": int(len(y)),
            "class_distribution": {"PNEUMONIA": int(y.sum()), "NORMAL": int((1 - y).sum())},
            "dimensions": {"width": {"min": int(df.width.min()), "median": float(df.width.median()), "max": int(df.width.max())},
                           "height": {"min": int(df.height.min()), "median": float(df.height.median()), "max": int(df.height.max())}},
            "quality": {"brightness": {"mean": float(df.brightness.mean()), "std": float(df.brightness.std())},
                        "contrast": {"mean": float(df.contrast.mean()), "std": float(df.contrast.std())}}}
    (s.datasets_dir / "rsna").mkdir(parents=True, exist_ok=True)
    (s.datasets_dir / "rsna" / "dataset_card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    d = result["discrimination"]
    print(f"RSNA ROC-AUC {d['roc_auc']:.4f} acc {d['accuracy']:.4f} refer rate {result['refer_bands']['refer_rate']:.3f}")


if __name__ == "__main__":
    main()
