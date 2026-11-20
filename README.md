# PneumoScope — Pneumonia Classification with Uncertainty

> **Educational research application. Not a clinically validated diagnostic system.**

A web app that classifies chest X-rays as **Normal** or **Pneumonia** with a trained ResNet-50, reports
an **uncertainty score**, makes an **AUTO / REFER** decision and shows a **Grad-CAM** heatmap.

| Page | What it does |
| --- | --- |
| Home | Public landing page |
| Login | Sign in or create an account (all other pages require sign-in) |
| Dashboard | Totals, recent analyses, prediction chart, model status |
| X-Ray Analysis | Upload (drag & drop or browse) → result + heatmap, saved automatically |
| Analysis History | Past results — open or delete |
| Model Performance | Accuracy, precision, recall, F1, ROC-AUC, confusion matrix, ROC curve (real test results) |
| About Project | Introduction, objectives, method, dataset, technologies, limitations |

## Project structure

```
backend/     FastAPI + PyTorch API (app/), tests/, training scripts (scripts/)
frontend/    React + TypeScript + Vite + Tailwind + Recharts
artifacts/   models/v1.1.0/  trained weights, config, evaluation results
docker-compose.yml
```

## Run locally (Windows)

Requirements: Python 3.11–3.13, Node.js 20+.

**1. Backend** (first time only: create the environment and install)

```bash
python -m venv .venv
```
```bash
.venv\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
```bash
.venv\Scripts\python -m pip install -r backend\requirements.txt
```

Start the API (keep this window open):

```bash
cd backend
```
```bash
..\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

**2. Frontend** (in a second window)

```bash
cd frontend
```
```bash
npm install
```
```bash
npm run dev
```

Open **http://localhost:5173** and click **Create account** (or sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`
if you set them in `.env`).

## Run with Docker

Copy `.env.example` to `.env` and set `SECRET_KEY` (and optionally `ADMIN_EMAIL` / `ADMIN_PASSWORD`), then:

```bash
docker compose up --build
```

Open **http://127.0.0.1:8080**. Stop with `docker compose down`.
To share a temporary public link from this PC, double-click `start-public.bat`.

## API

| Method | Path | |
| --- | --- | --- |
| POST | `/auth/register`, `/auth/login`, `/auth/logout` · GET `/auth/me` | Accounts; session in an HttpOnly cookie. All routes below require sign-in |
| POST | `/triage` | Upload an image (`file`) → prediction, probability, uncertainty, AUTO/REFER; saved |
| GET | `/analysis/history` | Saved analyses (newest first) |
| GET | `/analysis/{id}` | One analysis |
| DELETE | `/analysis/{id}` | Delete an analysis and its images |
| POST | `/analysis/{id}/gradcam` | Create the Grad-CAM heatmap |
| GET | `/model-info` | Model status and version |
| GET | `/metrics` | Test-set evaluation results |

Interactive API docs: http://localhost:8000/docs

## Tests

```bash
cd backend
```
```bash
..\.venv\Scripts\python -m pytest
```

## Model

- ResNet-50, trained on the Kermany Pediatric Chest X-Ray dataset (5,856 images, patient-disjoint split).
- Probabilities are calibrated (temperature scaling). The uncertainty score is the predictive entropy of
  repeated stochastic predictions; above the referral threshold the result is **REFER**.
- Weights and results live in `artifacts/models/v1.1.0/`. If they are missing, the app shows
  “Integration pending” and refuses to predict — it never returns made-up results.
- RSNA external testing: `backend/scripts/evaluate_external.py` (requires the RSNA data from Kaggle).
- To retrain: `pip install -r backend/requirements-train.txt`, then run `scripts/prepare_kermany.py` and
  `scripts/train_pipeline.py`.

## Disclaimer

This software is for education and research only. It is not a medical device and must not be used to
diagnose or treat patients.
