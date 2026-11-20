"""Builds docs/PneumoScope_Project_Guide.pdf — a complete guide to the project.

All numbers are read from the real project files (model config, evaluation
report, dataset card, database), so the PDF always matches the project.

    .venv/Scripts/python docs/build_project_guide.py
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
import os
OUT = Path(os.environ.get("GUIDE_OUT", ROOT / "docs" / "PneumoScope_Project_Guide.pdf"))
MODEL = ROOT / "artifacts" / "models" / "v1.1.0"

cfg = json.loads((MODEL / "config.json").read_text())
ev = json.loads((MODEL / "evaluation.json").read_text())
card = json.loads((ROOT / "artifacts" / "datasets" / "kermany" / "dataset_card.json").read_text())
test = ev["test"]
disc = test["discrimination"]
ci = test["bootstrap_ci"]
cal = test["calibration"]
rb = test["refer_bands"]
unc = test["uncertainty"]
leak = ev["leakage"]

# ------------------------------------------------------------------ styles
ORANGE = colors.HexColor("#E8642F")
DARK = colors.HexColor("#1E1A17")
INK = colors.HexColor("#202725")
MUTED = colors.HexColor("#6B6560")
LINE = colors.HexColor("#E3DED8")
SOFT = colors.HexColor("#FBF4EE")

ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.6, leading=14, textColor=INK, spaceAfter=5)
small = ParagraphStyle("small", parent=body, fontSize=8.4, leading=11.5, textColor=MUTED)
cell = ParagraphStyle("cell", parent=body, fontSize=8.4, leading=11, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=INK, spaceBefore=4, spaceAfter=10, keepWithNext=1)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=ORANGE, spaceBefore=12, spaceAfter=5, keepWithNext=1)
h3 = ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3, keepWithNext=1)
code = ParagraphStyle("code", parent=body, fontName="Courier", fontSize=8.2, leading=11, backColor=colors.HexColor("#F4F1EE"),
                      borderPadding=(5, 6, 5, 6), spaceBefore=3, spaceAfter=8)

story: list = []


def P(t, st=body):
    story.append(Paragraph(t, st))


def H1(t):
    story.append(Paragraph(t, h1))


def H2(t):
    story.append(Paragraph(t, h2))


def H3(t):
    story.append(Paragraph(t, h3))


def bullets(items, st=body):
    story.append(ListFlowable([ListItem(Paragraph(i, st), leftIndent=12) for i in items],
                              bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8, spaceAfter=6))


def CODE(t):
    story.append(Paragraph(t.replace("\n", "<br/>").replace(" ", "&nbsp;"), code))


def table(rows, widths, header=True, zebra=True):
    data = [[Paragraph(str(c), cellb if (header and r == 0) else cell) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == 0:
                st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FCFBFA")))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 8))


def pct(v, d=1):
    return f"{v * 100:.{d}f}%"


W = A4[0] - 36 * mm  # usable width

# ------------------------------------------------------------------ charts (matplotlib, from real data)
tmp = Path(tempfile.mkdtemp())
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def chart_roc():
    xs = [p["x"] for p in disc["roc_curve"]]
    ys = [p["y"] for p in disc["roc_curve"]]
    fig, ax = plt.subplots(figsize=(3.4, 2.9), dpi=200)
    ax.plot(xs, ys, color="#E8642F", lw=2)
    ax.fill_between(xs, ys, alpha=0.12, color="#E8642F")
    ax.plot([0, 1], [0, 1], "--", color="#999", lw=1)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title(f"ROC curve (AUC {disc['roc_auc']:.3f})", fontsize=9.5)
    fig.tight_layout(); f = tmp / "roc.png"; fig.savefig(f); plt.close(fig); return f


def chart_cm():
    cm = disc["confusion_matrix"]
    m = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
    fig, ax = plt.subplots(figsize=(3.2, 2.9), dpi=200)
    ax.imshow([[1, 0], [0, 1]], cmap="Oranges", alpha=0.35)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, m[i][j], ha="center", va="center", fontsize=16, fontweight="bold", color="#202725")
    ax.set_xticks([0, 1], ["Pred. normal", "Pred. pneumonia"]); ax.set_yticks([0, 1], ["Normal", "Pneumonia"])
    ax.set_title("Confusion matrix (test set)", fontsize=9.5)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout(); f = tmp / "cm.png"; fig.savefig(f); plt.close(fig); return f


def chart_reliability():
    fig, ax = plt.subplots(figsize=(3.4, 2.9), dpi=200)
    for key, col, lab in (("before", "#999999", "Before (T = 1)"), ("after", "#E8642F", f"After (T = {cal['temperature']:.3f})")):
        b = [x for x in cal[key]["reliability"] if x["count"]]
        ax.plot([x["mean_confidence"] for x in b], [x["observed_frequency"] for x in b], "o-", color=col, lw=1.6, ms=3, label=lab)
    ax.plot([0, 1], [0, 1], "--", color="#bbb", lw=1)
    ax.set_xlabel("Predicted probability"); ax.set_ylabel("Observed frequency")
    ax.set_title("Reliability diagram", fontsize=9.5); ax.legend(fontsize=7, frameon=False)
    fig.tight_layout(); f = tmp / "rel.png"; fig.savefig(f); plt.close(fig); return f


def chart_uncertainty():
    c = unc["entropy_histogram_correct"]; w = unc["entropy_histogram_incorrect"]
    xs = [b["bin_center"] for b in c]
    fig, ax = plt.subplots(figsize=(3.4, 2.9), dpi=200)
    ax.bar(xs, [b["count"] for b in c], width=0.045, color="#5B4A3F", label="Correct")
    ax.bar(xs, [b["count"] for b in w], width=0.045, bottom=[b["count"] for b in c], color="#E8642F", label="Wrong")
    ax.axvline(rb["refer_threshold"], ls="--", color="#C79A2C", lw=1.2)
    ax.set_yscale("symlog"); ax.set_xlabel("Uncertainty (predictive entropy)"); ax.set_ylabel("Test X-rays")
    ax.set_title("Wrong predictions have high uncertainty", fontsize=9.5); ax.legend(fontsize=7, frameon=False)
    fig.tight_layout(); f = tmp / "unc.png"; fig.savefig(f); plt.close(fig); return f


def chart_arc():
    pts = [p for p in unc["entropy"]["accuracy_rejection"] if p["accuracy"] is not None]
    fig, ax = plt.subplots(figsize=(3.4, 2.9), dpi=200)
    ax.plot([p["rejection_rate"] for p in pts], [p["accuracy"] for p in pts], color="#E8642F", lw=2)
    ax.axvline(rb["refer_rate"], ls="--", color="#C79A2C", lw=1.2)
    ax.set_xlabel("Share of X-rays referred"); ax.set_ylabel("Accuracy on the rest")
    ax.set_title("Accuracy rises as unsure cases are referred", fontsize=9.5)
    fig.tight_layout(); f = tmp / "arc.png"; fig.savefig(f); plt.close(fig); return f


def two(img1, img2, w=W / 2 - 3 * mm):
    t = Table([[Image(str(img1), width=w, height=w * 0.853), Image(str(img2), width=w, height=w * 0.853)]],
              colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t)
    story.append(Spacer(1, 6))


# ------------------------------------------------------------------ architecture diagram
def architecture() -> Drawing:
    d = Drawing(W, 250)

    def box(x, y, w, h, title, lines, fill="#FBF4EE", stroke="#E8642F"):
        d.add(Rect(x, y, w, h, rx=8, ry=8, fillColor=colors.HexColor(fill), strokeColor=colors.HexColor(stroke), strokeWidth=1))
        d.add(String(x + 8, y + h - 15, title, fontName="Helvetica-Bold", fontSize=9, fillColor=INK))
        for i, ln in enumerate(lines):
            d.add(String(x + 8, y + h - 28 - i * 11, ln, fontName="Helvetica", fontSize=7.4, fillColor=MUTED))

    def arrow(x1, y1, x2, y2, label=""):
        d.add(Line(x1, y1, x2, y2, strokeColor=INK, strokeWidth=0.9))
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        p = [x2, y2, x2 - 6 * math.cos(a - 0.4), y2 - 6 * math.sin(a - 0.4), x2 - 6 * math.cos(a + 0.4), y2 - 6 * math.sin(a + 0.4)]
        d.add(Polygon(p, fillColor=INK, strokeColor=INK))
        if label:
            d.add(String((x1 + x2) / 2 + 4, (y1 + y2) / 2 + 3, label, fontName="Helvetica", fontSize=7, fillColor=MUTED))

    bw = (W - 30) / 3
    box(0, 170, bw, 70, "Browser (user)", ["React + TypeScript web app", "Home, Login, Dashboard,", "Analysis, History, ..."])
    box(bw + 15, 170, bw, 70, "nginx (Docker) / Vite (dev)", ["Serves the built website", "Proxies /api/* to FastAPI", "Port 8080 (Docker), 5173 (dev)"])
    box(2 * (bw + 15), 170, bw, 70, "Cloudflare tunnel (optional)", ["Public https link to", "127.0.0.1:8080 on this PC", "*.trycloudflare.com"], fill="#F4F1EE", stroke="#999999")
    box(bw + 15, 75, bw, 75, "FastAPI backend (Python)", ["Login (cookie session)", "Upload validation", "Triage, history, metrics API", "Port 8000"])
    box(0, 75, bw, 75, "Model service (PyTorch)", ["ResNet-50 + dropout head", "30 MC passes + temperature", "Uncertainty, AUTO/REFER", "Grad-CAM heatmaps"])
    box(2 * (bw + 15), 75, bw, 75, "Storage (on disk)", ["SQLite: users, analyses", "var/uploads: X-ray PNGs", "var/gradcam: heatmaps", "artifacts/: trained model"], fill="#EEF2EE", stroke="#5B7A6A")
    box(bw + 15, 0, bw, 55, "Training pipeline (offline)", ["prepare_kermany.py, train_pipeline.py", "Optuna + MLflow, evaluation.json"], fill="#F4F1EE", stroke="#999999")

    arrow(bw, 205, bw + 15, 205, "")
    arrow(2 * (bw + 15), 205, 2 * bw + 15, 205, "")
    arrow(bw + 15 + bw / 2, 170, bw + 15 + bw / 2, 150, "/api")
    arrow(bw + 15, 112, bw, 112, "")
    arrow(2 * bw + 15, 112, 2 * (bw + 15), 112, "")
    arrow(bw + 15 + bw / 2, 55, bw + 15 + bw / 2, 75, "")
    return d


# ------------------------------------------------------------------ page decoration
def on_page(c, doc):
    c.saveState()
    if doc.page == 1:
        c.setFillColor(DARK)
        c.rect(0, A4[1] - 118 * mm, A4[0], 118 * mm, stroke=0, fill=1)
    else:
        c.setStrokeColor(LINE)
        c.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        c.setFont("Helvetica-Bold", 8); c.setFillColor(ORANGE)
        c.drawString(18 * mm, A4[1] - 11.5 * mm, "PneumoScope")
        c.setFont("Helvetica", 8); c.setFillColor(MUTED)
        c.drawRightString(A4[0] - 18 * mm, A4[1] - 11.5 * mm, "Complete Project Guide")
        c.drawString(18 * mm, 10 * mm, "Medical X-Ray Pneumonia Classification with Uncertainty Quantification")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    c.restoreState()


# ================================================================== CONTENT
# ---- cover
cover_title = ParagraphStyle("ct", parent=h1, fontSize=30, leading=35, textColor=colors.white)
cover_sub = ParagraphStyle("cs", parent=body, fontSize=12, leading=17, textColor=colors.HexColor("#E9DED6"))
story.append(Spacer(1, 18 * mm))
story.append(Paragraph('<font color="#E8642F">PneumoScope</font>', ParagraphStyle("brand", parent=body, fontSize=13, fontName="Helvetica-Bold")))
story.append(Spacer(1, 4))
story.append(Paragraph("Complete Project Guide", cover_title))
story.append(Paragraph("Medical X-Ray Pneumonia Classification with Uncertainty Quantification", cover_sub))
story.append(Spacer(1, 6))
story.append(Paragraph(f"Everything about the project: what it does, how it works, the technology used, "
                       f"the model and its results, and exactly where every piece of data is stored. "
                       f"Generated {date.today():%d %B %Y} from the live project files.", cover_sub))
story.append(Spacer(1, 22 * mm))

kpis = [["5,856", "chest X-rays in<br/>the dataset"], [f"{disc['roc_auc']:.3f}", "ROC-AUC on<br/>unseen patients"],
        [pct(disc["accuracy"]), "test accuracy"], [pct(disc["recall"]), "pneumonia cases<br/>detected (recall)"],
        [pct(rb["auto_decision_accuracy"]), "accuracy on<br/>AUTO results"]]
kt = Table([[Paragraph(f'<font size="17" color="#E8642F"><b>{v}</b></font>', ParagraphStyle("k", parent=body, alignment=TA_CENTER)) for v, _ in kpis],
            [Paragraph(l, ParagraphStyle("kl", parent=small, alignment=TA_CENTER)) for _, l in kpis]], colWidths=[W / 5] * 5)
kt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                        ("BACKGROUND", (0, 0), (-1, -1), SOFT), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
story.append(kt)
story.append(Spacer(1, 10))
imgs = [ROOT / "frontend/public/images/hero-xray.webp", ROOT / "frontend/public/images/gradcam.webp"]
if all(p.exists() for p in imgs):
    from PIL import Image as PILImage
    pngs = []
    for p in imgs:
        q = tmp / (p.stem + ".png")
        PILImage.open(p).convert("RGB").save(q)
        pngs.append(q)
    t = Table([[Image(str(pngs[0]), width=55 * mm, height=55 * mm), Image(str(pngs[1]), width=55 * mm, height=55 * mm)],
               [Paragraph("Chest X-ray from the Kermany dataset", ParagraphStyle("c1", parent=small, alignment=TA_CENTER)),
                Paragraph("Grad-CAM heatmap produced by the trained model", ParagraphStyle("c2", parent=small, alignment=TA_CENTER))]],
              colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(t)
story.append(Spacer(1, 6))
P("<b>Contents:</b> 1 Overview · 2 How it works · 3 Architecture · 4 Technology stack · 5 The model · "
  "6 Dataset · 7 Results · 8 Where data is saved · 9 Database · 10 Backend API · 11 Website pages · "
  "12 Security &amp; privacy · 13 Project files · 14 How to run · 15 Testing · 16 Limitations · 17 Glossary. "
  "<b>Part B — Technical reference:</b> 18 External services · 19 API reference · 20 Schemas · 21 Configuration · "
  "22 Backend code · 23 Frontend code · 24 Formulas · 25 Model files · 26 Scripts · 27 Docker &amp; nginx · "
  "28 Security internals · 29 Quick reference", small)
story.append(PageBreak())

# ---- 1 overview
H1("1. Overview")
P("<b>PneumoScope</b> is a full-stack web application built as an academic research project. A user signs in, uploads a "
  "chest X-ray, and the app returns: whether the X-ray looks <b>Normal</b> or shows <b>Pneumonia</b>, the "
  "<b>probability</b> of pneumonia, an <b>uncertainty score</b>, a decision (<b>AUTO</b> when the model is confident, "
  "<b>REFER</b> when it is unsure), and a <b>Grad-CAM heatmap</b> showing which areas of the image influenced the result. "
  "Every analysis is saved and can be reopened or deleted later.")
P("The guiding idea is that <i>a medical AI system should know when it does not know</i>: instead of always giving an "
  "answer, the model measures how sure it is and refers uncertain cases to a person.")
H3("Main features")
bullets([
    "Public home page and login page; every other page requires an account.",
    "Real inference with a trained ResNet-50 deep-learning model (no simulated or random predictions).",
    "Uncertainty score from 30 repeated stochastic predictions (Monte Carlo Dropout).",
    "Calibrated probabilities (temperature scaling) and an AUTO / REFER decision with a fixed threshold.",
    "Grad-CAM heatmap for every result, generated from the actual model.",
    "Dashboard, analysis history, model performance page with real test results, and an about page.",
    "Runs locally, in Docker, and can be shared through a free public link.",
])
P("<b>Important:</b> this is an educational research application. It is not a medical device and has not been "
  "clinically validated; it must not be used to diagnose or treat patients.", small)

# ---- 2 how it works
H1("2. How it works (step by step)")
H3("What the user does")
bullets([
    "Opens the home page and clicks <b>Get started</b> or <b>Join Now</b>.",
    "Creates an account or logs in (email + password). A secure session cookie is set.",
    "Goes to <b>X-Ray Analysis</b>, drags in (or browses for) a JPG/PNG chest X-ray and presses <b>Analyse</b>.",
    "Sees the result page: prediction, probability, uncertainty, AUTO/REFER and the heatmap.",
    "Can later open it again from <b>Analysis History</b>, or delete it.",
])
H3("What happens inside the system when an image is analysed")
rows = [["#", "Step", "Where in the code"],
        ["1", "The browser sends the file to <b>POST /triage</b> (through the /api proxy).", "frontend/src/services/api.ts"],
        ["2", "The backend checks you are logged in (session cookie).", "backend/app/auth.py"],
        ["3", "The file is validated: extension, content type, magic bytes, decodes as an image, ≤ 10 MB, sides 128–8192 px.", "services/image_validation.py"],
        ["4", "A quality check flags images that are colourful, have no contrast or an odd shape (these are forced to REFER).", "ml/preprocessing.py"],
        ["5", "The image is converted to grayscale, resized to 224 × 224, copied to 3 channels and normalised.", "ml/preprocessing.py"],
        ["6", "ResNet-50 turns the image into 2,048 numbers (features) — once.", "ml/resnet_model.py"],
        ["7", "The classification head runs <b>30 times</b> with dropout switched on, giving 30 slightly different answers.", "ml/mc_dropout.py"],
        ["8", f"Each answer is divided by the calibration temperature (T = {cfg['temperature']:.3f}) and turned into a probability.", "services/calibration_service.py"],
        ["9", "The 30 probabilities are averaged; the <b>uncertainty</b> is the predictive entropy of that average (0 = sure, 1 = coin flip).", "services/uncertainty_service.py"],
        ["10", f"Decision: if uncertainty &gt; {cfg['refer_threshold']:.3f} (or the quality check failed) → <b>REFER</b>; otherwise <b>AUTO</b>. Prediction = Pneumonia if probability ≥ 0.5.", "ml/prediction.py"],
        ["11", "The image is re-saved as a clean PNG under a random ID and the result is stored in the database.", "routes/analysis.py, storage_service.py"],
        ["12", "The website then calls <b>POST /analysis/{id}/gradcam</b>; the heatmap is computed from the same model and saved.", "services/gradcam_service.py"]]
table(rows, [8 * mm, W - 8 * mm - 52 * mm, 52 * mm])
P(f"Typical processing time on a laptop CPU is about 0.2–1 second per X-ray (the 30 passes run as one batched "
  f"computation on the small head, so they are cheap).", small)

# ---- 3 architecture
H1("3. System architecture")
P("The application is split into a <b>frontend</b> (the website the user sees), a <b>backend</b> (the API server that "
  "runs the model and stores data) and an offline <b>training pipeline</b> that produced the model files.")
story.append(architecture())
story.append(Spacer(1, 8))
table([["Part", "What it does", "Runs on"],
       ["Frontend", "React single-page app: home, login, dashboard, analysis, history, performance, about. Talks to the backend only through <b>/api</b>.", "Browser; served by Vite (dev) or nginx (Docker)"],
       ["Backend", "FastAPI app: authentication, upload validation, inference, Grad-CAM, history, metrics, dashboard data.", "Python, port 8000"],
       ["Model service", "Loads the trained model once at start-up and verifies its checksum; runs predictions and heatmaps.", "Inside the backend process (CPU)"],
       ["Database", "SQLite file with two tables: users and analyses.", "backend/var/pneumoscope.db"],
       ["File storage", "Uploaded X-rays (re-encoded PNG + small thumbnail) and Grad-CAM images.", "backend/var/uploads, backend/var/gradcam"],
       ["Model artefacts", "Trained weights, configuration (thresholds), evaluation results.", "artifacts/models/v1.1.0"],
       ["Training pipeline", "Scripts that prepared the dataset, trained and evaluated the model; logged to MLflow.", "Offline, run once"],
       ["Public link", "Cloudflare quick tunnel that exposes the Docker app on the internet.", "tools/cloudflared.exe"]],
      [28 * mm, W - 28 * mm - 50 * mm, 50 * mm])
H3("Two ways it runs")
table([["Mode", "Website", "API", "How to open"],
       ["Development", "Vite dev server (port 5173), proxies /api → 127.0.0.1:8000", "uvicorn app.main:app on port 8000", "http://localhost:5173"],
       ["Docker", "nginx container (port 8080) serving the built site, proxies /api → backend container", "backend container (uvicorn, port 8000 inside Docker)", "http://127.0.0.1:8080 (+ public tunnel)"]],
      [24 * mm, 62 * mm, 50 * mm, W - 136 * mm])

# ---- 4 tech stack
H1("4. Technology stack")
P("All tools are free and open source. Versions are the ones installed in this project.")
H3("Machine learning")
table([["Technology", "Version", "Used for"],
       ["Python", "3.13.1 (local) / 3.12 (Docker)", "Language for the backend, training and model"],
       ["PyTorch", "2.15.0 (CPU)", "Deep-learning framework: model, training, MC Dropout, Grad-CAM gradients"],
       ["Torchvision", "0.29.2", "ResNet-50 architecture and ImageNet pre-trained weights"],
       ["NumPy", "2.5.4", "Numerical arrays (probabilities, uncertainty, image statistics)"],
       ["Pillow", "13.0.0", "Reading, converting, resizing and re-encoding images"],
       ["OpenCV (headless)", "5.0.0", "Heatmap colouring and resizing for Grad-CAM"],
       ["scikit-learn", "1.9.1", "ROC-AUC, PR-AUC, confusion matrix, patient-grouped data splitting"],
       ["SciPy", "1.18.1", "Fitting the calibration temperature (optimisation)"],
       ["Optuna", "5.1.0", "Hyper-parameter search (25 trials) — training only"],
       ["MLflow", "3.18.0", "Experiment tracking of training runs and trials — training only"],
       ["pandas", "2.3.3", "Dataset manifest and statistics — training only"]],
      [34 * mm, 38 * mm, W - 72 * mm])
H3("Backend")
table([["Technology", "Version", "Used for"],
       ["FastAPI", "0.163.1", "REST API framework"],
       ["Uvicorn", "0.54.0", "ASGI web server that runs FastAPI"],
       ["SQLAlchemy", "2.1.9", "Database access (ORM) for SQLite"],
       ["SQLite", "built into Python", "Database file storing users and analyses"],
       ["Pydantic / pydantic-settings", "2.14.3 / 2.16.3", "Request/response validation and settings from .env"],
       ["bcrypt", "5.0.0", "Password hashing"],
       ["PyJWT", "2.15.1", "Signed session tokens"],
       ["email-validator", "2.4.0", "Checking email addresses at sign-up"],
       ["python-multipart", "0.0.34", "Receiving file uploads"],
       ["pytest + httpx", "9.2.0 / 0.28.1", "Automated tests"]],
      [44 * mm, 32 * mm, W - 76 * mm])
H3("Frontend")
table([["Technology", "Version", "Used for"],
       ["React", "18.3.1", "User-interface library"],
       ["TypeScript", "5.6.3", "Typed JavaScript"],
       ["Vite", "5.4.11", "Development server and production build"],
       ["Tailwind CSS", "3.4.16", "Styling (with colour variables for the light Home/Login and dark app theme)"],
       ["React Router", "6.28.0", "Page navigation and protected routes"],
       ["Axios", "1.7.9", "HTTP requests to the backend"],
       ["Recharts", "2.13.3", "Charts (dashboard, ROC curve, uncertainty charts)"],
       ["Lucide React", "0.468.0", "Icons"],
       ["Inter (Fontsource)", "5.1.0", "Font, bundled locally"]],
      [34 * mm, 24 * mm, W - 58 * mm])
H3("Deployment and tools")
table([["Technology", "Used for"],
       ["Docker + Docker Compose", "Two containers: <b>backend</b> (python:3.12-slim) and <b>frontend</b> (node:22 build → nginx:1.27)"],
       ["nginx", "Serves the built website and forwards /api to the backend inside Docker"],
       ["Cloudflare quick tunnel (cloudflared)", "Free temporary public https link to the Docker app (start-public.bat)"],
       ["Node.js 24 / npm 11", "Building the frontend"],
       ["reportlab + matplotlib", "Generating this PDF"]],
      [62 * mm, W - 62 * mm])

# ---- 5 model
H1("5. The machine-learning model")
H2("5.1 Architecture")
table([["Part", "Details"],
       ["Backbone", "<b>ResNet-50</b> (torchvision) initialised with ImageNet-1K V2 weights and kept <b>frozen</b> (not retrained) because training ran on a CPU. It turns a 224 × 224 image into 2,048 features."],
       ["Classification head", f"Dropout → Linear(2048 → {cfg['head']['hidden']}) → ReLU → Dropout → Linear({cfg['head']['hidden']} → 1). Dropout rate {cfg['head']['dropout']:.3f}. Output: one number (logit) for pneumonia."],
       ["Input", "Grayscale X-ray, resized to 224 × 224 (whole image, no cropping), repeated to 3 channels, ImageNet normalisation."],
       ["Output", "Probability of pneumonia (0–1), uncertainty (0–1), AUTO/REFER decision, Grad-CAM heatmap."],
       ["Model files", "artifacts/models/v1.1.0/model.pt (95 MB, SHA-256 checked on load) + config.json + evaluation.json"]],
      [32 * mm, W - 32 * mm])
H2("5.2 Training")
hp = cfg["hyperparameters"]
bullets([
    f"Data split by <b>patient</b> (no child appears in two groups): train {ev['training']['split_sizes']['train']}, validation {ev['training']['split_sizes']['val']}, test {ev['training']['split_sizes']['test']} images.",
    "Features from the frozen ResNet-50 were computed once for all 5,856 images and cached (data/features).",
    f"<b>Optuna</b> searched {ev['training']['optuna_trials']} combinations of learning rate, weight decay, dropout and head size, minimising validation loss. Best: learning rate {hp['lr']:.5f}, weight decay {hp['weight_decay']:.4f}, dropout {hp['dropout']:.3f}, hidden size {hp['hidden']}.",
    f"Optimiser AdamW, binary cross-entropy loss with a class weight (pneumonia images outnumber normal ones ~2.7 : 1), early stopping on validation loss (stopped after {ev['training']['epochs_run']} epochs).",
    "Every run and trial was logged to <b>MLflow</b> (mlflow/mlflow.db).",
    "The test set was used only once, for the final evaluation.",
])
H2("5.3 Uncertainty (Monte Carlo Dropout)")
P("Dropout randomly switches off parts of the network. Keeping it on during prediction and running the head "
  f"<b>{cfg['mc_passes']} times</b> gives {cfg['mc_passes']} slightly different probabilities. If they agree, the model is sure; "
  "if they disagree, it is unsure. From the 30 values the backend computes:")
table([["Quantity", "Meaning"],
       ["Mean probability", "The final pneumonia probability shown to the user"],
       ["Predictive entropy (bits)", "Total uncertainty of the mean: 0 = certain, 1 = coin flip. <b>This is the 'Uncertainty' shown in the app</b> and used for AUTO/REFER."],
       ["Mutual information", "How much the passes disagree (the model's own doubt) — computed, stored in the evaluation"],
       ["Variance / standard deviation", "Spread of the 30 answers"]],
      [48 * mm, W - 48 * mm])
H2("5.4 Calibration (temperature scaling)")
P(f"A single number T = <b>{cfg['temperature']:.3f}</b> was fitted on the validation set so that the stated probabilities match "
  f"how often the model is actually right. Expected Calibration Error on the test set: "
  f"{cal['before']['ece']:.3f} before → <b>{cal['after']['ece']:.3f}</b> after (target ≤ 0.05).")
H2("5.5 Decision policy: AUTO or REFER")
table([["Rule", "Result"],
       ["The image fails the quality check (colour, no contrast, unusual shape)", "<b>REFER</b>"],
       [f"Uncertainty &gt; {cfg['refer_threshold']:.3f} (53.5%)", "<b>REFER</b> — sent for specialist review"],
       ["Otherwise", "<b>AUTO</b> — Pneumonia if probability ≥ 0.5, otherwise Normal"]],
      [W - 60 * mm, 60 * mm])
P(f"The threshold was chosen on the validation set as the one that refers the fewest X-rays while keeping the error on "
  f"AUTO results at or below 1% ({ev['policy']['method']}).", small)
H2("5.6 Grad-CAM explanations")
P("Grad-CAM takes the gradients of the model's output with respect to ResNet-50's last convolutional block (layer4), "
  "weights the feature maps by them and produces a 7 × 7 map that is resized to the image. Red/yellow = areas that pushed "
  "the prediction most. It shows influence, not the location of disease.")

# ---- 6 dataset
H1("6. Dataset")
H2("6.1 Kermany Pediatric Chest X-Ray (used for training and testing)")
table([["Item", "Details"],
       ["Source", "Kermany, Zhang &amp; Goldbaum — Labeled Optical Coherence Tomography and Chest X-Ray Images for Classification, Mendeley Data v2 (2018), doi:10.17632/rscbjbr9sj.2"],
       ["Licence", "CC BY 4.0 (free to use with attribution)"],
       ["Population", "Children aged 1–5, Guangzhou Women and Children's Medical Center"],
       ["Size", f"{card['total_images']:,} images from {card['total_patients']:,} patients (identified from pseudonymous file names)"],
       ["Classes", f"Normal {card['class_distribution']['NORMAL']:,} · Pneumonia {card['class_distribution']['PNEUMONIA']:,} (bacterial {card['subtype_distribution']['bacterial']:,}, viral {card['subtype_distribution']['viral']:,})"],
       ["Download", "ChestXRay2017.zip (1.2 GB), SHA-256 checked, stored in data/raw/"]],
      [30 * mm, W - 30 * mm])
H2("6.2 How the data was split")
table([["Split", "Images", "Patients", "Normal", "Pneumonia"]] +
      [[s["split"].title(), f"{s['images']:,}", f"{s['patients']:,}", f"{s['normal']:,}", f"{s['pneumonia']:,}"] for s in card["patient_disjoint_split"]["splits"]],
      [W / 5] * 5)
P("The split is <b>patient-disjoint</b> (StratifiedGroupKFold, seed 42): 0 patients are shared between train, validation and "
  "test. For comparison a deliberately <b>flawed</b> random image-level split was also made; in it, "
  f"{leak['flawed_image_level']['overlap']['test_images_from_train_patients']} of {leak['flawed_image_level']['overlap']['test_images']} test images came from patients also in training.")
H2("6.3 Duplicate check")
dup = card["duplicates"]
P(f"Exact duplicates (same file content): {dup['exact_duplicate_images']} images in {dup['exact_duplicate_groups']} groups, none across splits. "
  f"Near-duplicates ({dup['near_duplicate_method']}): {dup['near_duplicate_pairs']} pairs, none across the patient-disjoint splits.")
H2("6.4 RSNA Pneumonia Detection (external test)")
P("Planned as an external test on adult X-rays from a different hospital. It has <b>not been run</b> because the data must be "
  "downloaded from Kaggle with an account. The script <b>backend/scripts/evaluate_external.py</b> is ready for when the data is available.")

# ---- 7 results
story.append(PageBreak())
H1("7. Results (test set: 837 X-rays from unseen patients)")
table([["Metric", "Value", "95% confidence interval", "Meaning"],
       ["Accuracy", pct(disc["accuracy"]), f"{pct(ci['accuracy']['lower'])} – {pct(ci['accuracy']['upper'])}", "Share of X-rays classified correctly"],
       ["Precision", pct(disc["precision"]), f"{pct(ci['precision']['lower'])} – {pct(ci['precision']['upper'])}", "When it says pneumonia, how often it is right"],
       ["Recall (sensitivity)", pct(disc["recall"]), f"{pct(ci['recall']['lower'])} – {pct(ci['recall']['upper'])}", "Share of pneumonia cases it catches"],
       ["Specificity", pct(disc["specificity"]), f"{pct(ci['specificity']['lower'])} – {pct(ci['specificity']['upper'])}", "Share of normal X-rays called normal"],
       ["F1-score", pct(disc["f1"]), f"{pct(ci['f1']['lower'])} – {pct(ci['f1']['upper'])}", "Balance of precision and recall"],
       ["ROC-AUC", f"{disc['roc_auc']:.3f}", f"{ci['roc_auc']['lower']:.3f} – {ci['roc_auc']['upper']:.3f}", "Overall ability to separate the classes (1 = perfect)"],
       ["PR-AUC", f"{disc['pr_auc']:.3f}", f"{ci['pr_auc']['lower']:.3f} – {ci['pr_auc']['upper']:.3f}", "Precision-recall area"],
       ["ECE (after calibration)", f"{cal['after']['ece']:.3f}", f"{ci['ece']['lower']:.3f} – {ci['ece']['upper']:.3f}", "How honest the probabilities are (0 = perfect)"],
       ["Brier score", f"{cal['after']['brier']:.3f}", f"{ci['brier']['lower']:.3f} – {ci['brier']['upper']:.3f}", "Probability error (lower is better)"]],
      [34 * mm, 20 * mm, 38 * mm, W - 92 * mm])
P("Confidence intervals come from 1,000 bootstrap resamples of the test set.", small)
two(chart_cm(), chart_roc())
H2("7.1 Uncertainty and referral")
table([["Result", "Value"],
       ["X-rays referred (REFER)", f"{rb['bands']['REFER']['n']} of {rb['n']} ({pct(rb['refer_rate'])})"],
       ["Accuracy on all X-rays", pct(rb["overall_accuracy"])],
       ["Accuracy on AUTO X-rays only", f"<b>{pct(rb['auto_decision_accuracy'])}</b>"],
       ["Wrong predictions caught by REFER", f"{rb['errors_captured_by_refer']} of {rb['total_errors']}"],
       ["Uncertainty as an error detector (AUROC)", f"{unc['entropy']['error_detection_auroc']:.3f}"],
       ["Average uncertainty on the test set", pct(unc["mean_entropy"])]],
      [W * 0.6, W * 0.4])
two(chart_uncertainty(), chart_arc())
H2("7.2 Calibration")
story.append(KeepTogether([Image(str(chart_reliability()), width=W / 2, height=W / 2 * 0.853)]))
H2("7.3 Leakage comparison")
table([["Split", "ROC-AUC", "Accuracy", "Test images from training patients"],
       ["Flawed (random by image)", f"{leak['flawed_image_level']['roc_auc']:.3f}", pct(leak["flawed_image_level"]["accuracy"]),
        f"{leak['flawed_image_level']['overlap']['test_images_from_train_patients']} / {leak['flawed_image_level']['overlap']['test_images']}"],
       ["Correct (patient-disjoint)", f"{leak['patient_disjoint']['roc_auc']:.3f}", pct(leak["patient_disjoint"]["accuracy"]),
        f"{leak['patient_disjoint']['overlap']['test_images_from_train_patients']} / {leak['patient_disjoint']['overlap']['test_images']}"]],
      [50 * mm, 28 * mm, 28 * mm, W - 106 * mm])
P(f"Mixing patients inflates the scores (ROC-AUC +{leak['delta']['roc_auc']:.3f}); the reported results use the correct patient-disjoint split.")
H2("7.4 Targets from the research plan")
table([["Target", "Required", "Achieved", "Met?"],
       ["ROC-AUC", "≥ 0.95", f"{disc['roc_auc']:.3f}", "Yes"],
       ["Recall", "≥ 0.93", pct(disc["recall"]), "Yes"],
       ["Calibration error (ECE)", "≤ 0.05", f"{cal['after']['ece']:.3f}", "Yes"],
       ["External RSNA test", "Reported", "Not run yet", "No"]],
      [55 * mm, 35 * mm, 35 * mm, W - 125 * mm])

# ---- 8 storage
story.append(PageBreak())
H1("8. Where all data is saved")
P("Everything is stored on this computer inside the project folder <b>D:\\backup\\Python\\Computer Science Project\\Pneumonia</b> "
  "(paths below are relative to it). Nothing is uploaded to a cloud database.")
H2("8.1 Data used by the running app")
table([["What", "Location", "Contents"],
       ["Database", "backend/var/pneumoscope.db (+ -wal, -shm files)", "SQLite file with the <b>users</b> and <b>analyses</b> tables (see section 9)"],
       ["Uploaded X-rays", "backend/var/uploads/&lt;id&gt;.png", "Each upload re-saved as a grayscale PNG under a random 32-character ID; original file name and EXIF/metadata are not kept"],
       ["Thumbnails", "backend/var/uploads/&lt;id&gt;.thumb.webp", "160-px preview for the history list (created on first view)"],
       ["Grad-CAM images", "backend/var/gradcam/&lt;id&gt;/", "overlay.png (shown in the app), heatmap.png, original.png, cam.npy (raw map)"],
       ["Trained model", "artifacts/models/v1.1.0/", "model.pt (95 MB weights), config.json (temperature, thresholds), evaluation.json (all test results), reference_stats.json"],
       ["Dataset statistics", "artifacts/datasets/kermany/dataset_card.json", "Counts, splits, image statistics, duplicates"],
       ["Session secret (dev)", "backend/var/.secret_key", "Random key used to sign login sessions when SECRET_KEY is not set"],
       ["Settings and secrets", ".env (project root, git-ignored)", "SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD and other settings"],
       ["Website images", "frontend/public/images/", "Home/login/dashboard backgrounds and heatmap example (made by scripts/make_site_images.py)"]],
      [30 * mm, 55 * mm, W - 85 * mm])
H2("8.2 In Docker")
P("Inside Docker the backend writes to <b>/srv/backend/var</b>, which is the Docker volume <b>pneumonia_backend_data</b> "
  "(database, uploads, heatmaps — kept when containers restart). The model folder <b>artifacts/</b> is mounted read-only "
  "into the container at /srv/artifacts. So the Docker app and the development app have <b>separate</b> databases.")
H2("8.3 Training data and experiment records")
table([["What", "Location", "Size"],
       ["Original dataset download", "data/raw/ChestXRay2017.zip", "1.2 GB"],
       ["Extracted X-ray images + manifest", "data/kermany/chest_xray/..., data/kermany/manifest.csv", "1.2 GB"],
       ["Cached ResNet-50 features", "data/features/kermany_resnet50.npz", "48 MB"],
       ["MLflow tracking database", "mlflow/mlflow.db (52 runs: 2 training runs + 50 Optuna trials)", "1.2 MB"],
       ["MLflow artifact files", "backend/mlruns/", "0.5 MB"],
       ["Public link tool and log", "tools/cloudflared.exe, tools/tunnel.log, tools/current_url.txt", "55 MB"]],
      [50 * mm, W - 72 * mm, 22 * mm])
H2("8.4 Left over from earlier versions (not used by the current app)")
bullets([
    "<b>backend/var/app.db</b>, <b>backend/var/outbox</b>, <b>backend/var/reports</b> — database and folders from the earlier, larger version of the app.",
    "<b>artifacts/models/v1.0.0</b> — the first model version (same weights, less strict referral threshold); replaced by v1.1.0.",
    "Docker volumes <b>pneumonia_backend_var</b> and <b>pneumonia_pgdata</b> — from the earlier PostgreSQL setup.",
])
P("These can be deleted to save space; the current app does not read them.", small)
H2("8.5 What is excluded from version control (.gitignore)")
P(".env, .venv/, node_modules/, frontend/dist/, backend/var/, data/raw/, data/kermany/, data/features/, mlflow/, model.pt weight files, tools/.", small)

# ---- 9 database
H1("9. Database structure")
P("SQLite database created automatically by SQLAlchemy at start-up (backend/app/models.py).")
H3("Table: users")
table([["Column", "Type", "Description"],
       ["id", "integer, primary key", "User number"],
       ["email", "text, unique", "Login email (stored in lower case)"],
       ["name", "text", "Full name shown in the app"],
       ["password_hash", "text", "bcrypt hash — the password itself is never stored"],
       ["created_at", "datetime (UTC)", "When the account was created"]],
      [32 * mm, 38 * mm, W - 70 * mm])
H3("Table: analyses")
table([["Column", "Type", "Description"],
       ["id", "text (32 hex), primary key", "Random ID, also used for the image file names"],
       ["created_at", "datetime (UTC)", "When the X-ray was analysed"],
       ["image_path, image_width, image_height", "text / integer", "Stored PNG file name and the image size"],
       ["prediction", "text", "PNEUMONIA or NORMAL"],
       ["pneumonia_probability", "float 0–1", "Calibrated mean probability"],
       ["uncertainty", "float 0–1", "Predictive entropy (bits)"],
       ["decision, decision_reason", "text", "AUTO or REFER, and why"],
       ["referral_threshold", "float", "Threshold that applied at the time"],
       ["model_version", "text", "Model that produced the result (v1.1.0)"],
       ["processing_ms", "float", "Time taken for inference"],
       ["gradcam_path", "text, nullable", "Folder of the heatmap once generated"]],
      [50 * mm, 36 * mm, W - 86 * mm])
P("No patient names, original file names or image metadata are stored.", small)

# ---- 10 API
H1("10. Backend API")
P("Base address: <b>http://127.0.0.1:8000</b> (development). The website reaches it as <b>/api/...</b>. Interactive "
  "documentation: http://127.0.0.1:8000/docs. All endpoints except /auth/* and /health require a logged-in session.")
table([["Method", "Path", "What it does"],
       ["POST", "/auth/register", "Create an account (name, email, password) and log in"],
       ["POST", "/auth/login", "Log in (email, password, remember me)"],
       ["POST", "/auth/logout", "Log out (removes the session cookie)"],
       ["GET", "/auth/me", "Who is logged in"],
       ["POST", "/triage", "Upload an X-ray (form field <b>file</b>) → prediction, probability, uncertainty, AUTO/REFER; saved"],
       ["GET", "/analysis/history", "List saved analyses, newest first"],
       ["GET", "/analysis/{id}", "One analysis"],
       ["DELETE", "/analysis/{id}", "Delete an analysis and its image files"],
       ["POST", "/analysis/{id}/gradcam", "Create the Grad-CAM heatmap for an analysis"],
       ["GET", "/analysis/{id}/image", "The stored X-ray (add ?thumb=true for a small preview)"],
       ["GET", "/analysis/{id}/gradcam", "The heatmap image"],
       ["GET", "/model-info", "Model status, version, threshold"],
       ["GET", "/metrics", "Test-set evaluation results (metrics, confusion matrix, ROC curve, uncertainty)"],
       ["GET", "/dashboard", "Totals, last-7-days counts, uncertainty trend, recent analyses"],
       ["GET", "/health", "Server and model status (public)"]],
      [16 * mm, 50 * mm, W - 66 * mm])
H3("Example /triage response (shortened)")
CODE('{ "id": "a664d302...", "prediction": "NORMAL",\n  "pneumonia_probability": 0.0066, "normal_probability": 0.9934,\n  "uncertainty": 0.057, "decision": "AUTO",\n  "decision_reason": "Uncertainty is below the referral threshold.",\n  "referral_threshold": 0.535, "model_version": "v1.1.0", "processing_ms": 410,\n  "image_url": "/analysis/a664.../image", "gradcam_url": null }')
H3("Error responses")
P("401 not logged in · 404 not found · 409 email already registered · 413 file too large · 415 wrong file type · "
  "422 invalid input (bad image, too small, weak password) · 503 model not available (\"integration pending\").")

# ---- 11 website
H1("11. Website pages")
table([["Page", "Address", "Access", "What is on it"],
       ["Home", "/", "Public", "Full-screen hero 'PNEUMO · SCOPE' with an X-ray, key results, how it works, results, get-started banner"],
       ["Login", "/login", "Public", "Glass card on a full-page X-ray: email, password, remember me, register mode"],
       ["Dashboard", "/dashboard", "Logged in", "Analyses (7-day chart), predictions, referred, accuracy gauge, uncertainty trend, recent analyses"],
       ["X-Ray Analysis", "/analyse", "Logged in", "Drag-and-drop upload, preview, validation, Analyse button, result with heatmap"],
       ["Analysis History", "/history", "Logged in", "Table of past analyses with thumbnails; open or delete"],
       ["Result", "/history/{id}", "Logged in", "One saved result: prediction, probability, uncertainty scale, AUTO/REFER, heatmap"],
       ["Model Performance", "/performance", "Logged in", "Metrics, confusion matrix, ROC curve, uncertainty &amp; referral charts, summary"],
       ["About Project", "/about", "Logged in", "Introduction, problem, objectives, method, dataset, technologies, limitations"]],
      [27 * mm, 24 * mm, 20 * mm, W - 71 * mm])
H3("Design")
bullets([
    "Home and Login: dark cinematic background (warm-toned chest X-rays), glass cards and an orange accent.",
    "Inside the app: same dark glass theme with a round icon sidebar, a greeting ('Hey, name') at the top and orange charts.",
    "Colours are CSS variables, so one class (<b>theme-dark</b>) switches the whole app area. Font: Inter.",
    "Responsive: works on desktop, tablet and phone (sidebar becomes a row of icons on small screens).",
    "Requests are cancelled when you change page and time out after 20 seconds with a Retry button.",
])

# ---- 12 security
H1("12. Security and privacy")
table([["Area", "How it is handled"],
       ["Passwords", "Hashed with bcrypt (12 rounds); minimum 8 characters with a letter and a number"],
       ["Sessions", "Signed token (HS256) in an <b>HttpOnly, SameSite=Lax</b> cookie that JavaScript cannot read; 12-hour lifetime with 'Remember me', otherwise ends when the browser closes"],
       ["Access control", "All analysis, model and dashboard endpoints require a valid session"],
       ["Upload checks", "Extension and content type must be JPG/PNG, file content must start with JPEG/PNG bytes, must decode, ≤ 10 MB, sides between 128 and 8,192 px, decompression-bomb limit"],
       ["Privacy", "Images are re-encoded to PNG (removes EXIF/metadata), saved under random IDs; original file names are never stored"],
       ["File serving", "Paths are resolved and checked to stay inside the storage folders (no path traversal)"],
       ["HTTP headers", "X-Content-Type-Options: nosniff, X-Frame-Options: SAMEORIGIN; gzip compression"],
       ["Model integrity", "Model weights are SHA-256 checked before loading; if missing or changed the app says 'integration pending' instead of guessing"],
       ["Secrets", "Kept in .env (git-ignored); never in the frontend code"]],
      [30 * mm, W - 30 * mm])

# ---- 13 project files
H1("13. Project files")
CODE("""Pneumonia/
 backend/
   app/
     main.py            FastAPI app, start-up, routes
     config.py          settings (.env), folder locations
     database.py        SQLite connection
     models.py          tables: users, analyses
     schemas.py         API response shapes
     auth.py            register / login / logout / sessions
     routes/analysis.py triage, history, delete, images, Grad-CAM
     routes/model.py    model-info, metrics, dashboard
     ml/                ResNet-50 model, MC Dropout, preprocessing,
                        decision policy, model loading, metrics
     services/          inference, uncertainty, calibration,
                        Grad-CAM, image validation, file storage
   scripts/             prepare_kermany, train_pipeline,
                        evaluate_external, make_site_images
   tests/               39 automated tests
   requirements.txt, requirements-train.txt, Dockerfile
 frontend/
   src/pages/           Home, Login, Dashboard, Analyse, History,
                        Result, Performance, About
   src/layouts/         AppLayout (sidebar + top bar)
   src/components/      ResultView, UI kit, chart theme, Logo
   src/services/api.ts  all calls to the backend
   src/context/         login state
   package.json, vite.config.ts, tailwind.config.js,
   nginx.conf, Dockerfile
 artifacts/models/v1.1.0/   trained model + results
 artifacts/datasets/        dataset statistics
 data/                       dataset and cached features
 mlflow/                     experiment tracking database
 docs/                       this guide and its generator
 docker-compose.yml, .env.example, README.md, start-public.bat""")
P("About 2,200 lines of Python and 1,700 lines of TypeScript/CSS.", small)

# ---- 14 how to run
H1("14. How to run it")
H2("14.1 Development (two terminal windows)")
CODE("""# Backend
cd backend
..\\.venv\\Scripts\\python -m uvicorn app.main:app --port 8000

