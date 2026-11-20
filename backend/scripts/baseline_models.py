"""Baseline comparison on the same cached ResNet-50 features and patient-disjoint split.

Models
------
* Logistic Regression  (baseline: simple, interpretable linear model)
* Random Forest        (non-linear tree ensemble)
* MLP head, default hyper-parameters (same architecture as the final model, no Optuna)
* Final model v1.1.0 (Optuna-tuned MC-Dropout head + temperature scaling) — read from evaluation.json

Model choice is made on the validation split; the test split is only reported.
Results: artifacts/experiments/baseline_comparison.json (+ MLflow experiment "baseline-comparison").

Usage:  python -m scripts.baseline_models [--no-mlflow]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402
from app.ml import evaluation as ev  # noqa: E402
from app.ml.mc_dropout import deterministic_head_logits  # noqa: E402
from app.services import calibration_service as cal  # noqa: E402
from scripts.train_pipeline import SEED, train_head  # noqa: E402


def metrics(y, p):
    m = ev.threshold_metrics(y, p, 0.5)
    return {"accuracy": m["accuracy"], "precision": m["precision"], "recall": m["recall"],
            "specificity": m["specificity"], "f1": m["f1"], "roc_auc": float(roc_auc_score(y, p)),
            "ece": cal.expected_calibration_error(p, y), "brier": cal.brier_score(p, y),
            "confusion_matrix": m["confusion_matrix"]}


def main(log_mlflow: bool = True) -> None:
    s = get_settings()
    df = pd.read_csv(s.data_dir / "kermany" / "manifest.csv")
    feats = np.load(s.data_dir / "features" / "kermany_resnet50.npz")["features"].astype(np.float32)
    y = df["label_int"].values.astype(np.int64)
    idx = {k: np.nonzero(df["split"].values == k)[0] for k in ("train", "val", "test")}
    xtr, xva, xte = feats[idx["train"]], feats[idx["val"]], feats[idx["test"]]
    ytr, yva, yte = y[idx["train"]], y[idx["val"]], y[idx["test"]]

    results = []

    def record(name, role, params, fit, predict):
        t0 = time.perf_counter()
        model = fit()
        train_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        pva, pte = predict(model, xva), predict(model, xte)
        infer_ms = (time.perf_counter() - t1) / (len(xva) + len(xte)) * 1000
        r = {"model": name, "role": role, "params": params, "train_seconds": round(train_s, 2),
             "inference_ms_per_image_head_only": round(infer_ms, 4),
             "validation": metrics(yva, pva), "test": metrics(yte, pte)}
        results.append(r)
        print(f"{name:32s} train {train_s:6.1f}s  val AUC {r['validation']['roc_auc']:.4f}  "
              f"test acc {r['test']['accuracy']:.4f} AUC {r['test']['roc_auc']:.4f} F1 {r['test']['f1']:.4f}")

    lr_params = {"C": 1.0, "class_weight": "balanced", "max_iter": 3000, "scaler": "StandardScaler"}
    record("Logistic Regression", "baseline", lr_params,
           lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=3000,
                                                                      random_state=SEED)).fit(xtr, ytr),
           lambda m, x: m.predict_proba(x)[:, 1])

    rf_params = {"n_estimators": 300, "max_features": "sqrt", "class_weight": "balanced"}
    record("Random Forest", "comparison", rf_params,
           lambda: RandomForestClassifier(n_estimators=300, max_features="sqrt", class_weight="balanced",
                                          n_jobs=-1, random_state=SEED).fit(xtr, ytr),
           lambda m, x: m.predict_proba(x)[:, 1])

    mlp_params = {"lr": 1e-3, "weight_decay": 1e-4, "dropout": 0.5, "hidden": 256}
    record("MLP head (default params)", "untuned neural head", mlp_params,
           lambda: train_head(xtr, ytr, xva, yva, **mlp_params)[0],
           lambda m, x: torch.sigmoid(deterministic_head_logits(m, torch.from_numpy(x))).numpy().astype(np.float64))

    # Final model: the per-case test probabilities saved by train_pipeline (30-pass MC, calibrated).
    evj = json.loads((s.model_dir / "evaluation.json").read_text())
    pc = evj["test"]["per_case"]
    final_test = metrics(np.array(pc["label"]), np.array(pc["p"]))
    vd = evj["validation"]["discrimination"]
    results.append({"model": "MC-Dropout head + Optuna + temperature (v1.1.0)", "role": "final optimised model",
                    "params": evj["training"]["best_params"] | {"mc_passes": 30, "temperature": evj["test"]["calibration"]["temperature"]},
                    "train_seconds": None, "validation": {"roc_auc": vd["roc_auc"], "accuracy": vd["accuracy"], "f1": vd["f1"]},
                    "test": final_test, "refer_rate": evj["test"]["refer_bands"]["refer_rate"],
                    "auto_accuracy": evj["test"]["refer_bands"]["auto_decision_accuracy"]})
    print(f"{'Final v1.1.0':32s} test acc {final_test['accuracy']:.4f} AUC {final_test['roc_auc']:.4f} F1 {final_test['f1']:.4f}")

    out = s.artifacts_dir / "experiments"
    out.mkdir(parents=True, exist_ok=True)
    (out / "baseline_comparison.json").write_text(json.dumps(
        {"split": "patient-disjoint (train 4182 / val 837 / test 837)", "features": "frozen ResNet-50 ImageNet, 2048-d",
         "selection": "validation ROC-AUC; test reported only", "results": results}, indent=2), encoding="utf-8")
    print("Saved", out / "baseline_comparison.json")

    if not log_mlflow:
        return
    try:
        import mlflow
        mlflow.set_tracking_uri(s.resolved_mlflow_uri)
        mlflow.set_experiment("baseline-comparison")
        for r in results:
            with mlflow.start_run(run_name=r["model"]):
                mlflow.log_params({k: str(v) for k, v in r["params"].items()} | {"role": r["role"]})
                mlflow.log_metrics({f"test_{k}": v for k, v in r["test"].items() if isinstance(v, float)}
                                   | {f"val_{k}": v for k, v in r["validation"].items() if isinstance(v, float)})
        print("Logged to MLflow experiment 'baseline-comparison'")
    except ImportError:
        print("mlflow not installed; skipped logging")


if __name__ == "__main__":
    main(log_mlflow="--no-mlflow" not in sys.argv)
