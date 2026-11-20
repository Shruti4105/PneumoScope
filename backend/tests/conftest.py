"""Test setup: temporary database, storage and model folder.

API tests use a structurally valid model bundle with random weights. It is a
test fixture only and is never used by the real application.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

TMP = Path(tempfile.mkdtemp(prefix="pneumoscope-test-"))
os.environ.update({
    "VAR_DIR": str(TMP / "var"),
    "ARTIFACTS_DIR": str(TMP / "artifacts"),
    "DATA_DIR": str(TMP / "data"),
    "DATABASE_URL": f"sqlite:///{(TMP / 'test.db').as_posix()}",
    "MODEL_VERSION": "test-v1",
    "TORCH_THREADS": "2",
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.ml.artifacts import file_sha256  # noqa: E402
from app.ml.resnet_model import PneumoniaResNet50  # noqa: E402


def make_xray_png(w: int = 320, h: int = 300, seed: int = 0) -> bytes:
    """Synthetic grayscale chest-X-ray-like image (two darker lung fields)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    img = 170 + 30 * rng.standard_normal((h, w))
    for cx in (0.32, 0.68):
        img -= 90 * np.exp(-(((xx / w - cx) / 0.13) ** 2 + ((yy / h - 0.5) / 0.28) ** 2))
    buf = io.BytesIO()
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "L").save(buf, format="PNG")
    return buf.getvalue()


def build_test_bundle() -> Path:
    d = get_settings().models_dir / "test-v1"
    d.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    torch.save(PneumoniaResNet50(hidden=32, dropout=0.5).state_dict(), d / "model.pt")
    cfg = {"name": "test", "version": "test-v1", "head": {"hidden": 32, "dropout": 0.5}, "mc_passes": 30,
           "mc_seed": 1, "calibrated": True, "temperature": 1.5, "decision_threshold": 0.5, "refer_threshold": 0.6,
           "weights_file": "model.pt", "weights_sha256": file_sha256(d / "model.pt")}
    (d / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return d


@pytest.fixture(scope="session")
def client():
    build_test_bundle()
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/auth/register", json={"name": "Test User", "email": "tester@example.org", "password": "Password123"})
        assert r.status_code == 201, r.text
        yield c
    shutil.rmtree(TMP, ignore_errors=True)
