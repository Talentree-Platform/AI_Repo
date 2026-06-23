# Admin AI Models Explained — What We Built & Why
> **Audience:** Everyone on the team (developers, designers, PMs, stakeholders)
> **Written by:** AI Engineer
> **Last Updated:** June 2026
> **Dashboard:** Admin Dashboard only (platform-wide, not per-seller)
> **Live API:** https://talentree-ai-service.azurewebsites.net/docs

---

## Overview

The Admin Dashboard introduces **2 new AI models** (Models 8 and 9) on top of the 7 existing BO models.

Unlike the BO models which give each **seller** insight about their own business, these 2 models give **super-admins** platform-wide intelligence:

| # | What | For Who | Answers |
|---|---|---|---|
| 8 | Revenue Forecasting | Platform admins | "How much will we earn next quarter?" |
| 9 | Customer RFM Segmentation | Platform admins | "Which customers are our best, and which are we losing?" |

The admin dashboard also **reuses all 7 existing BO model outputs** — it reads the AI-scored columns already written to the DB and aggregates them into platform-wide metrics.

---

## How the Admin Dashboard Reuses Existing Models

| Existing BO Model | What Admin Reads | Where It Shows |
|---|---|---|
| Model 1 — Churn Risk | `AspNetUsers.ChurnRiskScore` per seller | Seller risk ranking, Seller Churn Rate KPI |
| Model 2 — Fraud Detection | `BoProductionRequests.IsFraudFlag` | Platform fraud rate KPI, fraud alert feed |
| Model 3 — Anomaly Detection | `Transactions.AnomalyFlag`, `AnomalyScore` | Anomaly alert feed, Financial Integrity KPI |
| Model 4 — Sentiment | `ProductReviews.SentimentLabel`, `SentimentScore` | Customer satisfaction KPI, sentiment breakdown chart |
| Model 5 — Triage | `SupportTickets.AutoCategory`, `PriorityScore` | Ticket stats, overdue alert feed |
| Model 6 — Demand | `Products.LowStockFlag`, `DemandForecastQty` | Low stock alert feed |
| Model 7 — Quality | `Products.DescriptionQualityScore` | Avg quality score per category |

**Zero extra computation.** The admin service simply reads the columns already written by the nightly BO scheduler.

---

## Model 8 — Revenue Forecasting 📈

### What does it do?
Predicts how much platform-wide gross sales revenue will be generated in the **next 3 months**.

Think of it as: *"Based on how revenue has been growing, where will we be by September?"*

### How does it work?
1. Pulls the **last 12 months** of monthly revenue from the `Transactions` table (`Type = 'Sale'`)
2. Maps each month to a numeric index (January = 1, February = 2 … December = 12)
3. Fits a **Linear Regression** model: `revenue = (slope × month_index) + intercept`
4. Predicts indices 13, 14, 15 (the next 3 months)
5. Converts predicted indices back to readable month labels (`2026-07`, `2026-08`, `2026-09`)

### Example Output
```json
{
  "actuals": [
    { "month": "2026-01", "revenue": 12400.00 },
    { "month": "2026-02", "revenue": 13100.00 },
    { "month": "2026-03", "revenue": 14800.00 },
    { "month": "2026-04", "revenue": 15200.00 },
    { "month": "2026-05", "revenue": 16100.00 },
    { "month": "2026-06", "revenue": 17300.00 }
  ],
  "forecast": [
    { "month": "2026-07", "forecasted_revenue": 18400.00 },
    { "month": "2026-08", "forecasted_revenue": 19500.00 },
    { "month": "2026-09", "forecasted_revenue": 20600.00 }
  ],
  "model_meta": {
    "method": "LinearRegression",
    "r2_score": 0.9712,
    "trained_at": "2026-06-22T03:30:00"
  }
}
```

### What is R² Score?
R² (R-squared) measures how well the model explains the trend:
- **1.0** = Perfect fit — the line passes through every data point
- **0.9+** = Excellent — model captures the trend well
- **0.7–0.9** = Good — useful prediction
- **< 0.5** = Poor — too much noise, treat forecast as rough estimate

### Fallback Behavior
- **Less than 2 months of data:** Model skips training and uses a simple "average of last 3 months" flat forecast
- **Less than 12 months of data:** Model trains on whatever is available — still valid, just lower confidence

### When Does It Retrain?
- Every **Sunday at 03:30 Cairo time** (after the weekly BO model retrain at 03:00)
- Can also be triggered manually via `POST /admin/train/forecast`

### Algorithm: Linear Regression
```
revenue = slope × month_index + intercept

Example:
  slope     = +1,100  (platform grows ~1,100 EGP/month)
  intercept = 11,300
  Month 13  = 1100 × 13 + 11300 = 25,600 EGP predicted
```

### Why not use ARIMA or Prophet?
Linear Regression is appropriate here because:
- We have **< 12 months** of data currently — ARIMA needs 24+ months
- Platform is early-stage — growth trend is roughly linear
- When data grows to 2+ years, switching to ARIMA is straightforward (same endpoint, different model inside the pkl)

### Accuracy Note
- Current R² depends on actual transaction data
- As more months accumulate, the prediction confidence will increase
- The forecast visualizes the trend — not a guaranteed number

