"""Loads the trained model bundle once and runs real inference.

If the trained weights are missing or fail their checksum, the model is
reported as unavailable ("integration pending") — no prediction is ever faked.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import numpy as np
import torch
from PIL import Image

from app.config import get_settings
from app.ml.artifacts import ArtifactError, ModelBundle, load_bundle
from app.ml.mc_dropout import mc_head_logits
from app.ml.prediction import REFER, decide
from app.ml.preprocessing import image_descriptors, quality_flags, to_model_tensor
from app.services.calibration_service import mc_probs
from app.services.gradcam_service import compute_gradcam
from app.services.uncertainty_service import summarize_single

log = logging.getLogger("pneumoscope.model")


class ModelUnavailableError(RuntimeError):
    pass


@dataclass
class Result:
    prediction: str
    pneumonia_probability: float
    uncertainty: float
    decision: str
    reason: str
    processing_ms: float


class ModelService:
    def __init__(self) -> None:
        self._bundle: ModelBundle | None = None
        self._error: str | None = None
        self._lock = threading.Lock()
        torch.set_num_threads(max(1, get_settings().torch_threads))

    def bundle(self) -> ModelBundle:
        if self._bundle is not None:
            return self._bundle
        with self._lock:
            if self._bundle is None:
                d = get_settings().model_dir
                try:
                    self._bundle = load_bundle(d)
                    self._error = None
                    log.info("Loaded model %s from %s", self._bundle.version, d)
                except (ArtifactError, FileNotFoundError, RuntimeError) as e:
                    self._error = f"Trained model not available ({e}). Model integration pending."
                    raise ModelUnavailableError(self._error) from e
        return self._bundle

    def status(self) -> dict:
        try:
            b = self.bundle()
            return {"available": True, "version": b.version, "message": "Model loaded"}
        except ModelUnavailableError as e:
            return {"available": False, "version": get_settings().model_version, "message": str(e)}

    def predict(self, img: Image.Image) -> Result:
        b = self.bundle()
        t0 = time.perf_counter()
        blocking, _ = quality_flags(img, image_descriptors(img))
        x = to_model_tensor(img).unsqueeze(0)
        with self._lock, torch.no_grad():
            logits = mc_head_logits(b.model.head, b.model.features(x), passes=b.mc_passes, seed=b.config.get("mc_seed"))
        probs = mc_probs(logits.numpy()[:, 0], b.temperature)
        s = summarize_single(np.asarray(probs))
        d = decide(s["mean"], s["predictive_entropy"], b.policy, blocking)
        if d.band == REFER:
            reason = ("The image did not pass the quality check." if blocking
                      else "Uncertainty is above the referral threshold.")
        else:
            reason = "Uncertainty is below the referral threshold."
        return Result(prediction=d.predicted_class, pneumonia_probability=s["mean"],
                      uncertainty=s["predictive_entropy"], decision="REFER" if d.band == REFER else "AUTO",
                      reason=reason, processing_ms=(time.perf_counter() - t0) * 1000)

    def gradcam(self, img: Image.Image, target: str) -> np.ndarray:
        b = self.bundle()
        with self._lock:
            cam, _ = compute_gradcam(b.model, to_model_tensor(img), target)
        return cam


model_service = ModelService()
