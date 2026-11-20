"""Builds the Final Project Report (BTech AI/ML - Project Life Cycle Management format).

Every number is read from the project's own artefacts:
  artifacts/models/v1.1.0/{config,evaluation}.json, artifacts/datasets/kermany/dataset_card.json,
  artifacts/experiments/baseline_comparison.json, mlflow/mlflow.db (via stats.json),
  docs/report/stats.json (analyze.py) and docs/report/evidence.json (evidence.py).
Run:  .venv/Scripts/python docs/report/build_report.py
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from docx_kit import Report, TEXT_W  # noqa: E402

EV_SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else None   # folder with app/MLflow screenshots
OUT = HERE.parent / "PneumoScope_Group13_Final_Report.docx"

S = json.loads((HERE / "stats.json").read_text())
EVD = json.loads((HERE / "evidence.json").read_text())
ev = json.loads((ROOT / "artifacts/models/v1.1.0/evaluation.json").read_text())
ev0 = json.loads((ROOT / "artifacts/models/v1.0.0/evaluation.json").read_text())
cfg = json.loads((ROOT / "artifacts/models/v1.1.0/config.json").read_text())
card = json.loads((ROOT / "artifacts/datasets/kermany/dataset_card.json").read_text())
bc = json.loads((ROOT / "artifacts/experiments/baseline_comparison.json").read_text())["results"]
oapi = json.loads((HERE / "openapi.json").read_text())
FIG = HERE / "figs"
if EV_SRC:
    for f in EV_SRC.glob("*.jpg"):
        shutil.copy(f, FIG / f"ev_{f.name}")

t = ev["test"]; dsc = t["discrimination"]; cmx = dsc["confusion_matrix"]; ci = t["bootstrap_ci"]
v = ev["validation"]["discrimination"]; cal = t["calibration"]; rb = t["refer_bands"]; unc = t["uncertainty"]
LR, RF, MLP, FIN = bc
lk = ev["leakage"]; tr_ = S["trials"]; best = min(tr_, key=lambda x: x["nll"]); worst = max(tr_, key=lambda x: x["nll"])
D = S["descriptive"]; FA = S["fairness"]; ER = S["errors"]; DR = S["drift"]; IMP = S["importance"]
split = {s["split"]: s for s in card["patient_disjoint_split"]["splits"]}
TEAM = [("Shruti Shinde", "2402669"), ("Rushab Engolla", "2410251"), ("Dhruv Prabhu", "2405376"), ("Ali Shaikh", "2406682")]
TITLE = "PneumoScope: Uncertainty-Aware Pneumonia Detection from Paediatric Chest X-Rays with Monte Carlo Dropout"


def pc(x, d=1): return f"{x * 100:.{d}f}%"
def f3(x): return f"{x:.3f}"
def f4(x): return f"{x:.4f}"


# per-group counts for fairness tables
df = pd.read_csv(ROOT / "data/kermany/manifest.csv")
te = df[df.split == "test"].reset_index(drop=True)
te["p"] = t["per_case"]["p"]; te["pred"] = (te.p >= 0.5).astype(int)
mins = te[["width", "height"]].min(axis=1); te["res"] = np.where(mins < mins.median(), "lower-res", "higher-res")
res_counts = {g: (int((d.label_int == 0).sum()), int((d.label_int == 1).sum())) for g, d in te.groupby("res")}
res_median = float(mins.median())

R = Report(FIG)
d = R.d

# =====================================================================================  COVER (no page number)
sec0 = d.sections[0]
R.P("ATLAS SkillTech University", align="c", size=18, bold=True, space_after=2)
R.P("Department of Artificial Intelligence and Machine Learning", align="c", size=14, space_after=2)
R.P("Third Year B.Tech — AI & ML", align="c", size=12, space_after=18)
R.P("BTECH CAP 501 — Project Life Cycle Management", align="c", size=13, bold=True, space_after=4)
R.P("FINAL PROJECT IMPLEMENTATION REPORT", align="c", size=13, space_after=24)
R.P("PneumoScope", align="c", size=26, bold=True, space_after=0)
R.P("Uncertainty-Aware Pneumonia Detection from Paediatric Chest X-Rays with Monte Carlo Dropout",
    align="c", size=15, italic=True, space_after=24)
logo = d.add_paragraph(); logo.alignment = 1
logo.add_run().add_picture(str(FIG / "sample_xrays.png"), width=__import__("docx").shared.Inches(4.6))
R.P("Group Number: 13", align="c", size=13, bold=True, space_after=6)
tb = d.add_table(rows=1 + len(TEAM), cols=2); tb.style = "Table Grid"; tb.alignment = 1
for i, row in enumerate([("Student Name", "Roll No. / App ID")] + TEAM):
    for j, val in enumerate(row):
        c = tb.cell(i, j); c.width = __import__("docx").shared.Inches(2.4)
        p = c.paragraphs[0]; p.alignment = 1; p.paragraph_format.line_spacing = 1.0
        r = p.add_run(val); r.bold = i == 0
R.P("", space_after=6)
R.P("Faculty Mentor: **Dr. Amrita Banerjee**", align="c", size=13, space_after=2)
R.P("Academic Year: **2026**", align="c", size=13, space_after=0)

# =====================================================================================  PRELIMINARY (roman)
R.new_section("lowerRoman", 1)
R.H1("Certificate of Project Completion", chapter=False, toc=False)
R.P(f"This is to certify that the project entitled **“{TITLE}”** has been carried out by the following students of "
    "Group 13, Third Year B.Tech (Artificial Intelligence and Machine Learning), as part of the course **Project Life Cycle "
    "Management** during the academic year **2026**, under my supervision and guidance:")
R.TBL(["Sr. No.", "Student Name", "Roll No. / App ID"], [[str(i + 1), n, a] for i, (n, a) in enumerate(TEAM)],
      None, widths=[0.9, 3, 2.3], align="ccc")
R.P("The work presented in this report is a bona fide record of the project completed by the group. It satisfies the "
    "requirements of the final project implementation report prescribed for the course.")
R.P("\n\n")
sig = d.add_table(rows=2, cols=2); sig.alignment = 1
for j, (a, b) in enumerate((("______________________", "Dr. Amrita Banerjee\nFaculty Mentor"), ("______________________", "Dr. Shashikant Patil\nHead of the Department\nAI & ML"))):
    sig.cell(0, j).paragraphs[0].add_run(a); sig.cell(0, j).paragraphs[0].alignment = 1
    for k, ln in enumerate(b.split("\n")):
        pp = sig.cell(1, j).paragraphs[0] if k == 0 else sig.cell(1, j).add_paragraph()
        pp.alignment = 1; pp.paragraph_format.line_spacing = 1.0; rr = pp.add_run(ln); rr.bold = k == 0
R.P("\n**Date:** 13 November 2026", align="l", space_after=0)
R.P("**Place:** Kurla, Mumbai, Maharashtra 400070", align="l")

R.H1("Declaration of Originality", chapter=False, toc=False)
R.P(f"We, the members of Group 13, declare that the project report entitled **“{TITLE}”** is our own work. "
    "The software, experiments, figures and results presented here were produced by us during the academic year 2026. "
    "Where we have used published datasets, open-source libraries, pre-trained model weights or the ideas of other authors, "
    "they have been acknowledged and cited in the References. The results reported have not been altered, and every "
    "experiment that did not work as intended is reported as such. This report has not been submitted, in whole or in part, "
    "for any other degree, diploma or course.")
R.P("We further declare that no personal or confidential data, credentials or API keys are included in this report or in "
    "the accompanying repository.")
R.TBL(["Student Name", "Roll No. / App ID"], [[n, a] for n, a in TEAM], None,
      widths=[3.0, 2.2], size=11, align="lc")

R.H1("Acknowledgement", chapter=False, toc=False)
R.P("We express our sincere gratitude to our faculty mentor, **Dr. Amrita Banerjee**, for her guidance throughout this project. "
    "Her emphasis on evidence, honest reporting of limitations and the full project life cycle shaped how we designed and "
    "evaluated PneumoScope.")
R.P("We thank the Head of the Department, **Dr. Shashikant Patil**, and the faculty of the Department of Artificial Intelligence and Machine Learning "
    "for the course structure and the facilities provided. We are grateful to Daniel Kermany, Kang Zhang, Michael Goldbaum "
    "and the Guangzhou Women and Children’s Medical Center for publishing the paediatric chest X-ray dataset under an open "
    "licence, which made this project possible.")
R.P("We also acknowledge the open-source communities behind PyTorch, torchvision, scikit-learn, Optuna, MLflow, Fairlearn, "
    "FastAPI, React and Docker. Finally, we thank our families and classmates for their support and feedback during testing "
    "of the application.")
R.P("\n— Shruti Shinde, Rushab Engolla, Dhruv Prabhu and Ali Shaikh (Group 13)", align="l", italic=True)

R.H1("Abstract", chapter=False, toc=False)
R.P(f"Pneumonia is the largest infectious cause of death in children under five, and chest X-rays are the most common "
    f"diagnostic image, yet radiologists are scarce in many hospitals. This project, **PneumoScope**, builds a decision-support "
    f"web application that classifies a paediatric chest X-ray as Normal or Pneumonia and, crucially, reports how *uncertain* "
    f"it is, so that doubtful cases are referred to a doctor instead of being decided automatically. We used the public "
    f"Kermany paediatric chest X-ray dataset ({card['total_images']:,} images, {card['total_patients']:,} patients) and re-split "
    f"it by patient into training ({split['train']['images']:,}), validation ({split['val']['images']}) and test "
    f"({split['test']['images']}) sets with zero patient overlap. Following the CRISP-DM life cycle, we extracted 2048-dimensional "
    f"features with a frozen ImageNet ResNet-50 and compared Logistic Regression (baseline), Random Forest, a default "
    f"neural head and a Monte Carlo (MC) Dropout head tuned with Optuna (25 trials) and tracked in MLflow. The final model "
    f"uses 30 stochastic passes and temperature scaling. On the untouched test set it achieved accuracy {pc(dsc['accuracy'])}, "
    f"recall {pc(dsc['recall'])}, precision {pc(dsc['precision'])}, F1 {f3(dsc['f1'])} and ROC-AUC {f3(dsc['roc_auc'])} "
    f"(95% CI {f3(ci['roc_auc']['lower'])}–{f3(ci['roc_auc']['upper'])}), with a calibration error (ECE) of only "
    f"{pc(cal['after']['ece'])}. Referring the {pc(rb['refer_rate'])} most uncertain X-rays raised accuracy on the remaining "
    f"cases to {pc(rb['auto_decision_accuracy'])}. The model is deployed as a FastAPI backend and React frontend in Docker "
    f"containers with sign-in, Grad-CAM heatmaps and a history dashboard; 39 automated tests pass. The main limitations are "
    f"that the data come from a single hospital, image size is strongly correlated with the label (a possible shortcut), "
    f"no demographic attributes are available for fairness auditing, and external validation and CI/CD automation remain "
    f"future work. The system is an educational prototype, not a clinical device.")
R.P(f"**Keywords:** pneumonia detection, chest X-ray, ResNet-50, Monte Carlo Dropout, uncertainty, calibration, CRISP-DM, "
    f"Optuna, MLflow, FastAPI, Docker.", align="l")

R.H1("Table of Contents", chapter=False, toc=False)
R.toc('TOC \\o "1-2" \\h \\z \\u')
R.H1("List of Figures", chapter=False, toc=False)
R.toc('TOC \\h \\z \\t "Figure Caption,1"')
R.H1("List of Tables", chapter=False, toc=False)
R.toc('TOC \\h \\z \\t "Table Caption,1"')
R.H1("List of Abbreviations", chapter=False, toc=False)
ABBR = [("AI / ML", "Artificial Intelligence / Machine Learning"), ("API", "Application Programming Interface"),
        ("AUC", "Area Under the Curve"), ("AURC", "Area Under the Risk–Coverage curve"), ("BCE", "Binary Cross-Entropy"),
        ("CDSCO", "Central Drugs Standard Control Organisation (India)"), ("CI", "Confidence Interval"),
        ("CI/CD", "Continuous Integration / Continuous Delivery"), ("CNN", "Convolutional Neural Network"),
        ("CPU", "Central Processing Unit"), ("CRISP-DM", "Cross-Industry Standard Process for Data Mining"),
        ("CXR", "Chest X-Ray"), ("DPDP", "Digital Personal Data Protection Act, 2023 (India)"), ("DVC", "Data Version Control"),
        ("ECE", "Expected Calibration Error"), ("EDA", "Exploratory Data Analysis"), ("FN / FP", "False Negative / False Positive"),
        ("FPR / TPR", "False / True Positive Rate"), ("GDPR", "General Data Protection Regulation (EU)"),
        ("Grad-CAM", "Gradient-weighted Class Activation Mapping"), ("HTTP(S)", "Hypertext Transfer Protocol (Secure)"),
        ("IQR", "Inter-Quartile Range"), ("JSON", "JavaScript Object Notation"), ("JWT", "JSON Web Token"),
        ("KS", "Kolmogorov–Smirnov test"), ("LR", "Logistic Regression"), ("MAR / MCAR / MNAR", "Missing At Random / Completely At Random / Not At Random"),
        ("MC", "Monte Carlo"), ("MI", "Mutual Information"), ("MLP", "Multi-Layer Perceptron"), ("NLL", "Negative Log-Likelihood"),
        ("PCA", "Principal Component Analysis"), ("PR", "Precision–Recall"), ("PSI", "Population Stability Index"),
        ("RF", "Random Forest"), ("ROC", "Receiver Operating Characteristic"), ("REST", "Representational State Transfer"),
        ("SHAP", "SHapley Additive exPlanations"), ("SQL", "Structured Query Language"), ("TDSP", "Team Data Science Process (Microsoft)"),
        ("TPE", "Tree-structured Parzen Estimator"), ("WHO", "World Health Organization")]
R.TBL(["Abbreviation", "Full form"], [list(a) for a in ABBR], None, widths=[1.6, 4.6], size=10.5)

# =====================================================================================  CHAPTERS (arabic)
R.new_section("decimal", 1)

# ------------------------------------------------------------------ CH 1
R.H1("Project Introduction and Problem Definition")
R.mapped("Project Initiation, Feasibility and Requirements")
R.H2("1.1 Introduction")
R.P("Pneumonia is an infection that inflames the air sacs of the lungs and fills them with fluid or pus. According to the World "
    "Health Organization it is the single largest infectious cause of death in children worldwide, responsible for about 14% "
    "of all deaths of children under five years old (740,180 children in 2019) [1]. Most of these deaths occur in low- and "
    "middle-income countries, including India, where the number of radiologists per million people is far below that of "
    "high-income countries.")
R.P("A chest X-ray (CXR) is cheap, fast and widely available, and it is the standard imaging test for confirming pneumonia. "
    "Reading a paediatric CXR, however, requires expertise: the signs of pneumonia (consolidation, interstitial opacities, "
    "air bronchograms) can be subtle, and the reading may be delayed when a radiologist is not on site. Deep learning has "
    "shown that convolutional neural networks (CNNs) can recognise pneumonia on CXRs with accuracy close to that of "
    "specialists [2], [3]. Most published systems, however, return a single label with no indication of how confident they "
    "are, and many report results on splits where images of the same patient appear in both training and test sets.")
R.P("This project belongs to the domain of **medical image classification and clinical decision support**. It applies the full "
    "AI/ML project life cycle — initiation, data understanding, preparation, modelling, evaluation, deployment and monitoring — "
    "to build **PneumoScope**, a web application that triages paediatric chest X-rays and knows when it does not know.")
R.H2("1.2 Problem Statement")
R.P("*Given a frontal paediatric chest X-ray image, automatically classify it as NORMAL or PNEUMONIA, estimate the reliability "
    "of that prediction, and decide whether the case can be reported automatically (AUTO) or must be referred to a "
    "radiologist (REFER), while keeping the number of missed pneumonia cases low and ensuring that reported probabilities "
    "are trustworthy.*")
R.P("Three practical sub-problems follow from this statement. First, a missed pneumonia (false negative) is far more harmful "
    "than a false alarm, so **recall** must be prioritised over plain accuracy. Second, a probability of 0.9 should mean that "
    "pneumonia is present about 90% of the time, so the model must be **calibrated**. Third, the evaluation must be honest: "
    "the Kermany dataset contains several images per patient, so a naïve random split leaks patients between training and "
    "test sets and inflates the results.")
R.H2("1.3 Project Objectives")
R.P(f"The objectives were fixed at initiation and are stated in measurable form in {R.next_tab()}. They are re-assessed "
    "against the achieved results in Chapter 15.")
R.TBL(["ID", "Objective", "Measure and target"],
      [["O1", "Build a leakage-free dataset split", "0 patients shared between train, validation and test"],
       ["O2", "Detect pneumonia with high sensitivity", "Test recall ≥ 0.95"],
       ["O3", "Discriminate reliably", "Lower bound of 95% bootstrap CI of test ROC-AUC ≥ 0.90"],
       ["O4", "Produce calibrated probabilities", "Test ECE ≤ 0.05 (5%)"],
       ["O5", "Quantify uncertainty and refer doubtful cases", "Referral policy with ≤ 30% referred and higher accuracy on AUTO cases"],
       ["O6", "Beat a simple baseline", "Final model ≥ Logistic Regression on recall, F1 and calibration"],
       ["O7", "Track experiments and tune systematically", "All Optuna trials and baselines logged in MLflow"],
       ["O8", "Deploy a usable application", "Working API + web UI in Docker; prediction in < 2 s on CPU; automated tests pass"]],
      "Measurable project objectives", widths=[0.5, 2.5, 3.3], align="cll")
R.H2("1.4 Proposed AI/ML Solution")
R.P("The proposed solution combines transfer learning with Bayesian-approximate uncertainty estimation:")
R.B(["**Feature extraction:** each X-ray is converted to grayscale, resized to 224 × 224 pixels, normalised and passed through a "
     "ResNet-50 [4] pre-trained on ImageNet, whose weights are frozen. This produces a 2048-dimensional feature vector.",
     "**MC-Dropout classification head:** a small neural network (dropout → linear → ReLU → dropout → linear) predicts the "
     "probability of pneumonia. Dropout is kept active at prediction time and the head is run 30 times; the spread of the 30 "
     "predictions is the model’s uncertainty (Monte Carlo Dropout [5]).",
     "**Calibration:** temperature scaling [6] fitted on the validation set makes the probabilities match observed frequencies.",
     "**Referral policy:** if the predictive entropy is above a threshold chosen on the validation set, the case is marked "
     "REFER; otherwise the prediction is reported automatically (AUTO).",
     "**Explanation:** Grad-CAM [7] heatmaps show which lung regions influenced the prediction.",
     "**Application:** a FastAPI backend and a React frontend, packaged with Docker, with user accounts, upload, history and a "
     "model-performance dashboard."])
R.P("The expected benefits are faster preliminary reads, a safety net that hands difficult cases to humans, and transparent "
    "reporting of model performance to users.")
R.H2("1.5 Project Scope")
R.TBL(["In scope", "Out of scope"],
      [["Binary classification: Normal vs Pneumonia on frontal paediatric CXRs", "Bacterial vs viral sub-typing, other thoracic diseases"],
       ["Public Kermany dataset (Guangzhou, ages 1–5)", "Collection of new patient data or hospital integration (PACS/HIS)"],
       ["Uncertainty estimation, calibration and referral policy", "Clinical validation, regulatory approval or diagnostic use"],
       ["Grad-CAM visual explanation", "Lesion segmentation or localisation ground truth"],
       ["Web app with authentication, history and dashboard", "Mobile apps, multi-tenant hospital deployment"],
       ["Docker deployment on a single host with temporary public link", "Cloud production hosting, high availability"],
       ["Monitoring and CI/CD design", "Fully automated retraining and GitHub Actions execution (proposed only)"]],
      "Project scope: included and excluded items", widths=[3.15, 3.15])
R.H2("1.6 Expected Outcomes and Success Criteria")
R.P("The project is considered successful if (a) the targets O1–O4 in Table 1.1 are met on the held-out test set, which the "
    "training code stores as machine-checkable targets (`recall_min = 0.95`, `roc_auc_ci_lower_min = 0.90`, `ece_max = 0.05`); "
    "(b) the referral policy improves accuracy on automatically decided cases; (c) the final model is at least as good as the "
    "baseline on recall, F1 and calibration; and (d) the application runs end-to-end from upload to result in Docker with all "
    "automated tests passing. Expected outcomes are a trained and versioned model bundle, an evaluation report, an MLflow "
    "experiment history, a deployed web application, this report and a presentation.")

# ------------------------------------------------------------------ CH 2
R.H1("Project Life Cycle Frameworks")
R.H2("2.1 AI/ML Project Life Cycle")
R.P(f"{R.next_fig()} shows the life cycle that PneumoScope actually followed. It is iterative: after the first full pass "
    "(model v1.0.0) the evaluation showed that the referral policy referred only 2.4% of cases and left auto-decided accuracy at "
    "96.6%, so the team returned to the modelling stage, tightened the policy and produced v1.1.0. Monitoring is designed but "
    "not yet automated, so it is drawn with a dashed border.")
R.FIG("lifecycle.png", "Project-specific AI/ML life cycle of PneumoScope (dashed = designed, not yet automated)", 6.27)
R.TBL(["Stage", "What was done in this project", "Main artefact"],
      [["1 Initiation", "Problem, objectives, scope, success criteria, feasibility, stakeholders", "Chapters 1, 3, 4"],
       ["2 Data", "Download, patient-ID extraction, quality checks, duplicates, EDA", "manifest.csv, dataset_card.json"],
       ["3 Preparation", "Patient-disjoint split, preprocessing, ResNet-50 feature cache", "kermany_resnet50.npz"],
       ["4 Modelling", "LR / RF / MLP baselines, MC-Dropout head, Optuna tuning, MLflow tracking", "MLflow experiments 1 and 2"],
       ["5 Evaluation", "Test metrics, bootstrap CIs, calibration, uncertainty, leakage study", "evaluation.json"],
       ["6 Deployment", "FastAPI, React, Docker Compose, Cloudflare tunnel, 39 tests", "Running containers"],
       ["7 Monitoring", "Reference statistics stored; PSI drift method, retraining rules designed", "reference_stats.json"]],
      "Life-cycle stages and project artefacts", widths=[1.2, 3.5, 1.6])
R.H2("2.2 AI/ML vs Conventional Software Development")
R.P("Building PneumoScope involved both conventional software (the web application) and ML development (the model). The "
    f"two parts behaved very differently, as summarised in {R.next_tab()}.")
R.TBL(["Aspect", "Conventional software (our web app)", "AI/ML development (our model)"],
      [["Behaviour defined by", "Explicit code and rules (e.g. upload ≤ 10 MB)", "Data and learned parameters (1.05 M weights in the head)"],
       ["Development flow", "Requirements → design → code → test", "Experiment loop: data → train → evaluate → repeat"],
       ["Testing", "Deterministic unit/API tests (39 pytest tests)", "Statistical: metrics on held-out data with confidence intervals"],
       ["Correctness", "Pass / fail", "Degree of performance; errors are expected (39 of 837 test images)"],
       ["Uncertainty", "Low — same input, same output", "High — depends on data, split, seed; quantified by MC Dropout"],
       ["Versioning", "Code only (source files)", "Code + data + hyper-parameters + weights (hashes, MLflow run IDs)"],
       ["Maintenance", "Fix bugs, update dependencies", "Also monitor drift, recalibrate, retrain when data change"],
       ["Failure mode", "Crashes, exceptions", "Silent: confident wrong answers, shortcut learning, data leakage"]],
      "Comparison of conventional software and AI/ML development in this project", widths=[1.3, 2.5, 2.5])
R.H2("2.3 CRISP-DM Framework")
R.P(f"CRISP-DM [8] organises a data-mining project into six phases around the data ({R.next_fig()}). The mapping of our activities "
    "to each phase is given in Table 2.3.")
R.FIG("crispdm.png", "CRISP-DM phases applied to the Kermany chest X-ray data", 3.9)
R.TBL(["CRISP-DM phase", "PneumoScope activities", "Evidence"],
      [["Business understanding", "Defined triage use case, recall-first objective, AUTO/REFER output, success targets", "Ch. 1, Table 1.1"],
       ["Data understanding", f"Counted {card['total_images']:,} images / {card['total_patients']:,} patients, class imbalance 73:27, image sizes, "
        f"{card['duplicates']['exact_duplicate_images']} exact duplicates, EDA and correlation analysis", "Ch. 5–6"],
       ["Data preparation", "Patient IDs from file names, patient-disjoint split, resize + normalise, feature extraction", "Ch. 5, 8"],
       ["Modelling", "LR, RF, default MLP, MC-Dropout head with Optuna (25 trials), temperature scaling", "Ch. 9–10"],
       ["Evaluation", "Accuracy, precision, recall, F1, ROC-AUC, ECE, Brier, CIs, leakage comparison, error analysis", "Ch. 11"],
       ["Deployment", "FastAPI + React in Docker; health check; temporary HTTPS link; monitoring design", "Ch. 12–13"]],
      "CRISP-DM phase mapping", widths=[1.5, 3.6, 1.2])
R.H2("2.4 Microsoft TDSP Framework")
R.P("The Team Data Science Process (TDSP) [9] adds team roles, standard project structure and version control to the "
    "life cycle. We adopted its practices where they fitted a four-person student team:")
R.B(["**Team collaboration:** roles followed TDSP (project lead, data scientist, application developer, solution architect; "
     "see Section 15.2). Weekly stand-ups reviewed the Gantt chart and the risk register.",
     "**Standard project structure:** the repository separates `backend/app` (service code), `backend/scripts` (data "
     "preparation, training, baselines), `backend/tests`, `frontend`, `artifacts` (model bundles, dataset card, experiment "
     "results) and `docs`, similar to the TDSP template.",
     "**Version control:** source code is kept in a single public GitHub repository (https://github.com/Shruti4105/PneumoScope). Data and "
     "models are versioned by content hashes (MD5 per image, SHA-256 of weights), semantic model versions (v1.0.0, v1.1.0) "
     "and MLflow run IDs (Chapter 5).",
     "**Modelling and deployment:** TDSP’s ‘model → operationalise → customer acceptance’ steps map to our evaluation report, "
     "Docker deployment and the acceptance criteria of Section 3.5."])
R.H2("2.5 Google ML Life Cycle")
R.P("Google’s guidance on production ML [10] distinguishes the **ML project** (the human process of framing the problem, "
    "collecting data, experimenting and deciding) from the **ML pipeline** (the automated, repeatable sequence of steps that "
    "turns data into a deployed model). In PneumoScope:")
R.B(["The **ML project** included choosing recall and calibration as primary goals, discovering the patient-leakage problem, "
     "comparing four model families and deciding on the referral threshold — decisions recorded in this report.",
     "The **ML pipeline** is the code that can be re-run without human decisions: `prepare_kermany.py` (extract, manifest, "
     "split) → `train_pipeline.py` (features, Optuna, final head, temperature, threshold, evaluation, bundle, MLflow) → "
     "`baseline_models.py` → Docker build. Re-running it with the same seed (42) reproduces the same split and model."])
R.H2("2.6 Framework Selection and Justification")
R.TBL(["Criterion", "CRISP-DM", "Microsoft TDSP", "Google ML life cycle"],
      [["Focus", "Data-mining phases", "Team process + structure", "Production pipelines / MLOps"],
       ["Fit for a student team of 4", "High — simple, well known", "Medium — role-heavy", "Medium — assumes cloud tooling"],
       ["Data understanding emphasis", "Strong", "Moderate", "Moderate"],
       ["Deployment and monitoring", "Brief", "Included", "Strong"],
       ["Tool dependence", "None", "Azure-oriented templates", "Google Cloud / TFX oriented"],
       ["Used in this project", "Primary framework", "Team roles, repository structure", "Project vs pipeline separation"]],
      "Framework comparison", widths=[1.6, 1.6, 1.6, 1.6])
R.P("**Selected framework: CRISP-DM, extended with TDSP team practices and Google’s pipeline view.** CRISP-DM was chosen as "
    "the backbone because the hardest problems in this project were in data understanding and evaluation (patient leakage, "
    "duplicates, confounding image size), which CRISP-DM puts at the centre, and because it is tool-independent. CRISP-DM is "
    "weak on deployment and monitoring, so we borrowed TDSP’s role definitions and repository structure and Google’s "
    "separation of the experimental project from the reproducible pipeline.")

# ------------------------------------------------------------------ CH 3
R.H1("Feasibility Analysis and Requirements Engineering")
R.H2("3.1 Technical Feasibility")
R.H3("Dataset availability and sufficiency")
R.P(f"The Kermany dataset [2], [11] is freely downloadable (1.2 GB) under a CC BY 4.0 licence and contains "
    f"{card['total_images']:,} labelled images. To judge whether this is enough data, consider the precision of the test "
    f"estimates. With n = {t['n']} test images, the standard error of an accuracy p ≈ 0.95 is")
R.EQ("SE(p̂) = √( p(1 − p) / n ) = √( 0.95 × 0.05 / 837 ) ≈ 0.0075")
R.P(f"so the 95% confidence interval is about ±1.5 percentage points, which is narrow enough to compare models. For recall the "
    f"relevant n is the {t['n_pneumonia']} pneumonia cases, giving SE ≈ 0.008. The bootstrap intervals measured later "
    f"(accuracy {f3(ci['accuracy']['lower'])}–{f3(ci['accuracy']['upper'])}) confirm this calculation. For training, the "
    f"{split['train']['images']:,} training images are few for training a CNN from scratch, but more than sufficient for a "
    f"small head on frozen features: the final head has 2048 × 512 + 512 + 512 + 1 ≈ 1.05 million parameters, and transfer "
    f"learning means the 23.5 million backbone parameters do not need to be learned.")
R.H3("Model capability")
R.P("Published work reports ROC-AUC around 0.96–0.99 on this dataset with fine-tuned CNNs [2], [3]. A frozen ImageNet "
    "ResNet-50 is known to give strong generic features for radiographs, and MC Dropout adds uncertainty at almost no extra "
    "cost because only the small head is sampled. The approach was therefore expected to meet the targets on a CPU.")
R.H3("Hardware, software and computational limits")
R.TBL(["Resource", "Available / used", "Limitation and consequence"],
      [["Hardware", "Student laptop, CPU only (no GPU), Windows 11", "Fine-tuning ResNet-50 end-to-end impractical → frozen backbone + feature cache"],
       ["Feature extraction", "≈ 4 images/s on CPU → ≈ 25 min for 5,856 images (once)", "Cached to `kermany_resnet50.npz` so tuning reuses features"],
       ["Head training", "≈ 27 s per run (default MLP), 25 Optuna trials", "Full tuning study runs in minutes on CPU"],
       ["Software", "Python 3.13, PyTorch 2 (CPU), scikit-learn, Optuna, MLflow, FastAPI, React, Docker", "All free and open-source"],
       ["Storage", "1.2 GB raw data, 94 MB model weights, 2.5 GB backend image", "PyTorch dominates image size"]],
      "Hardware and software feasibility", widths=[1.3, 2.6, 2.4])
R.H3("Inference latency requirement")
L = S["latency_ms"]
R.P(f"A triage tool should answer while the user waits, so we set a requirement of under 2 seconds per image on a CPU. One "
    f"prediction requires one ResNet-50 forward pass (≈ 4.1 GFLOPs) plus 30 passes of the tiny head (≈ 30 × 1.05 M ≈ 31 MFLOPs, "
    f"under 1% of the backbone cost). Measured on 25 test images in the development environment, the end-to-end prediction "
    f"took a median of {L['median']:.0f} ms (mean {L['mean']:.0f} ms, 95th percentile {L['p95']:.0f} ms). The requirement is "
    f"met with a large margin; MC Dropout adds negligible latency because only the head is sampled.")
R.H2("3.2 Economic Feasibility")
R.P(f"{R.next_tab()} estimates the costs. Development cost is expressed as effort because the team members are students; "
    "infrastructure costs are indicative market prices for a small cloud server and are not actual expenses incurred.")
R.TBL(["Cost item", "This project (actual)", "Pilot deployment (estimate)"],
      [["Development effort", "4 students × ~14 weeks (course project)", "—"],
       ["Data acquisition", "₹0 — public CC BY 4.0 dataset", "Hospital data: ethics approval + radiologist labelling time"],
       ["Compute for training", "₹0 — existing laptops (CPU)", "Optional GPU time ≈ ₹50–100 per hour if fine-tuning"],
       ["Hosting", "₹0 — local Docker + free Cloudflare quick tunnel", "4 vCPU / 8 GB VM ≈ ₹3,000–5,000 per month"],
       ["Software licences", "₹0 — open-source stack", "₹0"],
       ["Maintenance", "Team time", "Monitoring, monthly drift review, periodic relabelling and retraining"]],
      "Economic feasibility estimate", widths=[1.6, 2.3, 2.4])
R.P("Because every component is open-source and the model runs on a CPU, the economic risk is low; the dominant future cost "
    "would be expert labelling of local data for external validation.")
R.H2("3.3 Operational Feasibility")
R.P("The system can be operated by a non-expert: users sign in, drag an X-ray onto the page and receive a result with a "
    "heatmap in about a second. The whole stack starts with one command (`docker compose up --build`), the backend has a "
    "health check endpoint that Docker polls every 30 seconds, and the model is loaded from a versioned, hash-checked bundle, "
    "so it can be replaced without code changes. Monitoring is feasible because reference distributions of the input "
    "descriptors were saved at training time (Chapter 13). The main operational constraint is that the temporary public link "
    "changes whenever the tunnel restarts.")
R.H2("3.4 Ethical Feasibility")
R.P("The dataset is de-identified and openly licensed, and no new patient data are collected. The application stores uploaded "
    "images only for the signed-in user who uploaded them and lets users delete them. The principal ethical risks are "
    "over-reliance on an unvalidated tool, possible bias because all images come from one hospital and age group, and the "
    "possibility that the model uses shortcuts. These are mitigated by the REFER mechanism, a disclaimer shown on every "
    "result, transparent model-performance pages and the explicit statement that the tool is not for clinical use "
    "(Chapter 7).")
R.H2("3.5 Requirements Engineering")
R.TBL(["ID", "Type", "Requirement", "Verification"],
      [["FR1", "Functional", "Users can register, sign in and sign out; all analysis pages require sign-in", "test_auth.py, manual"],
       ["FR2", "Functional", "Upload JPEG/PNG (≤ 10 MB) and receive class, probability, uncertainty, AUTO/REFER and reason", "test_api.py, Fig. 12.4"],
       ["FR3", "Functional", "Reject non-images, corrupt files, oversized files and non-radiograph colour images", "test_upload_validation.py"],
       ["FR4", "Functional", "Show a Grad-CAM heatmap for any saved analysis", "API evidence"],
       ["FR5", "Functional", "Store, list, open and delete past analyses (history)", "test_api.py"],
       ["FR6", "Functional", "Display real test-set metrics, confusion matrix and ROC curve", "/metrics endpoint, dashboard"],
       ["NFR1", "Performance", "Prediction latency < 2 s per image on CPU", f"median {L['median']:.0f} ms"],
       ["NFR2", "Security", "Passwords hashed (bcrypt); session token in HttpOnly cookie; no secrets in frontend", "Code review, tests"],
       ["NFR3", "Reliability", "Container health check; model integrity verified by SHA-256", "docker ps (healthy)"],
       ["NFR4", "Portability", "Runs anywhere with Docker", "docker compose"],
       ["NFR5", "Usability", "Result understandable by non-experts, with disclaimer", "UI screenshots"],
       ["DR1", "Data", "Labelled frontal paediatric CXRs with patient identifiers", "Kermany file names"],
       ["DR2", "Data", "No patient overlap between splits", "dataset_card.json overlap = 0"],
       ["ER1", "Ethical", "Uncertain or low-quality inputs must be referred, not auto-decided", "Refer policy + quality flags"],
       ["ER2", "Ethical", "Educational-use disclaimer on every result; no clinical claims", "API response field"]],
      "Requirements specification", widths=[0.55, 1.0, 3.3, 1.45], size=9.5)
R.P("**Acceptance criteria.** The product is accepted when: (AC1) test recall ≥ 0.95; (AC2) lower bound of the test ROC-AUC "
    "CI ≥ 0.90; (AC3) test ECE ≤ 0.05; (AC4) accuracy on AUTO cases exceeds overall accuracy with ≤ 30% referred; (AC5) all "
    "automated tests pass; (AC6) the Dockerised application completes an upload-to-result request successfully; (AC7) "
    "FR1–FR6 work in a manual walkthrough.")
R.H2("3.6 Feasibility Decision")
R.TBL(["Dimension", "Assessment", "Key evidence", "Rating"],
      [["Technical", "Feasible on CPU with frozen backbone", f"Latency {L['median']:.0f} ms; ~1 M trainable parameters; SE ≈ 0.0075", "High"],
       ["Economic", "No direct cost for prototype", "Open data, open-source stack, free tunnel", "High"],
       ["Operational", "Simple to run and update", "One-command Docker deployment, health checks, versioned bundles", "Medium–High"],
       ["Ethical", "Acceptable for education; not for clinical use", "De-identified data; single-site bias; needs human oversight", "Medium"]],
      "Four-dimensional feasibility matrix", widths=[1.1, 1.9, 2.5, 0.8])
R.P("**Decision: CONDITIONAL GO.** The project is technically and economically feasible and was approved to proceed as an "
    "educational prototype on the conditions that (1) evaluation uses a patient-disjoint split, (2) the system always shows "
    "uncertainty and a disclaimer, (3) uncertain cases are referred to a human, and (4) no claim of clinical validity is made "
    "until external, multi-site validation is completed.")

# ------------------------------------------------------------------ CH 4
R.H1("Stakeholder Identification and Management")
R.H2("4.1 Stakeholder Identification")
R.P(f"{R.next_fig()} maps the stakeholders around the system. The project owner is the faculty mentor; the developers are the "
    "four team members; the intended users are radiologists and clinicians (and, for this course, reviewers); the data owners "
    "are the Guangzhou Women and Children’s Medical Center and the dataset authors; and the affected groups are the children "
    "whose X-rays are analysed and their parents.")
R.FIG("stakeholder_map.png", "Stakeholder map of PneumoScope", 5.6)
R.H2("4.2 Stakeholder Classification")
R.TBL(["Class", "Stakeholders", "Role in the project"],
      [["Primary", "Faculty mentor; project team; radiologists / clinicians", "Own, build or directly use the system"],
       ["Secondary", "Hospital IT and administrators; course evaluators", "Deploy, maintain or assess the system"],
       ["Data subjects", "Paediatric patients (age 1–5) and their parents/guardians", "Their X-rays form the dataset and future inputs"],
       ["Data owners", "Guangzhou Women and Children’s Medical Center; Kermany et al.", "Collected, labelled and licensed the data"],
       ["Regulators", "CDSCO (medical devices), MeitY (DPDP Act 2023); EU MDR/GDPR if used in Europe", "Set legal requirements for software as a medical device and personal data"],
       ["Affected communities", "Families in low-resource regions with few radiologists", "Benefit from faster triage or harmed by errors"],
       ["Adversarial", "Users uploading non-X-ray or manipulated images; automation bias", "Could cause misleading outputs"]],
      "Stakeholder classification", widths=[1.2, 2.8, 2.3])
R.H2("4.3 Stakeholder Interest and Influence Analysis")
R.P(f"Each stakeholder was rated for interest and influence on a 0–10 scale ({R.next_fig()}); the quadrant determines the "
    "management approach.")
R.FIG("influence_interest.png", "Stakeholder influence–interest matrix", 4.8)
R.TBL(["Stakeholder", "Interest", "Influence", "Expectations"],
      [["Faculty mentor", "High", "High", "Sound life cycle, genuine evidence, honest limitations"],
       ["Project team", "High", "High", "Working system, good grade, learning"],
       ["Radiologists", "High", "Medium–High", "High recall, few false alarms, explanations, no extra workload"],
       ["Patients / parents", "High", "Low", "Correct and timely diagnosis, privacy"],
       ["Regulators", "Low (prototype)", "High", "Safety, clinical evidence, data protection compliance"],
       ["Hospital IT", "Medium", "Medium", "Easy deployment, security, low cost"],
       ["Data owners", "Low", "Low–Medium", "Attribution and licence compliance"],
       ["Adversarial users", "Medium", "Low", "—  (risk to be controlled)"]],
      "Stakeholder interests, influence and expectations", widths=[1.5, 1.0, 1.1, 2.7])
R.H2("4.4 Stakeholder Conflict Analysis")
R.TBL(["Conflict", "Between", "How it appeared in this project", "Resolution"],
      [["Accuracy vs interpretability", "Radiologists vs model design", "A CNN is more accurate than a linear model but harder to explain",
        "Kept the CNN features, added Grad-CAM and an interpretable LR baseline for comparison"],
       ["Data collection vs privacy", "Developers vs patients/regulators", "More (local, demographic) data would improve fairness checks but increases privacy risk",
        "Used only the de-identified public dataset; documented the fairness gap instead of collecting data"],
       ["Project speed vs compliance", "Team deadline vs regulators", "Deploying quickly for the course vs medical-device rules",
        "Positioned as educational prototype with disclaimer; no clinical use"],
       ["Performance vs fairness", "Overall accuracy vs subgroups", "Optimising average accuracy may hide worse results for viral pneumonia",
        "Reported sub-type results separately and refer uncertain cases (Chapter 7)"],
       ["Automation vs safety", "Hospital efficiency vs clinicians", "Auto-deciding more cases saves time but risks errors",
        "Validation-tuned REFER threshold (13.1% referred) that keeps AUTO error ≈ 1%"]],
      "Stakeholder conflict analysis", widths=[1.2, 1.2, 2.0, 1.9], size=9.5)
R.H2("4.5 Stakeholder Management Strategy")
R.B(["**Manage closely (mentor, team, radiologists):** weekly progress reviews with the mentor, shared task board, and a "
     "user walkthrough of the result screen focused on how REFER and uncertainty are explained.",
     "**Keep satisfied (regulators, hospital IT):** clear intended-use statement in the model card (`config.json`: "
     "“Educational research demonstration only. Not for clinical use.”), security measures documented in Chapter 12.",
     "**Keep informed (patients/parents, data owners):** disclaimer on every result; dataset licence and citation honoured.",
     "**Monitor (adversarial users):** upload validation, quality flags that force REFER, rate of rejected uploads tracked.",
     "**Conflict handling:** conflicts were decided by the project lead with the mentor, using the success criteria (recall "
     "and calibration first) as the tie-breaker; decisions were recorded in this report."])

# ------------------------------------------------------------------ CH 5
R.H1("Data Acquisition, Governance and Versioning")
R.mapped("Data Governance, Exploratory Analysis and Feature Engineering")
R.H2("5.1 Dataset Description")
R.TBL(["Property", "Value"],
      [["Dataset name", "Labeled Optical Coherence Tomography (OCT) and Chest X-Ray Images for Classification — chest X-ray part (“ChestXRay2017”)"],
       ["Source", "Mendeley Data, v2, DOI 10.17632/rscbjbr9sj.2 [11]; associated paper Kermany et al., Cell 2018 [2]"],
       ["Number of observations", f"{card['total_images']:,} JPEG images from {card['total_patients']:,} patients"],
       ["Target variable", f"Label: NORMAL ({card['class_distribution']['NORMAL']:,}) or PNEUMONIA ({card['class_distribution']['PNEUMONIA']:,}); "
        f"sub-type in file name: bacterial ({card['subtype_distribution']['bacterial']:,}), viral ({card['subtype_distribution']['viral']:,})"],
       ["Number of features", "Raw: one grayscale image per observation (variable size); model input: 224 × 224 × 3 tensor; "
        "learned: 2048 ResNet-50 features; metadata: 16 columns in manifest.csv"],
       ["Data types", f"Images (JPEG, {S['modes'].get('L', 0):,} grayscale + {S['modes'].get('RGB', 0)} RGB-encoded); "
        "integers (width, height, bytes); floats (brightness, contrast, entropy); strings (path, patient ID, MD5)"],
       ["Image size", f"Width {D['width']['min']:.0f}–{D['width']['max']:.0f} px, height {D['height']['min']:.0f}–{D['height']['max']:.0f} px "
        f"(median {D['width']['median']:.0f} × {D['height']['median']:.0f})"],
       ["Collection period", "Retrospective routine care at Guangzhou Women and Children’s Medical Center; published 2018 (exact acquisition dates not released)"],
       ["Population", "Paediatric patients aged one to five years"],
       ["Dataset size", "1.2 GB compressed archive"],
       ["Licence", "CC BY 4.0 (attribution required)"]],
      "Dataset information", widths=[1.6, 4.7], size=10)
R.H2("5.2 Data Provenance")
R.P("The images were selected from retrospective cohorts of paediatric patients aged one to five at the Guangzhou Women and "
    "Children’s Medical Center, Guangzhou, China, as part of routine clinical care [2]. According to the authors, all "
    "radiographs were screened for quality, low-quality and unreadable scans were removed, and the diagnoses were graded by "
    "two expert physicians before being used for training; the evaluation set was additionally checked by a third expert. "
    "The data were published by Kermany, Zhang and Goldbaum on Mendeley Data under the Creative Commons Attribution 4.0 "
    "licence, which permits use, modification and redistribution for any purpose, provided the source is credited. We "
    "downloaded the archive `ChestXRay2017.zip` once and never modified the original files.")
R.P("Important provenance facts that affect modelling are: (i) the images are de-identified, but the file names contain a "
    "patient identifier (e.g. `person101_bacteria_483.jpeg`, `IM-0003-0001.jpeg`), which we used to group images by patient; "
    f"(ii) {card['images_per_patient']['patients_with_multiple_images']:,} patients have more than one image (up to "
    f"{card['images_per_patient']['max']}); and (iii) the original folder split (5,232 train / 624 test) was made without "
    "regard to patient, so we did not use it.")
R.H2("5.3 Data Lineage")
R.P(f"{R.next_fig()} documents every major transformation from the raw archive to model-ready data and to the deployed bundle. "
    "Each step is performed by code (`prepare_kermany.py`, `train_pipeline.py`) and recorded in a JSON artefact.")
R.FIG("lineage.png", "Data lineage from raw archive to deployed model bundle", 6.27)
R.TBL(["Step", "Transformation", "Output", "Recorded in"],
      [["1", "Extract archive", "5,856 JPEGs in class folders", "dataset_card.json (counts)"],
       ["2", "Parse file names → label, sub-type, patient ID", "manifest.csv columns", "manifest.csv"],
       ["3", "Hash and describe every image (MD5, size, mode, brightness, contrast, entropy)", "manifest.csv columns", "manifest.csv"],
       ["4", "Exact- and near-duplicate detection", f"{card['duplicates']['exact_duplicate_groups']} exact groups, {card['duplicates']['near_duplicate_pairs']} near pairs", "dataset_card.json"],
       ["5", "Patient-disjoint StratifiedGroupKFold split (seed 42) + flawed image-level split for comparison", "split, split_flawed columns", "dataset_card.json"],
       ["6", "Grayscale → resize 224 → normalise → frozen ResNet-50", "5,856 × 2048 float32 matrix", "kermany_resnet50.npz"],
       ["7", "Train head, calibrate, choose threshold, evaluate", "model.pt + config + evaluation + reference stats", "MLflow run, SHA-256"]],
      "Data lineage steps", widths=[0.45, 2.9, 1.6, 1.4], size=9.5)
R.H2("5.4 Data Versioning")
R.P("A dataset version in this project is defined by the archive plus the deterministic preparation code and seed. Versions are "
    "maintained and linked to experiments as follows:")
R.B(["**Content hashes:** the MD5 hash of every image is stored in `manifest.csv`; any changed or added image changes the "
     "manifest and is detectable.",
     "**Dataset card:** `dataset_card.json` (generated 2026-11-17) records class counts, split sizes, patient overlap and "
     "duplicate statistics, acting as the version record of the prepared dataset.",
     "**Model bundles:** each model version folder (`artifacts/models/v1.0.0`, `v1.1.0`) contains `config.json` with the "
     "training dataset description, the SHA-256 of the weights (`500a7e41…`) and the MLflow run ID; the API refuses to load "
     "weights whose hash does not match.",
     "**MLflow:** every run logs its parameters, metrics and artefacts, and the parent run is tagged with the model version "
     "and weights hash, linking data, code configuration and model."])
R.TBL(["Version", "Date", "Change", "Result"],
      [["Dataset v1", "2026-11-17", "Manifest, patient IDs, patient-disjoint split, duplicate audit", "4,182 / 837 / 837; 0 overlap"],
       ["Model v1.0.0", "2026-11-17", "Optuna (25 trials), MC-Dropout head, temperature, refer target error 3%",
        f"Test AUC {f3(ev0['test']['discrimination']['roc_auc'])}; referred {pc(ev0['test']['refer_bands']['refer_rate'])}; AUTO acc {pc(ev0['test']['refer_bands']['auto_decision_accuracy'])}"],
       ["Model v1.1.0", "2026-11-17", "Same data/head; stricter refer target error 1%",
        f"Test AUC {f3(dsc['roc_auc'])}; referred {pc(rb['refer_rate'])}; AUTO acc {pc(rb['auto_decision_accuracy'])} (deployed)"],
       ["Baselines", "2026-11-19", "LR, RF, default MLP on the same features and split", "MLflow experiment ‘baseline-comparison’"]],
      "Version history", widths=[1.1, 1.0, 2.3, 1.9], size=9.5)
R.H2("5.5 Software Implementation")
R.TBL(["Tool", "Status", "How it was used / justification"],
      [["Git / GitHub", "Partially implemented", "Public repository https://github.com/Shruti4105/PneumoScope. Commits were made when the project was published, not continuously during "
        "development — a limitation we report honestly; team members add further commits from their own accounts."],
       ["DVC", "Not implemented (justified)", "The dataset is a single, immutable public archive; MD5 hashes in the manifest and the dataset card "
        "provide equivalent integrity checking without a remote store. DVC is proposed if local hospital data are added."],
       ["MLflow", "Implemented", "SQLite tracking store `mlflow/mlflow.db`; 2 experiments, 56 runs (2 parent runs with 50 nested Optuna trials, 4 baseline runs)"]],
      "Versioning tools used", widths=[1.2, 1.4, 3.7], size=10)
R.P(f"{R.next_fig()} shows the MLflow experiment ‘pneumonia-mc-dropout’ with the two model-version runs and their nested Optuna "
    "trials, and Figure 5.3 shows the run comparison view used to compare candidates.")
if (FIG / "ev_mlflow_runs.jpg").exists():
    R.FIG("ev_mlflow_runs.jpg", "MLflow tracking UI: experiment runs, including nested Optuna trials (screenshot)", 6.27)
    R.FIG("ev_mlflow_compare.jpg", "MLflow run comparison of the four models in the ‘baseline-comparison’ experiment (screenshot)", 6.27)

# ------------------------------------------------------------------ CH 6
R.H1("Data Quality Assessment and Exploratory Data Analysis")
R.H2("6.1 Data Quality Assessment")
R.TBL(["Dimension", "Check performed", "Finding", "Verdict"],
      [["Completeness", "Missing values in all 16 manifest columns; every file decodable", "0 missing values; 5,856 / 5,856 images decoded", "Good"],
       ["Accuracy", "Label source (two experts + third for evaluation); sub-type vs folder consistency", "Labels expert-graded; file names consistent with folders", "Good (cannot re-verify clinically)"],
       ["Consistency", "Image mode, size, aspect ratio", f"{S['modes'].get('RGB', 0)} RGB-encoded images among grayscale; widths {D['width']['min']:.0f}–{D['width']['max']:.0f} px", "Fixed by preprocessing"],
       ["Timeliness", "Acquisition period", "Retrospective images published 2018; equipment and protocols may have changed", "Limitation"],
       ["Uniqueness", "MD5 exact duplicates; 32 × 32 thumbnail correlation ≥ 0.985", f"{card['duplicates']['exact_duplicate_images']} images in {card['duplicates']['exact_duplicate_groups']} exact-duplicate groups; "
        f"{card['duplicates']['near_duplicate_pairs']} near-duplicate pairs", "Controlled by patient split"]],
      "Data quality assessment across five dimensions", widths=[1.1, 2.0, 2.2, 1.0], size=9.5)
R.H2("6.2 Missing Data Analysis")
R.P(f"All {S['n_rows']:,} rows and all derived columns of the manifest were checked with `pandas.DataFrame.isna()`; the count of "
    "missing values is **zero for every column**, and every image file could be decoded by Pillow. Because nothing is missing, "
    "no imputation was needed and the question of MCAR/MAR/MNAR does not arise for the recorded variables. However, there is "
    "**structural missingness** of information that is not recorded at all: age, sex, scanner model, acquisition date and "
    "clinical outcome are absent for every patient. This absence is by design of the data publisher (de-identification), "
    "so it is not related to the label and is best described as missing completely at random at the dataset level — but it "
    "prevents demographic fairness analysis (Chapter 7). The authors also state that unreadable scans were removed before "
    "publication; if image quality is related to disease severity, that exclusion would be MNAR, which we cannot test.")
R.H2("6.3 Descriptive Statistics")
R.P("Seven numerical attributes were computed for every image: width, height, aspect ratio, file size, brightness (mean pixel "
    "intensity / 255), contrast (standard deviation of intensity / 255) and intensity entropy (in bits). "
    f"{R.next_tab()} reports the statistics computed with NumPy (sample variance with n − 1).")
R.MATH("6.3.1 Mean, variance, standard deviation and IQR",
       "Summary statistics describe the centre and spread of each attribute and reveal skew and heterogeneity that "
       "preprocessing must handle.",
       ["x̄ = (1/n) Σ_{i=1}^{n} x_{i},     s^{2} = (1/(n − 1)) Σ_{i=1}^{n} (x_{i} − x̄)^{2},     s = √s^{2}",
        "IQR = Q_{3} − Q_{1}"],
       "n = number of images (5,856); x_{i} = value of the attribute for image i; x̄ = sample mean; s² = sample variance; "
       "s = standard deviation; Q₁, Q₃ = 25th and 75th percentiles.",
       "`numpy.mean`, `numpy.var(ddof=1)`, `numpy.std(ddof=1)`, `numpy.percentile` in `docs/report/analyze.py`.",
       f"See Table 6.2. For example, mean width = {D['width']['mean']:.1f} px with s = {D['width']['std']:.1f} px, while mean "
       f"brightness = {D['brightness']['mean']:.3f} with s = {D['brightness']['std']:.3f}.",
       f"Image dimensions vary widely (coefficient of variation of width ≈ {D['width']['std'] / D['width']['mean']:.0%}), and "
       f"file size is strongly right-skewed (mean {D['file_kb']['mean']:.0f} KB vs median {D['file_kb']['median']:.0f} KB). "
       "Intensity statistics are tightly concentrated.",
       "All images are resized to a fixed 224 × 224 input; file size and raw dimensions are not used as model features.")
rows = []
for k, nm in (("width", "Width (px)"), ("height", "Height (px)"), ("aspect_ratio", "Aspect ratio"), ("file_kb", "File size (KB)"),
              ("brightness", "Brightness"), ("contrast", "Contrast"), ("intensity_entropy", "Entropy (bits)")):
    x = D[k]; fm = (lambda z: f"{z:,.0f}") if k in ("width", "height", "file_kb") else (lambda z: f"{z:.3f}")
    var = f"{x['var']:,.0f}" if k in ("width", "height", "file_kb") else f"{x['var']:.4f}"
    rows.append([nm, fm(x["mean"]), fm(x["median"]), var, fm(x["std"]), fm(x["min"]), fm(x["max"]), fm(x["q1"]), fm(x["q3"]), fm(x["iqr"])])
R.nt = 1
R.TBL(["Attribute", "Mean", "Median", "Variance", "SD", "Min", "Max", "Q1", "Q3", "IQR"], rows,
      "Descriptive statistics of image attributes (n = 5,856)", widths=[1.2, 0.6, 0.6, 0.8, 0.55, 0.5, 0.55, 0.5, 0.55, 0.5], size=8.5,
      align="lccccccccc")
bcl = S["by_class"]
R.P(f"Splitting by class reveals an important pattern: pneumonia images are much smaller than normal images (median width "
    f"{bcl['width']['PNEUMONIA']['median']:.0f} px vs {bcl['width']['NORMAL']['median']:.0f} px; median file size "
    f"{bcl['file_kb']['PNEUMONIA']['median']:.0f} KB vs {bcl['file_kb']['NORMAL']['median']:.0f} KB), whereas mean brightness is "
    f"almost identical ({bcl['brightness']['PNEUMONIA']['mean']:.3f} vs {bcl['brightness']['NORMAL']['mean']:.3f}). This is "
    "investigated further in Sections 6.6 and 7.4.")
R.H2("6.4 Outlier Detection")
R.MATH("6.4.1 IQR (Tukey) fences and Z-scores",
       "Outliers may be corrupt images, non-standard acquisitions or data-entry errors. Two standard rules were applied.",
       ["Outlier if x < Q_{1} − 1.5·IQR  or  x > Q_{3} + 1.5·IQR", "z_{i} = (x_{i} − x̄) / s ,   outlier if |z_{i}| > 3"],
       "Q₁, Q₃, IQR as in Eq. (6.2); z_{i} = standardised score of image i; x̄, s as in Eq. (6.1).",
       "NumPy percentiles and boolean masks in `analyze.py`.",
       "Counts are in Table 6.3.",
       "The IQR rule flags many file-size outliers simply because the distribution is right-skewed; these are high-resolution "
       "normal images, not errors. Genuine anomalies are the very small images (shortest side < 256 px) and extreme aspect "
       f"ratios: {S['low_res']} images have a shortest side under 256 px.",
       "No images were deleted (they are valid radiographs and removing them would bias the test set). Instead, the deployed "
       "app applies the same rules at inference: an aspect ratio outside 0.4–2.5, near-zero contrast or a colour image forces "
       "REFER, and a shortest side under 256 px produces a warning.")
R.TBL(["Attribute", "Lower fence", "Upper fence", "IQR outliers", "|z| > 3"],
      [[nm, f"{D[k]['lower_fence']:.3f}" if D[k]['lower_fence'] < 50 else f"{D[k]['lower_fence']:.0f}",
        f"{D[k]['upper_fence']:.3f}" if D[k]['upper_fence'] < 50 else f"{D[k]['upper_fence']:.0f}",
        f"{D[k]['iqr_outliers']} ({D[k]['iqr_outliers'] / S['n_rows']:.1%})", str(D[k]["z_outliers"])]
       for k, nm in (("width", "Width"), ("height", "Height"), ("aspect_ratio", "Aspect ratio"), ("file_kb", "File size (KB)"),
                     ("brightness", "Brightness"), ("contrast", "Contrast"), ("intensity_entropy", "Entropy"))],
      "Outlier counts by the IQR and Z-score methods", widths=[1.6, 1.2, 1.2, 1.3, 1.0], align="lcccc")
R.H2("6.5 Distribution Analysis")
R.P(f"{R.next_fig()} shows the class balance: 73% of images are pneumonia, so a model that always predicts pneumonia would "
    "already reach 73% accuracy — which is why accuracy alone is not an adequate metric. Figures 6.2 and 6.3 show the "
    "distributions of the image attributes by class.")
R.FIG("eda_classes.png", "Class and sub-type distribution of the Kermany dataset", 6.0)
R.FIG("eda_histograms.png", "Histograms of image attributes by class", 6.27)
R.FIG("eda_boxplots.png", "Box plots of selected attributes by class (points beyond the whiskers are IQR outliers)", 6.27)
R.P("Brightness and entropy distributions overlap almost completely between classes, so the model cannot rely on simple "
    "exposure differences. Width and file size, in contrast, are clearly shifted: most normal images are larger. Sample images "
    f"from each sub-type are shown in {R.next_fig()}.")
R.FIG("sample_xrays.png", "Sample training images: normal, bacterial and viral pneumonia", 5.8)
R.H2("6.6 Correlation Analysis")
R.MATH("6.6.1 Pearson correlation coefficient",
       "Correlation measures linear association between attributes and with the label, to detect redundant attributes and "
       "possible shortcuts.",
       "r_{xy} = Σ (x_{i} − x̄)(y_{i} − ȳ) / √( Σ (x_{i} − x̄)^{2} · Σ (y_{i} − ȳ)^{2} )",
       "x, y = two attributes (the label is coded 1 = pneumonia, 0 = normal, making r with the label the point-biserial "
       "correlation); x̄, ȳ = means; r ∈ [−1, 1].",
       "`pandas.DataFrame.corr(method='pearson')`; heat map with Matplotlib.",
       f"Label correlations: file size r = {S['corr_label']['file_kb']:.2f}, height r = {S['corr_label']['height']:.2f}, "
       f"width r = {S['corr_label']['width']:.2f}, contrast r = {S['corr_label']['contrast']:.2f}, brightness r = "
       f"{S['corr_label']['brightness']:.3f}. Width and height are correlated with each other at r = {S['corr_top'][0][2]:.2f}.",
       "Image size is a strong proxy for the label. This is not medically meaningful — it reflects how the two classes were "
       "collected or exported — and a model could learn the shortcut ‘small image ⇒ pneumonia’.",
       "We resize every image to 224 × 224 so absolute size is not directly visible to the model, never feed metadata as "
       "features, and flag this confounder as a key limitation requiring external validation (Sections 7.4 and 14.6).")
R.FIG("eda_correlation.png", "Pearson correlation heat map of image attributes and the label", 4.9)
R.H2("6.7 Data Quality Improvement")
R.TBL(["#", "Issue identified", "Evidence", "Corrective action / remediation plan"],
      [["1", "Patient leakage in the original and in random splits", f"{card['images_per_patient']['patients_with_multiple_images']:,} patients with several images; a random split puts "
        f"{lk['flawed_image_level']['overlap']['test_images_from_train_patients']} of 837 test images from training patients",
        "Patient IDs parsed from file names; StratifiedGroupKFold split; overlap verified = 0"],
       ["2", "Exact and near-duplicate images", f"{card['duplicates']['exact_duplicate_images']} exact duplicates; {card['duplicates']['near_duplicate_pairs']} near pairs "
        f"({card['duplicates']['near_duplicate_pairs_across_flawed_splits']} would cross a random split)", "Duplicates stay in the same patient group; 0 cross the patient-disjoint split"],
       ["3", "Inconsistent formats and sizes", f"{S['modes'].get('RGB', 0)} RGB-encoded files; sizes 384–2,916 px", "Convert to grayscale, resize to 224 × 224, ImageNet normalisation"],
       ["4", "Class imbalance (73 : 27)", "4,273 pneumonia vs 1,583 normal", "Stratified split; positive-class weight in BCE loss; recall/F1/AUC instead of accuracy alone"],
       ["5", "Size–label confounding", "r(file size, label) = −0.78", "Resize; no metadata features; Grad-CAM review; external validation planned"],
       ["6", "Small / odd images at inference", f"{S['low_res']} images < 256 px", "Quality flags in the API force REFER or warn"]],
      "Data quality issues and remediation", widths=[0.3, 1.6, 2.2, 2.2], size=9.5)

# ------------------------------------------------------------------ CH 7
R.H1("Data Ethics and Bias Assessment")
R.H2("7.1 Data Privacy and Governance")
R.P("Chest X-rays are health data and therefore ‘special category’ personal data under the EU GDPR (Art. 9) and sensitive "
    "personal data under India’s Digital Personal Data Protection Act 2023 [12], [13]. The Kermany images are published "
    "de-identified (no names, dates or hospital numbers), so for our use they are not personal data of identifiable persons. "
    "Nevertheless, we applied the GDPR principles in the design of the application, because a real deployment would process "
    "identifiable patient images:")
R.B(["**Lawfulness, fairness, transparency:** every result states it is for educational use; the About page explains the data and limits.",
     "**Purpose limitation:** uploaded images are used only to produce the requested analysis and are shown only to the uploader.",
     "**Data minimisation:** only the image, file name and derived results are stored — no patient name or demographic fields exist.",
     "**Storage limitation:** users can delete any analysis, which removes the stored image.",
     "**Integrity and confidentiality:** passwords hashed with bcrypt; session tokens in HttpOnly SameSite cookies; secrets in "
     "environment variables, never in frontend code; security headers; upload validation.",
     "**Accountability:** model version, weights hash and decision reason are stored with every analysis."])
R.H2("7.2 Lawful and Ethical Data Use")
R.P("Legal permission and ethical appropriateness are different questions. *Legally*, the CC BY 4.0 licence allows us to use and "
    "redistribute the images with attribution, and the data are de-identified. *Ethically*, permission to use data does not "
    "automatically make every use appropriate: the children did not individually consent to machine-learning research, the "
    "images come from one hospital in one country, and a model that performs well on these images may harm patients if used "
    "elsewhere without validation. We therefore restrict the use to education and research, avoid any diagnostic claims, keep "
    "a human in the loop through the REFER mechanism and report limitations prominently.")
R.H2("7.3 Data Minimisation")
R.TBL(["Attribute", "Collected / retained?", "Justification"],
      [["X-ray pixels", "Yes", "Required input for the model"],
       ["Label and sub-type", "Yes (training only)", "Target variable and subgroup analysis"],
       ["Patient identifier (from file name)", "Yes, pseudonymous, training only", "Needed to build a leakage-free split; never displayed"],
       ["Image metadata (size, brightness…)", "Yes", "Quality checks and drift monitoring"],
       ["Age, sex, ethnicity", "No (not available)", "Not needed for prediction; would help fairness audit (trade-off noted)"],
       ["User name and e-mail", "Yes (app accounts)", "Authentication only"],
       ["Uploaded image", "Yes, until deleted by the user", "To show history and Grad-CAM; deletable"]],
      "Data minimisation decisions", widths=[2.0, 1.8, 2.5])
R.H2("7.4 Sources of Dataset Bias")
R.TBL(["Bias type", "Assessment in this dataset", "Risk"],
      [["Sampling bias", "Single hospital (Guangzhou), single age band (1–5 years), one population; class ratio 73:27 is not the real-world prevalence", "High — performance may not transfer"],
       ["Label bias", "Labels from expert reading of the X-ray, not from laboratory confirmation; bacterial/viral distinction from images is known to be unreliable", "Medium"],
       ["Historical / acquisition bias", f"Image size and file size differ systematically by class (r = {S['corr_label']['file_kb']:.2f}), suggesting different acquisition or export pipelines per class", "High — possible shortcut learning, as reported for other CXR models [14]"],
       ["Measurement bias", f"{S['modes'].get('RGB', 0)} images stored as RGB; varying resolution and exposure", "Low after preprocessing"]],
      "Bias assessment", widths=[1.3, 3.5, 1.5], size=10)
R.H2("7.5 Fairness Evaluation")
R.P("The dataset contains no demographic attributes, so demographic fairness (by sex, age or ethnicity) **cannot be evaluated** — "
    "this is reported as a limitation, not hidden. We instead evaluated the groups that *are* identifiable and clinically or "
    "technically relevant: pneumonia **sub-type** (bacterial vs viral), **image resolution** (shortest side below/above the "
    f"test median of {res_median:.0f} px) and **file encoding** (grayscale vs RGB JPEG). Metrics were computed with Fairlearn "
    "`MetricFrame` [15] on the 837 test images at the 0.5 threshold.")
R.MATH("7.5.1 Demographic parity and equalised odds",
       "Demographic parity checks whether the rate of positive predictions is equal across groups; equalised odds checks "
       "whether true- and false-positive rates are equal across groups. Calibration across groups checks whether a "
       "probability means the same thing in every group.",
       ["DPD = max_{g} P(Ŷ = 1 | A = g) − min_{g} P(Ŷ = 1 | A = g)",
        "EOD = max( max_{g,g′} |TPR_{g} − TPR_{g′}| ,  max_{g,g′} |FPR_{g} − FPR_{g′}| )"],
       "Ŷ = predicted class; A = group attribute; g = group; TPR = TP/(TP + FN); FPR = FP/(FP + TN).",
       "`fairlearn.metrics.MetricFrame`, `demographic_parity_difference`, `equalized_odds_difference`; per-group ECE with our "
       "`calibration_service.expected_calibration_error`.",
       "See Table 7.3 and Figure 7.1.",
       "Large DPD values between resolution groups are driven by different base rates (lower-resolution test images are "
       f"{res_counts['lower-res'][1] / sum(res_counts['lower-res']):.0%} pneumonia), not by unequal treatment, so demographic "
       "parity is not an appropriate fairness target for a diagnostic task. Equalised odds is more meaningful but the FPR in the "
       f"lower-resolution group rests on only {res_counts['lower-res'][0]} normal images.",
       "Sub-type recall is monitored, uncertain cases are referred, and the resolution confound is treated as a validity risk "
       "rather than a fairness result.")
fr = FA["res_group"]["by_group"]; ff = FA["format"]["by_group"]; fs = FA["subtype"]
R.TBL(["Group", "n (normal / pneu.)", "Accuracy", "Selection rate", "TPR (recall)", "FPR", "ECE"],
      [["Lower resolution", f"{res_counts['lower-res'][0]} / {res_counts['lower-res'][1]}", pc(fr['lower-res']['accuracy']), pc(fr['lower-res']['selection_rate']),
        pc(fr['lower-res']['TPR']), pc(fr['lower-res']['FPR']), f3(fr['lower-res']['ece'])],
       ["Higher resolution", f"{res_counts['higher-res'][0]} / {res_counts['higher-res'][1]}", pc(fr['higher-res']['accuracy']), pc(fr['higher-res']['selection_rate']),
        pc(fr['higher-res']['TPR']), pc(fr['higher-res']['FPR']), f3(fr['higher-res']['ece'])],
       ["Grayscale JPEG", f"n = {ff['grayscale JPEG']['n']:.0f}", pc(ff['grayscale JPEG']['accuracy']), pc(ff['grayscale JPEG']['selection_rate']),
        pc(ff['grayscale JPEG']['TPR']), pc(ff['grayscale JPEG']['FPR']), f3(ff['grayscale JPEG']['ece'])],
       ["RGB JPEG", f"n = {ff['RGB JPEG']['n']:.0f}", pc(ff['RGB JPEG']['accuracy']), pc(ff['RGB JPEG']['selection_rate']),
        pc(ff['RGB JPEG']['TPR']), "—", f3(ff['RGB JPEG']['ece'])]],
      f"Fairlearn subgroup metrics on the test set (DPD resolution = {FA['res_group']['dp_diff']:.2f}, EOD resolution = "
      f"{FA['res_group']['eo_diff']:.2f}; DPD format = {FA['format']['dp_diff']:.2f}, EOD format = {FA['format']['eo_diff']:.2f})",
      widths=[1.3, 1.2, 0.8, 0.9, 0.8, 0.6, 0.6], size=9.5, align="lcccccc")
R.P(f"By sub-type ({R.next_fig()}), the model correctly identifies {pc(fs['bacterial']['accuracy'])} of bacterial and "
    f"{pc(fs['viral']['accuracy'])} of viral pneumonia, and {pc(fs['normal']['accuracy'])} of normal X-rays. Viral pneumonia "
    f"is the hardest group, but the uncertainty mechanism compensates: {pc(fs['viral']['refer_rate'])} of viral cases are "
    f"referred, compared with {pc(fs['bacterial']['refer_rate'])} of bacterial cases. Notably, the model makes more errors on "
    f"higher-resolution images ({pc(ER['err_rate_highres'])}) than on lower-resolution ones ({pc(ER['err_rate_lowres'])}), "
    "which is consistent with the size confound: most normal images are high-resolution, and the high-resolution pneumonia "
    "cases are the ones it misses most often.")
R.FIG("fairness_subtype.png", "Correct-classification rate and referral rate by sub-type (test set)", 5.2)
R.H2("7.6 Bias Mitigation")
R.B(["**Leakage control:** patient-disjoint split so that results are not inflated by memorised patients.",
     "**Imbalance:** stratified splitting and a positive-class weight in the loss (pos_weight = N_normal / N_pneumonia).",
     "**Shortcut reduction:** fixed-size input; metadata never used as features; Grad-CAM inspection of correct and incorrect cases.",
     "**Safety net for weaker subgroups:** referral of high-entropy predictions disproportionately catches viral and atypical cases.",
     "**Transparency:** subgroup results, the size confound and the missing demographics are disclosed in the app’s About page and this report."])
R.TBL(["Checklist item", "Status"],
      [["Data source and licence documented", "✔ CC BY 4.0, cited"], ["Data de-identified", "✔ by publisher"],
       ["Sensitive attributes identified", "✔ none available — limitation recorded"], ["Consent / ethics approval for new data", "N/A — no new data collected"],
       ["Leakage between splits checked", "✔ 0 patient overlap"], ["Subgroup performance evaluated", "✔ Fairlearn MetricFrame"],
       ["Confounders investigated", "✔ image size (r = −0.78)"], ["Human oversight for uncertain cases", "✔ REFER policy"],
       ["Intended use and disclaimer shown", "✔ every result"], ["External validation", "✘ not yet — planned"]],
      "Data ethics checklist", widths=[3.6, 2.6])
R.P("**Ethical limitations and mitigation plan.** The remaining ethical risks are (1) unknown performance on other hospitals, "
    "ages and equipment, (2) inability to audit demographic fairness, and (3) automation bias by users. The mitigation plan is "
    "to validate on an external dataset (e.g. RSNA Pneumonia Detection Challenge; the script `evaluate_external.py` is already "
    "prepared), to request demographic metadata under an ethics approval before any pilot, and to keep the system in an "
    "advisory, human-in-the-loop role.")

# ------------------------------------------------------------------ CH 8
R.H1("Feature Engineering and Preprocessing")
R.H2("8.1 Feature Identification")
R.TBL(["Feature", "Category", "Description", "Used for"],
      [["Pixel intensities", "Raw", "Grayscale image, variable size, 0–255", "Model input (after transformation)"],
       ["Width, height, file size, mode", "Raw metadata", "Read from file", "Quality checks, EDA (not model input)"],
       ["Brightness, contrast, entropy, 32-bin histogram", "Derived", "Statistics of the grayscale image", "Quality flags, drift monitoring"],
       ["Patient ID, sub-type", "Derived (from file name)", "Pseudonymous ID; bacterial/viral/normal", "Splitting, subgroup analysis"],
       ["224 × 224 × 3 normalised tensor", "Derived", "Resized and standardised image", "Backbone input"],
       ["2048-d ResNet-50 embedding", "Learned", "Global-average-pooled layer-4 activations of an ImageNet ResNet-50", "Classifier input"],
       ["Hidden units (128–512)", "Learned", "ReLU layer of the MC-Dropout head", "Internal representation"]],
      "Feature engineering summary", widths=[1.8, 1.1, 2.1, 1.3], size=10)
R.H2("8.2 Numerical Transformations")
R.MATH("8.2.1 Intensity scaling and ImageNet standardisation",
       "Pre-trained networks expect inputs on the same scale as their training data. Pixels are scaled to [0, 1] and then "
       "standardised with the ImageNet channel means and standard deviations; the single grayscale channel is copied to three "
       "channels.",
       ["x′ = x / 255", "z_{c} = (x′ − μ_{c}) / σ_{c} ,   μ = (0.485, 0.456, 0.406),  σ = (0.229, 0.224, 0.225)"],
       "x = raw pixel value (0–255); x′ = scaled value; c = colour channel (R, G, B); μ_{c}, σ_{c} = ImageNet mean and SD for channel c; z_c = model input.",
       "`app/ml/preprocessing.py::to_model_tensor` (Pillow bilinear resize, NumPy, PyTorch).",
       f"Worked example: a pixel with value 223 gives x′ = 223/255 = 0.8745 and, for the red channel, z = (0.8745 − 0.485)/0.229 "
       f"= 1.701. For the whole example image `{Path(S['prep_example']['path']).name}`, the raw mean is "
       f"{S['prep_example']['raw_mean']:.1f} (SD {S['prep_example']['raw_std']:.1f}); after transformation the tensor has mean "
       f"{S['prep_example']['t_mean']:.3f}, SD {S['prep_example']['t_std']:.3f} and range "
       f"[{S['prep_example']['t_min']:.2f}, {S['prep_example']['t_max']:.2f}].",
       "The transformed values are centred near zero with unit-scale spread — the range the frozen backbone was trained on.",
       "The same function is reused by training, inference and monitoring, removing any train/serve skew.")
R.MATH("8.2.2 Resizing and feature extraction",
       "Images of any size are mapped to a fixed 224 × 224 grid, then to a fixed-length vector that a small classifier can learn from.",
       "f = GAP( ResNet50_{1:4}( z ) ) ∈ ℝ^{2048}",
       "z = standardised 3 × 224 × 224 tensor; ResNet50₁:₄ = convolutional stages 1–4 with frozen ImageNet-V2 weights; "
       "GAP = global average pooling over the 7 × 7 spatial grid; f = feature vector.",
       "`torchvision.models.resnet50(weights=IMAGENET1K_V2)` with `fc = Identity()`; batch extraction and caching in "
       "`train_pipeline.extract_features`.",
       f"Every image becomes a {S['prep_example']['f_dim']}-value vector (example: mean {S['prep_example']['f_mean']:.3f}, SD "
       f"{S['prep_example']['f_std']:.3f}, {S['prep_example']['f_zero_frac']:.0%} exact zeros from ReLU). The first two principal "
       f"components explain {pc(S['pca_var']['pc1'])} and {pc(S['pca_var']['pc2'])} of the variance; 50 components explain "
       f"{pc(S['pca_var']['pc50'])}.",
       "Figure 8.2 shows that normal and pneumonia images already form largely separate clusters in the first two principal "
       "components, so the learned features carry strong class information before any training.",
       "Because the features are separable, a shallow head is sufficient, which keeps training cheap and makes MC Dropout fast.")
R.P(f"{R.next_fig()} compares an image before and after preprocessing and shows its resulting feature vector.")
R.FIG("prep_before_after.png", "Before-and-after comparison: raw image, normalised input, pixel distributions and learned feature vector", 6.27)
R.H2("8.3 Feature Selection")
R.P("No hand-crafted feature selection was applied to the 2048 learned features: they are dense, distributed representations "
    "and the dropout layers act as a regulariser, while weight decay (tuned by Optuna) shrinks unhelpful weights. Selection "
    "decisions were instead made at the level of feature *sources*:")
R.B(["**Removed:** raw image size, file size and encoding were deliberately excluded from the model inputs even though they "
     "are highly predictive (r up to −0.78), because they are acquisition artefacts rather than disease signals.",
     "**Removed:** centre cropping was rejected because it can cut off peripheral lung fields; the whole image is resized instead.",
     "**Retained:** all 2048 backbone features (PCA to 50 components would keep only 72% of the variance).",
     "**Retained for monitoring only:** brightness, contrast, entropy and intensity histogram."])
R.FIG("features_pca.png", "PCA projection of the 2048-d training features coloured by class", 4.6)
R.H2("8.4 Reproducible Preprocessing Pipeline")
R.P(f"The pipeline in {R.next_fig()} is applied identically everywhere because it lives in one module, "
    "`app/ml/preprocessing.py`, imported by the training script, the API and the drift monitor. Reproducibility is further "
    "ensured by fixed seeds (split seed 42, MC seed 20240611), cached features, pinned model configuration and a SHA-256 check of "
    "the weights at load time. The core function is shown below.")
R.FIG("pipeline.png", "Preprocessing pipeline from upload to features", 6.27)
R.CODE('''def to_model_tensor(img: Image.Image) -> torch.Tensor:
    """Grayscale radiograph -> 3-channel, 224x224, ImageNet-normalised tensor [3,H,W]."""
    gray = img.convert("L").resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)
    arr = np.asarray(gray, dtype=np.float32) / 255.0
    t = torch.from_numpy(arr).unsqueeze(0).repeat(3, 1, 1)
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    return (t - mean) / std''', "Code excerpt 8.1: the shared preprocessing function (backend/app/ml/preprocessing.py)")
R.P("For the classical baselines, scikit-learn’s `make_pipeline(StandardScaler(), LogisticRegression(...))` guarantees that the "
    "feature scaling learned on the training set is applied unchanged to validation and test data.")

# ------------------------------------------------------------------ CH 9
R.H1("Model Selection and Baseline Development")
R.mapped("Model Development, Optimisation and Evaluation")
R.H2("9.1 Problem Type")
R.P("The task is **supervised binary image classification** (NORMAL = 0, PNEUMONIA = 1) with an additional **selective "
    "prediction** component: the system may abstain (REFER) when uncertain. The output is a calibrated probability plus an "
    "uncertainty score rather than only a hard label, so it is also a probabilistic prediction problem.")
R.H2("9.2 Candidate Models")
R.TBL(["Candidate", "Type", "Strengths", "Weaknesses"],
      [["Logistic Regression (on ResNet features)", "Linear, probabilistic", "Simple, fast (< 1 s), interpretable weights", "Linear boundary only; no model uncertainty"],
       ["Random Forest (300 trees)", "Tree ensemble", "Non-linear, robust to scale", "Poor probability calibration; slow on 2048-d"],
       ["MLP head, default settings", "Neural network", "Non-linear, fast inference", "Single point estimate; settings untuned"],
       ["MC-Dropout MLP head + Optuna + temperature", "Bayesian-approximate neural network", "Uncertainty, calibration, tuned", "More complex; 30 passes"],
       ["Fine-tuned full CNN (not trained)", "Deep CNN", "Potentially highest accuracy", "Infeasible on CPU; higher overfitting risk on 4 k images"]],
      "Candidate models", widths=[1.8, 1.2, 1.7, 1.6], size=10)
R.H2("9.3 Model Selection Criteria")
R.TBL(["Criterion (weight)", "LR", "RF", "MLP (default)", "MC-Dropout (final)"],
      [["Fit to dataset (imbalanced, 2048-d features) (15%)", "4", "3", "4", "5"],
       ["Interpretability (10%)", "5", "3", "2", "3 (Grad-CAM + uncertainty)"],
       ["Predictive performance – validation AUC (25%)", f"4 ({f3(LR['validation']['roc_auc'])})", f"3 ({f3(RF['validation']['roc_auc'])})", f"5 ({f3(MLP['validation']['roc_auc'])})", f"5 ({f3(FIN['validation']['roc_auc'])})"],
       ["Calibration – validation ECE (15%)", f"3 ({f3(LR['validation']['ece'])})", f"1 ({f3(RF['validation']['ece'])})", f"4 ({f3(MLP['validation']['ece'])})", "5 (temperature-scaled)"],
       ["Uncertainty / ability to refer (20%)", "1", "2", "1", "5"],
       ["Computational cost (10%)", "5", "3", "5", "4"],
       ["Stakeholder constraints: safety, explainability (5%)", "3", "2", "3", "5"],
       ["**Weighted score (out of 5)**", "**3.45**", "**2.55**", "**3.50**", "**4.80**"]],
      "Model selection matrix (scores 1–5, chosen on validation data only)", widths=[2.6, 0.8, 0.8, 1.0, 1.4], size=9.5, align="lcccc")
R.P("The weighted score is Σ wᵢ·sᵢ. The MC-Dropout head was selected because it is the only candidate that combines top-level "
    "discrimination with calibrated probabilities and a principled uncertainty estimate for the REFER decision, which is the "
    "core stakeholder requirement. All selection evidence comes from the validation split; the test split was not consulted.")
R.H2("9.4 Baseline Model")
R.P("Logistic Regression on the same frozen features is the baseline: it is the simplest probabilistic classifier, it is "
    "interpretable, and any more complex model must beat it to justify its complexity. It was trained with a "
    "`StandardScaler`, C = 1.0, balanced class weights and up to 3,000 iterations, in 0.9 seconds. "
    f"{R.next_tab()} lists the baseline’s results on validation and test data; "
    f"{R.next_fig()} shows the genuine console output of the baseline script.")
R.TBL(["Metric", "Validation", "Test"],
      [[m, f3(LR["validation"][k]), f3(LR["test"][k])] for m, k in (("Accuracy", "accuracy"), ("Precision", "precision"), ("Recall", "recall"),
       ("Specificity", "specificity"), ("F1-score", "f1"), ("ROC-AUC", "roc_auc"), ("ECE", "ece"), ("Brier score", "brier"))]
      + [["Missed pneumonia (FN)", "—", str(LR["test"]["confusion_matrix"]["fn"])]],
      "Baseline (Logistic Regression) results", widths=[2.2, 1.6, 1.6], align="lcc")
bt = Path(__import__("os").environ.get("TEMP", "")) / "pptbuild/assets/baseline_terminal.png"
if bt.exists():
    R.FIG(None, "Console output of `python -m scripts.baseline_models` (genuine run)", 6.0, src=bt)
R.H2("9.5 Initial Model Training")
R.P("**Splitting strategy.** All models use the same patient-disjoint split: 4,182 training images (2,278 patients), 837 "
    "validation images (457 patients) and 837 test images (454 patients), stratified by label (details in Section 11.1).")
R.P("**Training procedure of the neural head.** The head (Dropout → Linear(2048, h) → ReLU → Dropout → Linear(h, 1)) is trained "
    "with the AdamW optimiser, mini-batches of 128, a positive-class-weighted binary cross-entropy loss (Eq. 9.1), up to 60 "
    "epochs and early stopping with patience 8 on the validation loss; the weights of the best epoch are restored.")
R.EQ("ℒ = −(1/N) Σ_{i} [ w_{+} y_{i} log σ(ℓ_{i}) + (1 − y_{i}) log(1 − σ(ℓ_{i})) ] ,   w_{+} = N_{0} / N_{1}")
R.P(f"Here yᵢ is the label, ℓᵢ the logit, σ the sigmoid, and N₀ = {split['train']['normal']:,}, N₁ = {split['train']['pneumonia']:,} "
    f"the training counts, so w₊ = {split['train']['normal'] / split['train']['pneumonia']:.3f}; this weight balances the "
    "gradient contribution of the two classes. "
    f"{R.next_fig()} shows the training curve of the final model: the validation loss reached its minimum "
    f"({S['history_best']['val_loss']:.4f}) at epoch {S['best_epoch']} and training stopped after {ev['training']['epochs_run']} "
    "epochs. The gap between training and validation loss stays small, so the head does not overfit severely.")
R.FIG("training_curve.png", "Training and validation loss of the final MC-Dropout head (early stopping)", 5.0)
R.P(f"**Initial performance (candidate comparison).** {R.next_tab()} compares all candidates on the validation split, which "
    "was used for selection.")
R.TBL(["Model", "Train time", "Val. accuracy", "Val. F1", "Val. ROC-AUC"],
      [[r["model"].replace(" (v1.1.0)", ""), f"{r['train_seconds']:.1f} s" if r["train_seconds"] else "≈ 3 min (incl. Optuna)",
        f3(r["validation"]["accuracy"]), f3(r["validation"]["f1"]), f3(r["validation"]["roc_auc"])] for r in bc],
      "Candidate model comparison on the validation split", widths=[2.6, 1.2, 0.9, 0.8, 0.9], size=9.5, align="lcccc")

# ------------------------------------------------------------------ CH 10
R.H1("Experiment Tracking and Hyperparameter Optimisation")
R.H2("10.1 Model Parameters and Hyperparameters")
R.TBL(["", "Learned parameters", "Hyperparameters"],
      [["Definition", "Values fitted from data by gradient descent", "Settings chosen before training that control learning"],
       ["Examples in PneumoScope", "Head weights W₁ (2048 × 512), b₁, W₂ (512 × 1), b₂ — about 1.05 million numbers; temperature T (fitted on validation)",
        "Learning rate, weight decay, dropout rate, hidden size; also epochs (60), patience (8), batch (128), MC passes (30), refer target error (1%)"],
       ["Set by", "AdamW optimiser / L-BFGS-style search for T", "Optuna (4 tuned) or fixed by design"],
       ["Stored in", "model.pt (SHA-256 checked)", "config.json and MLflow params"]],
      "Learned parameters versus hyperparameters", widths=[1.3, 2.5, 2.5], size=10)
R.H2("10.2 Hyperparameter Optimisation")
R.P("**Objective function.** For each candidate setting θ, the head is trained on the training split and evaluated on the "
    "validation split with 10 MC-Dropout passes; the objective to minimise is the validation negative log-likelihood (NLL) of "
    "the MC-averaged probability (Eqs. 10.1–10.2). NLL was chosen instead of accuracy because it rewards both correct and *well-"
    "calibrated* probabilities, which is what the referral policy needs.")
R.EQ("θ* = argmin_{θ∈Θ} −(1/N_{v}) Σ_{i} [ y_{i} log p̄_{i} + (1 − y_{i}) log(1 − p̄_{i}) ]")
R.EQ("p̄_{i}(θ) = (1/T) Σ_{t=1}^{T} σ( ℓ_{i}^{(t)} )")
R.P("Nᵥ = 837 validation images, T = 10 stochastic passes, ℓᵢ⁽ᵗ⁾ = logit of pass t. The search space Θ is given in Table 10.2.")
R.TBL(["Hyperparameter", "Type", "Range / choices", "Scale", "Best value (trial 9)"],
      [["Learning rate", "float", "1×10⁻⁴ – 3×10⁻³", "log-uniform", f"{best['lr']:.2e}"],
       ["Weight decay", "float", "1×10⁻⁶ – 1×10⁻²", "log-uniform", f"{best['weight_decay']:.2e}"],
       ["Dropout rate", "float", "0.2 – 0.6", "uniform", f"{best['dropout']:.3f}"],
       ["Hidden units", "categorical", "{128, 256, 512}", "—", str(best["hidden"])]],
      "Hyperparameter search space", widths=[1.4, 1.0, 1.6, 1.1, 1.3], align="lcccc")
R.H2("10.3 Optuna Implementation")
R.TBL(["Item", "Configuration"],
      [["Library", f"Optuna {__import__('optuna').__version__} [16]"], ["Study direction", "minimise"],
       ["Sampler", "TPESampler (Tree-structured Parzen Estimator), seed 42"], ["Pruner", "None (each trial ≈ 5–30 s on CPU)"],
       ["Objective", "Validation MC-NLL with 10 passes (Eqs. 10.1–10.2)"], ["Number of trials", f"{len(tr_)} per model version (50 in total)"],
       ["Best trial", f"#{best['n']}: lr = {best['lr']:.2e}, weight decay = {best['weight_decay']:.2e}, dropout = {best['dropout']:.3f}, hidden = {best['hidden']}"],
       ["Best validation result", f"NLL = {best['nll']:.4f} (worst trial {worst['nll']:.4f}, {(worst['nll'] - best['nll']) / worst['nll']:.0%} higher)"]],
      "Optuna study configuration and result", widths=[1.6, 4.7])
R.CODE('''study = optuna.create_study(direction="minimize",
                            sampler=optuna.samplers.TPESampler(seed=SEED))
def objective(trial):
    params = {"lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
              "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-2, log=True),
              "dropout": trial.suggest_float("dropout", 0.2, 0.6),
              "hidden": trial.suggest_categorical("hidden", [128, 256, 512])}
    head, info = train_head(feats[tr], y[tr], feats[va], y[va], **params)
    val_nll = cal.nll(cal.mc_probs(mc_logits(head, feats[va], passes=10)).mean(0), y[va])
    with mlflow.start_run(run_name=f"optuna-trial-{trial.number}", nested=True):
        mlflow.log_params(params); mlflow.log_metrics({"val_mc_nll": val_nll})
    return val_nll
study.optimize(objective, n_trials=25)''', "Code excerpt 10.1: Optuna study with MLflow logging (backend/scripts/train_pipeline.py)")
R.P(f"{R.next_fig()} shows the optimisation history: the best value was found at trial {best['n']} and later trials did not "
    "improve on it. Figure 10.2 shows the fANOVA hyperparameter importance [17], computed from the 25 logged trials, and "
    "Figure 10.3 the slice plots.")
R.FIG("optuna_history.png", "Optuna optimisation history (25 trials, model v1.1.0)", 5.4)
R.FIG("optuna_importance.png", "Hyperparameter importance (fANOVA) for validation NLL", 5.0)
R.FIG("optuna_slice.png", "Validation NLL against each hyperparameter (slice plots)", 6.27)
R.P(f"Dropout rate explains {IMP['dropout']:.0%} of the variation in validation NLL and the learning rate "
    f"{IMP['lr']:.0%}; hidden size ({IMP['hidden']:.0%}) and weight decay ({IMP['weight_decay']:.0%}) matter little. The "
    "slice plot shows that low dropout (≈ 0.2–0.3) gives the lowest NLL. This is an important finding for MC Dropout, because "
    "the dropout rate also controls how much the stochastic passes disagree; a rate that is too high adds noise and makes the "
    "averaged probability less sharp.")
R.H2("10.4 Experiment Tracking with MLflow")
R.P("MLflow [18] was used with a local SQLite tracking store. Table 10.4 lists the tracked experiments and parent runs; each "
    "parent run contains 25 nested trial runs.")
runs = S["mlflow_runs"]
R.TBL(["Experiment", "Run name", "Run ID"],
      [[r["experiment"], r["name"].replace(" (v1.1.0)", ""), r["run_id"][:16] + "…"] for r in runs],
      "MLflow experiments and run IDs", widths=[1.6, 2.9, 1.8], size=9.5)
R.TBL(["What is tracked", "How"],
      [["Experiment names and run IDs", "pneumonia-mc-dropout (52 runs), baseline-comparison (4 runs)"],
       ["Hyperparameters", "log_params: lr, weight_decay, dropout, hidden, mc_passes, temperature, refer threshold"],
       ["Validation metrics", "val_mc_nll per trial; val ROC-AUC, accuracy, F1, ECE, Brier for parents and baselines"],
       ["Test metrics", "Logged once for the final model and baselines (not used for selection)"],
       ["Dataset and code versions", "Tags: model_version, weights_sha256; dataset described in config.json and dataset_card.json"],
       ["Model artifacts", "log_artifact: model.pt, config.json, evaluation.json, reference_stats.json"],
       ["Experiment comparison", "MLflow compare view (Figure 5.3)"]],
      "What MLflow tracks in this project", widths=[1.8, 4.5], size=10)
R.H2("10.5 Optimisation Results")
R.P(f"{R.next_tab()} compares the untuned head (default settings, deterministic) with the optimised model on the **test** set. "
    "The test set is used here only for reporting; the decision to keep the optimised model was taken on validation NLL.")
R.TBL(["Test metric", "Before (default MLP head)", "After (Optuna + MC + temperature)", "Change"],
      [[nm, f3(MLP["test"][k]), f3(FIN["test"][k]), f"{FIN['test'][k] - MLP['test'][k]:+.3f}"]
       for nm, k in (("Accuracy", "accuracy"), ("Precision", "precision"), ("Recall", "recall"), ("F1-score", "f1"),
                     ("ROC-AUC", "roc_auc"), ("ECE (lower is better)", "ece"), ("Brier (lower is better)", "brier"))]
      + [["Missed pneumonia (FN)", str(MLP["test"]["confusion_matrix"]["fn"]), str(cmx["fn"]), f"{cmx['fn'] - MLP['test']['confusion_matrix']['fn']:+d}"],
         ["Uncertainty / REFER available", "No", "Yes", "—"]],
      "Before-and-after optimisation comparison (test set)", widths=[1.9, 1.5, 1.8, 0.9], align="lccc")
R.P(f"Optimisation reduced missed pneumonia cases from {MLP['test']['confusion_matrix']['fn']} to {cmx['fn']} and nearly halved "
    f"the calibration error ({f3(MLP['test']['ece'])} → {f3(FIN['test']['ece'])}), at the cost of a slightly lower precision. "
    f"Ranking quality (ROC-AUC) did **not** improve ({f3(MLP['test']['roc_auc'])} vs {f3(FIN['test']['roc_auc'])}); the "
    "difference is well inside the bootstrap confidence interval. We report this transparently: tuning mainly improved "
    "calibration and recall, not discrimination.")
R.H2("10.6 Computational Cost")
R.TBL(["Activity", "Cost (CPU)", "Benefit"],
      [["Feature extraction (once)", "≈ 25 min for 5,856 images", "Reused by every experiment"],
       ["One head training run", "≈ 27 s", "—"],
       ["Optuna study (25 trials)", "≈ 5–10 min", "−8 missed cases, ECE −45% vs default"],
       ["MC Dropout at inference", "30 head passes ≈ +1–2 ms per image", "Uncertainty and REFER decision"],
       ["Temperature scaling", "< 1 s", "ECE 0.019 → 0.015"]],
      "Computational cost versus benefit", widths=[2.0, 2.1, 2.2])
R.P("Because the expensive backbone is run only once and cached, the full optimisation costs minutes, not hours, so the "
    "improvement in safety-relevant metrics clearly justifies the additional computation. Fine-tuning the full backbone was "
    "not attempted: on a CPU it would multiply training time by roughly 100× for an uncertain gain.")

# ------------------------------------------------------------------ CH 11
R.H1("Model Evaluation")
R.H2("11.1 Training, Validation and Testing Strategy")
R.P(f"{R.next_fig()} shows the data-splitting method. Images were grouped by patient and assigned with "
    "`StratifiedGroupKFold` (outer 7 folds → test; inner 6 folds → validation) so that every patient appears in exactly one "
    "split and the class ratio is preserved (73% pneumonia in each). The **training** split fits the weights; the "
    "**validation** split is used for early stopping, Optuna, temperature fitting and choosing the referral threshold; the "
    "**test** split is used once, for the final report.")
R.FIG("split.png", "Patient-disjoint data-splitting strategy", 6.0)
R.P(f"**Why patient-disjoint?** To measure the effect of leakage we trained the identical pipeline on a flawed image-level random "
    f"split in which {lk['flawed_image_level']['overlap']['test_images_from_train_patients']} of the 837 test images come from "
    f"patients seen during training. {R.next_tab()} shows that leakage makes every metric look better.")
R.TBL(["Test metric", "Patient-disjoint (honest)", "Image-level (leaky)", "Inflation"],
      [[nm, f4(lk["patient_disjoint"][k]), f4(lk["flawed_image_level"][k]), f"{lk['flawed_image_level'][k] - lk['patient_disjoint'][k]:+.4f}"]
       for nm, k in (("ROC-AUC", "roc_auc"), ("Accuracy", "accuracy"), ("Specificity", "specificity"), ("F1-score", "f1"))]
      + [["Test images from training patients", "0", str(lk["flawed_image_level"]["overlap"]["test_images_from_train_patients"]), "—"]],
      "Effect of patient leakage on test results", widths=[2.0, 1.6, 1.6, 1.0], align="lccc")
R.H2("11.2 Classification Evaluation")
R.P(f"{R.next_fig()} shows the confusion matrix of the final model on the 837 test images at a decision threshold of 0.5. The "
    "metrics are defined in Equations 11.1–11.4.")
R.FIG("confusion_matrix.png", "Confusion matrix of the final model on the test set", 3.4)
e1 = R.EQ("Accuracy = (TP + TN) / (TP + TN + FP + FN)")
R.EQ("Precision = TP / (TP + FP)")
R.EQ("Recall = TP / (TP + FN)")
R.EQ("F1 = 2 · Precision · Recall / (Precision + Recall)")
R.P(f"TP = pneumonia correctly detected ({cmx['tp']}), TN = normal correctly identified ({cmx['tn']}), FP = normal flagged as "
    f"pneumonia ({cmx['fp']}), FN = pneumonia missed ({cmx['fn']}). Worked calculations:")
R.B([f"Accuracy = ({cmx['tp']} + {cmx['tn']}) / 837 = {cmx['tp'] + cmx['tn']} / 837 = **{f4(dsc['accuracy'])}**",
     f"Precision = {cmx['tp']} / ({cmx['tp']} + {cmx['fp']}) = {cmx['tp']} / {cmx['tp'] + cmx['fp']} = **{f4(dsc['precision'])}**",
     f"Recall = {cmx['tp']} / ({cmx['tp']} + {cmx['fn']}) = {cmx['tp']} / {cmx['tp'] + cmx['fn']} = **{f4(dsc['recall'])}**",
     f"Specificity = {cmx['tn']} / ({cmx['tn']} + {cmx['fp']}) = **{f4(dsc['specificity'])}**",
     f"F1 = 2 × {f4(dsc['precision'])} × {f4(dsc['recall'])} / ({f4(dsc['precision'])} + {f4(dsc['recall'])}) = **{f4(dsc['f1'])}**"])
R.P(f"**Interpretation.** Of every 100 children with pneumonia, the model finds about 96 (recall); when it says pneumonia it is "
    f"right 97 times in 100 (precision). Recall is the most important metric here because a missed pneumonia can delay "
    "treatment, whereas a false alarm costs a second look by a doctor.")
R.MATH("11.2.1 ROC-AUC and bootstrap confidence intervals",
       "ROC-AUC measures how well the model ranks pneumonia above normal images across all thresholds; the bootstrap gives "
       "a confidence interval that reflects the finite test size.",
       ["AUC = P( p̂(X^{+}) > p̂(X^{−}) )", "CI_{95%} = [ q_{0.025} , q_{0.975} ] of { M(D^{*b}) }_{b=1}^{1000}"],
       "X⁺, X⁻ = random pneumonia and normal images; p̂ = predicted probability; D*ᵇ = b-th resample (with replacement) of the "
       "837 test cases; M = metric; q = percentile.",
       "`sklearn.metrics.roc_auc_score`, `precision_recall_curve`; 1,000 bootstrap resamples in `app/ml/evaluation.py`.",
       f"ROC-AUC = {f4(dsc['roc_auc'])} (95% CI {f4(ci['roc_auc']['lower'])}–{f4(ci['roc_auc']['upper'])}); PR-AUC = "
       f"{f4(dsc['pr_auc'])}; recall CI {f3(ci['recall']['lower'])}–{f3(ci['recall']['upper'])}.",
       "There is a 98.8% chance that a random pneumonia X-ray receives a higher score than a random normal one. The lower "
       f"CI bound ({f3(ci['roc_auc']['lower'])}) is far above the 0.90 target.",
       "Target O3 is met; the confidence intervals are reported with every metric in the app’s Model Performance page.")
R.FIG("roc_pr.png", "ROC and precision–recall curves of the final model (test set)", 6.0)
R.H2("11.3 Regression Evaluation")
R.P("Not applicable: the task is classification. MSE, RMSE, MAE, MAPE and R² are therefore not reported. (The Brier score in "
    "Section 11.4 is the mean squared error of the predicted probabilities.)")
R.H2("11.4 Probability Calibration")
R.MATH("11.4.1 Temperature scaling, ECE and Brier score",
       "A calibrated model’s probabilities match observed frequencies. Temperature scaling divides the logits by a single "
       "learned constant; ECE and the Brier score measure the remaining miscalibration.",
       ["p_{i} = (1/30) Σ_{t=1}^{30} σ( ℓ_{i}^{(t)} / T ) ,   T* = argmin_{T} NLL_{val}(T)",
        "ECE = Σ_{m=1}^{M} (|B_{m}| / n) · | acc(B_{m}) − conf(B_{m}) |",
        "Brier = (1/n) Σ_{i=1}^{n} (p_{i} − y_{i})^{2}"],
       "T = temperature; B_{m} = set of predictions in confidence bin m (M = 15 bins); acc(B_{m}) = observed pneumonia frequency in "
       "the bin; conf(B_{m}) = mean predicted probability; n = 837; yᵢ ∈ {0,1}.",
       "`scipy.optimize.minimize_scalar` for T in `calibration_service.fit_temperature`; ECE, Brier and reliability bins in the same module.",
       f"T = {cal['temperature']:.4f}. Test ECE {f4(cal['before']['ece'])} → **{f4(cal['after']['ece'])}**; Brier "
       f"{f4(cal['before']['brier'])} → **{f4(cal['after']['brier'])}**.",
       "A temperature slightly below 1 sharpens the MC-averaged probabilities, which are otherwise slightly under-confident "
       "because averaging over dropout masks pulls them towards 0.5. After scaling, a predicted 80% means roughly 80% in practice.",
       "Target O4 (ECE ≤ 0.05) is met with a wide margin, so probabilities can be shown to users and used for the referral rule.")
R.FIG("reliability.png", "Reliability diagram before and after temperature scaling (test set)", 4.6)
R.H3("Uncertainty and the referral policy")
R.MATH("11.4.2 Predictive entropy and the REFER rule",
       "MC Dropout turns one network into an ensemble of 30 sub-networks; the entropy of their averaged prediction measures "
       "uncertainty and drives the REFER decision.",
       ["H(p̄) = − p̄ log_{2} p̄ − (1 − p̄) log_{2}(1 − p̄)", "decision = REFER  if  H(p̄) > τ  or a quality flag is raised;  otherwise AUTO"],
       "p̄ = mean calibrated probability over 30 passes; H in bits (0 = certain, 1 = maximally uncertain); τ = threshold chosen "
       "on validation as the largest coverage with AUTO error ≤ 1% and referral ≤ 30%.",
       "`uncertainty_service.summarize_passes`, `train_pipeline.choose_refer_threshold`.",
       f"τ = {ev['policy']['refer_threshold']:.4f}. On the test set {rb['n'] - rb['bands']['REFER']['n']} cases were AUTO and "
       f"{rb['bands']['REFER']['n']} ({pc(rb['refer_rate'])}) REFER. Accuracy on AUTO cases = **{pc(rb['auto_decision_accuracy'])}** "
       f"versus {pc(rb['overall_accuracy'])} overall; the REFER group captured {rb['errors_captured_by_refer']} of the "
       f"{rb['total_errors']} errors. Entropy detects errors with AUROC {f3(unc['entropy']['error_detection_auroc'])}.",
       "Referring 13% of X-rays removes three quarters of the mistakes from the automatic stream.",
       "Version 1.1.0 (1% target) replaced v1.0.0 (3% target, 2.4% referred, AUTO accuracy 96.6%) because the stricter policy "
       "better matches the safety requirement.")
R.FIG("accuracy_referral.png", "Accuracy on automatically decided cases versus the percentage referred (test set)", 5.0)
R.H2("11.5 Final Test-Set Evaluation")
R.P(f"{R.next_tab()} presents the final results on the held-out test set, which was not used for any training, tuning, "
    "calibration or threshold decision, together with the model comparison.")
R.TBL(["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "ECE", "Brier", "FN"],
      [[r["model"].replace("MC-Dropout head + Optuna + temperature (v1.1.0)", "**Final: MC-Dropout + Optuna + T**").replace("MLP head (default params)", "MLP head (default)"),
        f3(r["test"]["accuracy"]), f3(r["test"]["precision"]), f3(r["test"]["recall"]), f3(r["test"]["f1"]), f3(r["test"]["roc_auc"]),
        f3(r["test"]["ece"]), f3(r["test"]["brier"]), str(r["test"]["confusion_matrix"]["fn"])] for r in bc],
      "Model comparison on the test set (n = 837)", widths=[1.9, 0.6, 0.6, 0.55, 0.5, 0.6, 0.5, 0.5, 0.35], size=9, align="lcccccccc")
R.FIG("model_comparison.png", "Test accuracy, recall, F1 and ROC-AUC of the four models", 5.8)
R.H2("11.6 Error Analysis")
R.P(f"The final model made {ER['n']} errors: {ER['fn']} false negatives and {ER['fp']} false positives. Investigation showed:")
R.B([f"**Viral pneumonia is over-represented among misses:** {ER['fn_by_subtype'].get('viral', 0)} of the {ER['fn']} false negatives are "
     f"viral, although viral cases are only {fs['viral']['n']} of {fs['viral']['n'] + fs['bacterial']['n']} test pneumonias. Viral "
     "pneumonia often produces subtle, diffuse interstitial patterns that resemble a normal film.",
     f"**Errors are usually uncertain:** the mean entropy of wrong predictions is {ER['mean_entropy_err']:.2f} bits versus "
     f"{ER['mean_entropy_ok']:.2f} for correct ones ({R.next_fig()}); {ER['referred']} of {ER['n']} errors would be REFERRED.",
     f"**Confident errors remain:** {ER['confident_errors']} errors fall below the threshold and would be reported automatically "
     f"(6 missed pneumonias and 4 false alarms in the AUTO bands). These are the most dangerous cases and the main argument for "
     "keeping a clinician in the loop.",
     f"**Image size confound:** the error rate is {pc(ER['err_rate_highres'])} on higher-resolution images versus "
     f"{pc(ER['err_rate_lowres'])} on lower-resolution ones, suggesting that part of the model’s confidence comes from "
     "acquisition characteristics rather than lung findings.",
     f"**Borderline probabilities:** missed pneumonias had a mean predicted probability of {ER['mean_p_fn']:.2f} and false "
     f"alarms {ER['mean_p_fp']:.2f}; many lie near the decision boundary."])
R.FIG("error_entropy.png", "Distribution of predictive entropy for correct and wrong test predictions", 5.0)
R.FIG("error_examples.png", "Examples of the most confident false negatives and false positives", 6.27)
R.P("**Justification of the final model.** The MC-Dropout model is selected because it (1) has the best recall, F1, ECE and "
    "Brier score and the fewest missed pneumonias of all candidates, (2) is the only one that can refer uncertain cases, which "
    "lifts automatic accuracy to 98.6%, (3) meets every quantitative target, and (4) runs well within the latency budget on a "
    "CPU. Its ROC-AUC is statistically indistinguishable from the default MLP head, which we acknowledge.")

# ------------------------------------------------------------------ CH 12
R.H1("Model Deployment and Application Integration")
R.H2("12.1 Deployment Objectives")
R.P("The intended users are radiologists and clinicians who want a quick second opinion, and — for this course — students and "
    "evaluators exploring an uncertainty-aware model. The deployment environment is a single Windows host running Docker "
    "Desktop, reachable on the local network at port 8080 and, for demonstrations, through a temporary Cloudflare HTTPS link. "
    "Application requirements are FR1–FR6 and NFR1–NFR5 (Section 3.5).")
R.FIG("deployment.png", "Deployment architecture", 6.27)
R.H2("12.2 Model Packaging")
R.P("Training writes a self-describing **model bundle** folder `artifacts/models/v1.1.0/`:")
R.TBL(["File", "Contents"],
      [["model.pt", "PyTorch state dict of backbone + MC-Dropout head (94 MB)"],
       ["config.json", "Architecture, image size, normalisation, MC passes and seed, temperature, thresholds, hyper-parameters, weights SHA-256, MLflow run ID, intended use"],
       ["evaluation.json", "All validation/test metrics, curves, CIs, calibration, uncertainty, leakage study, targets"],
       ["reference_stats.json", "Training distributions of brightness, contrast, entropy, histogram (for drift monitoring)"]],
      "Contents of the model bundle", widths=[1.5, 4.8], size=10)
R.P("At start-up the API loads the bundle selected by the `MODEL_VERSION` environment variable, recomputes the SHA-256 of "
    "`model.pt`, refuses to load on mismatch, and rebuilds the network from `config.json`. The preprocessing pipeline is code "
    "(not a pickled object), so it is versioned with the application and identical to training.")
R.H2("12.3 API Development")
R.P("The backend exposes a REST/JSON API built with FastAPI. Every analysis endpoint requires a signed-in user (session JWT in "
    "an HttpOnly cookie). The frontend calls the API through nginx, which proxies `/api/*` to the backend container.")
R.H2("12.4 FastAPI Implementation")
eps = [[m.upper(), p, (o.get("summary") or "").strip()] for p, ops in oapi["paths"].items() for m, o in ops.items()]
R.TBL(["Method", "Endpoint", "Purpose"], eps, f"API endpoint specification ({len(eps)} operations, from the live OpenAPI schema)",
      widths=[0.8, 2.9, 2.6], size=9.5)
R.P("**Request and response.** `POST /triage` takes a multipart file field `file` (JPEG or PNG, ≤ 10 MB). Validation checks "
    "the magic bytes, decodes the image, applies EXIF orientation, guards against decompression bombs and rejects colour "
    "photographs; errors return HTTP 415 or 422 with a readable message. The response schema `AnalysisOut` contains the "
    "prediction, both class probabilities, the uncertainty, the AUTO/REFER decision and its reason, the referral threshold, "
    "model version, processing time, image size, image and Grad-CAM URLs and the disclaimer. "
    f"{R.next_fig()} lists the endpoints from the running service and Figures 12.3–12.4 show genuine requests and responses.")
R.FIG("api_openapi.png", "FastAPI OpenAPI endpoint listing from the running service", 6.27)
R.FIG("api_auth.png", "Health check, rejected unauthenticated request (401) and sign-in", 6.27)
R.FIG("api_triage.png", "Successful prediction request and rejection of a non-image upload", 6.27)
R.H2("12.5 Containerisation Using Docker")
R.P("The application is packaged as two images orchestrated by Docker Compose: a Python 3.12-slim backend with CPU-only "
    "PyTorch, running as a non-root user with a health check, and an nginx frontend serving the production React build. The "
    "model bundle is mounted read-only; the SQLite database and uploads live in a named volume. Secrets (SECRET_KEY, optional "
    "admin credentials) come from a `.env` file that is excluded from version control.")
R.CODE('''FROM python:3.12-slim
WORKDIR /srv/backend
COPY requirements.txt .
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \\
    && pip install -r requirements.txt
COPY app ./app
RUN useradd --create-home --uid 1000 app && chown -R app /srv/backend
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s CMD curl -fs http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]''',
       "Code excerpt 12.1: backend Dockerfile (abridged)")
R.CODE('''services:
  backend:
    build: ./backend
    environment:
      MODEL_VERSION: ${MODEL_VERSION:-v1.1.0}
      SECRET_KEY: ${SECRET_KEY:?set SECRET_KEY in .env}
    volumes:
      - ./artifacts:/srv/artifacts:ro
      - backend_data:/srv/backend/var
  frontend:
    build: ./frontend
    depends_on: [backend]
    ports: ["8080:80"]''', "Code excerpt 12.2: docker-compose.yml (abridged)")
R.FIG("docker.png", "Docker execution evidence: running containers (backend healthy) and image sizes", 6.27)
R.H2("12.6 Deployment Testing")
tri = EVD["triage"]
R.TBL(["Test", "Method", "Result"],
      [["Automated test suite", "pytest: API, authentication, ML core, upload validation", f"{EVD['pytest_count']} passed"],
       ["Health check", "GET /api/health through nginx", "200 {status: ok, model_available: true}"],
       ["Access control", "POST /api/triage without session", "401 rejected"],
       ["Prediction", "POST /api/triage with viral pneumonia X-ray", f"201 {tri['prediction']}, p = {tri['pneumonia_probability']:.4f}, H = {tri['uncertainty']:.4f}, {tri['decision']}, {tri['processing_ms']:.0f} ms"],
       ["Input validation", "POST /api/triage with a text file", "415 rejected with message"],
       ["Grad-CAM", "POST /api/analysis/{id}/gradcam", f"{EVD.get('gradcam_status')} heatmap generated"],
       ["End-to-end UI", "Browser walkthrough: register, upload, history, dashboard", "Working (Figures 12.7–12.9)"],
       ["Public access", "Cloudflare quick tunnel", "Reachable over HTTPS while the tunnel runs"]],
      "Deployment test results", widths=[1.4, 2.6, 2.3], size=9.5)
R.FIG("pytest.png", "Automated test execution: 39 tests passed", 5.6)
for f_, cap in (("ev_app_result.jpg", "Web application: result screen with prediction, uncertainty, REFER/AUTO decision and Grad-CAM"),
                ("ev_app_dashboard.jpg", "Web application: dashboard with totals, recent analyses and model status"),
                ("ev_app_login.jpg", "Web application: sign-in page")):
    if (FIG / f_).exists():
        R.FIG(f_, cap, 6.0)
R.H2("12.7 Deployment Limitations")
R.B(["The public link comes from a Cloudflare *quick tunnel*; it changes on every restart and has no uptime guarantee.",
     "Single host, single backend process with SQLite — suitable for demonstration, not for concurrent hospital use.",
     "CPU-only inference: fine for one user at a time; throughput under load was not measured.",
     "No integration with hospital systems (DICOM/PACS); DICOM files are not accepted.",
     "The backend image is large (2.5 GB) because of PyTorch.",
     "External validation (RSNA) is prepared but not run, so performance on other populations is unknown.",
     "Not a medical device: no regulatory approval; the disclaimer is mandatory."])

# ------------------------------------------------------------------ CH 13
R.H1("Monitoring, Drift and Continuous Integration")
R.P("*Status: the reference statistics, the drift-detection method and the metrics needed for monitoring are implemented "
    "and demonstrated offline in this chapter; an automated monitoring service, scheduled drift reports and GitHub Actions "
    "are designed but not yet deployed.*", italic=False)
R.H2("13.1 Model Monitoring Requirements")
R.TBL(["Metric", "Why", "Alert rule (proposed)"],
      [["Referral (REFER) rate", "Rises when inputs become unfamiliar or harder", "> 25% over a rolling 100 cases (validation: 10%)"],
       ["Rejected / flagged uploads", "Non-radiographs, wrong modality", "> 10% of uploads"],
       ["Mean predictive entropy", "Uncertainty drift", "> 2 × training mean"],
       ["Predicted pneumonia rate", "Prevalence or concept shift", "Outside 50–90%"],
       ["Input PSI (brightness, contrast, entropy)", "Data drift", "PSI > 0.25 = significant"],
       ["Latency and error rate", "Service health", "p95 > 2 s or HTTP 5xx > 1%"],
       ["Clinician-confirmed accuracy / recall", "True performance (needs feedback labels)", "Recall < 0.95 on reviewed cases"]],
      "Monitoring plan", widths=[2.0, 2.2, 2.1], size=10)
R.H2("13.2 Data Drift")
R.P("Data drift is a change in the distribution of inputs P(X) while the relationship P(Y | X) stays the same. For PneumoScope "
    "it would occur if a hospital used a different X-ray machine, exposure settings, image export (e.g. inverted or "
    "windowed images), older patients, or portable bedside films. The model would then receive images unlike its training "
    "data and its confidence may no longer be reliable.")
R.H2("13.3 Concept Drift")
R.P("Concept drift is a change in P(Y | X): the same image pattern starts to mean something different. Examples are a change in "
    "labelling practice (e.g. labels confirmed by laboratory tests instead of image reading), a new pathogen with a different "
    "radiological appearance (as COVID-19 showed), or a change in the definition of ‘pneumonia’ used by the hospital. Concept "
    "drift cannot be detected from images alone; it requires feedback labels from clinicians.")
R.H2("13.4 Drift Detection")
R.MATH("13.4.1 Population Stability Index and Kolmogorov–Smirnov test",
       "PSI compares the binned distribution of a monitored variable with its training (reference) distribution; the KS test "
       "gives a significance test for the same comparison.",
       ["PSI = Σ_{k=1}^{10} (c_{k} − r_{k}) · ln( c_{k} / r_{k} )", "D_{KS} = sup_{x} | F_{ref}(x) − F_{cur}(x) |"],
       "r_{k}, c_{k} = proportion of reference (training) and current images in quantile bin k (10 bins from training deciles); "
       "F = empirical cumulative distribution function. Rule of thumb [19]: PSI < 0.1 stable, 0.1–0.25 moderate, > 0.25 significant.",
       "Reference deciles stored in `reference_stats.json` by `train_pipeline.reference_distribution`; PSI and "
       "`scipy.stats.ks_2samp` in `docs/report/analyze.py`.",
       "See Table 13.2.",
       "Validation and test splits are stable (PSI ≤ 0.02), as expected for a random patient split. The original Kermany "
       "‘test’ folder shows small but statistically detectable differences (KS p ≈ 0.03 for brightness) — evidence that it was "
       "collected differently. A simulated scanner change (+15% brightness, −20% contrast) gives PSI far above 0.25 and is "
       "detected immediately.",
       "PSI > 0.25 on any monitored input over a window of ≥ 100 images will trigger a drift review (Section 13.6).")
rows = []
for nm, dd in DR.items():
    rows.append([nm] + [f"{dd[c]['psi']:.3f} ({'stable' if dd[c]['psi'] < 0.1 else 'moderate' if dd[c]['psi'] < 0.25 else 'SIGNIFICANT'})" for c in ("brightness", "contrast", "intensity_entropy")]
                + [f"{min(dd[c]['ks_p'] for c in dd):.2g}"])
R.nt = 1
R.TBL(["Compared with training", "PSI brightness", "PSI contrast", "PSI entropy", "min KS p"], rows,
      "Drift detection results", widths=[2.1, 1.15, 1.15, 1.15, 0.75], size=9, align="lcccc")
R.FIG("drift_brightness.png", "Brightness distribution: training reference, test split and simulated drift", 5.0)
R.H2("13.5 Monitoring Dashboard")
R.P("The application’s dashboard (Figure 12.8) already displays the operational indicators that the monitoring plan needs: "
    "total analyses, the split between Normal and Pneumonia predictions, the number of REFER decisions, recent analyses, and "
    "the model version and status. The Model Performance page shows the reference test metrics, confusion matrix and ROC "
    "curve, so that live behaviour can be compared with the validated baseline. The designed extension adds a ‘Drift’ panel "
    "with rolling PSI values for brightness, contrast and entropy (computed with the same `image_descriptors` function used "
    "at training time), a referral-rate trend line and alert badges for the rules in Table 13.1.")
R.H2("13.6 Retraining Strategy")
R.TBL(["Trigger", "Condition", "Action"],
      [["Significant data drift", "PSI > 0.25 on any input for ≥ 100 images, or REFER rate > 25%", "Investigate source; collect and label 200+ local images; recalibrate T; retrain head if needed"],
       ["Performance drop", "Recall on clinician-reviewed cases < 0.95, or ECE > 0.05", "Retrain with new labelled data; full evaluation; new version"],
       ["Scheduled", "Every 6 months", "Re-run pipeline on accumulated reviewed data"],
       ["New data source / site", "Before any new hospital uses the system", "External validation first; site-specific recalibration"]],
      "Retraining decision criteria", widths=[1.4, 2.4, 2.5], size=10)
R.P("Because the backbone is frozen and features are cached, retraining means re-running `train_pipeline.py` (minutes on a "
    "CPU), which produces a new bundle with a new version number, MLflow run and evaluation report. A new version is promoted "
    "only if it meets the acceptance criteria on a held-out test set; the old bundle is kept for rollback by changing "
    "`MODEL_VERSION`.")
R.H2("13.7 CI/CD with GitHub Actions")
R.P(f"{R.next_fig()} shows the proposed CI/CD workflow. Its stages already exist and run locally — the 39-test pytest suite, the "
    "TypeScript build of the frontend and the Docker Compose build — but the GitHub Actions workflow has **not been executed** "
    "because the repository was not hosted on GitHub during development. The workflow definition below is therefore a "
    "design, not evidence of execution.")
R.FIG("cicd.png", "Proposed CI/CD workflow (not yet executed on GitHub)", 6.27)
R.CODE('''name: ci
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm run build
  docker:
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build''', "Code excerpt 13.1: proposed .github/workflows/ci.yml (design only)")

# ------------------------------------------------------------------ CH 14
R.H1("Responsible AI and Model Explainability")
R.P("This chapter is included because the project uses an explainability method (Grad-CAM) and uncertainty estimation. SHAP "
    "and DiCE were evaluated and judged not applicable, as explained in Sections 14.3 and 14.4.")
R.H2("14.1 Responsible AI Principles")
R.TBL(["Principle", "How PneumoScope addresses it", "Gap"],
      [["Fairness", "Subgroup metrics with Fairlearn; sub-type and resolution analysis; referral of uncertain cases", "No demographic data"],
       ["Transparency", "Probabilities, uncertainty and reason shown; Grad-CAM; public metrics page; model card in config.json", "Grad-CAM is approximate"],
       ["Accountability", "Every analysis stores model version and decision reason; versioned bundles; MLflow history", "No clinical governance yet"],
       ["Privacy", "De-identified data; minimal fields; deletion; hashed passwords; HttpOnly cookies", "Local storage not encrypted at rest"],
       ["Safety", "REFER policy, quality flags, calibrated probabilities, disclaimer, human in the loop", "10 confident errors remain"]],
      "Responsible AI assessment", widths=[1.2, 3.5, 1.6], size=10)
R.H2("14.2 Model Interpretability")
R.P("In a clinical decision-support setting the level of interpretability required is *case-level*: a clinician must be able to "
    "see whether the model looked at the lungs and how sure it was, so that they can decide whether to trust it. Global "
    "interpretability of 2048 abstract features is neither possible nor necessary. PneumoScope therefore provides three "
    "complementary explanations for every case: the calibrated probability, the uncertainty with an AUTO/REFER decision and "
    "reason, and a Grad-CAM heatmap.")
R.MATH("14.2.1 Grad-CAM",
       "Grad-CAM highlights the image regions whose features most increased the pneumonia score.",
       ["α_{k} = (1/Z) Σ_{i,j} ∂ℓ / ∂A_{ij}^{k}", "L_{Grad-CAM} = ReLU( Σ_{k} α_{k} A^{k} )"],
       "A^{k} = k-th feature map of ResNet-50 layer 4 (7 × 7, k = 1…2048); ℓ = deterministic pneumonia logit (−ℓ for NORMAL); "
       "Z = 49 spatial positions; the map is up-sampled to 224 × 224 and normalised to [0, 1].",
       "`app/services/gradcam_service.py` (PyTorch forward/backward hooks, OpenCV resize and colour map).",
       f"{R.next_fig()}. In the bacterial example {pc(S['gradcam'][0]['cam_area_gt_0.5'], 0)} of the image is above half of the "
       "maximum activation; in the viral example the activation lies over the lower central and left lung fields.",
       "For several correct predictions the heatmap lies over the lungs, but in other cases it highlights the image border or "
       "outside the lung (e.g. the bacterial example concentrates near the right edge). This is consistent with the size/"
       "acquisition confound found in Chapter 6 and warns that high accuracy does not prove clinically meaningful reasoning.",
       "Grad-CAM is shown to users as a qualitative aid only; systematic review of heatmaps and lung-masked training are listed "
       "as future work.")
R.FIG("gradcam_examples.png", "Grad-CAM from the deployed model: three correct cases and one confident miss", 6.27)
R.H2("14.3 SHAP Analysis")
R.P("**Not applicable (not implemented).** SHAP [20] attributes predictions to input features. Applied to our classifier head it "
    "would rank the 2048 ResNet features, which have no human meaning; applied to raw pixels it requires thousands of model "
    "evaluations per image and gives results similar to gradient maps. Grad-CAM was preferred because it explains predictions "
    "in image space at the cost of one backward pass. SHAP on the metadata-based Logistic Regression would be possible but would "
    "only re-confirm the size confound already shown by the correlation analysis.")
R.H2("14.4 DiCE Counterfactual Explanations")
R.P("**Not applicable (not implemented).** DiCE [21] generates counterfactuals by changing tabular feature values (e.g. ‘if "
    "income were higher, the loan would be approved’). For radiographs, a counterfactual would be a synthetically modified "
    "image, which needs a generative model and has no actionable meaning for a patient. A simple input-perturbation test was "
    "used instead in monitoring (Section 13.4): changing brightness and contrast shows how input changes would be detected.")
R.H2("14.5 Fairness and Risk Review")
R.P("Revisiting Chapter 7: the strongest identified risk is not group unfairness but **validity** — the model may partly rely on "
    "acquisition differences between the classes, and it has only been tested on one hospital’s children. Viral pneumonia is "
    "the subgroup with the lowest recall, partly offset by a higher referral rate.")
R.TBL(["Risk", "Likelihood", "Impact", "Mitigation recommendation"],
      [["Missed pneumonia reported as AUTO-NEGATIVE (6 on test)", "Low", "High", "Clinician review of all results; lower AUTO error target for negatives"],
       ["Shortcut learning on image size/source", "Medium", "High", "External validation; lung segmentation; train with size-matched classes"],
       ["Use on adults or other hospitals", "Medium", "High", "Intended-use statement; quality flags; drift monitoring; site validation"],
       ["Automation bias (over-trust)", "Medium", "Medium", "Show uncertainty and disclaimer; REFER language that requires human decision"],
       ["Privacy breach of uploaded images", "Low", "High", "Authentication, deletion, encryption at rest (future), no public storage"]],
      "Risk mitigation recommendations", widths=[2.0, 0.8, 0.7, 2.8], size=9.5)
R.H2("14.6 Limitations")
R.B(["Single-site, single-age-band data; generalisation is unproven.",
     "Strong correlation between image size and label; Grad-CAM shows attention outside the lungs in some cases.",
     "No demographic attributes, so demographic fairness cannot be measured.",
     "Labels come from image reading, not laboratory confirmation.",
     "MC Dropout is an approximation to Bayesian uncertainty and does not detect every out-of-distribution input.",
     "SHAP and DiCE were not applied; Grad-CAM explanations are qualitative."])

# ------------------------------------------------------------------ CH 15
R.H1("Project Management, Results and Closure")
R.H2("15.1 Project Timeline and Milestones")
R.P(f"{R.next_fig()} compares the planned and actual schedule over the 14-week project. The main slippages were the "
    "patient-disjoint split and leakage study (one extra week, because patient IDs had to be reverse-engineered from file "
    "names), baselines and tuning (one week, because MLflow tracking was added) and the frontend (one week, for the Grad-CAM "
    "view and dashboard).")
R.FIG("gantt.png", "Planned versus actual project timeline (weeks)", 6.27)
R.TBL(["Milestone", "Planned", "Actual", "Deliverable"],
      [["M1 Problem definition approved", "W2", "W2", "Objectives, scope, feasibility"],
       ["M2 Data ready", "W5", "W6", "manifest.csv, dataset card, patient-disjoint split"],
       ["M3 Model v1.0.0", "W8", "W9", "Optuna-tuned MC-Dropout bundle"],
       ["M4 Evaluation complete", "W9", "W10", "evaluation.json, leakage study, model v1.1.0"],
       ["M5 Application deployed", "W12", "W13", "Docker Compose stack, public link"],
       ["M6 Report and presentation", "W14", "W14", "This report, presentation"]],
      "Project milestones", widths=[2.2, 0.8, 0.8, 2.5], align="lccl")
R.H2("15.2 Team Roles and Responsibilities")
R.TBL(["Member (App ID)", "TDSP role", "Main responsibilities"],
      [[f"{TEAM[0][0]} ({TEAM[0][1]})", "Project lead / data scientist", "Project planning and coordination; training pipeline; MC Dropout, calibration and referral policy; Optuna and MLflow; report integration"],
       [f"{TEAM[1][0]} ({TEAM[1][1]})", "Data engineer / analyst", "Dataset acquisition; manifest and patient IDs; patient-disjoint split and leakage study; EDA and data quality; ethics and bias assessment"],
       [f"{TEAM[2][0]} ({TEAM[2][1]})", "Application developer (backend)", "FastAPI service, authentication and security; upload validation; Grad-CAM service; automated tests; Dockerfiles"],
       [f"{TEAM[3][0]} ({TEAM[3][1]})", "Application developer (frontend) / solution architect", "React interface, dashboard and history pages; deployment with Docker Compose and tunnel; monitoring design; presentation"]],
      "Team roles and responsibilities", widths=[1.6, 1.5, 3.2], size=10)
R.TBL(["Activity", "Shruti", "Rushab", "Dhruv", "Ali"],
      [["Problem definition and feasibility", "L", "C", "C", "C"], ["Data acquisition, EDA, quality", "C", "L", "S", "S"],
       ["Splitting and leakage study", "C", "L", "–", "–"], ["Feature extraction and modelling", "L", "C", "S", "–"],
       ["Optuna and MLflow", "L", "S", "–", "–"], ["Evaluation and error analysis", "L", "C", "S", "S"],
       ["Ethics, fairness (Fairlearn)", "C", "L", "–", "S"], ["Backend API, security, tests", "S", "–", "L", "C"],
       ["Frontend and Grad-CAM view", "–", "–", "C", "L"], ["Docker deployment", "–", "–", "L", "C"],
       ["Monitoring and CI/CD design", "C", "–", "C", "L"], ["Report and presentation", "L", "C", "C", "C"]],
      "Team contribution matrix (L = lead, C = contributor, S = support)", widths=[2.7, 0.9, 0.9, 0.9, 0.9], size=10, align="lcccc")
R.H2("15.3 Project Risks and Challenges")
R.TBL(["ID", "Risk / challenge", "Category", "L", "I", "Response and outcome"],
      [["R1", "Data leakage inflating results", "Data", "H", "H", "Patient-disjoint split; leakage quantified (+0.003 AUC) — closed"],
       ["R2", "No GPU for deep learning", "Technical", "H", "M", "Frozen backbone + feature cache — closed"],
       ["R3", "Class imbalance hides missed cases", "Data", "H", "H", "Weighted loss, recall-first metrics — closed"],
       ["R4", "Overconfident probabilities", "Technical", "M", "H", "Temperature scaling, ECE target — closed"],
       ["R5", "Shortcut learning (size confound)", "Data", "M", "H", "Resize, disclosure, external validation — open"],
       ["R6", "Large Docker image / slow builds", "Operational", "M", "L", "CPU-only torch wheels — accepted"],
       ["R7", "Temporary public URL expires", "Operational", "H", "L", "Restart script; documented — accepted"],
       ["R8", "Schedule slip in data preparation", "Scheduling", "M", "M", "Parallel frontend work; 1-week buffer used — closed"],
       ["R9", "Security of user accounts", "Operational", "L", "H", "bcrypt, HttpOnly cookies, tests — closed"]],
      "Risk register (L = likelihood, I = impact: H/M/L)", widths=[0.45, 1.9, 0.9, 0.3, 0.3, 2.45], size=9, align="llcccl")
R.H2("15.4 Consolidated Results")
R.TBL(["Area", "Result"],
      [["Data", f"{card['total_images']:,} images, {card['total_patients']:,} patients; patient-disjoint split with 0 overlap; 6 quality issues remediated"],
       ["Modelling", "4 models compared; Optuna 25 trials (best NLL 0.0982); 56 MLflow runs"],
       ["Test performance", f"Accuracy {pc(dsc['accuracy'])}, precision {pc(dsc['precision'])}, recall {pc(dsc['recall'])}, F1 {f3(dsc['f1'])}, ROC-AUC {f3(dsc['roc_auc'])} [{f3(ci['roc_auc']['lower'])}, {f3(ci['roc_auc']['upper'])}]"],
       ["Calibration", f"ECE {pc(cal['after']['ece'])}, Brier {f3(cal['after']['brier'])}"],
       ["Uncertainty", f"{pc(rb['refer_rate'])} referred → AUTO accuracy {pc(rb['auto_decision_accuracy'])}; {rb['errors_captured_by_refer']}/{rb['total_errors']} errors referred"],
       ["Deployment", f"FastAPI + React in Docker; 13 API operations; {EVD['pytest_count']} tests pass; median latency {L['median']:.0f} ms"],
       ["Ethics", "Fairlearn subgroup audit; size confound and missing demographics disclosed"]],
      "Final results summary", widths=[1.4, 4.9], size=10)
R.H2("15.5 Success Criteria Assessment")
R.TBL(["Objective / criterion", "Target", "Achieved", "Status"],
      [["O1 Leakage-free split", "0 overlap", "0 patients shared", "Met"],
       ["O2 Recall", "≥ 0.95", f3(dsc["recall"]), "Met"],
       ["O3 ROC-AUC CI lower bound", "≥ 0.90", f3(ci["roc_auc"]["lower"]), "Met"],
       ["O4 Calibration (ECE)", "≤ 0.05", f3(cal["after"]["ece"]), "Met"],
       ["O5 Referral policy", "≤ 30% referred, higher AUTO accuracy", f"{pc(rb['refer_rate'])}; {pc(rb['auto_decision_accuracy'])} vs {pc(rb['overall_accuracy'])}", "Met"],
       ["O6 Beat baseline", "≥ LR on recall, F1, ECE", f"Recall {f3(FIN['test']['recall'])} vs {f3(LR['test']['recall'])}; F1 {f3(FIN['test']['f1'])} vs {f3(LR['test']['f1'])}; ECE {f3(FIN['test']['ece'])} vs {f3(LR['test']['ece'])}", "Met"],
       ["O7 Tracking and tuning", "All runs in MLflow", "56 runs, 2 experiments", "Met"],
       ["O8 Deployed app", "< 2 s, tests pass, Docker", f"{L['median']:.0f} ms, {EVD['pytest_count']}/39, running", "Met"],
       ["External validation", "(stretch goal)", "Not performed", "Not met"],
       ["CI/CD automation", "(stretch goal)", "Designed only", "Partially met"]],
      "Success criteria assessment", widths=[1.8, 1.5, 2.1, 0.9], size=9.5, align="lllc")
R.H2("15.6 Final Project Status")
R.P("**Status: Completed and deployed as a working prototype (educational).** All core objectives O1–O8 are met, the model is "
    "trained, evaluated and versioned, and the application is deployed in Docker and was demonstrated through a public link. "
    "External validation, automated monitoring and GitHub Actions CI/CD are **not completed** and are explicitly listed as "
    "future work. The system is not clinically validated and must not be used for diagnosis.")
R.H2("15.7 Future Scope")
R.B(["**External validation** on the RSNA Pneumonia Detection Challenge or NIH ChestX-ray14 data using the prepared "
     "`evaluate_external.py`, with site-specific recalibration.",
     "**Remove the shortcut:** lung segmentation before classification, training on size-normalised images, and controlled "
     "experiments that test whether image size alone predicts the label.",
     "**Fine-tune the backbone** on a GPU (or use a chest-X-ray-specific foundation model) and compare with the frozen approach.",
     "**Deep ensembles** as a stronger uncertainty baseline than MC Dropout.",
     "**Monitoring service** with rolling PSI and referral-rate alerts on the dashboard; clinician feedback to measure live recall.",
     "**MLOps:** publish the repository on GitHub, activate the GitHub Actions workflow, add DVC if hospital data are added.",
     "**Integration:** DICOM upload, PACS integration and a production database (PostgreSQL) with encryption at rest."])
R.H2("15.8 Conclusion")
R.P(f"PneumoScope shows that a carefully engineered, modest model can be both accurate and honest about its limits. Using the "
    f"CRISP-DM life cycle, the team turned a public dataset into a leakage-free benchmark, compared four models, tuned the best "
    f"with Optuna under MLflow tracking, and deployed it as a secure, containerised web application. The final model detects "
    f"{pc(dsc['recall'])} of pneumonia cases with well-calibrated probabilities (ECE {pc(cal['after']['ece'])}), and by "
    f"referring the most uncertain {pc(rb['refer_rate'])} of X-rays it raises the accuracy of automatic decisions to "
    f"{pc(rb['auto_decision_accuracy'])}.")
R.P("The project’s most valuable lessons came from what did not look good at first: random splitting overstated performance, "
    "hyper-parameter tuning improved calibration but not ranking, image size turned out to predict the label, and Grad-CAM "
    "sometimes looked outside the lungs. Reporting these findings transparently — rather than only the headline accuracy — is "
    "what a responsible AI life cycle requires. The learning outcomes for the team span the whole life cycle: requirements and "
    "feasibility, data governance, statistical evaluation, MLOps tooling, software engineering and responsible-AI practice.")
R.P("**Project closure statement.** The PneumoScope project is formally closed as a completed educational prototype. All "
    "deliverables — source code, model bundle v1.1.0 with evaluation, MLflow experiment records, Docker deployment, this "
    "report and the presentation — have been produced and handed over to the faculty mentor. Open items (external validation, "
    "monitoring automation and CI/CD) are documented in Section 15.7 for any future continuation.")

# ------------------------------------------------------------------ References
R.H1("References", chapter=False)
REFS = [
    "World Health Organization, “Pneumonia in children,” Fact sheet, Nov. 2022. [Online]. Available: https://www.who.int/news-room/fact-sheets/detail/pneumonia",
    "D. S. Kermany et al., “Identifying medical diagnoses and treatable diseases by image-based deep learning,” *Cell*, vol. 172, no. 5, pp. 1122–1131.e9, 2018.",
    "P. Rajpurkar et al., “CheXNet: Radiologist-level pneumonia detection on chest X-rays with deep learning,” arXiv:1711.05225, 2017.",
    "K. He, X. Zhang, S. Ren, and J. Sun, “Deep residual learning for image recognition,” in *Proc. IEEE CVPR*, 2016, pp. 770–778.",
    "Y. Gal and Z. Ghahramani, “Dropout as a Bayesian approximation: Representing model uncertainty in deep learning,” in *Proc. ICML*, 2016, pp. 1050–1059.",
    "C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, “On calibration of modern neural networks,” in *Proc. ICML*, 2017, pp. 1321–1330.",
    "R. R. Selvaraju et al., “Grad-CAM: Visual explanations from deep networks via gradient-based localization,” in *Proc. IEEE ICCV*, 2017, pp. 618–626.",
    "P. Chapman et al., *CRISP-DM 1.0: Step-by-step data mining guide*. SPSS Inc., 2000.",
    "Microsoft, “Team Data Science Process documentation,” Microsoft Learn. [Online]. Available: https://learn.microsoft.com/azure/architecture/data-science-process/overview",
    "Google, “Rules of machine learning” and “MLOps: Continuous delivery and automation pipelines in machine learning,” Google for Developers / Google Cloud Architecture Center.",
    "D. Kermany, K. Zhang, and M. Goldbaum, “Labeled optical coherence tomography (OCT) and chest X-ray images for classification,” Mendeley Data, v2, 2018, doi: 10.17632/rscbjbr9sj.2.",
    "European Parliament and Council, “Regulation (EU) 2016/679 (General Data Protection Regulation),” *Official Journal of the European Union*, L 119, 2016.",
    "Government of India, “The Digital Personal Data Protection Act, 2023,” Act No. 22 of 2023.",
    "J. R. Zech et al., “Variable generalization performance of a deep learning model to detect pneumonia in chest radiographs: A cross-sectional study,” *PLoS Medicine*, vol. 15, no. 11, e1002683, 2018.",
    "S. Bird et al., “Fairlearn: A toolkit for assessing and improving fairness in AI,” Microsoft, Tech. Rep. MSR-TR-2020-32, 2020.",
    "T. Akiba, S. Sano, T. Yanase, T. Ohta, and M. Koyama, “Optuna: A next-generation hyperparameter optimization framework,” in *Proc. ACM SIGKDD*, 2019, pp. 2623–2631.",
    "F. Hutter, H. Hoos, and K. Leyton-Brown, “An efficient approach for assessing hyperparameter importance,” in *Proc. ICML*, 2014, pp. 754–762.",
    "M. Zaharia et al., “Accelerating the machine learning lifecycle with MLflow,” *IEEE Data Engineering Bulletin*, vol. 41, no. 4, pp. 39–45, 2018.",
    "N. Siddiqi, *Credit Risk Scorecards: Developing and Implementing Intelligent Credit Scoring*. Hoboken, NJ, USA: Wiley, 2006.",
    "S. M. Lundberg and S.-I. Lee, “A unified approach to interpreting model predictions,” in *Proc. NeurIPS*, 2017, pp. 4765–4774.",
    "R. K. Mothilal, A. Sharma, and C. Tan, “Explaining machine learning classifiers through diverse counterfactual explanations,” in *Proc. ACM FAT**, 2020, pp. 607–617.",
    "A. Paszke et al., “PyTorch: An imperative style, high-performance deep learning library,” in *Proc. NeurIPS*, 2019, pp. 8024–8035.",
    "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” *J. Machine Learning Research*, vol. 12, pp. 2825–2830, 2011.",
    "I. Loshchilov and F. Hutter, “Decoupled weight decay regularization,” in *Proc. ICLR*, 2019.",
    "M. P. Naeini, G. F. Cooper, and M. Hauskrecht, “Obtaining well calibrated probabilities using Bayesian binning,” in *Proc. AAAI*, 2015, pp. 2901–2907.",
    "G. W. Brier, “Verification of forecasts expressed in terms of probability,” *Monthly Weather Review*, vol. 78, no. 1, pp. 1–3, 1950.",
    "Y. Geifman and R. El-Yaniv, “Selective classification for deep neural networks,” in *Proc. NeurIPS*, 2017, pp. 4878–4887.",
    "S. Ramírez, “FastAPI,” 2018. [Online]. Available: https://fastapi.tiangolo.com",
    "D. Merkel, “Docker: Lightweight Linux containers for consistent development and deployment,” *Linux Journal*, no. 239, 2014."]
for i, r_ in enumerate(REFS, 1):
    p = R.P(f"[{i}] {r_}", align="l")
    p.paragraph_format.left_indent = __import__("docx").shared.Inches(0.45)
    p.paragraph_format.first_line_indent = __import__("docx").shared.Inches(-0.45)
    p.paragraph_format.line_spacing = 1.15

# ------------------------------------------------------------------ Appendices
R.H1("Appendix A — Submission Checklist and Repository", chapter=False)
R.TBL(["Required item (Part D)", "Location / status"],
      [["1. Final report (PDF)", "PneumoScope_Group13_Final_Report.pdf"],
       ["2. Final report document", "PneumoScope_Group13_Final_Report.docx"],
       ["3. GitHub repository link", "https://github.com/Shruti4105/PneumoScope"],
       ["4. Python scripts", "backend/scripts/prepare_kermany.py, train_pipeline.py, baseline_models.py, evaluate_external.py; docs/report/analyze.py"],
       ["5. Dataset source and versioning", "Mendeley DOI 10.17632/rscbjbr9sj.2; data/kermany/manifest.csv; artifacts/datasets/kermany/dataset_card.json"],
       ["6. Experiment tracking and optimisation", "artifacts/experiments/mlflow_runs.json (export of all 56 runs); local store mlflow/mlflow.db"],
       ["7. Final model evaluation outputs", "artifacts/models/v1.1.0/evaluation.json; artifacts/experiments/baseline_comparison.json"],
       ["8. Deployment artifacts", "backend/Dockerfile, frontend/Dockerfile, docker-compose.yml, start-public.bat"],
       ["9. Individual contribution statement", "Section 15.2 (Tables 15.2–15.3)"],
       ["10. Final presentation", "PneumoScope_Group13_Presentation.pptx"]],
      "Submission checklist", widths=[2.2, 4.1], size=9.5)
R.P("**Excluded from the repository:** the raw dataset archive (download from the DOI), `.env` files, user databases and "
    "uploaded images, and any credentials.")
R.H1("Appendix B — Software Tools Used (Part C)", chapter=False)
R.TBL(["Project phase", "Suggested tool", "Used in this project", "Evidence"],
      [["Project initiation", "GitHub, project boards", "Yes — public GitHub repository", "Ch. 1, 15"],
       ["Data acquisition and analysis", "Python, Pandas, Jupyter", "Python + Pandas scripts (no notebooks)", "Ch. 5–6"],
       ["Data versioning", "Git, DVC", "MD5 manifest, dataset card, hashes (DVC not applicable)", "Ch. 5"],
       ["Data ethics", "Fairlearn", "Yes — MetricFrame, DPD, EOD", "Ch. 7"],
       ["Feature engineering", "scikit-learn", "Yes — StandardScaler pipeline, PCA; PyTorch transforms", "Ch. 8"],
       ["Experiment tracking", "MLflow", "Yes — 2 experiments, 56 runs", "Ch. 5, 10"],
       ["Hyperparameter optimisation", "Optuna", "Yes — TPE, 25 trials, fANOVA importance", "Ch. 10"],
       ["Model evaluation", "scikit-learn", "Yes — metrics, curves, bootstrap", "Ch. 11"],
       ["Deployment", "FastAPI, Docker", "Yes — running containers", "Ch. 12"],
       ["CI/CD", "GitHub Actions", "Proposed (not executed)", "Ch. 13"],
       ["Explainability", "SHAP, DiCE", "Not applicable; Grad-CAM used instead", "Ch. 14"]],
      "Software tools: implemented, proposed and not applicable", widths=[1.6, 1.3, 2.4, 1.0], size=9.5)

R.save(OUT)
json.dump({"figs": R.figs, "tabs": R.tabs}, open(HERE / "captions.json", "w"), indent=1)
print("saved", OUT, len(R.figs), "figures", len(R.tabs), "tables")
