# Admin Dashboard — Implementation Plan
> **Document Type:** Technical Architecture & Engineering Record
> **Author:** AI Engineer
> **Date:** June 2026
> **Branch:** `feature/admin-dashboard` (branched from `feature/bo-dashboard`)
> **Deployment:** Azure App Service → `https://talentree-ai-service.azurewebsites.net`

---

## 1. Architecture Decision

### Why Same Service as BO Dashboard?

| Factor | Same Service ✅ (Chosen) | Separate Project ❌ |
|---|---|---|
| DB Connection | Shared SQLAlchemy engine pool | Duplicate connection setup |
| ML Libraries | sklearn, xgboost already installed | Must reinstall everything |
| Deployment | One Docker container, one Azure App Service | Second container + second cost |
| Code Reuse | Admin services import BO service functions | Zero reuse |
| Maintenance | DB schema changes → fix once | Fix in two places |
| Scheduler | APScheduler instance shared | Second scheduler process |

**Decision:** Add admin endpoints to the same FastAPI service on branch `feature/admin-dashboard`. Zero new infrastructure.

### Branch Structure
```
feature/bo-dashboard   ← stable, deployed, unchanged
        ↓  git checkout -b
feature/admin-dashboard  ← all admin code added here
```

---

## 2. Database Schema (Verified from Live DB)

### Integer Status Mappings

| Table | Column | Mapping |
|---|---|---|
| `BusinessOwnerProfile` | `Status` | `1`=Pending `2`=Approved `3`=Suspended |
| `Products` | `Status` | `2`=Pending `3`=Approved |
| `CustomerOrders` | `Status` | `1`=Pending `2`=Processing `3`=Shipped `4`=Delivered `5`=Cancelled |
| `SupportTickets` | `Status` | `1`=Open `2`=InProgress `3`=Resolved `4`=Closed `5`=Cancelled |
| `Complaints` | `Status` | `1`=Open `2`=UnderInvestigation `3`=Resolved |

### String Status Values (B2B Orders)
`Submitted` | `UnderReview` | `Quoted` | `Confirmed` | `InProduction` | `Completed` | `Rejected` | `Cancelled`

### Transaction Types
`Sale` | `Payout` | `Refund` | `Fee` | `MaterialPurchase` | `ProductionRequest`

### Key AI Columns (Written by BO Nightly Jobs, Read by Admin)
| Column | Table | Written By |
|---|---|---|
| `ChurnRiskScore` | `AspNetUsers` | churn_service (Model 1) |
| `IsFraudFlag`, `FraudScore` | `BoProductionRequests` | fraud_service (Model 2) |
| `AnomalyFlag`, `AnomalyScore` | `Transactions` | anomaly_service (Model 3) |
| `SentimentScore`, `SentimentLabel` | `ProductReviews` | sentiment_service (Model 4) |
| `AutoCategory`, `PriorityScore` | `SupportTickets` | triage_service (Model 5) |
| `LowStockFlag`, `DemandForecastQty` | `Products` | product_service (Model 6) |
| `DescriptionQualityScore` | `Products` | product_service (Model 7) |

### New Column Required from Backend Team
```sql
-- Ask .NET backend team to run this migration:
ALTER TABLE AspNetUsers
ADD RfmSegment NVARCHAR(20) NULL;
```
This column stores RFM segment labels (`Champion`, `Loyal`, `At Risk`, `Lost`) for each customer.
Nullable — null means not yet segmented. Safe to add at any time; the system handles missing column gracefully.

---

## 3. The 9 Services

### Services Overview