# Frontend
cd frontend
npm install        (first time only)
npm run dev        -> open http://localhost:5173""")
H2("14.2 Docker")
CODE("""docker compose up --build -d     -> open http://127.0.0.1:8080
docker compose down              (stop)""")
H2("14.3 Public link")
P("Make sure Docker Desktop is running, then double-click <b>start-public.bat</b>. It starts the containers and prints a "
  "link like https://xxxx.trycloudflare.com. Keep the window open. The link changes every time and stops working when the "
  "PC sleeps or restarts.")
H2("14.4 Tests")
CODE("""cd backend
..\\.venv\\Scripts\\python -m pytest""")
H2("14.5 Re-training and regenerating files")
CODE("""pip install -r backend/requirements-train.txt
cd backend
..\\.venv\\Scripts\\python -m scripts.prepare_kermany
..\\.venv\\Scripts\\python -m scripts.train_pipeline --trials 25 --version v1.2.0 --target-error 0.01
..\\.venv\\Scripts\\python -m scripts.make_site_images
..\\.venv\\Scripts\\python ..\\docs\\build_project_guide.py      (this PDF)""")
P("To use a new model version set MODEL_VERSION in .env (default v1.1.0).", small)

# ---- 15 testing
H1("15. Testing")
table([["Test file", "What it checks"],
       ["test_ml_core.py", "Uncertainty maths, temperature scaling and ECE, AUTO/REFER rules (never auto-decides above the threshold), MC Dropout randomness and reproducibility, preprocessing, Grad-CAM output, evaluation metrics"],
       ["test_upload_validation.py", "Accepts JPG/PNG; rejects empty, wrong type, fake image bytes, corrupted, too small and too large files"],
       ["test_api.py", "Full flow: upload → result → image → heatmap → history → dashboard → delete; invalid uploads; colour image referred; honest 'no evaluation' message"],
       ["test_auth.py", "Pages locked without login, register/login/logout, weak password and duplicate email rejected, passwords hashed, Remember me cookie"]],
      [44 * mm, W - 44 * mm])
