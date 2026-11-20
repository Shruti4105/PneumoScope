from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.ml.preprocessing import display_image
from app.models import Analysis
from app.schemas import AnalysisOut, HistoryOut
from app.services import storage_service as store
from app.services.gradcam_service import colourise, overlay
from app.services.image_validation import ImageValidationError, validate_upload
from app.services.inference_service import ModelUnavailableError, model_service

router = APIRouter(tags=["analysis"])


def _get(db: Session, analysis_id: str) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found.")
    return a


@router.post("/triage", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def triage(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Validate → preprocess → ResNet-50 inference → uncertainty → AUTO/REFER → save."""
    s = get_settings()
    data = file.file.read(s.max_upload_bytes + 1)
    try:
        img = validate_upload(file.filename, file.content_type, data)
    except ImageValidationError as e:
        raise HTTPException(e.status_code, str(e))
    try:
        r = model_service.predict(img)
        version = model_service.bundle().version
        threshold = model_service.bundle().policy.refer_threshold
    except ModelUnavailableError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))

    a = Analysis(image_path="", image_width=img.width, image_height=img.height, prediction=r.prediction,
                 pneumonia_probability=r.pneumonia_probability, uncertainty=r.uncertainty, decision=r.decision,
                 decision_reason=r.reason, referral_threshold=threshold, model_version=version,
                 processing_ms=r.processing_ms)
    db.add(a)
    db.flush()
    a.image_path = store.save_upload(a.id, img)
    db.commit()
    return AnalysisOut.from_record(a)


@router.get("/analysis/history", response_model=HistoryOut)
def history(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    rows = db.scalars(select(Analysis).order_by(Analysis.created_at.desc()).offset(offset).limit(limit)).all()
    total = db.scalar(select(func.count(Analysis.id))) or 0
    return HistoryOut(items=[AnalysisOut.from_record(a) for a in rows], total=total)


@router.get("/analysis/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    return AnalysisOut.from_record(_get(db, analysis_id))


@router.delete("/analysis/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    a = _get(db, analysis_id)
    store.delete_analysis_files(a.image_path, a.gradcam_path)
    db.delete(a)
    db.commit()


@router.post("/analysis/{analysis_id}/gradcam", response_model=AnalysisOut)
def gradcam(analysis_id: str, db: Session = Depends(get_db)):
    """Grad-CAM heatmap for the predicted class, computed from the actual model."""
    a = _get(db, analysis_id)
    if a.gradcam_path:
        return AnalysisOut.from_record(a)
    try:
        img = store.load_upload(a.image_path)
        cam = model_service.gradcam(img, a.prediction)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image file missing.")
    except ModelUnavailableError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    gray = display_image(img, cam.shape[0])
    a.gradcam_path = store.save_gradcam(a.id, cam, colourise(cam), overlay(gray, cam, 0.5), gray)
    db.commit()
    return AnalysisOut.from_record(a)


@router.get("/analysis/{analysis_id}/image")
def analysis_image(analysis_id: str, thumb: bool = False, db: Session = Depends(get_db)):
    """Stored X-ray. ?thumb=true returns a small cached WebP for lists."""
    p = store.upload_path(_get(db, analysis_id).image_path)
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image file missing.")
    if thumb:
        t = p.with_suffix(".thumb.webp")
        if not t.exists():
            from PIL import Image
            with Image.open(p) as im:
                im.thumbnail((160, 160))
                im.save(t, format="WEBP", quality=80)
        return FileResponse(t, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})
    return FileResponse(p, media_type="image/png")


@router.get("/analysis/{analysis_id}/gradcam")
def gradcam_image(analysis_id: str, db: Session = Depends(get_db)):
    a = _get(db, analysis_id)
    if not a.gradcam_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Heatmap not generated yet.")
    p = store.gradcam_file(a.gradcam_path, "overlay")
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Heatmap file missing.")
    return FileResponse(p, media_type="image/png")