---

## Model 9 — Customer RFM Segmentation 👥

### What does it do?
Groups every B2C customer into **one of 4 behavioral segments** based on their purchase history:

| Segment | Who They Are |
|---|---|
| 🏆 **Champion** | High spenders, buy frequently, bought recently |
| 💛 **Loyal** | Regular buyers, medium spend, still active |
| ⚠️ **At Risk** | Used to be good, now going quiet |
| ❌ **Lost** | Barely bought anything, not seen recently |

### What is RFM?
RFM stands for 3 customer behavior signals:

| Signal | Full Name | What it measures | Example |
|---|---|---|---|
| **R** | Recency | Days since last purchase | 5 days ago = great, 200 days = bad |
| **F** | Frequency | Total number of orders | 10 orders = loyal, 1 order = one-time |
| **M** | Monetary | Total amount spent (EGP) | 5,000 EGP = high value, 50 EGP = low |

### How does it work?
1. Queries `CustomerOrders` joined to `AspNetUsers` to compute R, F, M per customer
2. **Normalizes** scores to 0–1 range using MinMaxScaler (so EGP and days are on same scale)
3. Runs **K-Means Clustering** with k=4 clusters
4. Ranks cluster centers by composite score: `-Recency + Frequency + Monetary`
5. Highest composite → `Champion`, then `Loyal`, then `At Risk`, lowest → `Lost`
6. Writes the label back to `AspNetUsers.RfmSegment` in the database

### Example Output
```json
{
  "source": "database",
  "distribution": {
    "Champion": 3,
    "Loyal": 8,
    "At Risk": 12,
    "Lost": 5
  },
  "total": 28
}
```

### What Does K-Means Do?
K-Means finds 4 natural clusters in the customer data:

```
  High M  │  ●● Champion     ● Loyal
           │    (buy a lot)   (regular)
           │
  Low M   │  ● At Risk      ●● Lost
           │   (fading)      (gone)
           └────────────────────────────
               Low R            High R
             (recent)         (not recent)
```

Each customer is assigned to the closest cluster center. The cluster with the best combination of recent, frequent, and high-spend gets labeled "Champion".

### Fallback: Rule-Based (When Data is Too Small)
When fewer than 4 customers have orders, K-Means can't form 4 meaningful clusters. The system falls back to simple rules:

| Rule | Label |
|---|---|
| Last order < 30 days AND 2+ orders AND 500+ EGP spend | Champion |
| Last order < 60 days AND at least 1 order | Loyal |
| Last order < 180 days | At Risk |
| Everything else | Lost |

### Database Column Required
The `.NET backend team` must add this column before the model can write results:
```sql
ALTER TABLE AspNetUsers
ADD RfmSegment NVARCHAR(20) NULL;
```
If the column doesn't exist yet, the service computes segments live but doesn't persist them.

### When Does It Run?
- Every **Sunday at 03:45 Cairo time** (after the forecast retrain at 03:30)
- Can also be triggered manually via `POST /admin/train/rfm`

### Why K-Means and Not Something Else?
K-Means is the **industry standard** for RFM segmentation because:
- No labeled training data needed (unsupervised)
- Fast even on large customer bases
- Produces stable, interpretable segments
- RFM + K-Means is used by Amazon, Netflix, and Shopify for customer segmentation

---

## What Happens Automatically Every Week (Admin Jobs)

| Time | Job | What It Does |
|---|---|---|
| Sunday 03:00 Cairo | BO Model Retrain | Retrains all 7 BO models (churn, fraud, anomaly, etc.) |
| Sunday 03:30 Cairo | Admin Forecast Retrain | Updates LinearRegression model with latest monthly revenue |
| Sunday 03:45 Cairo | Admin RFM Retrain + Segment | Re-clusters customers, writes new RfmSegment labels to DB |

---

## How These Models Improve Over Time

| Now (June 2026) | Month 3 | Month 6 | Month 12 |
|---|---|---|---|
| Forecast: 12 months data, R²~0.85 | Forecast: more stable trend | Forecast: Consider ARIMA upgrade | Forecast: High confidence seasonal patterns |
| RFM: 3 B2C orders → rule-based fallback | RFM: 15+ orders → K-Means activates | RFM: Clear segment patterns | RFM: Champion/Loyal ratio stabilizes |

---

## Platform Health Score — How It's Calculated

The **Platform Health Score** is a composite KPI (0–100) that gives admins a single number representing platform wellness:

```
Health Score =
  (Avg Customer Rating / 5.0) × 40      ← Satisfaction drives 40% of score
  + (min(Conversion Rate, 50) / 50) × 20 ← Are customers buying?
  + ((100 - Churn Rate) / 100) × 20      ← Are sellers staying?
  + ((100 - Fraud Rate) / 100) × 10      ← Is the platform safe?
  + ((100 - Anomaly Rate) / 100) × 10    ← Are finances clean?
```

| Score | Label |
|---|---|
| 80–100 | Excellent ✅ |
| 60–79 | Good 🟡 |
| 40–59 | Fair 🟠 |
| 0–39 | Needs Attention 🔴 |