P("All <b>39 tests pass</b>. The app was also tested by hand in the browser at desktop and phone sizes, and end to end over the public link.", small)

# ---- 16 limitations
H1("16. Limitations and honest notes")
bullets([
    "The ResNet-50 backbone is frozen (only the head was trained) because training ran on a CPU; fine-tuning could change the results.",
    "Uncertainty comes from dropout in the head only, so it does not capture all of the backbone's uncertainty.",
    "Training data are children's X-rays from one hospital; performance on adults or other hospitals is unknown until the RSNA test is run.",
    "The validation set was used for early stopping, hyper-parameter search, calibration and the referral threshold; the test set was used once.",
    "Patient identity was inferred from file names.",
    "Grad-CAM shows which areas influenced the result, not where the disease is.",
    "There is no e-mail password reset; 'Forgot password' tells the user to ask the administrator.",
    "The public link is temporary (free tunnel from this PC); permanent hosting would need a paid service.",
    "Educational research software only — not a medical device and not for clinical use.",
])

# ---- 17 glossary
H1("17. Glossary")
table([["Term", "Meaning"],
       ["ResNet-50", "A 50-layer convolutional neural network widely used for image recognition"],
       ["Monte Carlo Dropout", "Running the model many times with random dropout to see how much its answers vary"],
       ["Predictive entropy", "A measure of uncertainty from 0 (certain) to 1 bit (50/50)"],
       ["Temperature scaling", "Dividing the model's raw output by one fitted number so probabilities are honest"],
       ["AUTO / REFER", "Confident result given directly / uncertain result sent for human review"],
       ["Grad-CAM", "A heatmap of the image regions that most influenced the prediction"],
       ["ROC-AUC", "Probability that the model ranks a random pneumonia X-ray above a random normal one"],
       ["ECE", "Expected Calibration Error: average gap between stated probability and actual accuracy"],
       ["Patient-disjoint split", "Splitting data so the same patient never appears in both training and testing"],
       ["Bootstrap CI", "A confidence range found by re-sampling the test set many times"],
       ["FastAPI", "Python framework for building web APIs"],
       ["SQLite", "A database stored in a single file"],
       ["Docker", "Packages the app and everything it needs into containers that run the same anywhere"]],
      [40 * mm, W - 40 * mm])


