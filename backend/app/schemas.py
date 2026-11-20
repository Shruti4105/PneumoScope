from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

DISCLAIMER = ("Educational research application. Not a clinically validated diagnostic system. "
              "Results must be reviewed by a qualified professional.")


class AnalysisOut(BaseModel):
    id: str
    created_at: datetime
    prediction: str
    pneumonia_probability: float
    normal_probability: float
    uncertainty: float
    decision: str
    decision_reason: str
    referral_threshold: float
    model_version: str
    processing_ms: float
    image_width: int
    image_height: int
    image_url: str
    gradcam_url: str | None
    disclaimer: str = DISCLAIMER

    @classmethod
    def from_record(cls, a) -> "AnalysisOut":
        return cls(
            id=a.id, created_at=a.created_at, prediction=a.prediction,
            pneumonia_probability=a.pneumonia_probability, normal_probability=1 - a.pneumonia_probability,
            uncertainty=a.uncertainty, decision=a.decision, decision_reason=a.decision_reason,
            referral_threshold=a.referral_threshold, model_version=a.model_version,
            processing_ms=a.processing_ms, image_width=a.image_width, image_height=a.image_height,
            image_url=f"/analysis/{a.id}/image",
            gradcam_url=f"/analysis/{a.id}/gradcam" if a.gradcam_path else None,
        )


class HistoryOut(BaseModel):
    items: list[AnalysisOut]
    total: int
