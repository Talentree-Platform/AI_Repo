# 🌳 Talentree AI Service — Business Owner Dashboard

> **AI-powered microservice for real-time predictions, analytics, and smart notifications**  
> Built by: Mai Farahat | AI Engineer  
> Last Updated: April 18, 2026

---

## 📌 What Is This?

This is the **AI brain** of the Talentree Business Owner (BO) Dashboard. It runs as a standalone FastAPI microservice that:

- 🔮 **Predicts** churn risk, fraud, anomalies, and demand
- 📊 **Analyzes** reviews, revenue trends, and performance benchmarks
- 🔔 **Notifies** BOs and admins when thresholds are crossed
- 📄 **Exports** financial reports as PDF/CSV
- 🤖 **Retrains** models automatically every week on real data

---

## 📖 Documentation

| Document | Who It's For | What's Inside |
|---|---|---|
| [**AI Models Explained**](AI_Models_Explained.md) | Everyone (PM, Dev, Design) | Plain-English explanation of every model and insight |
| [**AI Integration Guide**](AI_Integration_Guide.md) | Angular + .NET teams | Endpoints, TypeScript interfaces, chart code examples |
| [**AI Master Plan**](AI_Master_Plan.md) | AI Engineer / Tech Lead | Full technical strategy, DB schema, training pipeline |

---

## 🏗️ Architecture

```
┌──────────────────┐     JSON/REST      ┌───────────────────────┐
│  Angular Frontend │ ─────────────────► │  Talentree AI Service │
│  (Charts, Cards)  │                    │  FastAPI  :8000       │
└──────────────────┘                     │                       │
                                         │  ┌─ churn_service     │
┌──────────────────┐     HTTP calls      │  ├─ fraud_service     │
│  .NET Backend     │ ─────────────────► │  ├─ anomaly_service   │
│  (Event triggers) │                    │  ├─ sentiment_service │     ┌───────────┐
└──────────────────┘                     │  ├─ triage_service    │────►│  SQL      │
                                         │  ├─ product_service   │     │  Server   │
┌──────────────────┐     CRON jobs       │  ├─ dashboard_service │     │  (Remote) │
│  Scheduler        │ ─────────────────► │  ├─ export_service    │     └───────────┘
│  (Nightly/Weekly) │                    │  └─ retrain_service   │
└──────────────────┘                     └───────────────────────┘
```

---

## 🚀 Quick Start

### Option 1 — Docker (Recommended)
```bash
# Clone the repo
git clone -b feature/bo-dashboard https://github.com/Talentree-Platform/AI_Repo.git
cd AI_Repo

# Copy environment config
cp .env.example .env

# Run with Docker Compose
docker compose up --build -d

# API available at:
# http://localhost:8080/docs  (Swagger UI)
```

### Option 2 — Local Python
```bash
# Clone the repo
git clone -b feature/bo-dashboard https://github.com/Talentree-Platform/AI_Repo.git
cd AI_Repo

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# API available at:
# http://localhost:8000/docs  (Swagger UI)
```

### First-Time Setup (Seed Data + Train Models)
```bash
# 1. Seed synthetic data into the DB
python data/seed_generator.py

# 2. Train all ML models
python train/train_models.py

# 3. Run all AI computations
curl -X POST http://localhost:8000/ai/compute/all

# 4. Verify everything works
python test_api.py
```

---

## 📡 All API Endpoints (20 total)

### Health & Status
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ai/status` | Health check |
| `GET` | `/ai/models/status` | Model accuracy & last trained |

### Dashboard & Analytics *(Frontend calls these)*
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ai/dashboard/{bo_id}` | All 14 KPI metrics in one call |
| `GET` | `/ai/analytics/revenue-trend/{bo_id}?period=monthly` | Revenue line chart data |
| `GET` | `/ai/reviews/trends/{bo_id}?period=monthly` | Sentiment bar chart data |
| `GET` | `/ai/benchmark/{bo_id}` | BO vs platform percentile ranking |

### Predictions *(Backend calls on events)*
| Method | Endpoint | Trigger |
|---|---|---|
| `POST` | `/ai/predict/churn/{user_id}` | BO logs in |
| `POST` | `/ai/predict/fraud/{request_id}` | New production request |
| `POST` | `/ai/predict/anomaly/{tx_id}` | New transaction |
| `POST` | `/ai/predict/sentiment/{review_id}` | New review submitted |
| `POST` | `/ai/predict/triage/{ticket_id}` | New support ticket |
| `POST` | `/ai/predict/demand/{product_id}` | Product updated |

### Compute *(Batch processing)*
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ai/compute/product/{id}` | Quality + LowStock + Demand |
| `POST` | `/ai/compute/profile/{bo_id}` | Profile completeness % |
| `POST` | `/ai/compute/request/{id}` | Fulfillment time + Fraud |
| `POST` | `/ai/compute/materials/all` | OrderFrequency + PriceTrend |
| `POST` | `/ai/compute/all` | Run everything (takes ~2 min) |

### Notifications & Export
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ai/notify/check/{bo_id}` | Check thresholds, fire alerts |
| `GET` | `/ai/export/financial/{bo_id}?format=csv` | Download CSV report |
| `GET` | `/ai/export/financial/{bo_id}?format=pdf` | Download PDF report |

