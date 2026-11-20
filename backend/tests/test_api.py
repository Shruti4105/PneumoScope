"""API tests: triage, history, detail, Grad-CAM, delete, model info, metrics."""
from __future__ import annotations

import io

from PIL import Image

from tests.conftest import make_xray_png


def test_health_and_model_info(client):
    assert client.get("/health").json()["model_available"] is True
    info = client.get("/model-info").json()
    assert info["available"] and info["version"] == "test-v1" and info["status"] == "Ready"


def test_triage_full_flow(client):
    r = client.post("/triage", files={"file": ("chest.png", make_xray_png(), "image/png")})
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["prediction"] in ("NORMAL", "PNEUMONIA")
    assert 0 <= j["pneumonia_probability"] <= 1
    assert abs(j["pneumonia_probability"] + j["normal_probability"] - 1) < 1e-9
    assert 0 <= j["uncertainty"] <= 1
    assert j["decision"] in ("AUTO", "REFER")
    if j["uncertainty"] > j["referral_threshold"]:
        assert j["decision"] == "REFER"
    assert "Not a clinically validated" in j["disclaimer"]
    aid = j["id"]

    assert client.get(j["image_url"]).headers["content-type"] == "image/png"
    assert client.get(j["image_url"] + "?thumb=true").headers["content-type"] == "image/webp"
    assert client.get(f"/analysis/{aid}/gradcam").status_code == 404     # not generated yet
    g = client.post(f"/analysis/{aid}/gradcam").json()
    assert g["gradcam_url"]
    assert client.get(g["gradcam_url"]).headers["content-type"] == "image/png"

    h = client.get("/analysis/history").json()
    assert h["total"] >= 1 and h["items"][0]["id"] == aid
    assert client.get(f"/analysis/{aid}").json()["id"] == aid
    d = client.get("/dashboard").json()
    assert d["total"] == d["normal"] + d["pneumonia"]
    assert len(d["daily"]) == 7 and sum(x["normal"] + x["pneumonia"] for x in d["daily"]) >= 1
    assert d["uncertainty_series"][-1]["uncertainty"] == j["uncertainty"]

    assert client.delete(f"/analysis/{aid}").status_code == 204
    assert client.get(f"/analysis/{aid}").status_code == 404
    assert client.delete(f"/analysis/{aid}").status_code == 404


def test_rejects_invalid_uploads(client):
    assert client.post("/triage", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 415
    assert client.post("/triage", files={"file": ("x.png", b"", "image/png")}).status_code == 422
    small = io.BytesIO()
    Image.new("L", (50, 50)).save(small, format="PNG")
    assert client.post("/triage", files={"file": ("s.png", small.getvalue(), "image/png")}).status_code == 422


def test_colour_image_is_referred(client):
    img = Image.new("RGB", (300, 300), (230, 20, 40))
    img.paste((20, 200, 40), (0, 0, 150, 300))
    b = io.BytesIO()
    img.save(b, format="PNG")
    j = client.post("/triage", files={"file": ("c.png", b.getvalue(), "image/png")}).json()
    assert j["decision"] == "REFER" and "quality" in j["decision_reason"]


def test_metrics_without_evaluation_is_honest(client):
    m = client.get("/metrics").json()
    assert m["available"] is False


def test_unknown_analysis(client):
    assert client.get("/analysis/doesnotexist").status_code == 404
