"""End-to-end training, calibration and evaluation pipeline.

Steps
-----
1. Extract ResNet-50 (ImageNet) features for every Kermany image (cached).
2. Optuna hyper-parameter search for the MC-Dropout head (logged to MLflow).
3. Train the final head on the patient-disjoint train split (early stopping on val).
4. 30-pass MC Dropout on validation -> fit temperature -> choose refer threshold.
5. Full evaluation on the patient-disjoint test split (bootstrap CIs, calibration
   before/after temperature scaling, selective-prediction curves, refer bands).
6. Leakage experiment: identical training on the flawed image-level split.
7. Write a versioned artefact bundle and log everything to MLflow.

The backbone is frozen (CPU-only budget); this is documented as a limitation.

Usage:  python -m scripts.train_pipeline [--trials 25] [--version v1.0.0]
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402
from app.ml import evaluation as ev  # noqa: E402
from app.ml.artifacts import canonical_hash, file_sha256  # noqa: E402
from app.ml.mc_dropout import deterministic_head_logits, mc_head_logits  # noqa: E402
from app.ml.preprocessing import HIST_BINS, IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD, to_model_tensor  # noqa: E402
from app.ml.resnet_model import FEATURE_DIM, MCDropoutHead, PneumoniaResNet50  # noqa: E402
from app.services import calibration_service as cal  # noqa: E402
from app.services.uncertainty_service import summarize_passes  # noqa: E402

SEED = 42
MC_PASSES = 30
MC_SEED = 20240611
MODEL_NAME = "pneumonia-resnet50-mcd"


def set_seed(seed: int = SEED) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


# --------------------------------------------------------------------------- features
def extract_features(df: pd.DataFrame, root: Path, cache: Path, batch: int = 32) -> np.ndarray:
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        if list(z["paths"]) == list(df["path"]):
            print(f"Loaded cached features {cache}")
            return z["features"]
    print("Extracting ResNet-50 features (frozen ImageNet backbone) ...")
    model = PneumoniaResNet50(pretrained_backbone=True).eval()
    feats = np.zeros((len(df), FEATURE_DIM), dtype=np.float32)
    t0 = time.time()
    with torch.no_grad():
        for start in range(0, len(df), batch):
            paths = df["path"].iloc[start:start + batch]
            xs = []
            for p in paths:
                with Image.open(root / p) as im:
                    xs.append(to_model_tensor(im.convert("RGB")))
            feats[start:start + len(xs)] = model.features(torch.stack(xs)).numpy()
            if (start // batch) % 20 == 0:
                done = start + len(xs)
                rate = done / max(time.time() - t0, 1e-6)
                print(f"  {done}/{len(df)}  ({rate:.1f} img/s)")
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, features=feats, paths=np.array(df["path"].tolist()))
    return feats


# --------------------------------------------------------------------------- head training
def train_head(xtr, ytr, xva, yva, *, lr, weight_decay, dropout, hidden, epochs=60, patience=8,
               batch=128, seed=SEED, verbose=False) -> tuple[MCDropoutHead, dict]:
    set_seed(seed)
    head = MCDropoutHead(FEATURE_DIM, hidden, dropout)
    opt = torch.optim.AdamW(head.parameters(), lr=lr, weight_decay=weight_decay)
    pos_weight = torch.tensor([(ytr == 0).sum() / max((ytr == 1).sum(), 1)], dtype=torch.float32)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    eval_loss = nn.BCEWithLogitsLoss()
    Xtr, Ytr = torch.from_numpy(xtr), torch.from_numpy(ytr.astype(np.float32))
    Xva, Yva = torch.from_numpy(xva), torch.from_numpy(yva.astype(np.float32))
    best, best_state, bad, history = float("inf"), None, 0, []
    g = torch.Generator().manual_seed(seed)
    for epoch in range(epochs):
        head.train()
        perm = torch.randperm(len(Xtr), generator=g)
        tot = 0.0
        for i in range(0, len(perm), batch):
            idx = perm[i:i + batch]
            opt.zero_grad()
            loss = loss_fn(head(Xtr[idx]), Ytr[idx])
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        with torch.no_grad():
            vl = eval_loss(deterministic_head_logits(head, Xva), Yva).item()
        history.append({"epoch": epoch, "train_loss": tot / len(Xtr), "val_loss": vl})
        if verbose:
            print(f"  epoch {epoch:02d} train {tot / len(Xtr):.4f} val {vl:.4f}")
        if vl < best - 1e-4:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in head.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    head.load_state_dict(best_state)
    head.eval()
    return head, {"best_val_loss": best, "epochs_run": len(history), "history": history}


def mc_logits(head, x: np.ndarray, passes=MC_PASSES, seed=MC_SEED) -> np.ndarray:
    return mc_head_logits(head, torch.from_numpy(x), passes=passes, seed=seed).numpy().astype(np.float64)


# --------------------------------------------------------------------------- policy
def choose_refer_threshold(prob: np.ndarray, entropy: np.ndarray, y: np.ndarray,
                           target_error: float = 0.03, max_refer_rate: float = 0.30) -> dict:
    """Largest entropy threshold (max coverage) whose auto-decided error on the
    validation set is <= target_error, subject to refer rate <= max_refer_rate."""
    pred = (prob >= 0.5).astype(int)
    err = (pred != y).astype(float)
    order = np.argsort(entropy)
    ent_sorted, err_sorted = entropy[order], err[order]
    cum_err = np.cumsum(err_sorted) / np.arange(1, len(y) + 1)
    min_cov = 1 - max_refer_rate
    best_k = None
    for k in range(len(y), 0, -1):
        if k / len(y) < min_cov:
            break
        if cum_err[k - 1] <= target_error:
            best_k = k
            break
    if best_k is None:
        best_k = int(np.ceil(min_cov * len(y)))
        method = f"refer-rate cap ({max_refer_rate:.0%}) — target error {target_error:.1%} not reachable on validation"
    else:
        method = f"max coverage s.t. validation auto-decision error <= {target_error:.1%} (refer rate <= {max_refer_rate:.0%})"
    if best_k >= len(y):
        thr = float(min(1.0, ent_sorted[-1] + 1e-6))
    else:
        thr = float((ent_sorted[best_k - 1] + ent_sorted[best_k]) / 2)
    thr = float(np.clip(thr, 1e-3, 1.0))
    return {"refer_threshold": thr, "method": method, "validation_refer_rate": float((entropy > thr).mean()),
            "validation_auto_error": float(err[entropy <= thr].mean()) if (entropy <= thr).any() else None,
            "target_error": target_error, "max_refer_rate": max_refer_rate}


# --------------------------------------------------------------------------- reporting
def evaluate_split(name: str, pass_logits: np.ndarray, y: np.ndarray, temperature: float,
                   refer_threshold: float, n_boot: int = 1000) -> dict:
    probs_raw = cal.mc_probs(pass_logits, 1.0)
    probs_cal = cal.mc_probs(pass_logits, temperature)
    s_raw = summarize_passes(probs_raw)
    s = summarize_passes(probs_cal)
    p, ent, mi = s["mean"], s["predictive_entropy"], s["mutual_information"]
    pred = (p >= 0.5).astype(int)
    correct = pred == y
    rng = np.random.default_rng(SEED)
    sample = rng.choice(len(y), size=min(400, len(y)), replace=False)
    return {
        "split": name,
        "n": int(len(y)),
        "n_pneumonia": int(y.sum()),
        "n_normal": int((1 - y).sum()),
        "discrimination": ev.discrimination(y, p),
        "bootstrap_ci": ev.bootstrap_ci(y, p, n_boot=n_boot),
        "calibration": {
            "temperature": temperature,
            "before": {"ece": cal.expected_calibration_error(s_raw["mean"], y),
                       "brier": cal.brier_score(s_raw["mean"], y), "nll": cal.nll(s_raw["mean"], y),
                       "reliability": cal.reliability_diagram(s_raw["mean"], y)},
            "after": {"ece": cal.expected_calibration_error(p, y), "brier": cal.brier_score(p, y),
                      "nll": cal.nll(p, y), "reliability": cal.reliability_diagram(p, y)},
        },
        "uncertainty": {
            "entropy": ev.selective_curves(y, p, ent),
            "mutual_information": ev.selective_curves(y, p, mi),
            "std": ev.selective_curves(y, p, s["std"]),
            "entropy_histogram_correct": ev.histogram(ent[correct], 20, (0, 1)),
            "entropy_histogram_incorrect": ev.histogram(ent[~correct], 20, (0, 1)),
            "entropy_histogram_all": ev.histogram(ent, 20, (0, 1)),
            "mean_entropy": float(ent.mean()),
            "mean_mutual_information": float(mi.mean()),
            "mean_std": float(s["std"].mean()),
            "scatter": [{"confidence": float(max(p[i], 1 - p[i])), "entropy": float(ent[i]),
                         "mi": float(mi[i]), "correct": bool(correct[i]), "label": int(y[i])} for i in sample],
        },
        "refer_bands": ev.refer_band_composition(y, p, ent, refer_threshold),
        # Per-case arrays (no identifiers) so the UI can re-apply a threshold interactively.
        "per_case": {"p": np.round(p, 5).tolist(), "entropy": np.round(ent, 5).tolist(),
                     "mi": np.round(mi, 5).tolist(), "label": y.astype(int).tolist()},
    }


def quantile_bins(values: np.ndarray, n: int = 10) -> list[float]:
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    return [float(e) for e in edges]


def reference_distribution(values: np.ndarray, n_bins: int = 10) -> dict:
    edges = quantile_bins(values, n_bins)
    counts = np.histogram(values, bins=edges)[0]
    finite = values[np.isfinite(values)]
    return {"bin_edges": [e if np.isfinite(e) else None for e in edges],
            "proportions": (counts / counts.sum()).round(6).tolist(),
            "mean": float(finite.mean()), "std": float(finite.std()),
            "p05": float(np.quantile(finite, 0.05)), "p50": float(np.quantile(finite, 0.5)),
            "p95": float(np.quantile(finite, 0.95)), "n": int(len(finite)),
            "histogram": ev.histogram(finite, 20)}


# --------------------------------------------------------------------------- main
def main() -> None:
    s = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=25)
    ap.add_argument("--version", default=None)
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--no-mlflow", action="store_true")
    ap.add_argument("--target-error", type=float, default=0.03,
                    help="max auto-decision error on validation used to pick the refer threshold")
    ap.add_argument("--max-refer-rate", type=float, default=0.30)
    args = ap.parse_args()

    torch.set_num_threads(max(1, torch.get_num_threads()))
    set_seed()
    data_root = s.data_dir / "kermany"
    df = pd.read_csv(data_root / "manifest.csv")
    feats = extract_features(df, data_root, s.data_dir / "features" / "kermany_resnet50.npz")
    y = df["label_int"].values.astype(np.int64)

    def idx(col, name): return np.nonzero(df[col].values == name)[0]
    tr, va, te = idx("split", "train"), idx("split", "val"), idx("split", "test")
    print(f"Patient-disjoint split: train {len(tr)}, val {len(va)}, test {len(te)}")

    version = args.version or f"v{datetime.now():%Y.%m.%d-%H%M}"
    use_mlflow = not args.no_mlflow
    if use_mlflow:
        import mlflow
        (s.data_dir.parent / "mlflow").mkdir(exist_ok=True)
        mlflow.set_tracking_uri(s.resolved_mlflow_uri)
        mlflow.set_experiment("pneumonia-mc-dropout")
        parent = mlflow.start_run(run_name=f"{MODEL_NAME}-{version}")
        run_id = parent.info.run_id
    else:
        run_id = None

    # ---- Optuna HPO --------------------------------------------------------------
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
            "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-2, log=True),
            "dropout": trial.suggest_float("dropout", 0.2, 0.6),
            "hidden": trial.suggest_categorical("hidden", [128, 256, 512]),
        }
        head, info = train_head(feats[tr], y[tr], feats[va], y[va], **params)
        pl = mc_logits(head, feats[va], passes=10)
        val_nll = cal.nll(cal.mc_probs(pl).mean(0), y[va])
        if use_mlflow:
            with mlflow.start_run(run_name=f"optuna-trial-{trial.number}", nested=True):
                mlflow.log_params(params)
                mlflow.log_metrics({"val_mc_nll": val_nll, "epochs_run": info["epochs_run"]})
        return val_nll

    print(f"Optuna: {args.trials} trials ...")
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=args.trials)
    best = study.best_params
    print("Best params:", best, "val NLL", round(study.best_value, 4))

    # ---- Final head --------------------------------------------------------------
    head, train_info = train_head(feats[tr], y[tr], feats[va], y[va], **best, verbose=True)

    # ---- Calibration + policy on validation ---------------------------------------
    val_logits = mc_logits(head, feats[va])
    temperature = cal.fit_temperature(val_logits, y[va])
    val_s = summarize_passes(cal.mc_probs(val_logits, temperature))
    policy = choose_refer_threshold(val_s["mean"], val_s["predictive_entropy"], y[va],
                                    target_error=args.target_error, max_refer_rate=args.max_refer_rate)
    print(f"Temperature {temperature:.4f}; refer threshold {policy['refer_threshold']:.4f} ({policy['method']})")

    # ---- Test evaluation ----------------------------------------------------------
    test_logits = mc_logits(head, feats[te])
    test_eval = evaluate_split("kermany_patient_disjoint_test", test_logits, y[te], temperature,
                               policy["refer_threshold"], n_boot=args.bootstrap)
    val_eval = evaluate_split("kermany_patient_disjoint_val", val_logits, y[va], temperature,
                              policy["refer_threshold"], n_boot=200)
    d = test_eval["discrimination"]
    print(f"TEST  ROC-AUC {d['roc_auc']:.4f}  PR-AUC {d['pr_auc']:.4f}  acc {d['accuracy']:.4f}  "
          f"recall {d['recall']:.4f}  spec {d['specificity']:.4f}  ECE {test_eval['calibration']['after']['ece']:.4f}")

    # ---- Leakage experiment --------------------------------------------------------
    ftr, fva, fte = idx("split_flawed", "train"), idx("split_flawed", "val"), idx("split_flawed", "test")
    fhead, _ = train_head(feats[ftr], y[ftr], feats[fva], y[fva], **best)
    f_val_logits = mc_logits(fhead, feats[fva])
    f_temp = cal.fit_temperature(f_val_logits, y[fva])
    f_test_logits = mc_logits(fhead, feats[fte])
    flawed_eval = evaluate_split("kermany_flawed_image_level_test", f_test_logits, y[fte], f_temp,
                                 policy["refer_threshold"], n_boot=args.bootstrap)
    card = json.loads((s.datasets_dir / "kermany" / "dataset_card.json").read_text())
    fd = flawed_eval["discrimination"]
    print(f"FLAWED ROC-AUC {fd['roc_auc']:.4f}  acc {fd['accuracy']:.4f}")

    def brief(e):
        dd = e["discrimination"]
        return {"n": e["n"], "roc_auc": dd["roc_auc"], "pr_auc": dd["pr_auc"], "accuracy": dd["accuracy"],
                "recall": dd["recall"], "specificity": dd["specificity"], "precision": dd["precision"],
                "f1": dd["f1"], "ece": e["calibration"]["after"]["ece"], "brier": e["calibration"]["after"]["brier"],
                "roc_auc_ci": e["bootstrap_ci"].get("roc_auc"), "accuracy_ci": e["bootstrap_ci"].get("accuracy")}

    leakage = {
        "description": "Identical head, hyper-parameters and training procedure; only the split differs.",
        "patient_disjoint": {**brief(test_eval), "overlap": card["patient_disjoint_split"]["overlap"]},
        "flawed_image_level": {**brief(flawed_eval), "overlap": card["flawed_split"]["overlap"]},
        "delta": {k: brief(flawed_eval)[k] - brief(test_eval)[k]
                  for k in ("roc_auc", "pr_auc", "accuracy", "recall", "specificity", "f1")},
    }

    # ---- Reference statistics for drift monitoring ----------------------------------
    trdf = df.iloc[tr]
    from app.ml.preprocessing import image_descriptors
    sample_paths = trdf["path"].sample(n=min(800, len(trdf)), random_state=SEED)
    hists = []
    for p in sample_paths:
        with Image.open(data_root / p) as im:
            hists.append(image_descriptors(im)["intensity_hist"])
    reference = {
        "intensity_hist_mean": np.mean(np.array(hists), axis=0).round(6).tolist(),
        "intensity_hist_sample": int(len(hists)),
        "source": "Kermany patient-disjoint training split (inputs) and validation split (outputs)",
        "n_inputs": int(len(trdf)),
        "inputs": {k: reference_distribution(trdf[k].values.astype(np.float64))
                   for k in ("brightness", "contrast", "intensity_entropy", "width", "height")},
        "outputs": {
            "pneumonia_probability": reference_distribution(val_s["mean"]),
            "predictive_entropy": reference_distribution(val_s["predictive_entropy"]),
        },
        "refer_rate": float((val_s["predictive_entropy"] > policy["refer_threshold"]).mean()),
        "positive_rate": float((val_s["mean"] >= 0.5).mean()),
        "hist_bins": HIST_BINS,
    }

    # ---- Bundle --------------------------------------------------------------------
    bundle = s.models_dir / version
    bundle.mkdir(parents=True, exist_ok=True)
    full = PneumoniaResNet50(hidden=best["hidden"], dropout=best["dropout"], pretrained_backbone=True)
    full.head.load_state_dict(head.state_dict())
    weights_path = bundle / "model.pt"
    torch.save(full.state_dict(), weights_path)
    weights_sha = file_sha256(weights_path)

    trained_at = datetime.now(timezone.utc).isoformat()
    config = {
        "name": MODEL_NAME,
        "version": version,
        "architecture": "resnet50",
        "backbone": "torchvision ResNet-50, ImageNet-1K V2 initialisation, frozen",
        "head": {"hidden": best["hidden"], "dropout": round(best["dropout"], 6)},
        "image_size": IMAGE_SIZE,
        "normalization": {"mean": list(IMAGENET_MEAN), "std": list(IMAGENET_STD)},
        "mc_passes": MC_PASSES,
        "mc_seed": MC_SEED,
        "calibrated": True,
        "temperature": round(temperature, 6),
        "decision_threshold": 0.5,
        "refer_threshold": round(policy["refer_threshold"], 6),
        "refer_threshold_method": policy["method"],
        "uncertainty_metric": "predictive_entropy",
        "entropy_units": "bits",
        "refer_on_input_flags": True,
        "training_dataset": "Kermany pediatric CXR — patient-disjoint split",
        "trained_at": trained_at,
        "hyperparameters": {k: (round(v, 8) if isinstance(v, float) else v) for k, v in best.items()},
        "weights_file": "model.pt",
        "weights_sha256": weights_sha,
        "mlflow_run_id": run_id,
        "intended_use": "Educational research demonstration only. Not for clinical use.",
    }
    (bundle / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    evaluation = {
        "model_version": version,
        "generated_at": trained_at,
        "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "platform": platform.platform()},
        "training": {"best_params": best, "optuna_trials": args.trials, "optuna_best_val_nll": study.best_value,
                     "epochs_run": train_info["epochs_run"], "history": train_info["history"],
                     "split_sizes": {"train": int(len(tr)), "val": int(len(va)), "test": int(len(te))}},
        "policy": policy,
        "test": test_eval,
        "validation": val_eval,
        "leakage": leakage,
        "external": {"rsna": None, "status": "awaiting_artefacts",
                     "note": "Run scripts/evaluate_external.py with the RSNA images to populate this section."},
        "targets": {"roc_auc_ci_lower_min": 0.90, "ece_max": 0.05, "recall_min": 0.95},
    }
    (bundle / "evaluation.json").write_text(json.dumps(evaluation), encoding="utf-8")
    (bundle / "reference_stats.json").write_text(json.dumps(reference, indent=2), encoding="utf-8")
    print(f"Bundle written: {bundle}  (config hash {canonical_hash(config)[:12]})")

    if use_mlflow:
        mlflow.log_params({**{f"head_{k}": v for k, v in best.items()}, "mc_passes": MC_PASSES,
                           "backbone": "resnet50-frozen", "split": "patient-disjoint"})
        mlflow.log_metrics({
            "test_roc_auc": d["roc_auc"], "test_pr_auc": d["pr_auc"], "test_accuracy": d["accuracy"],
            "test_recall": d["recall"], "test_specificity": d["specificity"], "test_f1": d["f1"],
            "test_ece_before_ts": test_eval["calibration"]["before"]["ece"],
            "test_ece_after_ts": test_eval["calibration"]["after"]["ece"],
            "test_brier": test_eval["calibration"]["after"]["brier"], "temperature": temperature,
            "refer_threshold": policy["refer_threshold"], "test_refer_rate": test_eval["refer_bands"]["refer_rate"],
            "test_entropy_error_auroc": test_eval["uncertainty"]["entropy"]["error_detection_auroc"] or 0.0,
            "flawed_split_roc_auc": fd["roc_auc"], "flawed_split_accuracy": fd["accuracy"],
        })
        mlflow.set_tags({"model_version": version, "weights_sha256": weights_sha})
        for f in ("config.json", "evaluation.json", "reference_stats.json"):
            mlflow.log_artifact(str(bundle / f))
        mlflow.end_run()
    print("Done.")


if __name__ == "__main__":
    main()
