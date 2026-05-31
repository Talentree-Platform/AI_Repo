---
title: Talentree AI Service
emoji: 🌳
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: AI microservice for the Talentree Business Owner Dashboard
---

# 🌳 Talentree AI Service — Business Owner Dashboard

> **AI-powered microservice for real-time predictions, analytics, and smart notifications**
> Built by: Mai Farahat | AI Engineer
> Last Updated: June 1, 2026

---

## 🚀 Live Deployment

| Environment | URL |
|---|---|
| **HF Space (Production)** | https://memo620-talentree-ai.hf.space |
| **Swagger UI (API Docs)** | https://memo620-talentree-ai.hf.space/docs |
| **Health Check** | https://memo620-talentree-ai.hf.space/ai/status |

---

## 📌 What Is This?

This is the **AI brain** of the Talentree Business Owner (BO) Dashboard. It runs as a standalone FastAPI microservice that:

- 🔮 **Predicts** churn risk, fraud, anomalies, and demand
- 📊 **Analyzes** reviews, revenue trends, and performance benchmarks
- 🔔 **Notifies** BOs and admins when thresholds are crossed
- 📄 **Exports** financial reports as PDF/CSV
- 🤖 **Retrains** models automatically on every restart + every week on real data
- 🗄️ **Connects** to a live production SQL Server database

---

## 📖 Documentation

| Document | Who It's For | What's Inside |
|---|---|---|
| [**AI Models Explained**](docs/AI_Models_Explained.md) | Everyone (PM, Dev, Design) | Plain-English explanation of every model with live accuracy metrics |
| [**AI Integration Guide**](docs/AI_Integration_Guide.md) | Angular + .NET teams | Endpoints, TypeScript interfaces, chart code examples |
| [**AI Master Plan**](docs/AI_Master_Plan.md) | AI Engineer / Tech Lead | Full technical strategy, DB schema, training pipeline |

---

## 🏗️ Architecture

```
┌──────────────────┐     JSON/REST      ┌───────────────────────────────┐
│  Angular Frontend │ ─────────────────► │  Talentree AI Service         │
│  (Charts, Cards)  │                    │  FastAPI  :7860 (HF Spaces)   │
└──────────────────┘                     │                               │
                                         │  ┌─ churn_service             │
┌──────────────────┐     HTTP calls      │  ├─ fraud_service             │
│  .NET Backend     │ ─────────────────► │  ├─ anomaly_service           │
│  (Event triggers) │                    │  ├─ sentiment_service         │     ┌───────────────────────┐
└──────────────────┘                     │  ├─ triage_service            │────►│  SQL Server           │
                                         │  ├─ product_service           │     │  db52715.public.      │
┌──────────────────┐     CRON jobs       │  ├─ dashboard_service         │     │  databaseasp.net      │
│  APScheduler      │ ─────────────────► │  ├─ export_service            │     └───────────────────────┘
│  Nightly + Weekly │                    │  └─ retrain_service           │
└──────────────────┘                     └───────────────────────────────┘
```

### Key Design Decisions

| Decision | Why |
|---|---|
| **SQLAlchemy `creator` pattern** | Handles special characters in DB password (`+`, `#`, `=`) — pyodbc alone fails |
| **`await _ensure_models()` on startup** | HF Spaces uses ephemeral storage; pkl files are wiped on restart so models retrain automatically |
| **No pkl files in git** | HF rejects binary files — models train from live DB on startup |
| **Sliding time-window churn training** | 9 users → 9 rows would fail; windowing gives 100+ real training samples |
| **Minority-class oversampling for fraud** | Only ~8% of requests are fraud; oversampling to ~40% gives model enough fraud examples |

---

## 🚀 Quick Start

### Option 1 — Docker (Recommended)
```bash
git clone -b feature/bo-dashboard https://github.com/Talentree-Platform/AI_Repo.git
cd AI_Repo
cp .env.example .env
# Edit .env with your DB credentials
docker compose up --build -d
# API: http://localhost:8080/docs
```

### Option 2 — Local Python
```bash
git clone -b feature/bo-dashboard https://github.com/Talentree-Platform/AI_Repo.git
cd AI_Repo
pip install -r requirements.txt
cp .env.example .env
# Edit .env with DB credentials
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# API: http://localhost:8000/docs
```

### Models: Auto-Trained on Startup
The service **automatically trains all missing models** when it starts:
```
[STARTUP] Missing models: ['churn_model.pkl', 'fraud_model.pkl', ...] — retraining from DB ...
[STARTUP] Retrain result: {'churn': {'status': 'retrained', ...}, ...}
```
You can also trigger manually:
```bash
curl -X POST https://memo620-talentree-ai.hf.space/ai/train/all
```

---

## 📡 All API Endpoints (23 total)

