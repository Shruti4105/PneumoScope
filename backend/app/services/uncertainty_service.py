"""Uncertainty decomposition for binary MC-Dropout predictions.

With T stochastic passes producing p_t = P(pneumonia | x, w_t):

* mean probability        p̄  = (1/T) Σ p_t
* predictive variance     Var = (1/T) Σ (p_t - p̄)²
* predictive entropy      H[p̄]          (total uncertainty)
* expected entropy        E_t[H[p_t]]   (aleatoric component)
* mutual information      MI = H[p̄] - E_t[H[p_t]]   (epistemic component, BALD)

Entropies are reported in bits, so the maximum for a binary problem is 1.0.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-12


def binary_entropy(p: np.ndarray | float) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=np.float64), EPS, 1 - EPS)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


def summarize_passes(probs: np.ndarray) -> dict[str, np.ndarray]:
    """``probs``: array [T, N] of per-pass P(pneumonia). Returns per-sample stats."""
    probs = np.asarray(probs, dtype=np.float64)
    if probs.ndim == 1:
        probs = probs[:, None]
    mean = probs.mean(axis=0)
    var = probs.var(axis=0)
    h_total = binary_entropy(mean)
    h_expected = binary_entropy(probs).mean(axis=0)
    mi = np.clip(h_total - h_expected, 0.0, None)
    return {
        "mean": mean,
        "variance": var,
        "std": np.sqrt(var),
        "predictive_entropy": h_total,
        "expected_entropy": h_expected,
        "mutual_information": mi,
    }


def summarize_single(probs: np.ndarray) -> dict[str, float]:
    s = summarize_passes(np.asarray(probs).reshape(-1, 1))
    return {k: float(v[0]) for k, v in s.items()}
