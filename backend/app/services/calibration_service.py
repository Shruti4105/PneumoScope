"""Temperature scaling (Guo et al., 2017) for MC-Dropout logits, plus
calibration metrics (ECE, Brier score, reliability diagram)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

EPS = 1e-7


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def mc_probs(pass_logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """[T, N] logits -> [T, N] probabilities after dividing by the temperature."""
    return _sigmoid(np.asarray(pass_logits, dtype=np.float64) / temperature)


def nll(prob: np.ndarray, labels: np.ndarray) -> float:
    p = np.clip(prob, EPS, 1 - EPS)
    y = np.asarray(labels, dtype=np.float64)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_temperature(pass_logits: np.ndarray, labels: np.ndarray, bounds=(0.05, 10.0)) -> float:
    """Find T minimising the NLL of the MC-averaged probability on held-out data."""
    pass_logits = np.asarray(pass_logits, dtype=np.float64)
    if pass_logits.ndim == 1:
        pass_logits = pass_logits[None, :]

    def objective(t: float) -> float:
        return nll(mc_probs(pass_logits, t).mean(axis=0), labels)

    res = minimize_scalar(objective, bounds=bounds, method="bounded", options={"xatol": 1e-4})
    return float(res.x)


def expected_calibration_error(prob: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """ECE with equal-width bins over P(pneumonia) (positive-class reliability)."""
    prob = np.asarray(prob, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(prob, edges[1:-1], right=True), 0, n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        m = idx == b
        if m.any():
            ece += m.mean() * abs(prob[m].mean() - y[m].mean())
    return float(ece)


def brier_score(prob: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean((np.asarray(prob, dtype=np.float64) - np.asarray(labels, dtype=np.float64)) ** 2))


def reliability_diagram(prob: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> list[dict]:
    prob = np.asarray(prob, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(prob, edges[1:-1], right=True), 0, n_bins - 1)
    out = []
    for b in range(n_bins):
        m = idx == b
        out.append({
            "bin_lower": float(edges[b]), "bin_upper": float(edges[b + 1]),
            "bin_center": float((edges[b] + edges[b + 1]) / 2),
            "count": int(m.sum()),
            "mean_confidence": float(prob[m].mean()) if m.any() else None,
            "observed_frequency": float(y[m].mean()) if m.any() else None,
        })
    return out
