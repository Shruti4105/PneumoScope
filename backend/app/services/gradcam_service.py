"""Grad-CAM (Selvaraju et al., 2017) computed from the actual deployed model.

Target layer: ResNet-50 ``layer4`` (7×7×2048 feature map). The target score is
the deterministic head logit (dropout disabled) for the requested class:
``+logit`` for PNEUMONIA, ``-logit`` for NORMAL.
"""
from __future__ import annotations

import cv2
import numpy as np
import torch

from app.ml.resnet_model import PneumoniaResNet50


def compute_gradcam(model: PneumoniaResNet50, x: torch.Tensor, target: str = "PNEUMONIA") -> tuple[np.ndarray, float]:
    """Return (cam [H,W] in [0,1] at input resolution, deterministic logit)."""
    if x.dim() == 3:
        x = x.unsqueeze(0)
    acts: dict[str, torch.Tensor] = {}
    grads: dict[str, torch.Tensor] = {}

    def fwd_hook(_m, _i, out):
        acts["a"] = out
        out.register_hook(lambda g: grads.__setitem__("g", g))

    was_training = model.training
    model.eval()
    handle = model.gradcam_layer.register_forward_hook(fwd_hook)
    try:
        with torch.enable_grad():
            inp = x.clone().requires_grad_(True)
            logit = model(inp)[0]
            score = logit if target == "PNEUMONIA" else -logit
            model.zero_grad(set_to_none=True)
            score.backward()
    finally:
        handle.remove()
        model.train(was_training)

    a = acts["a"][0].detach()           # [C,h,w]
    g = grads["g"][0].detach()          # [C,h,w]
    weights = g.mean(dim=(1, 2))        # global-average-pooled gradients
    cam = torch.relu((weights[:, None, None] * a).sum(0)).numpy()
    if cam.max() > 0:
        cam = cam / cam.max()
    cam = cv2.resize(cam.astype(np.float32), (x.shape[-1], x.shape[-2]), interpolation=cv2.INTER_CUBIC)
    return np.clip(cam, 0, 1), float(logit.detach())


def colourise(cam: np.ndarray) -> np.ndarray:
    """CAM -> RGBA heatmap (uint8). Alpha follows activation so low-activation
    regions stay transparent when overlaid in the browser."""
    rgb = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)[..., ::-1]
    alpha = (np.clip(cam * 1.4, 0, 1) * 255).astype(np.uint8)
    return np.dstack([rgb, alpha])


def overlay(gray: np.ndarray, cam: np.ndarray, opacity: float = 0.45) -> np.ndarray:
    base = np.stack([gray] * 3, axis=-1).astype(np.float32)
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)[..., ::-1].astype(np.float32)
    a = (opacity * np.clip(cam * 1.4, 0, 1))[..., None]
    return (base * (1 - a) + heat * a).clip(0, 255).astype(np.uint8)


def cam_statistics(cam: np.ndarray) -> dict:
    """Simple quantitative descriptors that support the shortcut-learning audit."""
    h, w = cam.shape
    total = float(cam.sum()) or 1.0
    border = max(1, int(0.08 * min(h, w)))
    mask = np.zeros_like(cam, dtype=bool)
    mask[:border, :] = mask[-border:, :] = True
    mask[:, :border] = mask[:, -border:] = True
    ys, xs = np.unravel_index(np.argmax(cam), cam.shape)
    # Rough central "lung field" box: middle 70% width, 10–85% height.
    central = np.zeros_like(cam, dtype=bool)
    central[int(0.10 * h):int(0.85 * h), int(0.15 * w):int(0.85 * w)] = True
    return {
        "border_energy_fraction": float(cam[mask].sum() / total),
        "central_energy_fraction": float(cam[central].sum() / total),
        "peak_location": {"x": float(xs / w), "y": float(ys / h)},
        "activation_area_fraction": float((cam > 0.5).mean()),
    }
