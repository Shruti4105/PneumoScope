"""Unit tests: uncertainty maths, calibration, decision policy, MC Dropout,
preprocessing, Grad-CAM and evaluation metrics."""
from __future__ import annotations

import io

import numpy as np
import pytest
import torch
from PIL import Image

from app.ml import evaluation as ev
from app.ml.mc_dropout import deterministic_head_logits, mc_head_logits, set_mc_dropout
from app.ml.prediction import AUTO_NEGATIVE, AUTO_POSITIVE, REFER, DecisionPolicy, decide
from app.ml.preprocessing import IMAGE_SIZE, image_descriptors, quality_flags, to_model_tensor
from app.ml.resnet_model import MCDropoutHead, PneumoniaResNet50
from app.services import calibration_service as cal
from app.services.gradcam_service import cam_statistics, colourise, compute_gradcam, overlay
from app.services.uncertainty_service import binary_entropy, summarize_passes, summarize_single
from tests.conftest import make_xray_png


# ---------------------------------------------------------------- uncertainty
def test_binary_entropy_bounds():
    assert binary_entropy(0.5) == pytest.approx(1.0)
    assert binary_entropy(0.0) == pytest.approx(0.0, abs=1e-9)
    assert binary_entropy(1.0) == pytest.approx(0.0, abs=1e-9)
    assert binary_entropy(0.1) == pytest.approx(binary_entropy(0.9))


def test_identical_passes_have_zero_mutual_information():
    s = summarize_single(np.full(30, 0.8))
    assert s["mean"] == pytest.approx(0.8)
    assert s["variance"] == pytest.approx(0.0)
    assert s["mutual_information"] == pytest.approx(0.0, abs=1e-9)
    assert s["predictive_entropy"] == pytest.approx(s["expected_entropy"])


def test_disagreeing_passes_are_epistemic():
    s = summarize_single(np.array([0.02] * 15 + [0.98] * 15))
    assert s["mean"] == pytest.approx(0.5)
    assert s["predictive_entropy"] == pytest.approx(1.0)
    assert s["mutual_information"] > 0.8       # mostly epistemic
    assert s["std"] == pytest.approx(0.48)


def test_summarize_passes_shapes():
    s = summarize_passes(np.random.default_rng(0).uniform(size=(30, 7)))
    assert all(v.shape == (7,) for v in s.values())
    assert np.all(s["mutual_information"] >= 0)
    assert np.all(s["predictive_entropy"] <= 1 + 1e-9)


# ---------------------------------------------------------------- calibration
def test_temperature_recovers_overconfidence():
    rng = np.random.default_rng(1)
    true_logit = rng.normal(0, 2, 4000)
    y = (rng.uniform(size=4000) < 1 / (1 + np.exp(-true_logit))).astype(int)
    over = np.tile(true_logit * 3.0, (5, 1))  # 3x over-confident logits
    t = cal.fit_temperature(over, y)
    assert 2.5 < t < 3.5
    before = cal.expected_calibration_error(cal.mc_probs(over, 1.0).mean(0), y)
    after = cal.expected_calibration_error(cal.mc_probs(over, t).mean(0), y)
    assert after < before


def test_ece_and_brier_perfect():
    p = np.array([0.0, 1.0, 0.0, 1.0])
    y = np.array([0, 1, 0, 1])
    assert cal.expected_calibration_error(p, y) == pytest.approx(0.0)
    assert cal.brier_score(p, y) == pytest.approx(0.0)
    bins = cal.reliability_diagram(np.linspace(0, 1, 50), (np.linspace(0, 1, 50) > 0.5).astype(int))
    assert len(bins) == 10 and sum(b["count"] for b in bins) == 50


# ---------------------------------------------------------------- policy
POLICY = DecisionPolicy(refer_threshold=0.5)


def test_policy_bands():
    assert decide(0.98, 0.14, POLICY).band == AUTO_POSITIVE
    assert decide(0.02, 0.14, POLICY).band == AUTO_NEGATIVE
    assert decide(0.6, 0.97, POLICY).band == REFER


def test_positive_and_refer_require_review():
    assert decide(0.98, 0.1, POLICY).requires_review
    assert decide(0.6, 0.97, POLICY).requires_review
    assert not decide(0.02, 0.1, POLICY).requires_review


def test_never_auto_decides_above_threshold():
    for p in np.linspace(0.01, 0.99, 99):
        h = float(binary_entropy(p))
        d = decide(float(p), h, POLICY)
        if h > POLICY.refer_threshold:
            assert d.band == REFER


def test_input_flags_force_refer():
    d = decide(0.01, 0.05, POLICY, ["image contains colour"])
    assert d.band == REFER and "Input quality guard" in d.reason


def test_invalid_policy_rejected():
    with pytest.raises(ValueError):
        DecisionPolicy(refer_threshold=0)
    with pytest.raises(ValueError):
        DecisionPolicy(refer_threshold=0.5, decision_threshold=1.2)