# ================================================================== PART B — technical reference
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "backend"))
from app.main import app as fastapi_app  # noqa: E402
from app.config import Settings  # noqa: E402

spec = fastapi_app.openapi()
schemas = spec["components"]["schemas"]
ENDPOINTS = {(m.upper(), p) for p, ops in spec["paths"].items() for m in ops}


def fields(name):
    sc = schemas[name]
    req = set(sc.get("required", []))
    rows = []
    for k, v in sc["properties"].items():
        t = v.get("type") or " | ".join(a.get("type", "?") for a in v.get("anyOf", []))
        rows.append([f"<font face='Courier'>{k}</font>", t, "yes" if k in req else "no",
                     "" if "default" not in v else repr(v["default"])])
    return rows


story.append(PageBreak())
H1("Part B — Technical reference")
P("This part lists every technical detail: external services, every API endpoint with inputs and outputs, response "
  "schemas, all settings, each code module, the exact formulas, file formats, scripts, Docker set-up and security "
  "internals. The endpoint list is checked against the running API's OpenAPI definition each time this PDF is built, "
  "so it cannot drift from the code.")

# ---- 18 external services
H1("18. External services and APIs used")
table([["Service", "Used for", "When", "Cost / key"],
       ["Mendeley Data (Kermany et al., 2018, DOI 10.17632/rscbjbr9sj.2)", "Downloading the ChestXRay2017.zip dataset (5,856 images)", "Once, before training", "Free, public, no key"],
       ["download.pytorch.org", "PyTorch CPU wheels; ImageNet-pretrained ResNet-50 weights (torchvision IMAGENET1K_V2)", "Install / first training run", "Free, no key"],
       ["PyPI and npm registries", "Python and JavaScript packages", "Install / Docker build", "Free"],
       ["Docker Hub", "Base images python:3.12-slim, node:22-alpine, nginx:1.27-alpine", "Docker build", "Free"],
       ["Cloudflare Quick Tunnel (cloudflared)", "Temporary public https://*.trycloudflare.com link to the local Docker app", "When start-public.bat runs", "Free, no account"],
       ["Google Fonts", "Inter font for the website", "In the browser", "Free"],
       ["Kaggle (RSNA)", "Optional external test set — <b>not run</b>", "—", "Needs a Kaggle account"]],
      [44 * mm, 62 * mm, 32 * mm, W - 138 * mm])