### Model Training
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ai/train/churn` | Retrain churn model on real data |
| `POST` | `/ai/train/fraud` | Retrain fraud model |
| `POST` | `/ai/train/anomaly` | Retrain anomaly model |
| `POST` | `/ai/train/all` | Retrain all models |

---

## 🤖 AI Models

| # | Model | Algorithm | Input | Output | Accuracy |
|---|---|---|---|---|---|
| 1 | Churn Risk | XGBoost | Login history, orders, profile | `ChurnRiskScore` (0–1) | ~100%* |
| 2 | Fraud Detection | XGBoost | Price, frequency, behavior | `FraudScore` + `IsFraudFlag` | ~100%* |
| 3 | Anomaly Detection | Isolation Forest | Amount, hour, patterns | `AnomalyScore` + `AnomalyFlag` | ~98% |
| 4 | Sentiment Analysis | VADER NLP | Review text | `SentimentScore` + label | ~85% |
| 5 | Ticket Triage | Keywords | Ticket title + message | `PriorityScore` + `AutoCategory` | ~80% |
| 6 | Demand Forecast | Linear Regression | Purchase history | `DemandForecastQty` + `LowStockFlag` | ~75% |
| 7 | Description Quality | NLP Rules | Product description | `DescriptionQualityScore` (0–1) | N/A |

> *\*Trained on synthetic data. Accuracy improves automatically as real data grows (→ 90%+ by month 3).*

---

## ⏰ Automated Scheduler

| Time (Cairo) | Job | Frequency |
|---|---|---|
| 02:00 AM | Recompute all predictions for all BOs | Every night |
| 02:05 AM | Update product metrics | Every night |
| 02:10 AM | Update material stats | Every night |
| 02:15–02:45 AM | Predict churn, fraud, anomalies, sentiment, triage | Every night |
| 02:45 AM | Check notification thresholds | Every night |
| 03:00 AM Sunday | **Retrain all models** on accumulated real data | Weekly |

---

## 📁 Project Structure

```
talentree-ai/
├── main.py                        # FastAPI app — 20 endpoints
├── config.py                      # DB connection (env vars for Docker)
├── scheduler.py                   # APScheduler — nightly + weekly jobs
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker image definition
├── docker-compose.yml             # One-command deployment
├── .env.example                   # Environment variables template
├── test_api.py                    # Test all 20 endpoints
│
├── data/
│   ├── seed_generator.py          # Generate synthetic DB rows
│   ├── seed_resume.py             # Resume interrupted seeding
│   └── generate_training_data.py  # Export training CSVs from DB
│
├── db/
│   ├── __init__.py
│   └── connection.py              # pyodbc SQL Server connector
│
├── models/
│   ├── churn_model.pkl            # Trained XGBoost churn model
│   ├── fraud_model.pkl            # Trained XGBoost fraud model
│   ├── anomaly_model.pkl          # Trained Isolation Forest model
│   ├── demand_model.pkl           # Trained regression model
│   └── *_meta.json               # Training metadata (accuracy, date, features)
│
├── services/                      # Business logic (16 services)
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
│   ├── retrain_service.py         # Model retraining on real data
│   ├── sentiment_service.py       # Review sentiment (VADER)
│   └── triage_service.py          # Ticket auto-categorization
│
├── train/
│   └── train_models.py            # Train all 4 ML models from CSVs
│
└── docs/
    ├── AI_Master_Plan.md          # Full technical strategy
    ├── AI_Models_Explained.md     # Non-technical model guide
    └── AI_Integration_Guide.md    # Frontend/Backend integration
```

---

## 🔗 For the Angular Frontend Team

👉 Read the **[AI Integration Guide](AI_Integration_Guide.md)** — it has:
- Exact JSON response formats
- TypeScript interfaces you can copy-paste
- ApexCharts code for revenue, sentiment, and benchmark charts
- Download button implementation for CSV/PDF export
- Environment config setup

### Key calls for the dashboard:
```typescript
GET  /ai/dashboard/{bo_id}                          → KPI cards
GET  /ai/analytics/revenue-trend/{bo_id}?period=monthly  → Line chart
GET  /ai/reviews/trends/{bo_id}?period=monthly           → Bar chart
GET  /ai/benchmark/{bo_id}                               → Radar chart
GET  /ai/export/financial/{bo_id}?format=pdf             → Download
```

---

## 🔗 For the .NET Backend Team

👉 Read the **[AI Integration Guide](AI_Integration_Guide.md)** — it has C# HTTP client examples.

### When to call the AI service:
| Your Event | Call AI Endpoint |
|---|---|
| BO updates profile | `POST /ai/compute/profile/{bo_id}` |
| Product created/updated | `POST /ai/compute/product/{product_id}` |
| Production request completed | `POST /ai/compute/request/{request_id}` |
| New review submitted | `POST /ai/predict/sentiment/{review_id}` |
| New support ticket | `POST /ai/predict/triage/{ticket_id}` |
| New transaction | `POST /ai/predict/anomaly/{tx_id}` |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | Core language |
| **FastAPI** | REST API framework |
| **XGBoost** | Churn + Fraud models |
| **scikit-learn** | Anomaly detection (Isolation Forest) |
| **VADER** | Sentiment analysis (NLP) |
| **pyodbc** | SQL Server database connector |
| **APScheduler** | Nightly + weekly job scheduler |
| **reportlab** | PDF report generation |
| **Docker** | Containerized deployment |

---

## 📊 Database

- **Server:** `db39807.public.databaseasp.net`
- **Tables used:** 35 total (see [AI Master Plan](AI_Master_Plan.md#current-live-db-state-april-16-2026))
- **AI columns:** 20 columns across 5 tables (auto-populated by this service)

---

## 📝 License

Internal use only — Talentree Graduation Project (Faculty of Computer and Information Sciences).