| File | SRS Ref | Endpoint(s) | Lines |
|---|---|---|---|
| `admin_dashboard_service.py` | FR-AD-01 | `GET /admin/dashboard` | ~200 |
| `admin_kpi_service.py` | FR-AD-02 | `GET /admin/kpis` | ~100 |
| `admin_analytics_service.py` | FR-AD-18 | `GET /admin/analytics` | ~110 |
| `admin_seller_service.py` | FR-AD-19 | `GET /admin/sellers`, `GET /admin/sellers/{id}` | ~120 |
| `admin_customer_service.py` | FR-AD-20 | `GET /admin/customers` | ~110 |
| `admin_category_service.py` | FR-AD-21 | `GET /admin/categories`, `GET /admin/categories/{id}/trend` | ~90 |
| `admin_export_service.py` | FR-AD-02 | `GET /admin/export/kpis` | ~130 |
| `admin_forecast_service.py` | Model 8 | `GET /admin/analytics/forecast`, `POST /admin/train/forecast` | ~130 |
| `admin_rfm_service.py` | Model 9 | `GET /admin/customers/segments`, `POST /admin/train/rfm` | ~170 |

---

### Service 1: `admin_dashboard_service.py`

**Purpose:** One-call platform overview — all metric cards + all alert feeds.

**Queries run (12 total):**
1. Seller counts by status (approved / pending / suspended)
2. Total customer count
3. Product counts (total / approved / pending)
4. B2C order counts by status (5 statuses)
5. B2B order counts by status (8 statuses)
6. Current month net revenue (Sales − Refunds from `Transactions`)
7. Overdue complaints (Status=1, older than 48h)
8. Overdue support tickets (Status=1/2, older than 48h)
9. Alert: top 10 low-stock products (`LowStockFlag=1`)
10. Alert: top 10 sellers awaiting approval (`Status=1`)
11. Alert: top 10 overdue complaints (oldest first)
12. Alert: top 10 anomaly transactions (`AnomalyFlag=1`, sorted by score)

**Response structure:**
```json
{
  "sellers": { "total": 6, "active": 5, "pending": 1, "suspended": 0 },
  "customers_total": 13,
  "products": { "total": 16, "approved": 14, "pending": 2 },
  "b2c_orders": { "pending": 1, "processing": 0, "delivered": 2, "total": 3 },
  "b2b_orders": { "completed": 45, "in_production": 3, "total": 207 },
  "current_month_revenue": 17350.00,
  "pending_actions": { "total": 4, "sellers_pending_approval": 1, ... },
  "alerts": {
    "low_stock_products": [...],
    "sellers_awaiting_approval": [...],
    "overdue_complaints": [...],
    "anomaly_transactions": [...]
  },
  "recent_activity": { "new_sellers": [...], "new_products": [...], "recent_tickets": [...] }
}
```

---

### Service 2: `admin_kpi_service.py`

**Purpose:** 9 platform KPIs + composite Platform Health Score.

**KPIs:**
1. `customer_conversion_rate` — % customers who placed at least 1 order
2. `average_order_value` — AVG(`CustomerOrders.TotalAmount`) excluding cancelled
3. `seller_churn_rate` — % sellers with `ChurnRiskScore > 0.7`
4. `product_approval_rate` — % products with `Status = 3`
5. `customer_satisfaction_rating` — AVG(`ProductReviews.Rating`)
6. `fraud_rate` — % B2B requests with `IsFraudFlag = 1`
7. `transaction_anomaly_rate` — % transactions with `AnomalyFlag = 1`
8. `avg_fulfillment_hours` — AVG time to complete B2B orders
9. `avg_seller_profile_completeness` — AVG(`ProfileCompletenessPct`)

**Health Score Formula:**
```
Health = (satisfaction/5 × 40) + (conversion/50 × 20) +
         ((100−churn)/100 × 20) + ((100−fraud)/100 × 10) +
         ((100−anomaly)/100 × 10)
```

---

### Service 3: `admin_analytics_service.py`

**Purpose:** Time-series data for 6 chart types. Supports `?period=weekly|monthly`.

**Charts:**
1. Revenue trend (gross sales / refunds / fees / net — per period)
2. User growth (new sellers vs new customers — per period)
3. Order volume (total / delivered / cancelled + value — per period)
4. Category distribution (products, purchases, revenue, rating per category)
5. B2B order status distribution (pie/donut chart data)
6. Sentiment breakdown (Positive / Neutral / Negative counts + avg score)