P("No paid service, cloud AI API or third-party AI model is used. All predictions are computed locally by the project's "
  "own trained model; no image or user data ever leaves the machine (except through the tunnel to the user's browser).", small)

# ---- 19 API reference
H1("19. API reference (every endpoint)")
P("Base URL: <b>http://127.0.0.1:8000</b> directly, or <b>/api</b> through the website / nginx (e.g. /api/triage). "
  "Format: JSON unless stated. Authentication: the <font face='Courier'>pneumoscope_session</font> cookie set by "
  "/auth/login or /auth/register; browsers send it automatically (axios <font face='Courier'>withCredentials: true</font>). "
  "Error bodies always look like <font face='Courier'>{\"detail\": \"message\"}</font>. Interactive docs: /docs (Swagger), "
  "/redoc, raw definition /openapi.json.")

API = [
    ("POST", "/auth/register", "Public",
     "JSON body <b>RegisterIn</b>: name (2–120 chars), email (valid address), password (≥ 8 chars, a letter and a number).",
     "201 → <b>UserOut</b> and the session cookie is set (12 h).", "409 email already registered · 422 invalid fields / weak password"),
    ("POST", "/auth/login", "Public",
     "JSON body <b>LoginIn</b>: email, password, remember (bool, default true).",
     "200 → <b>UserOut</b>; cookie set (persistent 12 h if remember, otherwise a browser-session cookie).", "401 'Incorrect email or password.' · 422"),
    ("POST", "/auth/logout", "Public", "No body.", "204, cookie deleted.", "—"),
    ("GET", "/auth/me", "Session", "No body.", "200 → <b>UserOut</b> of the signed-in user.", "401 not signed in / session expired"),
    ("POST", "/triage", "Session",
     "multipart/form-data with one field <b>file</b> (JPG/JPEG/PNG, ≤ 10 MB, sides 128–8,192 px).",
     "201 → <b>AnalysisOut</b>. Runs validation → preprocessing → 30 MC passes → calibration → entropy → AUTO/REFER, "
     "then stores the record and the cleaned PNG.", "401 · 413 too large · 415 wrong type / fake bytes · 422 empty, corrupt, too small · 503 model unavailable"),
    ("GET", "/analysis/history", "Session",
     "Query <b>limit</b> (int, 1–200, default 50), <b>offset</b> (int ≥ 0, default 0).",
     "200 → <b>HistoryOut</b> {items: AnalysisOut[], total}. Newest first.", "401 · 422 out-of-range parameters"),
    ("GET", "/analysis/{analysis_id}", "Session", "Path: 32-character id.", "200 → <b>AnalysisOut</b>.", "401 · 404"),
    ("DELETE", "/analysis/{analysis_id}", "Session", "Path: id.",
     "204. Deletes the DB row, the PNG, its thumbnail and the Grad-CAM folder.", "401 · 404"),
    ("POST", "/analysis/{analysis_id}/gradcam", "Session", "Path: id. No body.",
     "200 → <b>AnalysisOut</b> with gradcam_url set. Computed once, then cached (calling again returns the saved one).",
     "401 · 404 analysis or image missing · 503"),
    ("GET", "/analysis/{analysis_id}/gradcam", "Session", "Path: id.", "200 image/png (heatmap overlaid on the X-ray, 224 × 224).",
     "401 · 404 not generated yet"),
    ("GET", "/analysis/{analysis_id}/image", "Session", "Path: id. Query <b>thumb</b> (bool, default false).",
     "200 image/png (stored X-ray), or image/webp 160 px thumbnail when thumb=true (cached; Cache-Control private, 1 day).",
     "401 · 404"),
    ("GET", "/model-info", "Session", "—",
     "200 → available, status ('Ready' / 'Integration pending'), message, name, version, architecture, training_dataset, "
     "trained_at, referral_threshold, calibrated, …", "401"),
    ("GET", "/metrics", "Session", "—",
     "200 → available, model_version, dataset, n_images, n_pneumonia, n_normal, accuracy, precision, recall, f1, roc_auc, "
     "roc_auc_ci, specificity, confusion_matrix, roc_curve [{x,y}], refer_rate, auto_accuracy, external_rsna (null), "
     "uncertainty {referral_threshold, refer_rate, n_referred, overall_accuracy, auto_accuracy, errors caught, histogram, "
     "accuracy_vs_referred}. If no evaluation exists: {available: false, message}.", "401"),
    ("GET", "/dashboard", "Session", "—",
     "200 → total, normal, pneumonia, referred, auto, average_uncertainty, recent (5 × AnalysisOut), "
     "daily (7 × {date, normal, pneumonia, referred}), uncertainty_series (last 30 × {date, uncertainty, decision}), model (= /model-info).",
     "401"),
    ("GET", "/health", "Public", "—", "200 → {status: 'ok', model_available: true/false} — used by the Docker healthcheck.", "—"),
]
documented = {(m, p) for m, p, *_ in API}
missing = ENDPOINTS - documented
extra = documented - ENDPOINTS
assert not missing and not extra, f"API reference out of date: missing={missing} extra={extra}"

