"""Prepare the Kermany pediatric chest X-ray dataset.

* extracts ChestXRay2017.zip (chest_xray/ only; macOS metadata skipped)
* derives pseudonymous patient IDs from filenames
* builds a **patient-disjoint** train/val/test split (StratifiedGroupKFold)
* builds the **flawed** image-level random split used in the leakage experiment
* computes image-quality descriptors, exact and near-duplicate statistics
* writes ``data/kermany/manifest.csv`` and ``artifacts/datasets/kermany/dataset_card.json``

Usage:  python -m scripts.prepare_kermany --zip ../data/raw/ChestXRay2017.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import StratifiedGroupKFold, StratifiedShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402
from app.ml.preprocessing import image_descriptors  # noqa: E402

SEED = 42


def patient_id(fname: str, label: str) -> str:
    stem = Path(fname).stem
    m = re.match(r"(person\d+)_", stem)
    if m:
        return m.group(1)
    # NORMAL: IM-0115-0001 / NORMAL2-IM-0001-0001  -> drop the trailing image index
    return stem.rsplit("-", 1)[0] if "-" in stem else stem


def subtype(fname: str, label: str) -> str:
    if label == "NORMAL":
        return "normal"
    return "viral" if "virus" in fname.lower() else "bacterial"


NEAR_DUP_CORR = 0.985
THUMB = 32


def thumbnail_vector(img: Image.Image) -> np.ndarray:
    """32x32 grayscale thumbnail, zero-mean and unit-norm (for correlation)."""
    g = np.asarray(img.convert("L").resize((THUMB, THUMB), Image.BILINEAR), dtype=np.float32).ravel()
    g -= g.mean()
    n = np.linalg.norm(g)
    return g / n if n > 0 else g


def extract(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.startswith("chest_xray/") and not m.endswith("/")
                   and "__MACOSX" not in m and re.search(r"\.(jpe?g|png)$", m, re.I)]
        for i, m in enumerate(members):
            target = (out_dir / m).resolve()
            if not str(target).startswith(str(out_dir.resolve())):  # zip-slip guard
                raise RuntimeError(f"Unsafe path in archive: {m}")
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(m) as src, open(target, "wb") as dst:
                dst.write(src.read())
            if i % 1000 == 0:
                print(f"  extracted {i}/{len(members)}")


def near_duplicate_pairs(vecs: np.ndarray, thr: float = NEAR_DUP_CORR, chunk: int = 512) -> list[tuple[int, int, float]]:
    """Pairs whose thumbnail Pearson correlation >= thr (excludes self-pairs)."""
    pairs = []
    for s0 in range(0, len(vecs), chunk):
        block = vecs[s0:s0 + chunk] @ vecs.T
        ii, jj = np.nonzero(block >= thr)
        for i, j in zip(ii, jj):
            gi = s0 + int(i)
            if int(j) > gi:
                pairs.append((gi, int(j), float(block[i, j])))
    return pairs


def split_patient_disjoint(df: pd.DataFrame) -> pd.Series:
    y, g = df["label_int"].values, df["patient_id"].values
    outer = StratifiedGroupKFold(n_splits=7, shuffle=True, random_state=SEED)
    trval_idx, test_idx = next(outer.split(df, y, g))
    inner = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=SEED)
    tr_rel, va_rel = next(inner.split(df.iloc[trval_idx], y[trval_idx], g[trval_idx]))
    split = np.array(["train"] * len(df), dtype=object)
    split[trval_idx[va_rel]] = "val"
    split[test_idx] = "test"
    return pd.Series(split, index=df.index)


def split_flawed(df: pd.DataFrame) -> pd.Series:
    """Image-level random split that ignores patient identity (the flawed default)."""
    y = df["label_int"].values
    s1 = StratifiedShuffleSplit(n_splits=1, test_size=1 / 7, random_state=SEED)
    trval_idx, test_idx = next(s1.split(df, y))
    s2 = StratifiedShuffleSplit(n_splits=1, test_size=1 / 6, random_state=SEED)
    tr_rel, va_rel = next(s2.split(df.iloc[trval_idx], y[trval_idx]))
    split = np.array(["train"] * len(df), dtype=object)
    split[trval_idx[va_rel]] = "val"
    split[test_idx] = "test"
    return pd.Series(split, index=df.index)


def overlap_report(df: pd.DataFrame, col: str) -> dict:
    sets = {s: set(df.loc[df[col] == s, "patient_id"]) for s in ("train", "val", "test")}
    test_imgs_with_train_patient = int(df[(df[col] == "test") & df["patient_id"].isin(sets["train"])].shape[0])
    return {
        "patients_train_test_overlap": len(sets["train"] & sets["test"]),
        "patients_train_val_overlap": len(sets["train"] & sets["val"]),
        "patients_val_test_overlap": len(sets["val"] & sets["test"]),
        "test_images_from_train_patients": test_imgs_with_train_patient,
        "test_images": int((df[col] == "test").sum()),
    }


def split_summary(df: pd.DataFrame, col: str) -> list[dict]:
    out = []
    for s in ("train", "val", "test"):
        d = df[df[col] == s]
        out.append({"split": s, "images": int(len(d)), "patients": int(d["patient_id"].nunique()),
                    "normal": int((d["label"] == "NORMAL").sum()), "pneumonia": int((d["label"] == "PNEUMONIA").sum())})
    return out


def hist(values, bins=20) -> list[dict]:
    c, e = np.histogram(values, bins=bins)
    return [{"bin_lower": float(e[i]), "bin_upper": float(e[i + 1]), "count": int(n)} for i, n in enumerate(c)]


def main() -> None:
    s = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, default=s.data_dir / "raw" / "ChestXRay2017.zip")
    ap.add_argument("--out", type=Path, default=s.data_dir / "kermany")
    args = ap.parse_args()

    print(f"Extracting {args.zip} ...")
    extract(args.zip, args.out)
    root = args.out / "chest_xray"

    rows, thumbs = [], []
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in (".jpeg", ".jpg", ".png"))
    print(f"Computing descriptors for {len(files)} images ...")
    for i, p in enumerate(files):
        label = p.parent.name.upper()
        data = p.read_bytes()
        with Image.open(p) as im:
            im.load()
            mode = im.mode
            d = image_descriptors(im)
            thumbs.append(thumbnail_vector(im))
        rows.append({
            "path": p.relative_to(args.out).as_posix(), "label": label,
            "label_int": int(label == "PNEUMONIA"), "subtype": subtype(p.name, label),
            "original_split": p.parent.parent.name, "patient_id": patient_id(p.name, label),
            "md5": hashlib.md5(data).hexdigest(), "file_bytes": len(data), "mode": mode,
            **{k: v for k, v in d.items() if k != "intensity_hist"},
        })
        if i % 500 == 0:
            print(f"  {i}/{len(files)}")
    df = pd.DataFrame(rows)
    df["split"] = split_patient_disjoint(df)
    df["split_flawed"] = split_flawed(df)

    # Duplicates
    exact_groups = df.groupby("md5").size()
    exact_dupe_images = int((df["md5"].map(exact_groups) > 1).sum())
    pairs = near_duplicate_pairs(np.stack(thumbs))
    md5_split = df.groupby("md5")["split"].nunique()
    exact_cross_split = int((md5_split > 1).sum())
    cross_split_pd = sum(1 for i, j, _ in pairs if df.at[i, "split"] != df.at[j, "split"])
    cross_split_flawed = sum(1 for i, j, _ in pairs if df.at[i, "split_flawed"] != df.at[j, "split_flawed"])
    cross_patient = sum(1 for i, j, _ in pairs if df.at[i, "patient_id"] != df.at[j, "patient_id"])

    manifest = args.out / "manifest.csv"
    df.to_csv(manifest, index=False)
    print(f"Manifest written: {manifest}")

    per_patient = df.groupby("patient_id").size()
    card = {
        "key": "kermany",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_images": int(len(df)),
        "total_patients": int(df["patient_id"].nunique()),
        "class_distribution": {k: int(v) for k, v in df["label"].value_counts().items()},
        "subtype_distribution": {k: int(v) for k, v in df["subtype"].value_counts().items()},
        "original_folder_split": [
            {"split": sp, "images": int((df["original_split"] == sp).sum()),
             "normal": int(((df["original_split"] == sp) & (df["label"] == "NORMAL")).sum()),
             "pneumonia": int(((df["original_split"] == sp) & (df["label"] == "PNEUMONIA")).sum())}
            for sp in sorted(df["original_split"].unique())],
        "patient_disjoint_split": {"method": "StratifiedGroupKFold (groups = patient ID), seed 42",
                                   "splits": split_summary(df, "split"), "overlap": overlap_report(df, "split")},
        "flawed_split": {"method": "StratifiedShuffleSplit at image level (ignores patient ID), seed 42",
                         "splits": split_summary(df, "split_flawed"), "overlap": overlap_report(df, "split_flawed")},
        "images_per_patient": {"mean": float(per_patient.mean()), "median": float(per_patient.median()),
                               "max": int(per_patient.max()),
                               "patients_with_multiple_images": int((per_patient > 1).sum())},
        "dimensions": {
            "width": {"min": int(df.width.min()), "median": float(df.width.median()), "max": int(df.width.max())},
            "height": {"min": int(df.height.min()), "median": float(df.height.median()), "max": int(df.height.max())},
            "aspect_ratio_median": float((df.width / df.height).median()),
            "width_histogram": hist(df.width), "height_histogram": hist(df.height),
        },
        "image_modes": {k: int(v) for k, v in Counter(df["mode"]).items()},
        "quality": {
            "brightness": {"mean": float(df.brightness.mean()), "std": float(df.brightness.std()),
                           "histogram": hist(df.brightness)},
            "contrast": {"mean": float(df.contrast.mean()), "std": float(df.contrast.std()),
                         "histogram": hist(df.contrast)},
            "intensity_entropy": {"mean": float(df.intensity_entropy.mean()),
                                  "std": float(df.intensity_entropy.std()),
                                  "histogram": hist(df.intensity_entropy)},
            "by_class": {lab: {"brightness": float(g.brightness.mean()), "contrast": float(g.contrast.mean()),
                               "width": float(g.width.median()), "height": float(g.height.median())}
                         for lab, g in df.groupby("label")},
        },
        "duplicates": {
            "exact_duplicate_images": exact_dupe_images,
            "exact_duplicate_groups": int((exact_groups > 1).sum()),
            "near_duplicate_pairs": len(pairs),
            "near_duplicate_method": f"Pearson correlation of 32x32 thumbnails >= {NEAR_DUP_CORR}",
            "exact_duplicate_groups_across_patient_disjoint_splits": exact_cross_split,
            "near_duplicate_pairs_cross_patient": cross_patient,
            "near_duplicate_pairs_across_patient_disjoint_splits": cross_split_pd,
            "near_duplicate_pairs_across_flawed_splits": cross_split_flawed,
        },
    }
    out_dir = s.datasets_dir / "kermany"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dataset_card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(json.dumps({k: card[k] for k in ("total_images", "total_patients", "class_distribution")}, indent=2))
    print("Patient-disjoint overlap:", card["patient_disjoint_split"]["overlap"])
    print("Flawed split overlap:", card["flawed_split"]["overlap"])
    print("Duplicates:", card["duplicates"])


if __name__ == "__main__":
    main()
