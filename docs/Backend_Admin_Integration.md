# Admin Dashboard & Report Analysis — Backend Integration Guide

> **Audience:** .NET Backend Team & Database Administrators
> **AI Service URL (Production):** `http://20.244.32.232:8000`
> **Swagger UI:** `http://20.244.32.232:8000/docs` → scroll to **Admin** section
> **Last Updated:** June 2026

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [How It Differs from the BO Dashboard](#2-how-it-differs-from-the-bo-dashboard)
3. [Database Migration Required](#3-database-migration-required)
4. [Admin Endpoints — Full Reference](#4-admin-endpoints--full-reference)
5. [Report Analysis — Data Export Endpoints](#5-report-analysis--data-export-endpoints)
6. [Admin AI Models — Backend Awareness](#6-admin-ai-models--backend-awareness)
7. [Manual Trigger Endpoints](#7-manual-trigger-endpoints)
8. [C# Proxy Pattern (Optional but Recommended)](#8-c-proxy-pattern-optional-but-recommended)
9. [Scheduler — What Runs Automatically](#9-scheduler--what-runs-automatically)
10. [Database Column Reference](#10-database-column-reference)
11. [Checklist for the Backend Team](#11-checklist-for-the-backend-team)

---

## 1. Architecture Overview

The Admin Dashboard follows a **direct-to-AI** architecture. The Angular Admin Frontend calls the Python AI Service directly for all analytics, reports, and AI predictions. The .NET backend's role is minimal compared to the BO Dashboard.

```
                ┌──────────────────────────────┐
                │  Angular Admin Frontend       │
                │  (admin.talentree.com)        │
                └──────────────┬───────────────┘
                               │
             ┌─────────────────┼──────────────────┐
             │                 │                  │
    .NET API calls         AI Service calls       │
   (user auth, CRUD)      (analytics, AI)         │
             │                 │                  │
    ┌────────▼────────┐  ┌────▼─────────────┐    │
    │  .NET Backend   │  │  Python AI Service│    │
    │  api.talentree  │  │  /admin/* routes  │    │
    └────────┬────────┘  └────────┬──────────┘    │
             │                    │               │
             └─────────┬──────────┘               │
                       │                          │
               ┌───────▼──────────────────────────┘
               │  SQL Server DB (db52715)
               │  Both services read/write the same DB
               └───────────────────────────────────
```

**Key principle:** The .NET backend and the Python AI service **share the same SQL database** (`db52715`). The AI service reads the raw business data and writes enriched AI columns back. The .NET backend reads and writes its own operational data.

---

## 2. Security Model — MUST READ

### The Problem

The Python AI Service (`http://20.244.32.232:8000`) is an **internal microservice** with no built-in authentication, no API keys, and no rate limiting. It was designed to be called from a trusted internal network only.

If the Angular frontend calls the AI service directly:
- ❌ Any user (not just admins) could call `/admin/dashboard` directly via browser DevTools
- ❌ Any user could call `POST /ai/train/all` and force a costly model retrain
- ❌ Any user could call `GET /admin/export/kpis?format=xlsx` and download the full platform report
- ❌ There is no rate limiting — a bot could spam the endpoints and overwhelm the VM

### The Solution — Backend as Secure Proxy

The .NET backend **must expose its own admin endpoints** that:
1. Validate the user's JWT token
2. Confirm the user has the `Admin` role
3. Forward the request to the AI service internally (server-to-server)
4. Return the response to the Angular frontend

```
[Angular Frontend]
      │
      │  POST /api/admin/ai/dashboard       ← .NET secured route
      ▼
[.NET Backend]  ←── Validates JWT + Admin role here
      │
      │  GET http://20.244.32.232:8000/admin/dashboard  ← Internal call, no auth needed
      ▼
[Python AI Service]
      │
      ▼
[SQL Server DB]
```

### What Needs to Be Blocked

The AI Service VM firewall should be updated to **only allow inbound connections on port 8000 from the .NET backend server IP**. This ensures no external party can call the AI service directly.

Contact your DevOps/Azure team to add this NSG (Network Security Group) rule:
```
Source:       <.NET Backend Server IP or VNET>
Destination:  20.244.32.232
Port:         8000
Action:       Allow

Source:       Any (0.0.0.0/0)
Destination:  20.244.32.232
Port:         8000
Action:       Deny
```

---

## 3. Backend Responsibilities

Here is a clear list of **what the .NET backend team needs to build** for the Admin AI integration:

### 3.1 Secure Proxy Controller (REQUIRED)
Create `AdminAiProxyController` that wraps every `/admin/*` AI endpoint with `[Authorize(Roles = "Admin")]`. The Angular frontend will call `GET /api/admin/ai/dashboard` instead of `GET http://20.244.32.232:8000/admin/dashboard` directly. See Section 10 for the full ready-to-use code.

### 3.2 Admin Role Guard (REQUIRED)
Ensure the `Admin` role exists in `AspNetRoles` and is assigned correctly. The proxy controller gates all AI analytics behind this role.

### 3.3 Rate Limiting (RECOMMENDED)
Add rate limiting to the proxy endpoints to prevent abuse. Export endpoints in particular can be heavy.

```csharp
// Using ASP.NET Core rate limiting middleware
builder.Services.AddRateLimiter(options =>
{
    options.AddFixedWindowLimiter("AdminAi", opt =>
    {
        opt.PermitLimit = 20;
        opt.Window = TimeSpan.FromMinutes(1);
    });
});

// Apply on the controller
[EnableRateLimiting("AdminAi")]
public class AdminAiProxyController : ControllerBase { ... }
```

### 3.4 Audit Logging (RECOMMENDED)
Log when an admin downloads a report or triggers a model retrain. This is important for compliance and traceability.

```csharp
[HttpGet("export/kpis")]
[Authorize(Roles = "Admin")]
public async Task<IActionResult> ExportKpis([FromQuery] string format = "xlsx")
{
    var adminId = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
    _logger.LogInformation("Admin {AdminId} downloaded KPI report (format: {Format}) at {Time}",
        adminId, format, DateTime.UtcNow);

    // ... proxy to AI service
}
```

### 3.5 EF Core — Mark AI Columns as Read-Only (REQUIRED)
The .NET EF Core models must not overwrite AI-managed columns during regular SaveChanges calls.

```csharp
// In your ApplicationDbContext or entity configuration:
modelBuilder.Entity<ApplicationUser>()
    .Property(u => u.ChurnRiskScore)
    .ValueGeneratedOnAddOrUpdate()  // tells EF not to include in UPDATE statements
    .Metadata.SetAfterSaveBehavior(PropertySaveBehavior.Ignore);

modelBuilder.Entity<ApplicationUser>()
    .Property(u => u.RfmSegment)
    .Metadata.SetAfterSaveBehavior(PropertySaveBehavior.Ignore);
```

Or simpler — use `[DatabaseGenerated(DatabaseGeneratedOption.Computed)]` on the entity properties:

```csharp
public class ApplicationUser : IdentityUser
{
    // AI-managed — do NOT update from .NET code
    [DatabaseGenerated(DatabaseGeneratedOption.Computed)]
    public float? ChurnRiskScore { get; set; }

    [DatabaseGenerated(DatabaseGeneratedOption.Computed)]
    public DateTime? ChurnRiskUpdatedAt { get; set; }

    [DatabaseGenerated(DatabaseGeneratedOption.Computed)]
    public string? RfmSegment { get; set; }
}
```

### 3.6 Environment Configuration (REQUIRED)
Store the AI service base URL in `appsettings.json` — do not hardcode it.

```json
// appsettings.Production.json
{
  "AiService": {
    "BaseUrl": "http://20.244.32.232:8000",
    "TimeoutSeconds": 60
  }
}
```

```csharp
// Program.cs
builder.Services.AddHttpClient("AiService", client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AiService:BaseUrl"]!);
    client.Timeout = TimeSpan.FromSeconds(
        int.Parse(builder.Configuration["AiService:TimeoutSeconds"] ?? "60"));
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});
```

---

## 4. How It Differs from the BO Dashboard

Understanding this distinction is critical to avoid duplicating work.

| Behaviour | BO Dashboard | Admin Dashboard |
|---|---|---|
| Who triggers the AI? | .NET Backend fires `POST /ai/predict/*` on each user event | Angular Frontend calls .NET proxy which calls AI internally |
| AI computation timing | Real-time (per user event) + nightly batch | On-demand (when admin loads the page) + weekly batch |
| Does .NET need new routes? | YES — triggers for each event | **YES — secure proxy controller** (see Section 10) |
| Does AI write to DB? | YES (ChurnRiskScore, FraudScore, etc.) | Only for RFM segments (`AspNetUsers.RfmSegment`) |
| Backend code changes? | Many — add `AiServiceClient` calls everywhere | **Secure proxy controller + one SQL migration** |

---

## 5. Database Migration Required

**Only one migration was needed** to support the Admin AI Models — and the backend team has already executed it. ✅

The RFM Segmentation model (Model 9) needed a column to persist the customer label in the database so the AI can save results permanently (e.g., for the .NET backend to later use for marketing email filtering).

### ✅ Already Executed on `db52715`:

```sql
-- DONE — Executed by backend team (June 2026)
-- Model 9: Customer RFM Segmentation
ALTER TABLE AspNetUsers
ADD RfmSegment NVARCHAR(20) NULL;
```

> **Status:** This column now exists in the production database. The AI service will write `Champion`, `Loyal`, `At Risk`, or `Lost` into this column every Sunday at 03:45 Cairo time.

---

## 4. Admin Endpoints — Full Reference

All endpoints return `application/json`. No authentication header is required from the .NET backend (the AI service is internal).

### 4.1 Dashboard Overview

```
GET /admin/dashboard
```
Returns all metric cards, pending action counts, and 4 alert feeds in one call.

**Response summary:**
```json
{
  "sellers": { "total": 9, "active": 7, "pending": 1, "suspended": 1 },
  "customers_total": 13,
  "products": { "total": 216, "approved": 200, "pending": 16 },
  "b2c_orders": { "total": 3, "pending": 1, "processing": 0, "shipped": 1, "delivered": 1 },
  "b2b_orders": { "total": 213, "submitted": 5, "completed": 180 },
  "current_month_revenue": 17350.00,
  "pending_actions": { "total": 4, "sellers_pending_approval": 1, "products_pending_approval": 2, "overdue_complaints": 1 },
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

### 4.2 Platform KPIs

```
GET /admin/kpis
```
Returns 9 computed KPIs aggregated from AI-scored database columns.

| KPI Field | Source Column | Description |
|---|---|---|
| `seller_churn_rate` | `AspNetUsers.ChurnRiskScore` | % of sellers with ChurnRiskScore > 0.6 |
| `fraud_rate` | `BoProductionRequests.IsFraudFlag` | % of production requests flagged as fraud |
| `transaction_anomaly_rate` | `Transactions.AnomalyFlag` | % of transactions flagged as anomalous |
| `customer_satisfaction_rating` | `ProductReviews.SentimentScore` | Average review sentiment score (0–5 scale) |
| `avg_fulfillment_hours` | `BoProductionRequests.FulfillmentHours` | Average hours from submission to completion |
| `avg_seller_profile_completeness` | `BusinessOwnerProfile.ProfileCompletenessPct` | Platform-wide average profile % |
| `product_approval_rate` | `Products.IsApproved` | % of products that are approved |
| `customer_conversion_rate` | `CustomerOrders` / `AspNetUsers` | % of customers who placed at least one order |
| `average_order_value` | `CustomerOrders.TotalAmount` | Average B2C order value in EGP |

---

### 4.3 Platform Health Score

```
GET /admin/platform/health
```
Returns the **composite 0–100 score** computed using the formula:

```
Health Score =
  (Avg Rating / 5.0) × 40
  + (min(Conversion Rate, 50) / 50) × 20
  + ((100 - Churn Rate) / 100) × 20
  + ((100 - Fraud Rate) / 100) × 10
  + ((100 - Anomaly Rate) / 100) × 10
```

**Response:**
```json
{
  "health_score": 74.3,
  "label": "Good",
  "components": {
    "avg_rating": 4.1,
    "conversion_rate_pct": 23.1,
    "churn_rate_pct": 14.3,
    "fraud_rate_pct": 2.8,
    "anomaly_rate_pct": 5.6
  }
}
```

| Score | Label |
|---|---|
| 80–100 | Excellent ✅ |
| 60–79 | Good 🟡 |
| 40–59 | Fair 🟠 |
| 0–39 | Needs Attention 🔴 |

---

### 4.4 Platform Analytics & Trends

```
GET /admin/analytics?period=monthly
GET /admin/analytics?period=weekly
```

Returns chart-ready trend data: revenue over time, user growth, order volume, category distribution, B2B vs B2C split, and sentiment breakdown.

---

### 4.5 Revenue Forecast (Model 8)

```
GET /admin/analytics/forecast
```

Returns the last 6 months actuals + 3-month forward prediction using Linear Regression trained on `Transactions` data.

**Response:**
```json
{
  "actuals": [
    { "month": "2026-01", "revenue": 12400.0 },
    { "month": "2026-06", "revenue": 17300.0 }
  ],
  "forecast": [
    { "month": "2026-07", "forecasted_revenue": 18400.0 },
    { "month": "2026-08", "forecasted_revenue": 19500.0 },
    { "month": "2026-09", "forecasted_revenue": 20600.0 }
  ],
  "model_meta": { "method": "LinearRegression", "r2_score": 0.97 }
}
```

---

### 4.6 Seller Performance Report

```
GET /admin/sellers?sort_by=risk
GET /admin/sellers?sort_by=revenue
GET /admin/sellers?sort_by=rating
GET /admin/sellers?sort_by=orders
```

Returns all sellers ranked with AI risk flags per seller.

```
GET /admin/sellers/{seller_id}
```
Full performance profile for one seller including 6-month revenue trend.

---

### 4.7 Customer Insights & RFM Segmentation

```
GET /admin/customers
```
B2C customer cohort analysis: CLV segments, inactive customers, peak shopping hours.

```
GET /admin/customers/segments
```

Returns the RFM segment distribution (Model 9):

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

---

### 4.8 Category Performance

```
GET /admin/categories
```
All product categories with pricing stats, purchase counts, revenue, avg rating, quality score, and seller count.

```
GET /admin/categories/{category_id}/trend?period=monthly
```
Revenue trend for one category over the last 6 months.

---

### 4.9 Price Anomaly Detection (Model 12)

```
GET /admin/products/price-anomalies
```
Detects products priced significantly outside their category range using Isolation Forest.

**Response:**
```json
{
  "status": "success",
  "total_products_scanned": 216,
  "anomalies_detected": 11,
  "anomalies": [
    {
      "product_id": 45,
      "name": "Premium Leather Bag",
      "seller": "Nour Designs",
      "category": "Accessories",
      "price": 4500.0,
      "category_avg_price": 320.0,
      "anomaly_severity": 0.412,
      "reason": "Price is significantly higher than category average"
    }
  ]
}
```

---

### 4.10 Category Demand Forecast (Model 13)

```
GET /admin/categories/forecast
```
Predicts 3-month forward order quantity per category using per-category Linear Regression.

**Response:**
```json
{
  "status": "success",
  "categories_forecasted": 8,
  "forecasts": [
    {
      "category_id": 3,
      "category_name": "Handmade Jewelry",
      "projected_growth_pct": 24.5,
      "trend_r2_score": 0.91,
      "forecast": [
        { "month": "2026-07", "forecasted_qty": 142 },
        { "month": "2026-08", "forecasted_qty": 158 },
        { "month": "2026-09", "forecasted_qty": 174 }
      ]
    }
  ]
}
```

---

## 5. Report Analysis — Data Export Endpoints

These endpoints generate downloadable financial and platform reports. The Angular frontend can call them directly, or the .NET backend can proxy them (see Section 8).

### 5.1 Platform KPI Report

```
GET /admin/export/kpis?format=csv
GET /admin/export/kpis?format=xlsx
```

| Format | Content | Sheets |
|---|---|---|
| `csv` | Flat CSV of all KPIs | Single sheet |
| `xlsx` | Styled Excel workbook | 3 sheets: KPIs, Sellers, Categories |

**Response headers:**
```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename=talentree_admin_report.xlsx
```

### 5.2 BO Financial Report (Per Seller)

```
GET /ai/export/financial/{bo_user_id}?format=csv
GET /ai/export/financial/{bo_user_id}?format=pdf
GET /ai/export/financial/{bo_user_id}?format=csv&from_date=2026-01-01&to_date=2026-06-30
GET /ai/export/financial/{bo_user_id}?format=csv&tx_type=Sale
```

Generates a per-seller financial export showing all transactions, totals by type, and summary. Available as PDF or CSV.

---

## 6. Admin AI Models — Backend Awareness

The .NET backend does not need to call these models, but should understand what columns they write so the backend team does not accidentally overwrite them.

| Model | Reads From | Writes To | When |
|---|---|---|---|
| Model 1 — BO Churn | `LoginHistories`, `BoProductionRequests` | `AspNetUsers.ChurnRiskScore` | Nightly 02:20 + on BO login |
| Model 3 — Anomaly | `Transactions` | `Transactions.AnomalyFlag`, `AnomalyScore` | Nightly 02:30 + on transaction insert |
| Model 4 — Sentiment | `ProductReviews` | `ProductReviews.SentimentScore`, `SentimentLabel` | Nightly 02:35 + on review insert |
| Model 8 — Forecast | `Transactions` | `models/admin_forecast_model.pkl` (local file) | Sunday 03:30 |
| Model 9 — RFM | `CustomerOrders`, `AspNetUsers` | `AspNetUsers.RfmSegment` | Sunday 03:45 |
| Model 11 — Health | All tables (read-only) | Nothing — computed live | On request |
| Model 12 — Price Anomaly | `Products`, `Categories` | Nothing — computed live | On request |
| Model 13 — Category Forecast | `CustomerOrderItems`, `CustomerOrders` | Nothing — computed live | On request |

> ⚠️ **IMPORTANT:** Never write to AI-managed columns like `ChurnRiskScore`, `AnomalyFlag`, `SentimentScore`, or `RfmSegment` from the .NET backend. These are owned by the AI service.

---

## 7. Manual Trigger Endpoints

If the Admin UI needs a "Re-run AI" or "Force Refresh" button, the .NET backend can expose a controller that calls these Python endpoints:

### Retrain Revenue Forecast Model

```http
POST http://20.244.32.232:8000/admin/train/forecast
```
Forces the Revenue Forecast model to retrain on the latest Transactions data.

### Retrain RFM Segmentation Model

```http
POST http://20.244.32.232:8000/admin/train/rfm
```
Forces a re-cluster of all customers and writes updated `RfmSegment` labels to DB.

### Retrain All BO Models

```http
POST http://20.244.32.232:8000/ai/train/all
```
Retrains all 7 BO models (Churn, Fraud, Anomaly, Sentiment, Demand, Triage, Quality).

### Run All BO Predictions Right Now

```http
POST http://20.244.32.232:8000/ai/compute/all
```
Runs all nightly predictions immediately without waiting for the 02:00 AM scheduler.

---

## 8. C# Proxy Pattern (Optional but Recommended)

If your security policy requires all admin calls to pass through the .NET backend (e.g., to verify the JWT Admin role before allowing access to reports), use this proxy pattern.

```csharp
// AdminAiProxyController.cs
[ApiController]
[Route("api/admin/ai")]
[Authorize(Roles = "Admin")]
public class AdminAiProxyController : ControllerBase
{
    private readonly HttpClient _httpClient;
    private const string AI_BASE = "http://20.244.32.232:8000";

    public AdminAiProxyController(IHttpClientFactory factory)
    {
        _httpClient = factory.CreateClient("AiService");
    }

    // Dashboard
    [HttpGet("dashboard")]
    public async Task<IActionResult> GetDashboard()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/dashboard");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // Platform KPIs
    [HttpGet("kpis")]
    public async Task<IActionResult> GetKpis()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/kpis");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // Platform Health Score
    [HttpGet("health")]
    public async Task<IActionResult> GetHealth()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/platform/health");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // Revenue Forecast
    [HttpGet("forecast")]
    public async Task<IActionResult> GetForecast()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/analytics/forecast");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // Price Anomalies
    [HttpGet("price-anomalies")]
    public async Task<IActionResult> GetPriceAnomalies()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/products/price-anomalies");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // Category Forecast
    [HttpGet("category-forecast")]
    public async Task<IActionResult> GetCategoryForecast()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/categories/forecast");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // RFM Segments
    [HttpGet("rfm-segments")]
    public async Task<IActionResult> GetRfmSegments()
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/customers/segments");
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    // Excel / CSV Export (stream file through)
    [HttpGet("export/kpis")]
    public async Task<IActionResult> ExportKpis([FromQuery] string format = "xlsx")
    {
        var response = await _httpClient.GetAsync($"{AI_BASE}/admin/export/kpis?format={format}");
        if (!response.IsSuccessStatusCode) return StatusCode(500, "AI Export Failed");

        var stream = await response.Content.ReadAsStreamAsync();
        var contentType = format == "xlsx"
            ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            : "text/csv";

        return File(stream, contentType, $"talentree_admin_report.{format}");
    }

    // Force Retrain (Admin button)
    [HttpPost("train/forecast")]
    public async Task<IActionResult> TrainForecast()
    {
        var response = await _httpClient.PostAsync($"{AI_BASE}/admin/train/forecast", null);
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }

    [HttpPost("train/rfm")]
    public async Task<IActionResult> TrainRfm()
    {
        var response = await _httpClient.PostAsync($"{AI_BASE}/admin/train/rfm", null);
        var content = await response.Content.ReadAsStringAsync();
        return Content(content, "application/json");
    }
}
```

### Register HttpClient (Program.cs)

```csharp
builder.Services.AddHttpClient("AiService", client =>
{
    client.Timeout = TimeSpan.FromSeconds(60); // reports can take a moment
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});
```

---

## 9. Scheduler — What Runs Automatically

The Python AI service runs a background cron scheduler. The .NET backend does not need to invoke any of these jobs manually — they run on their own.

| Time | Job | DB Effect |
|---|---|---|
| Every day @ 02:00 Cairo | Recompute BO profile completeness | `BusinessOwnerProfile.ProfileCompletenessPct` updated |
| Every day @ 02:05 Cairo | Recompute product metrics | `Products.DescriptionQualityScore`, `LowStockFlag`, `DemandForecastQty` |
| Every day @ 02:20 Cairo | Predict churn for all BOs | `AspNetUsers.ChurnRiskScore` updated |
| Every day @ 02:25 Cairo | Predict fraud for all requests | `BoProductionRequests.IsFraudFlag` updated |
| Every day @ 02:30 Cairo | Predict anomaly for all transactions | `Transactions.AnomalyFlag` updated |
| Every day @ 02:35 Cairo | Predict sentiment for all reviews | `ProductReviews.SentimentScore` updated |
| Every day @ 02:40 Cairo | Auto-triage all open tickets | `SupportTickets.AutoCategory`, `PriorityScore` updated |
| Every day @ 02:45 Cairo | Fire notification alerts | `Notifications` table updated per BO |
| **Every Sunday @ 03:00** | Retrain all 7 BO models | `models/*.pkl` files updated |
| **Every Sunday @ 03:30** | Retrain Revenue Forecast model | `admin_forecast_model.pkl` updated |
| **Every Sunday @ 03:45** | Re-cluster customers + write segments | `AspNetUsers.RfmSegment` updated for all customers |

---

## 10. Database Column Reference

The following columns are written by the AI service. The .NET backend should treat these as **read-only** in its EF Core models.

### `AspNetUsers`
| Column | Type | Written By | Description |
|---|---|---|---|
| `ChurnRiskScore` | `real` | Model 1 | 0.0–1.0 churn probability for BOs |
| `ChurnRiskUpdatedAt` | `datetime2` | Model 1 | Timestamp of last score update |
| `RfmSegment` | `nvarchar(20)` | Model 9 | Champion / Loyal / At Risk / Lost |

### `BoProductionRequests`
| Column | Type | Written By | Description |
|---|---|---|---|
| `FraudScore` | `real` | Model 2 | 0.0–1.0 fraud probability |
| `IsFraudFlag` | `bit` | Model 2 | 1 if fraud probability > 0.5 |
| `FulfillmentHours` | `real` | Model 7 | Predicted hours to complete request |

### `Transactions`
| Column | Type | Written By | Description |
|---|---|---|---|
| `AnomalyFlag` | `bit` | Model 3 | 1 if transaction is anomalous |
| `AnomalyScore` | `real` | Model 3 | Raw Isolation Forest anomaly score |

### `ProductReviews`
| Column | Type | Written By | Description |
|---|---|---|---|
| `SentimentScore` | `real` | Model 4 | 0.0–1.0 sentiment strength |
| `SentimentLabel` | `nvarchar(20)` | Model 4 | Positive / Neutral / Negative |

### `SupportTickets`
| Column | Type | Written By | Description |
|---|---|---|---|
| `AutoCategory` | `nvarchar(max)` | Model 5 | Payment / Quality / Delivery / Account / Technical |
| `PriorityScore` | `real` | Model 5 | Computed priority 0.0–1.0 |

### `Products`
| Column | Type | Written By | Description |
|---|---|---|---|
| `DescriptionQualityScore` | `real` | Model 7 | 0.0–1.0 product description quality |
| `LowStockFlag` | `bit` | Model 6 | 1 if stock < demand forecast |
| `DemandForecastQty` | `real` | Model 6 | Predicted units to be ordered |

### `BusinessOwnerProfile`
| Column | Type | Written By | Description |
|---|---|---|---|
| `ProfileCompletenessPct` | `real` | Nightly job | 0–100% profile completeness |

---

## 13. Checklist for the Backend Team

Use this list to verify the Admin AI integration is complete:

**Security (REQUIRED)**
- [x] **SQL Migration** — `ALTER TABLE AspNetUsers ADD RfmSegment NVARCHAR(20) NULL` ✅ Already done (June 2026)
- [ ] **Secure Proxy** — Implement `AdminAiProxyController` with `[Authorize(Roles = "Admin")]` on every endpoint (Section 10)
- [ ] **Firewall / NSG** — Block direct access to port 8000 from the internet. Only allow the .NET backend server IP
- [ ] **Rate Limiting** — Apply `AddRateLimiter` to the proxy controller (Section 3.3)
- [ ] **Audit Logging** — Log admin report downloads and manual retrain triggers (Section 3.4)

**Code Quality (REQUIRED)**
- [ ] **EF Core Read-Only** — Mark AI columns with `[DatabaseGenerated(DatabaseGeneratedOption.Computed)]` (Section 3.5)
- [ ] **No Overwrites** — Verify .NET `UPDATE` queries never touch `ChurnRiskScore`, `AnomalyFlag`, `SentimentScore`, `RfmSegment`
- [ ] **appsettings.json** — Store the AI base URL in config, not hardcoded (Section 3.6)

**Optional Features**
- [ ] **Force Retrain Buttons** — Wire admin UI buttons to `POST /api/admin/ai/train/forecast` and `POST /api/admin/ai/train/rfm`

**Testing**
- [ ] **Service Reachable** — From .NET server, confirm `curl http://20.244.32.232:8000/admin/status` returns `{"status":"ok","module":"admin"}`
- [ ] **Auth Works** — Confirm unauthenticated requests to `/api/admin/ai/dashboard` return `401 Unauthorized`
- [ ] **Role Works** — Confirm non-admin JWT requests return `403 Forbidden`

---

*For any questions about the AI endpoints, consult the Swagger UI at `http://20.244.32.232:8000/docs` or refer to `Admin_Integration_Guide.md` for the full Angular TypeScript types.*
