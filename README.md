# 🌳 Talentree AI Service — README

> **Built by:** Mai Farahat | AI Engineer
> **Last Updated:** June 2026
> **Branch:** `feature/admin-dashboard` (extends `feature/bo-dashboard`)

---

## 🚀 Live Deployment

| Environment | URL |
|---|---|
| **Production (Azure)** | http://20.244.32.232:8000 |
| **Swagger UI (API Docs)** | http://20.244.32.232:8000/docs |
| **Health Check** | http://20.244.32.232:8000/ai/status |

---

## 📌 What Is This?

This is the **AI brain** of the Talentree platform. It runs as a standalone FastAPI microservice that powers **two dashboards**:

### 🧑‍💼 Business Owner (BO) Dashboard
Every seller on the platform gets their own intelligent dashboard:
- 🔮 Predicts churn risk, fraud, anomalies, and demand
- 📊 Analyzes reviews, revenue trends, and performance benchmarks
- 🔔 Notifies BOs when thresholds are crossed
- 📄 Exports financial reports as PDF/CSV
- 🤖 Retrains models weekly on real accumulated data

### 🛡️ Admin Dashboard *(New — feature/admin-dashboard)*
Super-admins get platform-wide intelligence:
- 📈 Platform health score, KPIs, and trend analytics
- 🏆 Seller ranking with AI risk flags (churn + fraud)
- 👥 Customer RFM segmentation (Champion / Loyal / At Risk / Lost)
- 🔮 3-month revenue forecasting
- 📁 Styled Excel & CSV export of all platform reports
- 🚨 Alert feeds: low stock, overdue complaints, anomaly transactions

---

## 📖 Documentation

| Document | Audience | Contents |
|---|---|---|
| [**AI Models Explained (BO)**](docs/AI_Models_Explained.md) | Everyone | Plain-English explanation of all 7 BO models with accuracy metrics |
| [**Admin AI Models Explained**](docs/Admin_AI_Models_Explained.md) | Everyone | Plain-English explanation of 2 new admin models (Forecast + RFM) |
| [**BO Integration Guide**](docs/AI_Integration_Guide.md) | Angular + .NET teams | BO endpoints, TypeScript types, chart code examples |
| [**Admin Integration Guide**](docs/Admin_Integration_Guide.md) | Angular + .NET teams | All admin endpoints, TypeScript types, chart code, .NET triggers |
| [**Admin Implementation Plan**](docs/Admin_Implementation_Plan.md) | AI Engineer / Tech Lead | Architecture decisions, DB schema, service file breakdown |
| [**AI Master Plan (BO)**](docs/AI_Master_Plan.md) | AI Engineer / Tech Lead | Full BO technical strategy, training pipeline |
| [**Azure Deployment Guide**](docs/Azure_Deployment_Guide.md) | DevOps | Docker + Azure App Service setup |
| [**Backend Integration Events**](docs/Backend_Integration_Events.md) | .NET team | Webhook-style event triggers for .NET backend |

---

## 🏗️ Architecture

```
┌──────────────────┐     JSON/REST      ┌───────────────────────────────────────┐
│  Angular Frontend │ ─────────────────► │  Talentree AI Service                 │
│  BO Dashboard     │                    │  FastAPI  :8000 → Azure :443          │
│  Admin Dashboard  │                    │                                       │
└──────────────────┘                     │  ── Business Owner Module ──          │
                                         │  ├─ churn_service        (Model 1)   │
┌──────────────────┐     HTTP calls      │  ├─ fraud_service        (Model 2)   │
│  .NET Backend     │ ─────────────────► │  ├─ anomaly_service      (Model 3)   │
│  (Event triggers) │                    │  ├─ sentiment_service    (Model 4)   │     ┌──────────────────┐
└──────────────────┘                     │  ├─ triage_service       (Model 5)   │────►│  SQL Server      │
                                         │  ├─ product_service      (Model 6+7) │     │  Azure DB        │
┌──────────────────┐     CRON jobs       │  ├─ dashboard_service               │     │  db52715.public. │
│  APScheduler      │ ─────────────────► │  ├─ export_service                  │     │  databaseasp.net │
│  Nightly + Weekly │                    │                                       │     └──────────────────┘
└──────────────────┘                     │  ── Admin Module ──                  │
                                         │  ├─ admin_dashboard_service          │
                                         │  ├─ admin_kpi_service                │
                                         │  ├─ admin_analytics_service          │
                                         │  ├─ admin_seller_service             │
                                         │  ├─ admin_customer_service           │
                                         │  ├─ admin_category_service           │
                                         │  ├─ admin_export_service             │
                                         │  ├─ admin_forecast_service  (Model 8)│
                                         │  └─ admin_rfm_service       (Model 9)│
                                         └───────────────────────────────────────┘
```

---

## 📊 All 9 AI Models at a Glance