---

### Service 4: `admin_seller_service.py`

**Purpose:** Ranked seller table with AI risk signals.

**Per-seller data:**
- Business info (name, category, email, approval status, join date)
- AI Risk: `ChurnRiskScore` + computed `risk_level` (Healthy / Medium / High Risk)
- Revenue: SUM of Sale transactions
- Orders: B2B total + completed count + avg fulfillment hours
- Rating: AVG review rating across all seller products
- Quality: AVG `DescriptionQualityScore`
- Fraud: AVG `FraudScore`

**Sort options:** `?sort_by=revenue|rating|risk|orders`

**Detail endpoint:** Adds 6-month monthly revenue sparkline per seller.

---

### Service 5: `admin_customer_service.py`

**Purpose:** B2C customer cohort analysis.

**6 cohorts returned:**
1. Top 10 customers by CLV (lifetime value)
2. Inactive customers (no order in 90+ days)
3. Peak shopping hours histogram (0–23h)
4. Top 10 most wishlisted products
5. Category purchase preferences
6. New vs returning customers (last 30 days)

---

### Service 6: `admin_category_service.py`

**Purpose:** Performance metrics for each product category using the real `Categories` table.

**Per category:**
- Product counts (total / approved / pending) + approval rate %
- Pricing range (avg / min / max)
- Total purchases, revenue, views
- Average rating and description quality score
- Low-stock product count
- Number of active sellers in this category

---

### Service 7: `admin_export_service.py`

**Purpose:** Download reports in two formats.

**CSV format:**
- Flat CSV with all 9 KPIs + health score

**XLSX format (3 sheets, styled):**
- Sheet 1: Platform KPIs (dark blue headers, alternating row fill)
- Sheet 2: Sellers Report (all sellers ranked by revenue)
- Sheet 3: Category Analytics (all categories with metrics)

**Library:** `openpyxl` — added to `requirements.txt`

---

### Service 8: `admin_forecast_service.py` — Model 8 (NEW)

**Purpose:** 3-month revenue forecast.

**Training pipeline:**
```python
# 1. Query last 12 months of monthly revenue
months   = ['2025-07', '2025-08', ..., '2026-06']   # 12 data points
revenues = [12400, 13100, ..., 17300]

# 2. Encode as numeric indices
X = [0, 1, 2, ..., 11]   # month index
y = [12400, 13100, ..., 17300]   # revenue

# 3. Fit LinearRegression
model = LinearRegression().fit(X.reshape(-1,1), y)

# 4. Predict next 3 months (indices 12, 13, 14)
predictions = model.predict([[12], [13], [14]])
# → [18400, 19500, 20600]

# 5. Save model to admin_forecast_model.pkl
```

**Fallback:** When < 2 months data → flat average of last 3 months.

**Scheduler:** Sunday 03:30 Cairo — `job_admin_forecast()`

---

### Service 9: `admin_rfm_service.py` — Model 9 (NEW)

**Purpose:** K-Means customer segmentation.

**Training pipeline:**
```python
# 1. Compute RFM per customer from CustomerOrders
rfm = [(recency_days, frequency, monetary), ...]

# 2. Normalize to 0-1 range
X_scaled = MinMaxScaler().fit_transform(rfm)

# 3. K-Means clustering (k=4)
km = KMeans(n_clusters=4, random_state=42).fit(X_scaled)

# 4. Map cluster IDs to human labels by ranking cluster centers
# Score = -R + F + M  →  highest = Champion, lowest = Lost
label_map = {0: 'Champion', 2: 'Loyal', 3: 'At Risk', 1: 'Lost'}

# 5. Write labels to DB
UPDATE AspNetUsers SET RfmSegment = 'Champion' WHERE Id = '...'
```

**Fallback:** When < 4 customers have orders → rule-based scoring (no K-Means).

**Scheduler:** Sunday 03:45 Cairo — `job_admin_rfm_segment()`

