# 🌳 Talentree BO Dashboard — AI Engineer Master Plan
> **Strategy: Synthetic Pre-train → Connect DB → Retrain on Real Data**
> **DB**: db39807.public.databaseasp.net | **Updated**: April 16, 2026

---

## ✅ Already Done

| Task | Status |
|---|---|
| Connected to live DB | ✅ Done |
| Full schema audit + gap analysis sent to backend | ✅ Done |
| Confirmed AI engineer has full DB permissions (INSERT/UPDATE/SELECT/DELETE) | ✅ Done |
| Strategy decided: Synthetic → Train → Connect DB → Retrain | ✅ Done |
| **Backend created all 4 missing tables** (ProductReviews, SupportTickets, TicketMessages, OnboardingProgress) | ✅ Done Apr 16 |
| **DB now has 35 tables — Schema 100% complete** | ✅ Done Apr 16 |
| All 20 AI columns deployed in correct tables | ✅ Done |

### Current Live DB State (April 16, 2026)
| Table | Rows | Ready? |
|---|---|---|
| AspNetUsers | 63 | ✅ Has data |
| BusinessOwnerProfile | 25 | ✅ Has data |
| Products | 12 | ✅ Has data |
| BoProductionRequests | 12 | ✅ Has data |
| RawMaterials | 31 | ✅ Has data |
| MaterialOrders | 10 | ✅ Has data |
| Transactions | 0 | ⏳ Needs synthetic seed |
| LoginHistories | 0 | ⏳ Needs synthetic seed |
| ProductReviews | 0 | ⏳ Needs synthetic seed |
| SupportTickets | 0 | ⏳ Needs synthetic seed |
| TicketMessages | 0 | ⏳ Needs synthetic seed |
| OnboardingProgress | 0 | ⏳ Needs synthetic seed |
| PayoutRequests | 0 | ⏳ Needs synthetic seed |

---

## 🔴 AI ENGINEER — WEEK 1: Generate Synthetic Data + Train Models

### Step 1: Generate Synthetic Data (Same Schema as DB)

Generate fake rows that match the **exact column format** of each table, using **real IDs from the DB** for foreign keys so INSERT works without FK errors.

#### `BoProductionRequests` — Generate 500 rows
```
Use real BusinessOwnerIds from DB (25 BOs)
Status mix: 40% Completed, 20% InProduction, 15% Submitted,
            10% Confirmed, 5% Rejected, 5% Cancelled, 5% Quoted
QuotedPrice: 2,000 – 50,000 EGP
Label (IsFraudFlag): 10% flagged as fraud = 50 rows
FraudScore: fraud rows = 0.55–0.98, normal rows = 0.0–0.25
Dates: spanning last 6 months
```

#### `LoginHistories` — Generate 3000 rows
```
Use real UserIds from AspNetUsers (63 users)
Active users: 10–30 logins per month
Churned users (IsActive=0): logins stop 30–60 days ago
IsSuccessful: 95% True, 5% False (failed attempts)
DeviceInfo: mix of Mobile/Desktop/Tablet
```

#### `Transactions` — Generate 1000 rows
```
Use real BusinessOwnerIds
Type: 50% Sale, 25% MaterialPurchase, 15% Refund, 10% Fee
Amount: Sales +500 to +15,000 | Purchases -200 to -5,000
Label (AnomalyFlag): 5% flagged = 50 rows
AnomalyScore: anomaly rows = 0.65–0.99, normal = 0.0–0.2
Dates: spanning last 4 months
StripePaymentIntentId: realistic pi_xxx strings
```

#### `Products` — Update Existing 13 Rows (Not Insert)
```
UPDATE Products SET:
  ViewCount     = realistic (50–2000)
  CartAddCount  = realistic (10–300)
  PurchaseCount = realistic (5–150)
  RevenueTotal  = Price × PurchaseCount
  AvgRating     = random 3.5–5.0
```

#### `AspNetUsers` — Update Existing: LoginCount
```
UPDATE AspNetUsers SET LoginCount = realistic (1–200)
Keep all other Identity columns untouched
```

---

### Step 2: Train ML Models (Offline, on Synthetic Data)