for m, p, auth_, inp, out, err in API:
    story.append(KeepTogether([
        Paragraph(f"<font color='#E8642F'><b>{m}</b></font>&nbsp;&nbsp;<font face='Courier'><b>{p}</b></font>"
                  f"&nbsp;&nbsp;<font color='#6B6560' size='8'>({auth_})</font>", h3),
        Table([[Paragraph("<b>Input</b>", cell), Paragraph(inp, cell)],
               [Paragraph("<b>Success</b>", cell), Paragraph(out, cell)],
               [Paragraph("<b>Errors</b>", cell), Paragraph(err, cell)]],
              colWidths=[20 * mm, W - 20 * mm], hAlign="LEFT",
              style=TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (0, -1), SOFT),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 3)])),
    ]))
P(f"<i>Verified at build time: {len(ENDPOINTS)} endpoints in the OpenAPI definition, all documented above.</i>", small)

H2("19.1 Status codes")
table([["Code", "Meaning in this app"],
       ["200 / 201 / 204", "OK / created (register, triage) / done with no body (logout, delete)"],
       ["401", "\"Please sign in.\" or \"Your session has expired. Please sign in again.\" — the website then shows the login page"],
       ["404", "\"Analysis not found.\", \"Image file missing.\", \"Heatmap not generated yet.\""],
       ["409", "\"An account with this email already exists.\""],
       ["413", "\"File exceeds the 10 MB limit.\""],
       ["415", "Unsupported file type / content type / bytes are not JPEG or PNG"],
       ["422", "Validation: empty, corrupted, too small/large image; bad email; weak password; bad query parameters"],
       ["503", "\"Trained model not available … Model integration pending.\" — weights missing or SHA-256 mismatch"]],
      [26 * mm, W - 26 * mm])