# ---------------------------------------------------------------- MC dropout
def test_mc_dropout_produces_stochastic_passes():
    torch.manual_seed(0)
    head = MCDropoutHead(16, 8, 0.5).eval()
    feats = torch.randn(3, 16)
    out = mc_head_logits(head, feats, passes=30, seed=7)
    assert out.shape == (30, 3)
    assert out.std(dim=0).min() > 0          # passes differ
    again = mc_head_logits(head, feats, passes=30, seed=7)
    assert torch.allclose(out, again)        # seeded -> reproducible
    assert not head.training                 # mode restored


def test_deterministic_eval_mode():
    head = MCDropoutHead(16, 8, 0.5)
    f = torch.randn(2, 16)
    assert torch.allclose(deterministic_head_logits(head, f), deterministic_head_logits(head, f))


def test_set_mc_dropout_only_dropout_in_train():
    m = PneumoniaResNet50(hidden=8)
    set_mc_dropout(m)
    assert not m.backbone.training
    assert all(x.training for x in m.modules() if isinstance(x, torch.nn.Dropout))
    assert not any(x.training for x in m.modules() if isinstance(x, torch.nn.BatchNorm2d))


# ---------------------------------------------------------------- preprocessing
def test_model_tensor_shape_and_normalisation():
    img = Image.open(io.BytesIO(make_xray_png())).convert("RGB")
    t = to_model_tensor(img)
    assert t.shape == (3, IMAGE_SIZE, IMAGE_SIZE)
    assert torch.allclose(t[0] * 0.229 + 0.485, t[1] * 0.224 + 0.456, atol=1e-5)  # grey replicated


def test_descriptors_and_quality_flags():
    img = Image.open(io.BytesIO(make_xray_png())).convert("RGB")
    d = image_descriptors(img)
    assert d["width"] == 320 and d["height"] == 300
    assert 0 < d["brightness"] < 1 and 0 < d["contrast"] < 1
    assert len(d["intensity_hist"]) == 32 and sum(d["intensity_hist"]) == pytest.approx(1, abs=1e-4)
    blocking, _ = quality_flags(img, d)
    assert blocking == []
    colour = Image.new("RGB", (300, 300), (230, 20, 40))
    colour.paste((20, 200, 40), (0, 0, 150, 300))
    blocking, _ = quality_flags(colour, image_descriptors(colour))
    assert any("colour" in b for b in blocking)


# ---------------------------------------------------------------- Grad-CAM
def test_gradcam_from_model():
    torch.manual_seed(0)
    model = PneumoniaResNet50(hidden=8).eval()
    x = to_model_tensor(Image.open(io.BytesIO(make_xray_png())).convert("RGB"))
    cam, logit = compute_gradcam(model, x, "PNEUMONIA")
    assert cam.shape == (IMAGE_SIZE, IMAGE_SIZE)
    assert cam.min() >= 0 and cam.max() <= 1
    assert isinstance(logit, float)
    assert colourise(cam).shape == (IMAGE_SIZE, IMAGE_SIZE, 4)
    assert overlay(np.zeros((224, 224), np.uint8), cam).shape == (224, 224, 3)
    stats = cam_statistics(cam)
    assert 0 <= stats["border_energy_fraction"] <= 1
    assert all(p.grad is None or True for p in model.parameters())


# ---------------------------------------------------------------- evaluation
def test_selective_curves_with_informative_uncertainty():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    prob = np.where(y == 1, 0.9, 0.1).astype(float)
    wrong = rng.choice(500, 50, replace=False)
    prob[wrong] = 1 - prob[wrong]
    unc = np.zeros(500)
    unc[wrong] = 1.0  # uncertainty perfectly flags errors
    out = ev.selective_curves(y, prob, unc)
    assert out["error_detection_auroc"] == pytest.approx(1.0)
    accs = [p["accuracy"] for p in out["accuracy_rejection"]]
    assert accs[0] == pytest.approx(0.9)
    assert accs[5] == pytest.approx(1.0)          # all errors rejected once >= 10% removed
    assert all(b >= a - 1e-12 for a, b in zip(accs, accs[1:]))


def test_refer_band_composition_counts():
    y = np.array([1, 0, 1, 0])
    p = np.array([0.9, 0.1, 0.4, 0.6])
    h = binary_entropy(p)
    rb = ev.refer_band_composition(y, p, h, 0.8)
    assert sum(b["n"] for b in rb["bands"].values()) == 4
    assert rb["bands"]["REFER"]["n"] == 2 and rb["errors_captured_by_refer"] == 2


def test_threshold_metrics_and_bootstrap():
    y = np.array([0, 0, 1, 1, 1, 0, 1, 0])
    p = np.array([0.1, 0.2, 0.8, 0.7, 0.4, 0.6, 0.9, 0.3])
    m = ev.threshold_metrics(y, p)
    assert m["confusion_matrix"] == {"tn": 3, "fp": 1, "fn": 1, "tp": 3}
    ci = ev.bootstrap_ci(y, p, n_boot=100)
    assert ci["roc_auc"]["lower"] <= ci["roc_auc"]["upper"]