#### Model 1 — Churn Prediction (XGBoost)
```
Input features (from synthetic LoginHistories + AspNetUsers):
  - days_since_last_login
  - login_count_30d (logins in last 30 days)
  - total_login_count
  - account_age_days
  - has_production_requests (0/1)
  - has_material_orders (0/1)
  - profile_completeness

Label: IsActive = 0 → churned

Output → AspNetUsers.ChurnRiskScore (0.0–1.0)
Save → models/churn_model.pkl
Expected accuracy: ~82% on synthetic, ~90%+ after retrain on real
```

#### Model 2 — Fraud Detection (Isolation Forest + XGBoost)
```
Input features (from synthetic BoProductionRequests):
  - quoted_price
  - days_since_account_created
  - requests_count_per_bo
  - requests_per_day
  - has_no_quoted_price (0/1)
  - item_count_per_request

Label: IsFraudFlag = 1

Output → BoProductionRequests.FraudScore (0.0–1.0)
       → BoProductionRequests.IsFraudFlag (True if score >= 0.5)
Save → models/fraud_model.pkl
Expected accuracy: ~85% on synthetic, ~92%+ after retrain
```

#### Model 3 — Financial Anomaly Detection (Isolation Forest)
```
Input features (from synthetic Transactions):
  - amount
  - amount_vs_user_average (ratio)
  - transaction_hour
  - transactions_per_day_for_user
  - type_encoded

Label: AnomalyFlag = 1

Output → Transactions.AnomalyFlag + AnomalyScore
Save → models/anomaly_model.pkl
Expected accuracy: ~83% on synthetic, ~90%+ after retrain
```

#### Model 4 — Sentiment Analysis (Pre-trained BERT — No Training Needed)
```
No synthetic data needed — uses pre-trained weights

Arabic text → CAMeL-BERT (HuggingFace)
English text → VADER + distilbert-sentiment
Toxicity → Detoxify library

Output → ProductReviews.SentimentScore (-1 to +1)
       → ProductReviews.SentimentLabel (Positive/Neutral/Negative)
       → ProductReviews.FlaggedToxic (True/False)

Accuracy: ~90% out of the box (no training needed)
```

#### Model 5 — Support Ticket Auto-Triage (Zero-shot — No Training Needed)
```
No synthetic data needed — uses pre-trained weights

Model: facebook/bart-large-mnli (zero-shot classification)
Labels: Technical, Account, Payment, Other

Priority score: rule-based on keywords + urgency signals

Output → SupportTickets.PriorityScore (0.0–1.0)
       → SupportTickets.AutoCategory

Accuracy: ~80% out of the box
```

#### Model 6 — Description Quality Score (NLP Rules — No Training Needed)
```
Score each product description:
  + length score (0–0.3): min 50 chars for full score
  + keyword score (0–0.3): has relevant tags
  + readability score (0–0.2): Flesch score via textstat
  + completeness (0–0.2): no placeholder text

Output → Products.DescriptionQualityScore (0.0–1.0)
```

#### Model 7 — Demand Forecast (Prophet — Synthetic Time Series)
```
Generate 6 months of synthetic daily sales per product
Train Facebook Prophet on synthetic data

Output → Products.DemandForecastQty
       → Products.LowStockFlag (True if StockQty < ForecastQty × 0.5)
Save → models/demand_model_{product_id}.pkl
```

---

### Step 3: Compute Rule-Based Features (No Model Needed)

```
ProfileCompletenessPct  → Count filled fields / 10 × 100
FulfillmentTimeHours    → CompletedAt - CreatedAt in hours
OrderFrequency          → COUNT(*) from MaterialOrderItems per material
PriceTrend              → 'Stable' now (update when price history exists)
```

---

### Step 4: Missing SRS Features (FR-BO-30, FR-AI-08, FR-BO-23)