H2("19.2 Calling the API from the command line")
CODE("""# 1. log in and keep the cookie
curl -c cookies.txt -H "Content-Type: application/json" \\
     -d '{"email":"you@example.org","password":"********"}' \\
     http://127.0.0.1:8000/auth/login
# 2. analyse an X-ray
curl -b cookies.txt -F "file=@chest.png" http://127.0.0.1:8000/triage
# 3. heatmap, history, delete
curl -b cookies.txt -X POST http://127.0.0.1:8000/analysis/<id>/gradcam
curl -b cookies.txt "http://127.0.0.1:8000/analysis/history?limit=10"
curl -b cookies.txt -X DELETE http://127.0.0.1:8000/analysis/<id>""")

# ---- 20 schemas
H1("20. Response and request schemas")
for name, note in [("AnalysisOut", "One analysis (returned by /triage, /analysis/{id}, history items, dashboard recent)"),
                   ("HistoryOut", "Paged list of analyses"), ("UserOut", "The signed-in user"),
                   ("LoginIn", "Body of POST /auth/login"), ("RegisterIn", "Body of POST /auth/register")]:
    H3(f"{name} — {note}")
    table([["Field", "Type", "Required", "Default"]] + fields(name), [48 * mm, 40 * mm, 22 * mm, W - 110 * mm])
P("AnalysisOut meanings: <b>prediction</b> NORMAL/PNEUMONIA (p ≥ 0.5); <b>pneumonia_probability</b> calibrated mean of 30 "
  "passes; <b>normal_probability</b> = 1 − that; <b>uncertainty</b> predictive entropy in bits (0–1); <b>decision</b> "
  "AUTO/REFER; <b>decision_reason</b> plain-text reason; <b>referral_threshold</b> entropy above which REFER; "
  "<b>processing_ms</b> server time; <b>image_url</b>/<b>gradcam_url</b> relative paths to the image endpoints.", small)

# ---- 21 configuration
H1("21. Configuration (environment variables)")
P("Read by <font face='Courier'>backend/app/config.py</font> (pydantic-settings) from the environment or the <b>.env</b> "
  "file. Variable name = field name in capitals (e.g. MAX_UPLOAD_MB).")
desc = {"app_name": "Name shown in API docs", "database_url": "SQLAlchemy URL; empty = sqlite:///var/pneumoscope.db",
        "cors_origins": "Comma-separated origins allowed to call the API with cookies",
        "var_dir": "Runtime data folder (DB, uploads, Grad-CAM, secret key)", "artifacts_dir": "Model bundles and dataset cards",
        "data_dir": "Raw dataset and cached features (training only)", "model_version": "Which artifacts/models/<version> to load",
        "max_upload_mb": "Upload size limit", "min_image_side": "Smallest allowed width/height (px)",
        "max_image_side": "Largest allowed width/height (px)", "torch_threads": "CPU threads for PyTorch",
        "mlflow_tracking_uri": "MLflow store; empty = sqlite mlflow/mlflow.db", "secret_key": "Signs session tokens; empty = generated once into var/.secret_key",
        "session_hours": "Login lifetime", "cookie_secure": "Send cookie only over HTTPS",
        "admin_email": "Creates this account at start-up if missing", "admin_password": "Password for that account",
        "admin_name": "Display name for that account"}
rows = [["Variable", "Default", "Purpose"]]
for k, f in Settings.model_fields.items():
    d = f.default
    if isinstance(d, Path):
        d = str(d.relative_to(ROOT)).replace("\\", "/") if ROOT in d.parents or d == ROOT else str(d)
    rows.append([f"<font face='Courier'>{k.upper()}</font>", "—" if d is None else str(d), desc.get(k, "")])
table(rows, [44 * mm, 52 * mm, W - 96 * mm])
P("Docker sets ARTIFACTS_DIR=/srv/artifacts, VAR_DIR=/srv/backend/var and CORS_ORIGINS=http://127.0.0.1:8080,"
  "http://localhost:8080, and refuses to start without SECRET_KEY. Frontend build variable: VITE_API_BASE (default /api).", small)

# ---- 22 backend modules
H1("22. Backend code reference")
table([["File", "Key contents"],
       ["app/main.py", "FastAPI app; lifespan: init_db() → ensure_admin() → preload model; GZipMiddleware, CORSMiddleware(allow_credentials), security-header middleware, validation-error handler; mounts routers"],
       ["app/config.py", "Settings class, get_settings() (cached), get_secret_key(), folder properties uploads_dir, gradcam_dir, models_dir, model_dir, datasets_dir"],
       ["app/database.py", "SQLAlchemy engine (SQLite, check_same_thread=False), SessionLocal, Base, get_db() dependency, init_db()"],
       ["app/models.py", "ORM tables User and Analysis (see section 9)"],
       ["app/schemas.py", "Pydantic models AnalysisOut (+ from_record()), HistoryOut, UserOut, LoginIn, RegisterIn"],
       ["app/auth.py", "Router /auth; hash_password / verify_password (bcrypt), _token() JWT, _set_cookie(), current_user dependency, ensure_admin()"],
       ["app/routes/analysis.py", "triage, history, get_analysis, delete_analysis, gradcam, analysis_image, gradcam_image"],
       ["app/routes/model.py", "model_info, metrics (+ _uncertainty_summary), dashboard"],
       ["app/ml/resnet_model.py", "MCDropoutHead (Linear 2048→512, ReLU, Dropout 0.235, Linear 512→1); PneumoniaResNet50 (frozen torchvision resnet50 backbone + head); gradcam_layer() = layer4"],
       ["app/ml/mc_dropout.py", "set_mc_dropout() switches only Dropout layers to train mode; mc_head_logits() repeats features 30× in one batch with a fixed seed; deterministic_head_logits()"],
       ["app/ml/preprocessing.py", "decode_image (16-bit → 8-bit), to_model_tensor (grey → 3 channels, 224 × 224, ImageNet normalise), display_image, colourfulness, image_descriptors, quality_flags"],
       ["app/ml/prediction.py", "DecisionPolicy (refer_threshold, decision_threshold 0.5, refer_on_input_flags) and decide()"],
       ["app/ml/artifacts.py", "file_sha256, read_config, ModelBundle, load_bundle() (verifies weights hash)"],
       ["app/ml/evaluation.py", "threshold_metrics, bootstrap_ci, discrimination, selective_curves, refer_band_composition, histogram"],
       ["app/services/inference_service.py", "ModelService singleton: bundle(), status(), predict(img) → result, gradcam(img, class); ModelUnavailableError"],
       ["app/services/uncertainty_service.py", "binary_entropy, summarize_passes (mean, variance, predictive entropy, expected entropy, mutual information)"],
       ["app/services/calibration_service.py", "mc_probs, nll, fit_temperature, expected_calibration_error (15 bins), brier_score, reliability_diagram"],
       ["app/services/gradcam_service.py", "compute_gradcam (hooks on layer4), colourise (colour map), overlay, cam_statistics"],
       ["app/services/image_validation.py", "validate_upload() and ImageValidationError (with HTTP status)"],
       ["app/services/storage_service.py", "save_upload (metadata-free PNG), load_upload, save_gradcam, gradcam_file, delete_analysis_files, _safe() path check"]],
      [50 * mm, W - 50 * mm])

# ---- 23 frontend
H1("23. Frontend code reference")
table([["File", "Key contents"],
       ["src/main.tsx, App.tsx", "React root; BrowserRouter; routes: / and /login public; /dashboard, /analyse, /history, /history/:id, /performance, /about inside RequireLogin + AppLayout"],
       ["src/services/api.ts", "axios instance (baseURL VITE_API_BASE or /api, withCredentials, 120 s); authApi.me/login/register/logout; api.dashboard, modelInfo, metrics, history (limit 200), analysis, remove, gradcam, triage (with upload progress); 401 interceptor; withSignal(); errorMessage(); assetUrl()"],
       ["src/context/AuthContext.tsx", "AuthProvider: user, loading, login(), register(), logout(); calls /auth/me on start; resets the user on any 401"],
       ["src/hooks/useApi.ts", "useApi(fn): data / error / loading / reload; AbortController cancels on page change; 20-second timeout with Retry"],
       ["src/layouts/AppLayout.tsx", "Dark theme wrapper, round icon sidebar (5 pages), greeting 'Hey, name' + page subtitle, + new-analysis button, account menu with Sign out"],
       ["src/pages/*.tsx", "HomePage, LoginPage, DashboardPage, AnalysePage, HistoryPage, ResultPage, PerformancePage, AboutPage"],
       ["src/components/", "ResultView (result + UncertaintyCard + heatmap), ui/index.tsx (Card, Stat, PredictionBadge, DecisionBadge, Bar, Loading, Empty, ErrorBox, Modal, cx), charts/theme.tsx (Recharts colours), Logo"],
       ["src/index.css, tailwind.config.js", "Colour tokens as CSS variables (--c-brand-*, --c-ink, --c-muted, …) for :root (light) and .theme-dark (dark, orange #F06C38); glass card styles"],
       ["vite.config.ts", "Dev server port 5173; proxy /api → http://127.0.0.1:8000 (prefix removed)"],
       ["public/images/", "hero-xray, login-bg, app-bg, gradcam, thumb-1..3 (.webp) — made from dataset images by make_site_images.py"]],
      [44 * mm, W - 44 * mm])
