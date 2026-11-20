"""Block diagrams for the report (life cycle, lineage, pipeline, split, deployment, CI/CD, stakeholders, Gantt)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent / "figs"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11})
OR, AMB, GRN, BLU, GRY, INK, PALE = "#E0612B", "#F2A541", "#2E9E6B", "#3B6EA8", "#8A8A8A", "#222222", "#FFF3EC"
FILL = {"o": ("#FDE6DA", OR), "b": ("#E1ECF7", BLU), "g": ("#DFF2E8", GRN), "y": ("#FDF0D9", AMB), "k": ("#EFEFEF", GRY)}


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, c="o", fs=10.5, bold=False, ls="-"):
    f, e = FILL[c]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=f, ec=e, lw=1.4, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)
    return (x, y, w, h)


def arrow(ax, p, q, c=INK, ls="-", rad=0.0, text=None, fs=9, shrink=0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=13, color=c, lw=1.3, ls=ls, shrinkA=shrink, shrinkB=shrink,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.12, text, ha="center", fontsize=fs, color=c, style="italic")


def R(b): return (b[0] + b[2], b[1] + b[3] / 2)
def L(b): return (b[0], b[1] + b[3] / 2)
def T(b): return (b[0] + b[2] / 2, b[1] + b[3])
def B(b): return (b[0] + b[2] / 2, b[1])


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", facecolor="white"); plt.close(fig)


# 1 Project-specific life cycle
fig, ax = canvas(11, 4.6)
st = [("1. Initiation\nproblem, objectives,\nsuccess criteria", "o"), ("2. Data\nKermany CXR,\npatient IDs,\nquality + EDA", "b"),
      ("3. Preparation\npatient-disjoint split,\nResNet-50 features", "b"), ("4. Modelling\nbaselines, MC-Dropout\nhead, Optuna", "y"),
      ("5. Evaluation\ntest metrics, calibration,\nuncertainty, leakage", "g"), ("6. Deployment\nFastAPI + React,\nDocker, tunnel", "o")]
bx = []
for i, (t, c) in enumerate(st):
    bx.append(box(ax, 0.1 + i * 1.83, 2.5, 1.72, 1.4, t, c, fs=8.6))
for a, b in zip(bx, bx[1:]): arrow(ax, R(a), L(b))
m = box(ax, 7.4, 0.4, 3.2, 1.1, "7. Monitoring (designed)\ninput drift (PSI), referral rate,\nretraining trigger", "k", fs=9.5, ls="--")
arrow(ax, B(bx[5]), (9.0, 1.5))
arrow(ax, L(m), (B(bx[1])[0], 2.5), c=GRY, ls="--", rad=-0.15, text="retrain on new data")
arrow(ax, B(bx[4]), (B(bx[3])[0] + 0.2, 2.5), c=OR, rad=-0.9)
ax.text(6.7, 1.3, "iterate (v1.0 → v1.1)", color=OR, fontsize=9, style="italic", ha="center")
save(fig, "lifecycle.png")

# 2 Data lineage
fig, ax = canvas(11, 5.2)
r1 = [("ChestXRay2017.zip\n(Mendeley, 1.2 GB)\n5,856 JPEGs", "k"), ("Extracted folders\nchest_xray/{train,test}/\n{NORMAL,PNEUMONIA}", "b"),
      ("manifest.csv\n+ label, sub-type, patient ID,\nMD5, size, brightness…", "b"), ("Patient-disjoint split\nStratifiedGroupKFold\n4,182 / 837 / 837", "o")]
b1 = [box(ax, 0.2 + i * 2.7, 3.4, 2.4, 1.4, t, c, fs=9.5) for i, (t, c) in enumerate(r1)]
for a, b in zip(b1, b1[1:]): arrow(ax, R(a), L(b))
r2 = [("Image → grayscale →\n224×224 resize →\nImageNet normalise", "y"), ("Frozen ResNet-50\n(ImageNet V2)\n→ 2048-d features", "y"),
      ("kermany_resnet50.npz\nfeature cache\n(5,856 × 2048)", "b"), ("Model bundle v1.1.0\nmodel.pt (SHA-256), config,\nevaluation, reference stats", "g")]
b2 = [box(ax, 8.3 - i * 2.7, 1.0, 2.4, 1.4, t, c, fs=9.5) for i, (t, c) in enumerate(r2)]
arrow(ax, B(b1[3]), T(b2[0]))
for a, b in zip(b2, b2[1:]): arrow(ax, L(a), R(b))
ax.text(5.5, 0.3, "dataset_card.json records counts, duplicates and split overlap at every step;  MLflow run 45a89990… links the bundle to its data and parameters",
        ha="center", fontsize=9, style="italic", color=GRY)
save(fig, "lineage.png")

# 3 Preprocessing pipeline
fig, ax = canvas(11, 2.6)
steps = [("Upload\nJPEG / PNG\n≤ 10 MB", "k"), ("Validate\nmagic bytes,\ndecode, EXIF", "b"), ("Quality flags\ncolour, contrast,\naspect, size", "b"),
         ("Grayscale →\n3 channels", "y"), ("Resize\n224 × 224\n(bilinear)", "y"), ("Normalise\n(x − μ) / σ\nImageNet", "y"), ("ResNet-50\n2048-d\nfeatures", "o")]
bs = [box(ax, 0.1 + i * 1.57, 0.6, 1.35, 1.35, t, c, fs=9.2) for i, (t, c) in enumerate(steps)]
for a, b in zip(bs, bs[1:]): arrow(ax, R(a), L(b))
ax.text(5.5, 0.15, "one function (app/ml/preprocessing.py :: to_model_tensor) is used by training, the API and drift monitoring",
        ha="center", fontsize=9, style="italic", color=GRY)
save(fig, "pipeline.png")

# 4 Data split
fig, ax = canvas(11, 3.8)
a = box(ax, 0.2, 1.3, 2.3, 1.3, "5,856 images\n3,189 patients", "k", fs=11, bold=True)
g = box(ax, 3.2, 1.3, 2.4, 1.3, "Group by patient ID\nStratify by label\n(seed 42)", "b", fs=10)
arrow(ax, R(a), L(g))
sp = [("Train  4,182 img / 2,278 pts\nfit the head (71%)", "o", 2.6), ("Validation  837 img / 457 pts\nOptuna, early stop, temperature,\nrefer threshold (14.3%)", "y", 1.35),
      ("Test  837 img / 454 pts\nused once, final report (14.3%)", "g", 0.1)]
for t, c, y in sp:
    b = box(ax, 6.5, y, 4.3, 1.05, t, c, fs=10)
    arrow(ax, R(g), L(b))
ax.text(8.65, -0.15, "0 patients shared between any two splits", ha="center", fontsize=9.5, style="italic", color=GRN)
save(fig, "split.png")

# 5 Deployment architecture
fig, ax = canvas(11, 5.4)
u = box(ax, 0.2, 2.2, 1.7, 1.2, "Browser\n(student /\nreviewer)", "k", fs=10)
cf = box(ax, 2.4, 3.9, 2.2, 1.0, "Cloudflare quick tunnel\n(temporary HTTPS URL)", "k", fs=9.5, ls="--")
ax.add_patch(FancyBboxPatch((2.4, 0.3), 8.4, 3.3, boxstyle="round,pad=0.02,rounding_size=0.15", fc="none", ec=BLU, lw=1.2, ls="--"))
ax.text(2.6, 3.35, "Docker Compose on the host PC", color=BLU, fontsize=10, fontweight="bold")
fe = box(ax, 2.8, 1.4, 2.5, 1.5, "frontend container\nnginx :80 → host :8080\nReact + TypeScript build\n/api/* → backend", "b", fs=9.3)
be = box(ax, 6.0, 1.4, 2.4, 1.5, "backend container\nFastAPI + Uvicorn :8000\nauth, triage, Grad-CAM,\nmetrics, history", "o", fs=9.3)
md = box(ax, 8.9, 2.2, 1.8, 1.1, "artifacts/ (ro)\nmodel v1.1.0\nconfig + eval", "g", fs=9)
db = box(ax, 8.9, 0.5, 1.8, 1.1, "volume\nSQLite + uploads", "y", fs=9)
arrow(ax, R(u), L(fe), text="HTTP"); arrow(ax, T(u), L(cf), ls="--"); arrow(ax, B(cf), T(fe), ls="--")
arrow(ax, R(fe), L(be), text="REST/JSON"); arrow(ax, R(be), L(md)); arrow(ax, (8.4, 1.8), L(db))
save(fig, "deployment.png")

# 6 CI/CD (proposed)
fig, ax = canvas(11, 2.8)
cs = [("git push /\npull request", "k"), ("GitHub Actions\ncheckout, Python 3.12,\npip install (CPU torch)", "b"), ("pytest\n39 tests\n(API, auth, ML, upload)", "y"),
      ("npm ci + build\n(frontend type\ncheck)", "y"), ("docker compose\nbuild", "o"), ("manual approval →\ndeploy / tag release", "g")]
cb = [box(ax, 0.1 + i * 1.83, 0.7, 1.6, 1.5, t, c, fs=9.2, ls="--") for i, (t, c) in enumerate(cs)]
for a, b in zip(cb, cb[1:]): arrow(ax, R(a), L(b))
ax.text(5.5, 0.2, "PROPOSED design – the test and Docker stages run today locally; the GitHub Actions workflow is not yet executed",
        ha="center", fontsize=9, style="italic", color=OR)
save(fig, "cicd.png")

# 7 Stakeholder map
fig, ax = canvas(10, 6)
c = box(ax, 3.9, 2.55, 2.2, 0.9, "PneumoScope", "o", fs=13, bold=True)
ring = [("Project team\n(4 students)", "b", 0.2, 4.7), ("Faculty mentor\n(project owner)", "b", 3.8, 5.0), ("Radiologists /\nclinicians (users)", "b", 7.5, 4.7),
        ("Patients & parents\n(data subjects)", "y", 7.7, 2.5), ("Data owners\nGuangzhou WCMC,\nKermany et al.", "y", 7.4, 0.2),
        ("Regulators\nCDSCO, DPDP Act,\nEU MDR / GDPR", "k", 3.8, 0.0), ("Hospitals / IT\n(deployers)", "g", 0.2, 0.2), ("Adversarial\nmisuse, bad uploads,\nover-reliance", "k", 0.0, 2.5)]
for t, cc, x, y in ring:
    b = box(ax, x, y, 2.3, 0.95, t, cc, fs=9.5)
    ax.plot([x + 1.15, 5.0], [y + 0.47, 3.0], color=GRY, lw=0.8, zorder=0)
save(fig, "stakeholder_map.png")

# 8 Influence-interest matrix
fig, ax = plt.subplots(figsize=(7.2, 5.4))
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axhline(5, color=GRY); ax.axvline(5, color=GRY)
for (x, y, t) in ((2.5, 9.4, "Keep satisfied"), (7.5, 9.4, "Manage closely"), (2.5, 0.5, "Monitor"), (7.5, 0.5, "Keep informed")):
    ax.text(x, y, t, ha="center", fontsize=11, fontweight="bold", color=GRY)
pts = [(8.8, 8.6, "Faculty mentor"), (9.3, 7.3, "Project team"), (8.0, 6.3, "Radiologists"), (3.0, 8.2, "Regulators"),
       (3.8, 6.7, "Hospital IT"), (8.4, 3.4, "Patients / parents"), (2.4, 3.6, "Data owners"), (4.2, 2.0, "Adversarial users")]
for x, y, t in pts:
    ax.scatter(x, y, s=90, color=OR, zorder=3); ax.annotate(t, (x, y), xytext=(-8 if x > 7.5 else 8, 6), ha="right" if x > 7.5 else "left", textcoords="offset points", fontsize=10)
ax.set_xlabel("Interest in the project →"); ax.set_ylabel("Influence over the project →")
ax.set_xticks([]); ax.set_yticks([])
save(fig, "influence_interest.png")

# 9 Gantt
tasks = [("Problem definition & feasibility", 1, 2, 1, 2), ("Literature & framework selection", 2, 3, 2, 3), ("Dataset acquisition & EDA", 3, 5, 3, 5),
         ("Patient-disjoint split & leakage study", 4, 5, 4, 6), ("Feature extraction (ResNet-50)", 5, 6, 5, 6), ("Baselines & candidate models", 6, 7, 6, 8),
         ("Optuna tuning + MLflow tracking", 7, 8, 7, 9), ("Calibration, uncertainty, evaluation", 8, 9, 8, 10), ("FastAPI backend + tests", 8, 10, 8, 10),
         ("React frontend + Grad-CAM", 9, 11, 9, 12), ("Docker deployment & public link", 11, 12, 11, 13), ("Report, presentation, viva prep", 12, 14, 12, 14)]
fig, ax = plt.subplots(figsize=(10, 5))
for i, (t, ps, pe, as_, ae) in enumerate(tasks):
    y = len(tasks) - i
    ax.barh(y + 0.18, pe - ps + 1, left=ps - 0.5, height=0.32, color="#C9C9C9", label="Planned" if i == 0 else None)
    ax.barh(y - 0.18, ae - as_ + 1, left=as_ - 0.5, height=0.32, color=OR, label="Actual" if i == 0 else None)
ax.set_yticks(range(len(tasks), 0, -1), [t[0] for t in tasks]); ax.set_xticks(range(1, 15), [f"W{w}" for w in range(1, 15)])
ax.set_xlim(0.4, 14.6); ax.grid(axis="x", color="#E5E5E5"); ax.set_axisbelow(True); ax.legend(loc="lower left")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); save(fig, "gantt.png")

# 10 CRISP-DM wheel-like
fig, ax = canvas(8, 6)
import numpy as np
ph = [("Business\nunderstanding", "o"), ("Data\nunderstanding", "b"), ("Data\npreparation", "b"), ("Modelling", "y"), ("Evaluation", "g"), ("Deployment", "o")]
cx, cy, r = 4, 3, 2.3
pos = []
for i, (t, c) in enumerate(ph):
    a = np.pi / 2 - i * 2 * np.pi / 6
    pos.append(box(ax, cx + r * np.cos(a) - 0.85, cy + r * np.sin(a) - 0.45, 1.7, 0.9, t, c, fs=10))
for i in range(6):
    a, b = pos[i], pos[(i + 1) % 6]
    arrow(ax, (a[0] + a[2] / 2, a[1] + a[3] / 2), (b[0] + b[2] / 2, b[1] + b[3] / 2), c=GRY, rad=-0.2, shrink=38)
ax.add_patch(plt.Circle((cx, cy), 0.75, fc="#EFEFEF", ec=GRY)); ax.text(cx, cy, "Kermany\nCXR data", ha="center", va="center", fontsize=10, fontweight="bold")
save(fig, "crispdm.png")
print("diagrams ok")