#### ✅ AI Notification Triggers (FR-BO-30–31)
```
When AI computes these results, INSERT a row into Notifications table:

  LowStockFlag = True            → Notify BO: "Product X is low on stock"
  DemandForecastQty > StockQty   → Notify BO: "Reorder recommended for Product X"
  ChurnRiskScore > 0.7           → Notify BO: "High churn risk detected for your account"
  IsFraudFlag = True             → Notify Admin: "Suspicious production request #ID"
  AnomalyFlag = True             → Notify BO: "Unusual transaction detected: Amount X"
  SentimentLabel = 'Negative'    → Notify BO: "New negative review on Product X"

INSERT into: Notifications (UserId, Type, Title, Message, RelatedEntityType, RelatedEntityId)
No new table needed — Notifications table already deployed ✅
```

#### ✅ Performance Benchmarking (FR-AI-08)
```
For each Business Owner, compare their metrics to category average:

  avg_order_value      → BO total revenue / BO order count vs category avg
  fulfillment_time     → BO avg FulfillmentTimeHours vs category avg
  product_quality_avg  → BO avg DescriptionQualityScore vs category avg
  review_score_avg     → BO avg AvgRating vs category avg
  churn_risk           → BO ChurnRiskScore vs platform avg

Output: JSON per BO with percentile ranking
Example: { "fulfillment_rank": "top 20%", "quality_rank": "bottom 40%" }

No ML needed — pure SQL aggregation + comparison
Save result to: BusinessOwnerProfile (new column needed: BenchmarkJson nvarchar(max))
  OR return via API endpoint only (no DB write)
```

#### ✅ Financial Report Export (FR-BO-23)
```
Generate PDF or CSV of Transactions for a BO:
  Date range filter
  Type filter (Sale/Refund/etc)
  Summary: total revenue, total expenses, net profit

Library: reportlab (PDF) + pandas (CSV)
Endpoint: GET /ai/export/financial/{bo_id}?format=pdf&from=2026-01-01&to=2026-04-01
Returns: file download

No ML needed — just data formatting
```

---

### Step 5: Dashboard & Analytics Endpoints (FR-BO-05, FR-BO-26, FR-AI-06, FR-BO-24)

#### ✅ Dashboard Summary Endpoint (FR-BO-05)
```
Frontend needs ONE call to populate the entire BO dashboard:

GET /ai/dashboard/{bo_id}
Returns:
{
  "revenue_total": 45000.00,
  "revenue_trend": "Rising",         ← new
  "total_orders": 8,
  "avg_fulfillment_hours": 432,
  "fraud_alerts": 1,
  "low_stock_count": 2,
  "churn_risk": 0.23,
  "profile_completeness": 80,
  "avg_product_quality": 0.76,
  "avg_review_sentiment": 0.65,
  "negative_reviews_count": 3,
  "open_tickets": 2,
  "benchmark": { "fulfillment_rank": "top 20%", ... }
}

No ML needed — aggregation query from all AI columns
```

#### ✅ Review Sentiment Trends Over Time (FR-BO-26)
```
Not just per-review score — need weekly/monthly trend for charts:

GET /ai/reviews/trends/{bo_id}?period=monthly
Returns:
[
  { "month": "2026-01", "avg_sentiment": 0.72, "count": 15, "negative_pct": 13 },
  { "month": "2026-02", "avg_sentiment": 0.68, "count": 22, "negative_pct": 18 },
  { "month": "2026-03", "avg_sentiment": 0.81, "count": 19, "negative_pct": 5 }
]

No ML needed — GROUP BY month on SentimentScore from ProductReviews
```

#### ✅ Sales & Revenue Trend Analysis (FR-AI-06)
```
Revenue trend over time for dashboard charts:

GET /ai/analytics/revenue-trend/{bo_id}?period=weekly
Returns:
[
  { "week": "2026-W10", "revenue": 5200, "orders": 3, "avg_order": 1733 },
  { "week": "2026-W11", "revenue": 8100, "orders": 5, "avg_order": 1620 },
  { "week": "2026-W12", "revenue": 7400, "orders": 4, "avg_order": 1850 }
]
+ overall_trend: "Rising" / "Stable" / "Falling" (compare last 4 weeks vs prior 4)

No ML needed — GROUP BY week on Transactions WHERE Type = 'Sale'
```

