# Contributors

PneumoScope was built by **Group 13**, Third Year B.Tech (AI & ML), ATLAS SkillTech University,
for the course BTECH CAP 501 — Project Life Cycle Management (academic year 2026),
under the guidance of **Dr. Amrita Banerjee**.

| Member | App ID | GitHub | Role |
| --- | --- | --- | --- |
| Shruti Shinde (author) | 2402669 | — | Project lead / data scientist: planning, training pipeline, MC Dropout, calibration and referral policy, Optuna and MLflow, report |
| Rushab Engolla | 2410251 | [@MrRushabGit](https://github.com/MrRushabGit) | Data engineer / analyst: dataset, patient-disjoint split, leakage study, EDA, data quality, ethics and bias |
| Dhruv Prabhu | 2405376 | [@dhruvprabhu17](https://github.com/dhruvprabhu17) | Backend developer: FastAPI service, authentication, upload validation, Grad-CAM, tests, Dockerfiles |
| Ali Shaikh | 2406682 | [@ali98251](https://github.com/ali98251) | Frontend developer / solution architect: React app, dashboard, Docker Compose deployment, monitoring design, presentation |

The full contribution matrix is in Section 15.2 of the final report
(`docs/PneumoScope_Group13_Final_Report.pdf`).

## Data and model weights

Not stored in this repository:

- **Dataset:** download from Mendeley Data, DOI [10.17632/rscbjbr9sj.2](https://doi.org/10.17632/rscbjbr9sj.2) (CC BY 4.0).
- **Model weights:** `artifacts/models/*/model.pt` (94 MB). Regenerate them with `backend/scripts/train_pipeline.py`.

The model configuration, evaluation results and MLflow tracking store are included.