---

## 4. Modified Files

### `main.py`
Added 13 routes at the bottom under the `Admin` Swagger tag:

```
GET  /admin/dashboard
GET  /admin/kpis
GET  /admin/analytics
GET  /admin/analytics/forecast
GET  /admin/sellers
GET  /admin/sellers/{seller_id}
GET  /admin/customers
GET  /admin/customers/segments
GET  /admin/categories
GET  /admin/categories/{category_id}/trend
GET  /admin/export/kpis
POST /admin/train/rfm
POST /admin/train/forecast
```

### `scheduler.py`
Added 2 weekly jobs after the existing `job_retrain_all()`:
```python
scheduler.add_job(job_admin_forecast,    CronTrigger(day_of_week="sun", hour=3, minute=30))
scheduler.add_job(job_admin_rfm_segment, CronTrigger(day_of_week="sun", hour=3, minute=45))
```

### `requirements.txt`
Added 2 packages:
```
openpyxl>=3.1.0       # Multi-sheet styled Excel export
python-dateutil>=2.9.0 # Date arithmetic for forecast month labels
```

---

## 5. Dependencies Summary

| Package | Version | Purpose | Already Present? |
|---|---|---|---|
| `fastapi` | ≥0.110 | API framework | ✅ Yes |
| `sqlalchemy` | ≥2.0 | DB connection | ✅ Yes |
| `pyodbc` | ≥5.1 | SQL Server driver | ✅ Yes |
| `pandas` | ≥2.2 | Data manipulation | ✅ Yes |
| `numpy` | ≥1.26 | Numerical ops | ✅ Yes |
| `scikit-learn` | ≥1.4 | LinearRegression + KMeans | ✅ Yes |
| `xgboost` | ≥2.0 | Churn + Fraud models | ✅ Yes |
| `apscheduler` | ≥3.10 | Nightly scheduler | ✅ Yes |
| `openpyxl` | ≥3.1 | Excel export | ➕ Added |
| `python-dateutil` | ≥2.9 | Month arithmetic | ➕ Added |

---

## 6. Deployment

### Azure App Service (Current)
The service is deployed as a Docker container via Azure:
- **URL:** `https://talentree-ai-service.azurewebsites.net`
- **Docs:** `https://talentree-ai-service.azurewebsites.net/docs`
- **Port:** 8000 (internal) → 443 (Azure HTTPS)

### Deploy Steps
```bash
# 1. On branch feature/admin-dashboard
git add .
git commit -m "feat(admin): ..."
git push origin feature/admin-dashboard

# 2. Azure builds and deploys automatically via GitHub Actions (or manual trigger)
# OR: docker compose up --build in Azure SSH

# 3. Verify
curl https://talentree-ai-service.azurewebsites.net/admin/dashboard
curl https://talentree-ai-service.azurewebsites.net/docs  # check Admin tag appears
```

---

## 7. What the Backend Team Needs To Do

1. **Add DB column** (one-time migration):
   ```sql
   ALTER TABLE AspNetUsers ADD RfmSegment NVARCHAR(20) NULL;
   ```

2. **No new event triggers needed** — all admin endpoints are called by the Angular admin frontend directly (same as BO dashboard pattern)

3. **CORS** — the Angular admin frontend origin should be whitelisted in the AI service (currently open via `allow_origins=["*"]` — production should restrict to known origins)

---

## 8. Summary Numbers

| Metric | Count |
|---|---|
| New service files created | 9 |
| New API endpoints | 13 |
| Files modified | 3 (`main.py`, `scheduler.py`, `requirements.txt`) |
| New ML models | 2 (Models 8 + 9) |
| Existing models reused (read-only) | 7 |
| New DB columns needed | 1 (`AspNetUsers.RfmSegment`) |
| New Python packages | 2 (`openpyxl`, `python-dateutil`) |
| New Docker containers | 0 |
| New Azure App Services | 0 |
| Implementation time | 1 day |