| # | Model | Dashboard | Algorithm | DB Output |
|---|---|---|---|---|
| 1 | Churn Risk | BO | XGBoost | `AspNetUsers.ChurnRiskScore` |
| 2 | Fraud Detection | BO | XGBoost | `BoProductionRequests.IsFraudFlag` |
| 3 | Anomaly Detection | BO | Isolation Forest | `Transactions.AnomalyFlag` |
| 4 | Sentiment Analysis | BO | VADER NLP | `ProductReviews.SentimentLabel` |
| 5 | Ticket Triage | BO | Rule-based | `SupportTickets.AutoCategory` |
| 6 | Demand Forecast | BO | Linear Regression | `Products.DemandForecastQty` |
| 7 | Description Quality | BO | NLP Rules | `Products.DescriptionQualityScore` |
| 8 | **Revenue Forecast** | **Admin** | **Linear Regression** | Live (not stored) |
| 9 | **RFM Segmentation** | **Admin** | **K-Means (k=4)** | `AspNetUsers.RfmSegment` |

---

## 🔑 Key Design Decisions

| Decision | Why |
|---|---|
| **SQLAlchemy `creator` pattern** | Handles special characters in DB password (`+`, `#`, `=`) — pyodbc alone fails |
| **Auto-retrain on startup** | Azure App Service can restart at any time; models retrain automatically if pkl files are missing |
| **No pkl files in git** | Binary files are large and noisy in git history — models train from live DB on startup |
| **Sliding time-window churn** | 9 users → 9 rows would fail; windowing gives 476 real training samples |
| **Minority-class oversampling for fraud** | Only ~8% of requests are fraud; oversampling to ~40% gives model enough examples |
| **Admin on same service** | Same DB engine, same ML libraries, same Docker container — no second deployment needed |
| **K-Means fallback to rules** | With < 4 customers with orders, K-Means degrades; rule-based segmentation is used instead |

---

## 🚀 Quick Start

### Option 1 — Docker (Recommended)
```bash
git clone -b feature/admin-dashboard https://github.com/Talentree-Platform/AI_Repo.git
cd AI_Repo
cp .env.example .env
# Edit .env with your DB credentials
docker compose up --build -d
# API: http://localhost:8080/docs
```

### Option 2 — Local Python
```bash
git clone -b feature/admin-dashboard https://github.com/Talentree-Platform/AI_Repo.git
cd AI_Repo
pip install -r talentree-ai/requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# API: http://localhost:8000/docs
```

### Models: Auto-Trained on Startup
```
[STARTUP] Missing models detected — retraining from DB...
[STARTUP] churn_model.pkl        → trained (476 rows, F1=1.0)
[STARTUP] fraud_model.pkl        → trained (218 rows, F1=0.87)
[STARTUP] anomaly_model.pkl      → trained (1012 rows)
[STARTUP] sentiment — no pkl needed (VADER is rule-based)
[STARTUP] admin_forecast_model.pkl → trained (12 months data)
[STARTUP] admin_rfm_model.pkl    → trained (k=4 clusters)
[STARTUP] All models ready. API starting...
```

---

## ⏰ Scheduled Jobs

| Time | Job |
|---|---|
| 02:00 Cairo nightly | Recompute all BO predictions (10 jobs, staggered by 5 min) |
| 03:00 Sunday | Retrain all 7 BO ML models on weekly real data |
| 03:30 Sunday | Retrain Revenue Forecast model (Admin Model 8) |
| 03:45 Sunday | Retrain + run RFM segmentation (Admin Model 9) |

---

## 📁 Project Structure

```
talentree-ai/
├── main.py                          ← All API routes (BO + Admin)
├── scheduler.py                     ← APScheduler nightly + weekly jobs
├── requirements.txt                 ← Python dependencies
├── config.py                        ← Environment config
├── Dockerfile                       ← Azure-ready Docker image
├── db/
│   └── connection.py                ← SQLAlchemy creator pattern
├── models/                          ← Auto-generated .pkl files (git-ignored)
├── services/
│   ├── [BO services — 16 files]     ← Business Owner AI module
│   ├── admin_dashboard_service.py   ← FR-AD-01: metrics + alerts
│   ├── admin_kpi_service.py         ← FR-AD-02: KPIs + health score
│   ├── admin_analytics_service.py   ← FR-AD-18: trend charts
│   ├── admin_seller_service.py      ← FR-AD-19: seller ranking
│   ├── admin_customer_service.py    ← FR-AD-20: customer cohorts
│   ├── admin_category_service.py    ← FR-AD-21: category analytics
│   ├── admin_export_service.py      ← CSV + XLSX export
│   ├── admin_forecast_service.py    ← Model 8: Revenue Forecast
│   └── admin_rfm_service.py         ← Model 9: RFM Segmentation
└── docs/
    ├── AI_Models_Explained.md
    ├── Admin_AI_Models_Explained.md ← NEW
    ├── AI_Integration_Guide.md
    ├── Admin_Integration_Guide.md   ← NEW
    ├── Admin_Implementation_Plan.md ← NEW
    ├── AI_Master_Plan.md
    ├── Azure_Deployment_Guide.md
    └── Backend_Integration_Events.md
```

---

## 🧑‍💻 Branches

| Branch | Purpose |
|---|---|
| `feature/bo-dashboard` | Business Owner AI module (stable, deployed) |
| `feature/admin-dashboard` | Admin Dashboard AI module (extends BO) |