#### ✅ AvgRating Auto-Recalculation (FR-BO-24/26)
```
When a new review is added → recalculate Products.AvgRating:

AvgRating = SELECT AVG(CAST(Rating AS FLOAT)) FROM ProductReviews WHERE ProductId = ?
UPDATE Products SET AvgRating = ? WHERE Id = ?

Triggered by: POST /ai/predict/sentiment/{review_id}
(included in same call — no separate endpoint needed)
```

## 🔵 AI ENGINEER — WEEK 2: Build FastAPI + Connect to DB

### FastAPI Microservice Structure
```
talentree-ai/
├── main.py
├── config.py                ← DB connection string
├── scheduler.py             ← Nightly + weekly jobs
├── db/
│   └── connection.py        ← pyodbc connector
├── data/
│   └── seed_generator.py    ← Synthetic data generator
├── services/
│   ├── product_service.py      ← DescriptionQuality + LowStock + Demand + AvgRating
│   ├── profile_service.py      ← ProfileCompleteness
│   ├── order_service.py        ← FulfillmentHours + Fraud
│   ├── material_service.py     ← OrderFrequency + PriceTrend
│   ├── user_service.py         ← ChurnRiskScore
│   ├── sentiment_service.py    ← SentimentScore + Toxicity + AvgRating update
│   ├── triage_service.py       ← PriorityScore + AutoCategory
│   ├── notification_service.py ← AI notification triggers (FR-BO-30)
│   ├── benchmark_service.py    ← BO vs category benchmarking (FR-AI-08)
│   ├── export_service.py       ← PDF/CSV financial reports (FR-BO-23)
│   ├── dashboard_service.py    ← Single dashboard summary endpoint (FR-BO-05)
│   └── analytics_service.py    ← Revenue trends + Review trends (FR-AI-06, FR-BO-26)
├── models/
│   ├── churn_model.pkl      ← Trained Week 1
│   ├── fraud_model.pkl      ← Trained Week 1
│   ├── anomaly_model.pkl    ← Trained Week 1
│   └── demand_model_*.pkl   ← Trained Week 1
└── requirements.txt
```

### API Endpoints
```
# Compute endpoints (run anytime)
POST /ai/compute/product/{id}       → Quality + LowStock + Demand + AvgRating
POST /ai/compute/profile/{bo_id}    → ProfileCompleteness
POST /ai/compute/request/{id}       → FulfillmentHours + Fraud prediction
POST /ai/compute/materials/all      → OrderFrequency + PriceTrend
POST /ai/compute/all                → Run EVERYTHING

# Predict endpoints (use trained models)
POST /ai/predict/churn/{user_id}        → ChurnRiskScore
POST /ai/predict/fraud/{request_id}     → FraudScore + IsFraudFlag
POST /ai/predict/anomaly/{tx_id}        → AnomalyFlag + AnomalyScore
POST /ai/predict/sentiment/{review_id}  → SentimentScore + Label + Toxic + AvgRating update
POST /ai/predict/triage/{ticket_id}     → PriorityScore + AutoCategory
POST /ai/predict/demand/{product_id}    → DemandForecastQty

# Dashboard summary (FR-BO-05) ← NEW
GET  /ai/dashboard/{bo_id}          → Single JSON with ALL AI metrics for frontend dashboard

# Analytics & Trends (FR-AI-06, FR-BO-26) ← NEW
GET  /ai/analytics/revenue-trend/{bo_id}?period=weekly   → Revenue over time
GET  /ai/analytics/revenue-trend/{bo_id}?period=monthly  → Revenue over time
GET  /ai/reviews/trends/{bo_id}?period=monthly           → Sentiment trend over time

# Notification triggers (FR-BO-30–31)
POST /ai/notify/check/{bo_id}       → Check all thresholds, fire notifications if needed
POST /ai/notify/check/all           → Check all BOs and fire any needed notifications

# Benchmarking (FR-AI-08)
GET  /ai/benchmark/{bo_id}          → Return BO vs category percentile ranking (JSON)
GET  /ai/benchmark/all              → Return benchmarks for all BOs

# Financial Export (FR-BO-23)
GET  /ai/export/financial/{bo_id}?format=pdf&from=DATE&to=DATE  → Download PDF report
GET  /ai/export/financial/{bo_id}?format=csv&from=DATE&to=DATE  → Download CSV report

# Training endpoints
POST /ai/train/churn            → Retrain churn model on real DB data
POST /ai/train/fraud            → Retrain fraud model on real DB data
POST /ai/train/anomaly          → Retrain anomaly model on real DB data
POST /ai/train/all              → Retrain everything

# Status
GET  /ai/status                 → Health check
GET  /ai/models/status          → Which models trained + accuracy + last updated
```