P("Versions: React 18.3, TypeScript 5.6, Vite 5.4, Tailwind CSS 3.4, React Router 6.28, Axios 1.7, Recharts 2.13, lucide-react icons.", small)

# ---- 24 formulas
H1("24. Algorithms and formulas")
table([["Step", "Formula / rule"],
       ["Preprocessing", "grey image → resize 224 × 224 → copy to 3 channels → x = (pixel/255 − mean) / std with ImageNet mean (0.485, 0.456, 0.406), std (0.229, 0.224, 0.225)"],
       ["Features", "f = ResNet-50 backbone(x), 2,048 numbers (computed once per image)"],
       ["MC Dropout", f"for t = 1…T (T = {cfg['mc_passes']}): z<sub>t</sub> = head(f) with dropout active; all T passes run as one batch, seed {cfg['mc_seed']} (same image → same answer)"],
       ["Calibration", f"p<sub>t</sub> = sigmoid(z<sub>t</sub> / T<sub>temp</sub>), T<sub>temp</sub> = {cfg['temperature']:.3f}; T<sub>temp</sub> minimises NLL = −mean[y·ln p + (1−y)·ln(1−p)] on the validation set (bounded search 0.05–10)"],
       ["Probability", "p = (1/T) Σ p<sub>t</sub>;  prediction = PNEUMONIA if p ≥ 0.5 else NORMAL"],
       ["Uncertainty (shown)", "Predictive entropy H(p) = −[p·log<sub>2</sub>p + (1−p)·log<sub>2</sub>(1−p)], 0 (certain) to 1 bit (50/50)"],
       ["Mutual information", "MI = H(p) − (1/T) Σ H(p<sub>t</sub>) — the part due to model (epistemic) uncertainty; computed and stored in the evaluation"],
       ["Decision", f"REFER if any input-quality flag, or H(p) &gt; {cfg['refer_threshold']:.4f}; otherwise AUTO"],
       ["Threshold choice", f"Largest coverage on validation with automatic-decision error ≤ 1 % and refer rate ≤ 30 % ({cfg['refer_threshold_method']})"],
       ["Quality guard", "colourfulness &gt; 0.12 (colour photo), contrast (std/255) &lt; 0.03 (blank), aspect ratio &gt; 2.5 or &lt; 0.4 → REFER"],
       ["ECE", "15 equal-width bins: Σ (n<sub>b</sub>/N)·|mean p<sub>b</sub> − mean y<sub>b</sub>|"],
       ["Brier score", "mean (p − y)<super>2</super>"],
       ["Bootstrap CI", "1,000 resamples of the test set with replacement; 2.5th and 97.5th percentiles"],
       ["Grad-CAM", "A = layer4 activations (2048 × 7 × 7), g = ∂score/∂A; weights α<sub>k</sub> = mean of g<sub>k</sub>; CAM = ReLU(Σ α<sub>k</sub>A<sub>k</sub>), up-sampled to 224 × 224, scaled 0–1, coloured and blended 50 % over the X-ray"]],
      [32 * mm, W - 32 * mm])
hp = cfg["hyperparameters"]
P(f"Training: head trained with AdamW, binary cross-entropy, lr {hp['lr']:.2e}, weight decay {hp['weight_decay']:.2e}, "
  f"hidden {hp['hidden']}, dropout {hp['dropout']:.3f} (best of 25 Optuna trials), early stopping on validation; backbone frozen.", small)

# ---- 25 file formats
H1("25. Model files and formats")
P(f"Folder <b>artifacts/models/{cfg['version']}/</b>:")
table([["File", "Contents"],
       ["model.pt", f"PyTorch state_dict of the head ({cfg['weights_file']}); SHA-256 {cfg['weights_sha256'][:16]}… stored in config.json and checked at load"],
       ["config.json", ", ".join(cfg.keys())],
       ["evaluation.json", ", ".join(ev.keys()) + ". test → " + ", ".join(test.keys())],
       ["reference_stats.json", "Reference input/output statistics of the training data (intensity histogram, positive rate, refer rate) for drift checks"]],
      [36 * mm, W - 36 * mm])
H3("Other formats")
bullets([
    "Dataset card <b>artifacts/datasets/kermany/dataset_card.json</b>: counts per split/class, patients, split method, seed.",
    "Feature cache <b>data/</b>: backbone features (.npy) per image so training trials don't recompute ResNet-50.",
    "MLflow: runs in <b>mlflow/mlflow.db</b> (SQLite), artefacts in <b>backend/mlruns/</b>.",
    "Grad-CAM folder <b>var/gradcam/&lt;id&gt;/</b>: heatmap.png (RGBA), overlay.png, original.png, cam.npy (float16 heatmap array).",
])

# ---- 26 scripts
H1("26. Training and utility scripts")
table([["Script", "Arguments", "What it does"],
       ["scripts.prepare_kermany", "--zip (default data/raw/ChestXRay2017.zip), --out (data/kermany)",
        "Unzips, infers patient IDs from file names, makes a patient-disjoint StratifiedGroupKFold split 4,182 / 837 / 837, writes the dataset card"],
       ["scripts.train_pipeline", "--trials 25, --version, --bootstrap 1000, --no-mlflow, --target-error 0.03, --max-refer-rate 0.30",
        "Caches features, Optuna search, trains the head, fits the temperature and refer threshold, evaluates once on test, leakage experiment, writes the model bundle, logs to MLflow"],
       ["scripts.evaluate_external", "--images, --labels (required), --model, --limit 2000",
        "Evaluates a bundle on an external labelled set (e.g. RSNA) and adds the result to evaluation.json"],
       ["scripts.make_site_images", "—", "Creates the website images in frontend/public/images from dataset X-rays and a real Grad-CAM"],
       ["docs/build_project_guide.py", "—", "Builds this PDF from the real project files"]],
      [38 * mm, 52 * mm, W - 90 * mm])
P("v1.1.0 was trained with --target-error 0.01.", small)

# ---- 27 docker
H1("27. Docker, nginx and public link")
table([["Item", "Details"],
       ["backend image", "python:3.12-slim; installs CPU PyTorch then requirements.txt; runs as non-root user 'app' (uid 1000); "
                         "uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers; HEALTHCHECK curl /health every 30 s"],
       ["frontend image", "Stage 1 node:22-alpine: npm ci + npm run build; stage 2 nginx:1.27-alpine serves dist/ with nginx.conf"],
       ["Ports", "Only 8080 on the host → nginx port 80; backend port 8000 is internal to the Docker network"],
       ["Volumes", "./artifacts → /srv/artifacts (read-only); named volume backend_data → /srv/backend/var (database, uploads, heatmaps, secret key)"],
       ["nginx /api/", "proxy_pass http://backend:8000/ (prefix removed), forwards Host / X-Forwarded-For / -Proto, read timeout 180 s, max body 12 MB"],
       ["nginx caching", "/assets/ 30 days, public, immutable (file names contain a hash); index.html and routes no-cache so new versions show at once; SPA fallback try_files → index.html"],
       ["nginx headers", "X-Content-Type-Options nosniff, X-Frame-Options SAMEORIGIN, Referrer-Policy same-origin"],
       ["Public link", "start-public.bat: docker compose up -d, then tools/cloudflared.exe tunnel --url http://127.0.0.1:8080 → https://&lt;random&gt;.trycloudflare.com (saved in tools/current_url.txt)"]],
      [30 * mm, W - 30 * mm])

# ---- 28 security internals
H1("28. Security internals")
table([["Mechanism", "Exact behaviour"],
       ["Password hash", "bcrypt.hashpw(password[:72 bytes], gensalt(rounds=12)); checked with bcrypt.checkpw"],
       ["Token", "JWT, algorithm HS256, claims {sub: user id, exp: now + 12 h}, signed with SECRET_KEY"],
       ["Cookie", "name pneumoscope_session; HttpOnly; SameSite=Lax; Path=/; Secure when COOKIE_SECURE=true; Max-Age 43,200 s with Remember me, none otherwise"],
       ["Request check", "current_user reads the cookie → jwt.decode (signature + expiry) → loads the user; any failure → 401"],
       ["Upload validation order", "empty? → size ≤ 10 MB → extension .jpg/.jpeg/.png → content type → magic bytes (FF D8 FF / 89 50 4E 47) → Pillow decode → format JPEG/PNG → full load → side limits 128–8,192 px"],
       ["Decompression bomb", "Pillow MAX_IMAGE_PIXELS = 80,000,000"],
       ["Stored file", "Re-encoded as 8-bit greyscale PNG named &lt;uuid&gt;.png — no EXIF, no original name"],
       ["Path traversal", "_safe() resolves every path and refuses anything outside the storage root"],
       ["CORS", "Only the configured origins, with credentials; in Docker the API is same-origin through nginx"],
       ["Model integrity", "SHA-256 of the weights must equal config.json → otherwise 503 'integration pending'"]],
      [36 * mm, W - 36 * mm])

# ---- 29 quick reference
H1("29. Quick reference")
table([["What", "Value"],
       ["Website (development)", "http://localhost:5173"],
       ["API (development)", "http://127.0.0.1:8000 · docs /docs · health /health"],
       ["Docker app", "http://127.0.0.1:8080 (API at /api)"],
       ["Public link", "https://&lt;random&gt;.trycloudflare.com — see tools/current_url.txt"],
       ["Database", "backend/var/pneumoscope.db (Docker: volume backend_data)"],
       ["Model", f"artifacts/models/{cfg['version']}/"],
       ["Run tests", "cd backend → ..\\.venv\\Scripts\\python -m pytest (39 tests)"],
       ["Rebuild this PDF", ".venv\\Scripts\\python docs\\build_project_guide.py"]],
      [44 * mm, W - 44 * mm])


# ------------------------------------------------------------------ build
doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=17 * mm,
                        title="PneumoScope — Complete Project Guide", author="PneumoScope project",
                        subject="Medical X-Ray Pneumonia Classification with Uncertainty Quantification")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"Written {OUT} ({OUT.stat().st_size // 1024} KB)")
