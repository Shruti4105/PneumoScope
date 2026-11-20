"""Statistics and figures for the final report, computed from the real project files.

Run from the project root:   .venv/Scripts/python docs/report/analyze.py
Writes docs/report/figs/*.png and docs/report/stats.json
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
OUT = Path(__file__).resolve().parent / "figs"; OUT.mkdir(exist_ok=True)
S = {}

OR, AMB, GRN, RED, BLU, GRY, INK = "#E0612B", "#F2A541", "#2E9E6B", "#C8453A", "#3B6EA8", "#8A8A8A", "#222222"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#E3E3E3",
                     "grid.linewidth": 0.6, "legend.frameon": False, "axes.edgecolor": "#555555"})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=220, facecolor="white")
    plt.close(fig)


df = pd.read_csv(ROOT / "data/kermany/manifest.csv")
ev = json.loads((ROOT / "artifacts/models/v1.1.0/evaluation.json").read_text())
card = json.loads((ROOT / "artifacts/datasets/kermany/dataset_card.json").read_text())
df["aspect_ratio"] = df["width"] / df["height"]
df["file_kb"] = df["file_bytes"] / 1024

# ---------------------------------------------------------------- 6.2 missing values
S["missing"] = {c: int(df[c].isna().sum()) for c in df.columns}
S["n_rows"], S["n_cols"] = len(df), len(df.columns)
S["modes"] = df["mode"].value_counts().to_dict()

# ---------------------------------------------------------------- 6.3 descriptive stats + 6.4 outliers
NUM = {"width": "Width (px)", "height": "Height (px)", "aspect_ratio": "Aspect ratio (W/H)",
       "file_kb": "File size (KB)", "brightness": "Brightness (mean intensity)",
       "contrast": "Contrast (intensity SD)", "intensity_entropy": "Intensity entropy (bits)"}
desc = {}
for c in NUM:
    v = df[c].values.astype(float)
    q1, med, q3 = np.percentile(v, [25, 50, 75]); iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    z = (v - v.mean()) / v.std(ddof=1)
    desc[c] = {"mean": v.mean(), "median": med, "var": v.var(ddof=1), "std": v.std(ddof=1), "min": v.min(),
               "max": v.max(), "q1": q1, "q3": q3, "iqr": iqr, "lower_fence": lo, "upper_fence": hi,
               "iqr_outliers": int(((v < lo) | (v > hi)).sum()), "z_outliers": int((np.abs(z) > 3).sum())}
S["descriptive"] = desc
S["by_class"] = {c: {lab: {"mean": float(g[c].mean()), "median": float(g[c].median())}
                     for lab, g in df.groupby("label")} for c in NUM}
# images flagged by the app's own quality rules (on file metadata)
S["low_res"] = int((df[["width", "height"]].min(axis=1) < 256).sum())
S["min_side_lt_400"] = int((df[["width", "height"]].min(axis=1) < 400).sum())

# ---------------------------------------------------------------- 6.5 distributions
fig, axes = plt.subplots(2, 3, figsize=(10, 6))
for ax, c in zip(axes.ravel(), ["width", "height", "file_kb", "brightness", "contrast", "intensity_entropy"]):
    for lab, col in (("NORMAL", BLU), ("PNEUMONIA", OR)):
        ax.hist(df.loc[df.label == lab, c], bins=40, alpha=0.6, color=col, label=lab.title())
    ax.set_title(NUM[c], fontsize=11); ax.set_ylabel("Images")
axes[0, 0].legend(fontsize=9)
save(fig, "eda_histograms.png")

fig, axes = plt.subplots(1, 4, figsize=(10, 3.6))
for ax, c in zip(axes, ["width", "brightness", "contrast", "intensity_entropy"]):
    data = [df.loc[df.label == l, c] for l in ("NORMAL", "PNEUMONIA")]
    bp = ax.boxplot(data, tick_labels=["Normal", "Pneumonia"], patch_artist=True, widths=0.55,
                    flierprops=dict(marker=".", markersize=3, markerfacecolor=GRY, markeredgecolor=GRY))
    for p, col in zip(bp["boxes"], (BLU, OR)):
        p.set_facecolor(col); p.set_alpha(0.55)
    ax.set_title(NUM[c], fontsize=10.5)
save(fig, "eda_boxplots.png")

fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
cls = card["class_distribution"]; sub = card["subtype_distribution"]
axes[0].bar(["Normal", "Pneumonia"], [cls["NORMAL"], cls["PNEUMONIA"]], color=[BLU, OR])
for i, v in enumerate([cls["NORMAL"], cls["PNEUMONIA"]]):
    axes[0].text(i, v + 60, f"{v:,} ({v / sum(cls.values()):.1%})", ha="center")
axes[0].set_title("Class distribution (5,856 images)"); axes[0].set_ylim(0, 4900)
axes[1].bar(["Normal", "Bacterial", "Viral"], [sub["normal"], sub["bacterial"], sub["viral"]], color=[BLU, OR, AMB])
for i, v in enumerate([sub["normal"], sub["bacterial"], sub["viral"]]):
    axes[1].text(i, v + 40, f"{v:,}", ha="center")
axes[1].set_title("Sub-type distribution"); axes[1].set_ylim(0, 3200)
save(fig, "eda_classes.png")

# ---------------------------------------------------------------- 6.6 correlation
cc = ["label_int", "width", "height", "aspect_ratio", "file_kb", "brightness", "contrast", "intensity_entropy"]
corr = df[cc].corr(method="pearson")
S["corr_label"] = corr["label_int"].drop("label_int").to_dict()
S["corr_top"] = sorted(((a, b, corr.loc[a, b]) for i, a in enumerate(cc) for b in cc[i + 1:]),
                       key=lambda t: -abs(t[2]))[:5]
fig, ax = plt.subplots(figsize=(7, 5.8)); ax.grid(False)
names = ["Label (1 = pneumonia)", "Width", "Height", "Aspect ratio", "File size", "Brightness", "Contrast", "Entropy"]
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(cc)), names, rotation=40, ha="right"); ax.set_yticks(range(len(cc)), names)
for i in range(len(cc)):
    for j in range(len(cc)):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8.5,
                color="white" if abs(corr.values[i, j]) > 0.6 else INK)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Pearson r")
save(fig, "eda_correlation.png")

# ---------------------------------------------------------------- sample images
fig, axes = plt.subplots(1, 3, figsize=(9, 3.4))
for ax, st in zip(axes, ("normal", "bacterial", "viral")):
    r = df[(df.subtype == st) & (df.split == "train")].iloc[3]
    ax.imshow(Image.open(ROOT / "data/kermany" / r.path).convert("L"), cmap="gray"); ax.axis("off")
    ax.set_title(f"{st.title()}  ({r.width}×{r.height})", fontsize=11)
save(fig, "sample_xrays.png")

# ---------------------------------------------------------------- 8 preprocessing before/after
from app.ml.preprocessing import to_model_tensor  # noqa: E402
r = df[df.split == "train"].iloc[0]
img = Image.open(ROOT / "data/kermany" / r.path)
raw = np.asarray(img.convert("L"), dtype=np.float32)
t = to_model_tensor(img.convert("RGB")).numpy()
feats = np.load(ROOT / "data/features/kermany_resnet50.npz")["features"].astype(np.float32)
fv = feats[df.index[df.path == r.path][0]]
S["prep_example"] = {"path": r.path, "raw_shape": list(raw.shape), "raw_min": float(raw.min()), "raw_max": float(raw.max()),
                     "raw_mean": float(raw.mean()), "raw_std": float(raw.std()), "t_shape": list(t.shape),
                     "t_min": float(t.min()), "t_max": float(t.max()), "t_mean": float(t.mean()), "t_std": float(t.std()),
                     "pix_example_raw": float(raw[raw.shape[0] // 2, raw.shape[1] // 2]),
                     "f_dim": int(fv.shape[0]), "f_mean": float(fv.mean()), "f_std": float(fv.std()),
                     "f_zero_frac": float((fv == 0).mean()), "f_max": float(fv.max())}
fig, axes = plt.subplots(1, 4, figsize=(11, 3))
axes[0].imshow(raw, cmap="gray"); axes[0].set_title(f"Raw {raw.shape[1]}×{raw.shape[0]}, 0–255")
axes[1].imshow(t[0], cmap="gray"); axes[1].set_title("Resized 224×224, normalised")
for a in axes[:2]: a.axis("off")
axes[2].hist(raw.ravel(), bins=50, color=GRY, alpha=0.7, density=True, label="raw / 255")
axes[2].hist(t[0].ravel(), bins=50, color=OR, alpha=0.6, density=True, label="normalised (R ch.)")
axes[2].set_title("Pixel distribution"); axes[2].legend(fontsize=8)
raw01 = raw.ravel() / 255.0
axes[2].cla(); axes[2].hist(raw01, bins=50, color=GRY, alpha=0.7, density=True, label="before: x/255")
axes[2].hist(t[0].ravel(), bins=50, color=OR, alpha=0.6, density=True, label="after: (x-μ)/σ")
axes[2].set_title("Pixel values before / after"); axes[2].legend(fontsize=8)
axes[3].plot(fv, color=BLU, lw=0.5); axes[3].set_title("2048-d ResNet-50 feature vector"); axes[3].set_xlabel("feature index")
save(fig, "prep_before_after.png")

# PCA of learned features
from sklearn.decomposition import PCA  # noqa: E402
tr = (df.split == "train").values
pca = PCA(n_components=50, random_state=42).fit(feats[tr])
S["pca_var"] = {"pc1": float(pca.explained_variance_ratio_[0]), "pc2": float(pca.explained_variance_ratio_[1]),
                "pc10": float(pca.explained_variance_ratio_[:10].sum()), "pc50": float(pca.explained_variance_ratio_.sum())}
z = pca.transform(feats[tr])[:, :2]
fig, ax = plt.subplots(figsize=(6, 4.4))
for lab, col in ((0, BLU), (1, OR)):
    m = df.label_int.values[tr] == lab
    ax.scatter(z[m, 0], z[m, 1], s=4, alpha=0.45, color=col, label=["Normal", "Pneumonia"][lab])
ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)"); ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.1%})")
ax.legend(markerscale=4)
save(fig, "features_pca.png")

# ---------------------------------------------------------------- 7 fairness / subgroups (test split)
te = df[df.split == "test"].reset_index(drop=True)
pc = ev["test"]["per_case"]
assert list(te.label_int) == list(pc["label"]), "per_case order mismatch"
te["p"], te["entropy"] = pc["p"], pc["entropy"]
te["pred"] = (te.p >= 0.5).astype(int)
thr = ev["policy"]["refer_threshold"]
te["refer"] = te.entropy > thr
from fairlearn.metrics import (MetricFrame, demographic_parity_difference, equalized_odds_difference,  # noqa: E402
                               false_positive_rate, selection_rate, true_positive_rate)
from sklearn.metrics import accuracy_score  # noqa: E402
from app.services import calibration_service as cal  # noqa: E402

te["res_group"] = np.where(te[["width", "height"]].min(axis=1) < te[["width", "height"]].min(axis=1).median(), "lower-res", "higher-res")
te["format"] = np.where(te["mode"] == "L", "grayscale JPEG", "RGB JPEG")
fair = {}
for g in ("res_group", "format"):
    mf = MetricFrame(metrics={"n": lambda y, p: len(y), "accuracy": accuracy_score, "selection_rate": selection_rate,
                              "TPR": true_positive_rate, "FPR": false_positive_rate},
                     y_true=te.label_int, y_pred=te.pred, sensitive_features=te[g])
    tab = mf.by_group
    ece = te.groupby(g).apply(lambda d: cal.expected_calibration_error(d.p.values, d.label_int.values), include_groups=False)
    fair[g] = {"by_group": {k: {**{m: float(tab.loc[k, m]) for m in tab.columns}, "ece": float(ece[k])} for k in tab.index},
               "dp_diff": float(demographic_parity_difference(te.label_int, te.pred, sensitive_features=te[g])),
               "eo_diff": float(equalized_odds_difference(te.label_int, te.pred, sensitive_features=te[g]))}
# pneumonia sub-type (only positives -> recall per subtype)
sub = {}
for st, d in te.groupby("subtype"):
    sub[st] = {"n": len(d), "accuracy": float((d.pred == d.label_int).mean()), "recall_or_spec": float((d.pred == d.label_int).mean()),
               "refer_rate": float(d.refer.mean()), "mean_p": float(d.p.mean()), "mean_entropy": float(d.entropy.mean())}
fair["subtype"] = sub
S["fairness"] = fair
fig, ax = plt.subplots(figsize=(7.5, 3.6))
groups = [("Normal", sub["normal"]), ("Bacterial", sub["bacterial"]), ("Viral", sub["viral"])]
x = np.arange(len(groups))
ax.bar(x - 0.2, [g["accuracy"] * 100 for _, g in groups], 0.4, color=OR, label="Correct (%)")
ax.bar(x + 0.2, [g["refer_rate"] * 100 for _, g in groups], 0.4, color=GRY, label="Referred to doctor (%)")
for i, (_, g) in enumerate(groups):
    ax.text(i - 0.2, g["accuracy"] * 100 + 1.5, f"{g['accuracy']:.1%}", ha="center", fontsize=9)
    ax.text(i + 0.2, g["refer_rate"] * 100 + 1.5, f"{g['refer_rate']:.1%}", ha="center", fontsize=9)
ax.set_xticks(x, [f"{n}\n(n={g['n']})" for n, g in groups]); ax.set_ylim(0, 112); ax.legend(loc="upper center", ncol=2)
save(fig, "fairness_subtype.png")

# ---------------------------------------------------------------- 11.6 error analysis
err = te[te.pred != te.label_int]
S["errors"] = {"n": len(err), "fn": int(((err.label_int == 1)).sum()), "fp": int((err.label_int == 0).sum()),
               "fn_by_subtype": err[err.label_int == 1].subtype.value_counts().to_dict(),
               "referred": int(err.refer.sum()), "mean_entropy_err": float(err.entropy.mean()),
               "mean_entropy_ok": float(te[te.pred == te.label_int].entropy.mean()),
               "mean_p_fn": float(err[err.label_int == 1].p.mean()), "mean_p_fp": float(err[err.label_int == 0].p.mean()),
               "err_rate_lowres": float((te[te.res_group == "lower-res"].pred != te[te.res_group == "lower-res"].label_int).mean()),
               "err_rate_highres": float((te[te.res_group == "higher-res"].pred != te[te.res_group == "higher-res"].label_int).mean()),
               "confident_errors": int(((~err.refer)).sum())}
fig, ax = plt.subplots(figsize=(6.6, 3.6))
bins = np.linspace(0, 1, 21)
ax.hist(te[te.pred == te.label_int].entropy, bins=bins, color=GRN, alpha=0.6, label=f"Correct (n={len(te) - len(err)})", density=True)
ax.hist(err.entropy, bins=bins, color=RED, alpha=0.6, label=f"Wrong (n={len(err)})", density=True)
ax.axvline(thr, color=INK, ls="--", lw=1.2); ax.text(thr + 0.01, ax.get_ylim()[1] * 0.85, f"refer threshold {thr:.3f}", fontsize=9)
ax.set_xlabel("Predictive entropy (bits)"); ax.set_ylabel("Density"); ax.legend()
save(fig, "error_entropy.png")

ex = pd.concat([err[err.label_int == 1].sort_values("p").head(2), err[err.label_int == 0].sort_values("p", ascending=False).head(2)])
fig, axes = plt.subplots(1, 4, figsize=(11, 3.2))
for ax, (_, r) in zip(axes, ex.iterrows()):
    ax.imshow(Image.open(ROOT / "data/kermany" / r.path).convert("L"), cmap="gray"); ax.axis("off")
    kind = "False negative" if r.label_int == 1 else "False positive"
    ax.set_title(f"{kind} ({r.subtype})\np={r.p:.2f}, H={r.entropy:.2f} → {'REFER' if r.refer else 'AUTO'}", fontsize=9.5)
save(fig, "error_examples.png")
S["error_examples"] = [{"path": r.path, "label": r.label, "subtype": r.subtype, "p": r.p, "entropy": r.entropy, "refer": bool(r.refer)}
                       for _, r in ex.iterrows()]

# ---------------------------------------------------------------- 10 Optuna from MLflow
con = sqlite3.connect(ROOT / "mlflow/mlflow.db")
parent, prun = con.execute("select run_uuid, name from runs where name='pneumonia-resnet50-mcd-v1.1.0'").fetchone()
S["mlflow_parent"] = {"run_id": parent, "name": prun}
S["mlflow_experiments"] = [dict(zip(("id", "name"), r)) | {"runs": con.execute("select count(*) from runs where experiment_id=? and lifecycle_stage='active'", (r[0],)).fetchone()[0]}
                           for r in con.execute("select experiment_id, name from experiments where lifecycle_stage='active'")]
S["mlflow_runs"] = [dict(zip(("run_id", "name", "experiment", "start"), r)) for r in con.execute(
    "select r.run_uuid, r.name, e.name, r.start_time from runs r join experiments e on e.experiment_id=r.experiment_id "
    "where r.lifecycle_stage='active' and r.name not like 'optuna-trial%' order by r.start_time")]
kids = [r[0] for r in con.execute("select run_uuid from tags where key='mlflow.parentRunId' and value=?", (parent,))]
trials = []
for k in kids:
    name = con.execute("select name from runs where run_uuid=?", (k,)).fetchone()[0]
    p = dict(con.execute("select key, value from params where run_uuid=?", (k,)).fetchall())
    m = dict(con.execute("select key, value from metrics where run_uuid=?", (k,)).fetchall())
    trials.append({"n": int(name.split("-")[-1]), "lr": float(p["lr"]), "weight_decay": float(p["weight_decay"]),
                   "dropout": float(p["dropout"]), "hidden": int(p["hidden"]), "nll": m["val_mc_nll"], "epochs": m.get("epochs_run")})
trials.sort(key=lambda t: t["n"])
S["trials"] = trials
import optuna  # noqa: E402
optuna.logging.set_verbosity(optuna.logging.WARNING)
dist = {"lr": optuna.distributions.FloatDistribution(1e-4, 3e-3, log=True),
        "weight_decay": optuna.distributions.FloatDistribution(1e-6, 1e-2, log=True),
        "dropout": optuna.distributions.FloatDistribution(0.2, 0.6),
        "hidden": optuna.distributions.CategoricalDistribution([128, 256, 512])}
study = optuna.create_study(direction="minimize")
for t_ in trials:
    study.add_trial(optuna.trial.create_trial(params={k: t_[k] for k in dist}, distributions=dist, value=t_["nll"]))
imp = optuna.importance.get_param_importances(study, evaluator=optuna.importance.FanovaImportanceEvaluator(seed=42))
S["importance"] = {k: float(v) for k, v in imp.items()}
fig, ax = plt.subplots(figsize=(6, 2.8))
ks = list(imp.keys())[::-1]
ax.barh(ks, [imp[k] for k in ks], color=OR)
for i, k in enumerate(ks): ax.text(imp[k] + 0.01, i, f"{imp[k]:.2f}", va="center")
ax.set_xlabel("fANOVA importance (share of NLL variance explained)"); ax.set_xlim(0, max(imp.values()) * 1.2)
save(fig, "optuna_importance.png")
xs = [t_["n"] for t_ in trials]; ys = [t_["nll"] for t_ in trials]; best = np.minimum.accumulate(ys); bi = int(np.argmin(ys))
fig, ax = plt.subplots(figsize=(6.6, 3.6))
ax.scatter(xs, ys, color=AMB, s=36, label="Trial value (validation MC NLL)", zorder=3)
ax.step(xs, best, where="post", color=OR, lw=2.2, label="Best so far")
ax.scatter([xs[bi]], [ys[bi]], s=150, facecolor="none", edgecolor=GRN, lw=2, zorder=4)
ax.annotate(f"best: trial {xs[bi]}, NLL {ys[bi]:.4f}", (xs[bi], ys[bi]), xytext=(25, 40), textcoords="offset points",
            color=GRN, arrowprops=dict(arrowstyle="-", color=GRN))
ax.set_xlabel("Trial number"); ax.set_ylabel("Validation NLL (lower is better)"); ax.legend()
save(fig, "optuna_history.png")
fig, axes = plt.subplots(1, 4, figsize=(11, 2.9), sharey=True)
for ax, k in zip(axes, ("lr", "weight_decay", "dropout", "hidden")):
    ax.scatter([t_[k] for t_ in trials], ys, color=OR, s=22)
    if k in ("lr", "weight_decay"): ax.set_xscale("log")
    ax.set_xlabel(k)
axes[0].set_ylabel("Validation NLL")
save(fig, "optuna_slice.png")

# ---------------------------------------------------------------- 11 evaluation figures (light theme)
t = ev["test"]
cm = t["discrimination"]["confusion_matrix"]
M = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
fig, ax = plt.subplots(figsize=(4.2, 3.7)); ax.grid(False)
ax.imshow(M, cmap="Oranges")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{M[i, j]}\n{[['TN', 'FP'], ['FN', 'TP']][i][j]}", ha="center", va="center", fontsize=15,
                fontweight="bold", color="white" if M[i, j] > 300 else INK)
ax.set_xticks([0, 1], ["Normal", "Pneumonia"]); ax.set_yticks([0, 1], ["Normal", "Pneumonia"])
ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
save(fig, "confusion_matrix.png")
roc = t["discrimination"]["roc_curve"]
fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
axes[0].plot([p["x"] for p in roc], [p["y"] for p in roc], color=OR, lw=2.4, label=f"AUC = {t['discrimination']['roc_auc']:.3f}")
axes[0].plot([0, 1], [0, 1], ls="--", color=GRY); axes[0].set_xlabel("False positive rate"); axes[0].set_ylabel("True positive rate")
axes[0].set_title("ROC curve (test)"); axes[0].legend(loc="lower right")
pr = t["discrimination"]["pr_curve"]
axes[1].plot([p["x"] for p in pr], [p["y"] for p in pr], color=BLU, lw=2.4, label=f"PR-AUC = {t['discrimination']['pr_auc']:.3f}")
axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("Precision–recall curve (test)"); axes[1].legend(loc="lower left")
save(fig, "roc_pr.png")
fig, ax = plt.subplots(figsize=(5.6, 4.4))
ax.plot([0, 1], [0, 1], ls="--", color=GRY, label="Perfect calibration")
for key, col, lab in (("before", GRY, "Before temperature scaling"), ("after", OR, "After temperature scaling")):
    rel = [b for b in t["calibration"][key]["reliability"] if b["count"] > 0]
    ax.plot([b["mean_confidence"] for b in rel], [b["observed_frequency"] for b in rel], marker="o", lw=2,
            color=col, label=f"{lab} (ECE {t['calibration'][key]['ece']:.3f})")
ax.set_xlabel("Predicted probability of pneumonia"); ax.set_ylabel("Observed frequency of pneumonia"); ax.legend(loc="upper left", fontsize=9)
save(fig, "reliability.png")
h = ev["training"]["history"]
fig, ax = plt.subplots(figsize=(6.2, 3.5))
ax.plot([r["epoch"] + 1 for r in h], [r["train_loss"] for r in h], color=AMB, lw=2, label="Training loss (weighted BCE)")
ax.plot([r["epoch"] + 1 for r in h], [r["val_loss"] for r in h], color=OR, lw=2, label="Validation loss (BCE)")
bv = int(np.argmin([r["val_loss"] for r in h])); ax.axvline(bv + 1, color=GRN, ls="--")
ax.text(bv + 1.3, ax.get_ylim()[1] * 0.9, f"best epoch {bv + 1}", color=GRN)
ax.set_xlabel("Epoch"); ax.set_ylabel("Loss"); ax.legend()
save(fig, "training_curve.png")
S["best_epoch"] = bv + 1; S["history_last"] = h[-1]; S["history_best"] = h[bv]
ar = t["uncertainty"]["entropy"]["accuracy_rejection"]
fig, ax = plt.subplots(figsize=(6.2, 3.5))
ax.plot([p["rejection_rate"] * 100 for p in ar], [p["accuracy"] * 100 for p in ar], color=OR, lw=2.4)
rr, aa = t["refer_bands"]["refer_rate"] * 100, t["refer_bands"]["auto_decision_accuracy"] * 100
ax.scatter([rr], [aa], color=GRN, s=70, zorder=4)
ax.annotate(f"chosen policy: {rr:.1f}% referred → {aa:.1f}% accurate", (rr, aa), xytext=(15, -35), textcoords="offset points", color=GRN)
ax.set_xlabel("% of X-rays referred to a radiologist"); ax.set_ylabel("Accuracy on auto-decided (%)")
save(fig, "accuracy_referral.png")

bc = json.loads((ROOT / "artifacts/experiments/baseline_comparison.json").read_text())
S["baseline"] = bc
fig, ax = plt.subplots(figsize=(8, 3.6))
names = ["Logistic\nRegression", "Random\nForest", "MLP head\n(default)", "Final model\n(tuned + MC)"]
mets = [("accuracy", "Accuracy"), ("recall", "Recall"), ("f1", "F1"), ("roc_auc", "ROC-AUC")]
x = np.arange(4); w = 0.2
for k, (m, lab) in enumerate(mets):
    vals = [r["test"][m] * 100 for r in bc["results"]]
    ax.bar(x + (k - 1.5) * w, vals, w, label=lab, color=[OR, AMB, BLU, GRN][k])
ax.set_xticks(x, names); ax.set_ylim(88, 100.5); ax.set_ylabel("Test score (%)"); ax.legend(ncol=4, loc="upper center")
save(fig, "model_comparison.png")

# ---------------------------------------------------------------- 13 drift (PSI)
def psi(ref, cur, bins=10):
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1))); edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref); c = np.histogram(cur, edges)[0] / len(cur)
    r, c = np.clip(r, 1e-4, None), np.clip(c, 1e-4, None)
    return float(np.sum((c - r) * np.log(c / r)))
from scipy.stats import ks_2samp  # noqa: E402
ref = df[df.split == "train"]
drift = {}
sets = {"Validation split": df[df.split == "val"], "Test split": df[df.split == "test"],
        "Original 'test' folder": df[df.original_split == "test"]}
rng = np.random.default_rng(42)
for nm, d in sets.items():
    drift[nm] = {c: {"psi": psi(ref[c].values, d[c].values), "ks_p": float(ks_2samp(ref[c], d[c]).pvalue)} for c in ("brightness", "contrast", "intensity_entropy")}
sim = df[df.split == "test"].copy(); sim["brightness"] = np.clip(sim["brightness"] * 1.15, 0, 1); sim["contrast"] = sim["contrast"] * 0.8
drift["Simulated shift (+15% brightness, -20% contrast)"] = {c: {"psi": psi(ref[c].values, sim[c].values), "ks_p": float(ks_2samp(ref[c], sim[c]).pvalue)} for c in ("brightness", "contrast", "intensity_entropy")}
S["drift"] = drift
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.hist(ref.brightness, bins=40, density=True, alpha=0.55, color=BLU, label="Reference (training)")
ax.hist(df[df.split == "test"].brightness, bins=40, density=True, histtype="step", lw=2, color=GRN, label=f"Test split (PSI {drift['Test split']['brightness']['psi']:.3f})")
ax.hist(sim.brightness, bins=40, density=True, histtype="step", lw=2, color=RED, label=f"Simulated shift (PSI {drift['Simulated shift (+15% brightness, -20% contrast)']['brightness']['psi']:.2f})")
ax.set_xlabel("Image brightness"); ax.set_ylabel("Density"); ax.legend(fontsize=9)
save(fig, "drift_brightness.png")

# ---------------------------------------------------------------- latency + Grad-CAM (deployed model)
from app.services.inference_service import model_service  # noqa: E402
from app.services.gradcam_service import overlay  # noqa: E402
from app.ml.preprocessing import display_image  # noqa: E402
samp = df[df.split == "test"].sample(25, random_state=1)
lat = []
model_service.predict(Image.open(ROOT / "data/kermany" / samp.iloc[0].path).convert("RGB"))  # warm-up
for p_ in samp.path:
    im_ = Image.open(ROOT / "data/kermany" / p_).convert("RGB")
    t0 = time.perf_counter(); model_service.predict(im_); lat.append((time.perf_counter() - t0) * 1000)
S["latency_ms"] = {"mean": float(np.mean(lat)), "median": float(np.median(lat)), "p95": float(np.percentile(lat, 95)), "n": len(lat)}
cases = [te[(te.subtype == "bacterial") & (te.pred == 1) & ~te.refer].iloc[0], te[(te.subtype == "viral") & (te.pred == 1) & ~te.refer].iloc[0],
         te[(te.subtype == "normal") & (te.pred == 0) & ~te.refer].iloc[0], err[err.label_int == 1].iloc[0]]
fig, axes = plt.subplots(2, 4, figsize=(11, 5.8))
gc = []
for k, r in enumerate(cases):
    im_ = Image.open(ROOT / "data/kermany" / r.path).convert("RGB")
    res = model_service.predict(im_)
    cam = model_service.gradcam(im_, "PNEUMONIA")
    g = display_image(im_)
    axes[0, k].imshow(g, cmap="gray"); axes[0, k].axis("off")
    axes[0, k].set_title(f"{r.subtype.title()} (true {r.label.title()})", fontsize=10)
    axes[1, k].imshow(overlay(g, cam)); axes[1, k].axis("off")
    axes[1, k].set_title(f"{res.prediction.title()} p={res.pneumonia_probability:.2f}\nH={res.uncertainty:.2f} → {res.decision}", fontsize=9.5)
    ys_, xs_ = np.nonzero(cam > 0.5)
    gc.append({"path": r.path, "true": r.label, "pred": res.prediction, "p": res.pneumonia_probability, "H": res.uncertainty,
               "decision": res.decision, "cam_area_gt_0.5": float((cam > 0.5).mean()),
               "cam_centroid": [float(xs_.mean() / cam.shape[1]) if len(xs_) else None, float(ys_.mean() / cam.shape[0]) if len(ys_) else None]})
save(fig, "gradcam_examples.png")
S["gradcam"] = gc

json.dump(S, open(Path(__file__).resolve().parent / "stats.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("ok", len(trials), "trials", S["latency_ms"], S["errors"])
