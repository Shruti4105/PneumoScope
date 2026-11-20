"""Evaluation metrics: discrimination, bootstrap CIs, selective prediction
(accuracy-rejection, risk-coverage) and uncertainty-as-error-detector."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (average_precision_score, confusion_matrix, precision_recall_curve,
                             roc_auc_score, roc_curve)

from app.services.calibration_service import brier_score, expected_calibration_error


def _downsample(xs: np.ndarray, ys: np.ndarray, n: int = 120) -> list[dict]:
    if len(xs) > n:
        idx = np.unique(np.linspace(0, len(xs) - 1, n).round().astype(int))
        xs, ys = xs[idx], ys[idx]
    return [{"x": float(a), "y": float(b)} for a, b in zip(xs, ys)]


def threshold_metrics(y: np.ndarray, prob: np.ndarray, threshold: float = 0.5) -> dict:
    pred = (prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    def div(a, b): return float(a / b) if b else 0.0
    precision, recall = div(tp, tp + fp), div(tp, tp + fn)
    return {
        "threshold": threshold,
        "accuracy": div(tp + tn, len(y)),
        "recall": recall,
        "precision": precision,
        "specificity": div(tn, tn + fp),
        "f1": div(2 * precision * recall, precision + recall),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def bootstrap_ci(y: np.ndarray, prob: np.ndarray, n_boot: int = 1000, seed: int = 0,
                 threshold: float = 0.5) -> dict:
    rng = np.random.default_rng(seed)
    n = len(y)
    stats: dict[str, list[float]] = {k: [] for k in ("roc_auc", "pr_auc", "accuracy", "recall", "specificity",
                                                     "precision", "f1", "ece", "brier")}
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        yb, pb = y[i], prob[i]
        if yb.min() == yb.max():
            continue
        stats["roc_auc"].append(roc_auc_score(yb, pb))
        stats["pr_auc"].append(average_precision_score(yb, pb))
        tm = threshold_metrics(yb, pb, threshold)
        for k in ("accuracy", "recall", "specificity", "precision", "f1"):
            stats[k].append(tm[k])
        stats["ece"].append(expected_calibration_error(pb, yb))
        stats["brier"].append(brier_score(pb, yb))
    return {k: {"lower": float(np.percentile(v, 2.5)), "upper": float(np.percentile(v, 97.5)),
                "n_boot": len(v)} for k, v in stats.items() if v}


def discrimination(y: np.ndarray, prob: np.ndarray, threshold: float = 0.5) -> dict:
    fpr, tpr, _ = roc_curve(y, prob)
    prec, rec, _ = precision_recall_curve(y, prob)
    return {
        "roc_auc": float(roc_auc_score(y, prob)),
        "pr_auc": float(average_precision_score(y, prob)),
        **threshold_metrics(y, prob, threshold),
        "roc_curve": _downsample(fpr, tpr),
        "pr_curve": _downsample(rec[::-1], prec[::-1]),
    }


def selective_curves(y: np.ndarray, prob: np.ndarray, uncertainty: np.ndarray, threshold: float = 0.5,
                     steps: int = 41) -> dict:
    """Reject the most-uncertain cases first and track accuracy / risk."""
    order = np.argsort(-uncertainty)  # most uncertain first
    correct = ((prob >= threshold).astype(int) == y).astype(float)
    n = len(y)
    arc, rc = [], []
    for frac in np.linspace(0, 0.95, steps):
        k = int(round(frac * n))
        keep = order[k:]
        acc = float(correct[keep].mean()) if len(keep) else None
        arc.append({"rejection_rate": float(frac), "accuracy": acc, "n_retained": int(len(keep))})
        rc.append({"coverage": float(1 - frac), "risk": None if acc is None else 1 - acc})
    # Area under risk-coverage curve (lower is better), using every possible cut.
    sorted_correct = correct[np.argsort(uncertainty)]  # most certain first
    cum_risk = 1 - np.cumsum(sorted_correct) / np.arange(1, n + 1)
    aurc = float(cum_risk.mean())
    err = 1 - correct
    det_auroc = float(roc_auc_score(err, uncertainty)) if 0 < err.sum() < n else None
    return {"accuracy_rejection": arc, "risk_coverage": rc, "aurc": aurc, "error_detection_auroc": det_auroc}


def refer_band_composition(y: np.ndarray, prob: np.ndarray, entropy: np.ndarray, refer_threshold: float,
                           threshold: float = 0.5) -> dict:
    refer = entropy > refer_threshold
    pred = (prob >= threshold).astype(int)
    def cm(mask):
        yy, pp = y[mask], pred[mask]
        return {"tp": int(((yy == 1) & (pp == 1)).sum()), "tn": int(((yy == 0) & (pp == 0)).sum()),
                "fp": int(((yy == 0) & (pp == 1)).sum()), "fn": int(((yy == 1) & (pp == 0)).sum()),
                "n": int(mask.sum())}
    auto = ~refer
    auto_pos = auto & (pred == 1)
    auto_neg = auto & (pred == 0)
    n = len(y)
    auto_acc = float((pred[auto] == y[auto]).mean()) if auto.any() else None
    return {
        "refer_threshold": refer_threshold,
        "n": n,
        "refer_rate": float(refer.mean()),
        "bands": {"REFER": cm(refer), "AUTO-POSITIVE": cm(auto_pos), "AUTO-NEGATIVE": cm(auto_neg)},
        "auto_decision_accuracy": auto_acc,
        "overall_accuracy": float((pred == y).mean()),
        "errors_captured_by_refer": int(((pred != y) & refer).sum()),
        "total_errors": int((pred != y).sum()),
    }


def histogram(values: np.ndarray, bins: int = 20, range_: tuple[float, float] | None = None) -> list[dict]:
    counts, edges = np.histogram(values, bins=bins, range=range_)
    return [{"bin_lower": float(edges[i]), "bin_upper": float(edges[i + 1]),
             "bin_center": float((edges[i] + edges[i + 1]) / 2), "count": int(c)} for i, c in enumerate(counts)]