### Health & Status
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ai/status` | Health check → `{"status": "ok"}` |
| `GET` | `/ai/models/status` | Model accuracy, F1 score, training rows, last trained |

### Dashboard & Analytics *(Frontend calls these)*
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ai/dashboard/{bo_id}` | All KPI metrics in one call |
| `GET` | `/ai/analytics/revenue-trend/{bo_id}?period=weekly\|monthly` | Revenue line chart data |
| `GET` | `/ai/reviews/trends/{bo_id}?period=weekly\|monthly` | Sentiment bar chart data |
| `GET` | `/ai/benchmark/{bo_id}` | BO vs platform percentile ranking |
| `GET` | `/ai/benchmark/all` | All BOs benchmark comparison |

### Predictions *(Backend calls on events)*
| Method | Endpoint | Trigger | Returns |
|---|---|---|---|
| `POST` | `/ai/predict/churn/{user_id}` | BO logs in | `churn_risk_score` (0–1) |
| `POST` | `/ai/predict/fraud/{request_id}` | New production request | `fraud_score` + `is_fraud` |
| `POST` | `/ai/predict/anomaly/{tx_id}` | New transaction | `anomaly_score` + `is_anomaly` |
| `POST` | `/ai/predict/sentiment/{review_id}` | New review submitted | `sentiment_score` + label |
| `POST` | `/ai/predict/triage/{ticket_id}` | New support ticket | `priority_score` + `auto_category` |
| `POST` | `/ai/predict/demand/{product_id}` | Product updated | `demand_forecast_qty` + `low_stock_flag` |

### Compute *(Batch processing)*
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ai/compute/product/{id}` | Quality + LowStock + Demand |
| `POST` | `/ai/compute/profile/{bo_id}` | Profile completeness % |
| `POST` | `/ai/compute/request/{id}` | Fulfillment time + Fraud check |
| `POST` | `/ai/compute/materials/all` | OrderFrequency + PriceTrend |
| `POST` | `/ai/compute/all` | Run everything (takes ~2 min) |

### Notifications & Export
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ai/notify/check/{bo_id}` | Check thresholds, write alerts |
| `POST` | `/ai/notify/check/all` | Check all BOs |
| `GET` | `/ai/export/financial/{bo_id}?format=csv` | Download CSV financial report |
| `GET` | `/ai/export/financial/{bo_id}?format=pdf` | Download PDF financial report |

### Model Training
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ai/train/churn` | Retrain churn model on real data |
| `POST` | `/ai/train/fraud` | Retrain fraud model |
| `POST` | `/ai/train/anomaly` | Retrain anomaly model |
| `POST` | `/ai/train/all` | Retrain all models |

---

## 🤖 AI Models — Live Performance (June 2026)

| # | Model | Algorithm | Training Rows | Accuracy | F1 Score |
|---|---|---|---|---|---|
| 1 | Churn Risk | XGBoost | 476 (112 real + augmented) | 100% | **1.0** |
| 2 | Fraud Detection | XGBoost | 218 (oversampled) | 92.7% | **0.87** |
| 3 | Anomaly Detection | Isolation Forest | 1,012 real | N/A (unsupervised) | N/A |
| 4 | Sentiment Analysis | VADER NLP | Rule-based | ~85% | N/A |
| 5 | Ticket Triage | Keywords + NLP | Rule-based | ~80% | N/A |
| 6 | Demand Forecast | Linear Regression | 12 products | MAE = 2.64 | N/A |
| 7 | Description Quality | NLP Rules | Rule-based | N/A | N/A |
| 8 | Profile Completeness | Count-based | Deterministic | 100% | N/A |

### How Models Improve
- **Sliding time-windows:** Churn model creates 1 training sample per user per month (not 1 per user), multiplying data 6x
- **Noise augmentation:** Each real sample copied with small Gaussian noise → 476 total training rows from 112 real
- **Minority oversampling:** Fraud model oversamples rare fraud cases to ~40% of dataset, enabling the model to learn fraud patterns
- **Weekly retraining:** Every Sunday 03:00 Cairo time, all models retrain automatically on accumulated real data

---

## ⏰ Automated Scheduler

| Time (Cairo) | Job | Frequency |
|---|---|---|
| 02:00 AM | Recompute all profile completeness | Every night |
| 02:05 AM | Recompute all product metrics | Every night |
| 02:10 AM | Recompute all material stats | Every night |
| 02:15 AM | Predict churn for all BOs | Every night |
| 02:20 AM | Predict fraud for all requests | Every night |
| 02:25 AM | Predict anomaly for all transactions | Every night |
| 02:30 AM | Predict sentiment for all reviews | Every night |
| 02:35 AM | Triage all open tickets | Every night |
| 02:45 AM | Check notification thresholds | Every night |
| 03:00 AM Sunday | **Retrain all ML models** on accumulated real data | Weekly |

---

## 📁 Project Structure

```
talentree-ai/
├── main.py                        # FastAPI app — 23 endpoints
├── config.py                      # DB config (env vars)
├── scheduler.py                   # APScheduler — nightly + weekly jobs
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker image definition
├── docker-compose.yml             # One-command local deployment
├── .env.example                   # Environment variables template (safe)
│
├── data/
│   ├── generate_seed_json.py      # Generate base seed JSON files (9 users)
│   ├── generate_extra_seed.py     # Generate EXTRA seed data for ML improvement
│   ├── for_backend_team/          # Base seed JSON files (9 tables)
│   └── for_backend_team_extra/    # Extra seed files (40 users, 800 requests @ 15% fraud)
│
├── db/
│   ├── __init__.py
│   └── connection.py              # SQLAlchemy creator pattern (handles special chars in password)
│
├── models/
│   ├── *.pkl                      # Trained model files (NOT in git — auto-generated on startup)
│   └── *_meta.json               # Training metadata (accuracy, date, features, rows)
│
├── services/                      # Business logic (15 services)
│   ├── analytics_service.py       # Revenue trends + review trends
│   ├── anomaly_service.py         # Transaction anomaly detection
│   ├── benchmark_service.py       # BO vs platform ranking
│   ├── churn_service.py           # Churn risk prediction
│   ├── dashboard_service.py       # Dashboard KPI aggregation
│   ├── export_service.py          # PDF/CSV financial reports
│   ├── fraud_service.py           # Fraud detection
│   ├── material_service.py        # Material order stats
│   ├── notification_service.py    # Smart notification triggers
│   ├── order_service.py           # Fulfillment time computation
│   ├── product_service.py         # Quality, demand, stock
│   ├── profile_service.py         # Profile completeness
│   ├── retrain_service.py         # Model retraining (with oversampling + augmentation)
│   ├── sentiment_service.py       # Review sentiment (VADER)
│   └── triage_service.py          # Ticket auto-categorization
│
├── train/
│   └── train_models.py            # Train demand model from CSVs
│
└── docs/
    ├── AI_Master_Plan.md          # Full technical strategy
    ├── AI_Models_Explained.md     # Non-technical model guide (updated)
    └── AI_Integration_Guide.md    # Frontend/Backend integration guide
