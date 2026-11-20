from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.ml.artifacts import read_json
from app.models import Analysis
from app.schemas import AnalysisOut
from app.services.inference_service import model_service

router = APIRouter(tags=["model"])


def _config() -> dict | None:
    return read_json(get_settings().model_dir / "config.json")


def _evaluation() -> dict | None:
    return read_json(get_settings().model_dir / "evaluation.json")


@router.get("/model-info")
def model_info():
    st = model_service.status()
    cfg = _config() or {}
    return {
        "available": st["available"],
        "status": "Ready" if st["available"] else "Integration pending",
        "message": st["message"],
        "name": "ResNet-50 pneumonia classifier",
        "version": cfg.get("version", st["version"]),
        "architecture": "ResNet-50",
        "training_dataset": "Kermany Pediatric Chest X-Ray",
        "trained_at": cfg.get("trained_at"),
        "referral_threshold": cfg.get("refer_threshold"),
        "calibrated": bool(cfg.get("calibrated")),
    }


@router.get("/metrics")
def metrics():
    ev = _evaluation()
    if ev is None:
        return {"available": False, "message": "No evaluation results found for the trained model."}
    t = ev["test"]
    d = t["discrimination"]
    cm = d["confusion_matrix"]
    rb = t["refer_bands"]
    rsna = (ev.get("external") or {}).get("rsna")
    rsna_out = None
    if isinstance(rsna, dict):
        rd = rsna["discrimination"]
        rsna_out = {k: rd[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc")} | {"n": rsna["n"]}
    return {
        "available": True,
        "model_version": ev.get("model_version"),
        "dataset": "Kermany test set (patients not seen in training)",
        "n_images": t["n"],
        "n_pneumonia": t["n_pneumonia"],
        "n_normal": t["n_normal"],
        "accuracy": d["accuracy"],
        "precision": d["precision"],
        "recall": d["recall"],
        "f1": d["f1"],
        "roc_auc": d["roc_auc"],
        "roc_auc_ci": t["bootstrap_ci"].get("roc_auc"),
        "specificity": d["specificity"],
        "confusion_matrix": cm,
        "roc_curve": d["roc_curve"],
        "refer_rate": rb["refer_rate"],
        "auto_accuracy": rb["auto_decision_accuracy"],
        "external_rsna": rsna_out,
        "uncertainty": _uncertainty_summary(t),
    }


def _uncertainty_summary(t: dict) -> dict:
    """Test-set uncertainty results: does uncertainty flag the model's mistakes?"""
    u = t["uncertainty"]
    rb = t["refer_bands"]
    hist = [{"bin": round(c["bin_center"], 3), "correct": c["count"], "wrong": w["count"]}
            for c, w in zip(u["entropy_histogram_correct"], u["entropy_histogram_incorrect"])]
    curve = [{"referred": p["rejection_rate"], "accuracy": p["accuracy"]}
             for p in u["entropy"]["accuracy_rejection"] if p["accuracy"] is not None]
    return {
        "referral_threshold": rb["refer_threshold"],
        "refer_rate": rb["refer_rate"],
        "n_referred": rb["bands"]["REFER"]["n"],
        "overall_accuracy": rb["overall_accuracy"],
        "auto_accuracy": rb["auto_decision_accuracy"],
        "errors_caught": rb["errors_captured_by_refer"],
        "total_errors": rb["total_errors"],
        "mean_uncertainty": u["mean_entropy"],
        "error_detection_auroc": u["entropy"]["error_detection_auroc"],
        "histogram": hist,
        "accuracy_vs_referred": curve,
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Analysis.id))) or 0
    counts = dict(db.execute(select(Analysis.prediction, func.count(Analysis.id)).group_by(Analysis.prediction)).all())
    referred = db.scalar(select(func.count(Analysis.id)).where(Analysis.decision == "REFER")) or 0
    avg_unc = db.scalar(select(func.avg(Analysis.uncertainty)))
    recent = db.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(5)).all()

    # Analyses per day for the last 7 days (UTC dates), oldest first.
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    since = datetime.combine(days[0], datetime.min.time())
    daily = {d: {"date": d.isoformat(), "normal": 0, "pneumonia": 0, "referred": 0} for d in days}
    for created, pred, decision in db.execute(select(Analysis.created_at, Analysis.prediction, Analysis.decision)
                                              .where(Analysis.created_at >= since)):
        row = daily.get(created.date())
        if row:
            row["pneumonia" if pred == "PNEUMONIA" else "normal"] += 1
            row["referred"] += decision == "REFER"

    # Uncertainty of the most recent analyses, oldest first (for the trend chart).
    series = db.execute(select(Analysis.created_at, Analysis.uncertainty, Analysis.decision)
                        .order_by(Analysis.created_at.desc()).limit(30)).all()
    uncertainty_series = [{"date": c.isoformat(), "uncertainty": u, "decision": d} for c, u, d in reversed(series)]
    return {
        "total": total,
        "normal": counts.get("NORMAL", 0),
        "pneumonia": counts.get("PNEUMONIA", 0),
        "referred": referred,
        "auto": total - referred,
        "average_uncertainty": avg_unc,
        "recent": [AnalysisOut.from_record(a) for a in recent],
        "daily": list(daily.values()),
        "uncertainty_series": uncertainty_series,
        "model": model_info(),
    }