### Scheduler
```python
# NIGHTLY (02:00 AM Cairo) — predict with current models
scheduler.add_job(compute_all_profiles,    'cron', hour=2, minute=0)
scheduler.add_job(compute_all_products,    'cron', hour=2, minute=5)
scheduler.add_job(compute_material_stats,  'cron', hour=2, minute=10)
scheduler.add_job(predict_all_churn,       'cron', hour=2, minute=15)
scheduler.add_job(predict_all_fraud,       'cron', hour=2, minute=20)
scheduler.add_job(predict_all_anomalies,   'cron', hour=2, minute=25)
scheduler.add_job(predict_all_sentiment,   'cron', hour=2, minute=30)
scheduler.add_job(predict_all_triage,      'cron', hour=2, minute=35)

# WEEKLY (Sunday 03:00 AM) — retrain models on accumulated real data
scheduler.add_job(retrain_all_models, 'cron', day_of_week='sun', hour=3)
```

---

## 🟠 ONGOING: Auto-Retrain as Real Data Grows

```
Week 1–2:   Models trained on synthetic data → Accuracy ~80–85%
Month 1:    100+ real requests, 200+ real logins → Models retrain → ~85–88%
Month 3:    500+ real transactions, 400+ real users → Retrain → ~90–92%
Month 6:    Full dataset → Retrain → ~92–95%

Model file is replaced automatically every Sunday
Same API endpoints — no code changes needed
Dashboard accuracy improves silently over time ✅
```

---

## 📋 BACKEND TEAM TASKS

### ✅ DONE — Tables Created (April 16)
```
✅ ProductReviews     → created with all AI columns
✅ SupportTickets     → created with PriorityScore, AutoCategory
✅ TicketMessages     → created
✅ OnboardingProgress → created
```

### Remaining — Call AI Endpoints on Events (Next Sprint)

| When This Happens in Backend | Call This AI Endpoint |
|---|---|
| BO updates profile | `POST /ai/compute/profile/{bo_id}` |
| Product created or updated | `POST /ai/compute/product/{product_id}` |
| Production request status → Completed | `POST /ai/compute/request/{request_id}` |
| Material order placed | `POST /ai/compute/materials/all` |
| New review submitted | `POST /ai/predict/sentiment/{review_id}` |
| New support ticket created | `POST /ai/predict/triage/{ticket_id}` |
| New transaction recorded | `POST /ai/predict/anomaly/{transaction_id}` |

---

## 📊 Execution Timeline

```
✅ COMPLETED
   Schema audit, gap analysis, backend created all 4 tables
   DB = 35 tables, 20 AI columns, schema 100% complete

🔴 NOW — AI Engineer Week 1 (Start immediately)
   Day 1–2: Build seed_generator.py → run → 7 tables filled
   Day 3–4: Build train_models.py   → run → 4 models trained (.pkl files)
   Day 5–6: Build FastAPI + services → test locally
   Day 7:   Run /ai/compute/all → all AI columns filled in DB ✅

🔵 WEEK 2 — AI Engineer
   Deploy FastAPI to server
   Enable nightly scheduler
   Dashboard shows LIVE AI values ✅

🟡 BACKEND — Next Sprint
   Add HTTP calls to AI endpoints on events

⏰ ONGOING — Automatic forever
   Nightly: recompute all predictions
   Weekly: retrain models as real data grows
   Accuracy: 80% now → 90%+ after 3 months real data
```

---

## 🗂️ Project Files

| File | Purpose |
|---|---|
| `AI_Master_Plan.md` | This file |
| `BO_MVP_Database_Schema.md` | Live schema — 31 tables, all AI columns |
| `BO_MVP_Database_Schema.html` | Visual formatted schema |
| `db_schema_dump.txt` | Raw column dump from live DB |