```

---

## 🔗 For the Angular Frontend Team

👉 Read the **[AI Integration Guide](docs/AI_Integration_Guide.md)**

### Key calls for the dashboard:
```typescript
// All KPI cards in one call
GET /ai/dashboard/{bo_id}

// Charts
GET /ai/analytics/revenue-trend/{bo_id}?period=monthly
GET /ai/reviews/trends/{bo_id}?period=monthly
GET /ai/benchmark/{bo_id}

// Download buttons
GET /ai/export/financial/{bo_id}?format=csv
GET /ai/export/financial/{bo_id}?format=pdf
```

---

## 🔗 For the .NET Backend Team

👉 Read the **[AI Integration Guide](docs/AI_Integration_Guide.md)** for C# HTTP client examples.

### When to call the AI service:
| Your Event | Call AI Endpoint |
|---|---|
| BO updates profile | `POST /ai/compute/profile/{bo_id}` |
| Product created/updated | `POST /ai/compute/product/{product_id}` |
| Production request submitted | `POST /ai/predict/fraud/{request_id}` |
| Production request completed | `POST /ai/compute/request/{request_id}` |
| New review submitted | `POST /ai/predict/sentiment/{review_id}` |
| New support ticket | `POST /ai/predict/triage/{ticket_id}` |
| New transaction | `POST /ai/predict/anomaly/{tx_id}` |
| BO logs in | `POST /ai/predict/churn/{user_id}` |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | Core language |
| **FastAPI** | REST API framework |
| **XGBoost** | Churn + Fraud classification models |
| **scikit-learn** | Isolation Forest anomaly detection |
| **VADER (nltk)** | Sentiment analysis NLP |
| **SQLAlchemy + pyodbc** | SQL Server connection (creator pattern for special chars) |
| **APScheduler** | Nightly + weekly cron jobs |
| **reportlab** | PDF report generation |
| **Docker** | Containerized deployment |
| **Hugging Face Spaces** | Cloud hosting (ephemeral storage — models auto-train on startup) |

---

## 🗄️ Database

- **Server:** `db52715.public.databaseasp.net`
- **Connection:** SQLAlchemy `creator` pattern (required for passwords with `+`, `#`, `=`)
- **Live data:** 9 users, 16 products, 1,012 transactions, 207 production requests, 229 reviews
- **AI columns:** Auto-populated by this service across 5 tables

---

## 🌱 Seed Data

The `data/` folder contains JSON seed files for the backend team:

| Folder | Contents |
|---|---|
| `for_backend_team/` | Base 9-table seed (original data) |
| `for_backend_team_extra/` | Extra data for ML improvement: 40 users, 800 requests (15% fraud), 300 reviews |

After inserting extra data, call `POST /ai/train/all` to retrain all models.

---

## 📝 License

Internal use only — Talentree Graduation Project (Faculty of Computer and Information Sciences).
