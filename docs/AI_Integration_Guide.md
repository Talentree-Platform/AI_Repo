# Talentree AI Service — Frontend & Backend Integration Guide
> **For:** Angular Frontend Team & .NET Backend Team  
> **AI Service Base URL:** `http://[ai-service-host]:8000`  
> **Swagger Docs:** `http://[ai-service-host]:8000/docs`  
> **Last Updated:** April 17, 2026

---

## Overview

The AI microservice is a standalone FastAPI service that runs alongside the .NET backend.  
It exposes JSON endpoints that the frontend calls **directly** or through the backend proxy.

```
┌─────────────────┐      HTTP/JSON      ┌──────────────────┐
│  Angular Front  │ ──────────────────► │  AI Microservice │
│  (TypeScript)   │                     │  FastAPI :8000   │
└─────────────────┘                     └──────────────────┘
        │                                       │
        │        .NET Backend :5000             │  pyodbc
        └──────────────────────────────►  SQL Server DB
```

---

## 1. Dashboard Page (Load on Mount)

**Endpoint:** `GET /ai/dashboard/{bo_user_id}`

Call this once when the BO dashboard loads to populate all KPI cards.

### Request
```http
GET http://ai-service:8000/ai/dashboard/a091d9c9-e581-4f6e-8cf6-d38fc68dffbf
Accept: application/json
```

### Response
```json
{
  "user_id": "a091d9c9-e581-4f6e-8cf6-d38fc68dffbf",
  "revenue_total": 226016.86,
  "revenue_last_30d": 113945.21,
  "revenue_trend": "Rising",
  "total_orders": 10,
  "avg_fulfillment_hours": 864.0,
  "fraud_alerts": 1,
  "low_stock_count": 0,
  "churn_risk_score": 0.9997,
  "profile_completeness_pct": 90,
  "avg_product_quality_score": 0.29,
  "avg_review_sentiment": 0.5189,
  "negative_reviews_count": 4,
  "open_support_tickets": 4
}
```

### Angular Usage
```typescript
// dashboard.service.ts
getDashboardSummary(boId: string): Observable<DashboardSummary> {
  return this.http.get<DashboardSummary>(`${AI_BASE}/ai/dashboard/${boId}`);
}

// dashboard.component.ts
ngOnInit() {
  this.aiService.getDashboardSummary(this.boUserId).subscribe(data => {
    this.kpis = data;
  });
}
```

### UI Mapping — KPI Cards
| JSON Field | Card Label | Format | Color Logic |
|---|---|---|---|
| `revenue_total` | Total Revenue | `EGP 226,016.86` | Always green |
| `revenue_last_30d` | Last 30 Days | `EGP 113,945.21` | Green |
| `revenue_trend` | Trend | Badge: Rising/Stable/Falling | Green / Grey / Red |
| `total_orders` | Total Orders | `10` | Neutral |
| `avg_fulfillment_hours` | Avg Fulfillment | `864 hrs` | Red if > 720h |
| `fraud_alerts` | Fraud Alerts | `1` | Red if > 0 |
| `churn_risk_score` | Churn Risk | Progress bar `99.97%` | Red if > 0.7 |
| `profile_completeness_pct` | Profile | Progress bar `90%` | Green if > 80% |
| `open_support_tickets` | Open Tickets | `4` | Orange if > 3 |

---

## 2. Revenue Chart (Line Chart)

**Endpoint:** `GET /ai/analytics/revenue-trend/{bo_user_id}?period=monthly`

### Request
```http
GET http://ai-service:8000/ai/analytics/revenue-trend/a091d9c9...?period=monthly
```

### Response
```json
{
  "user_id": "a091d9c9-e581-4f6e-8cf6-d38fc68dffbf",
  "period": "monthly",
  "overall_trend": "Stable",
  "data": [
    { "period": "2026-W10", "revenue": 5200.00, "order_count": 3, "avg_order_value": 1733.33 },
    { "period": "2026-W11", "revenue": 8100.00, "order_count": 5, "avg_order_value": 1620.00 },
    { "period": "2026-W12", "revenue": 7400.00, "order_count": 4, "avg_order_value": 1850.00 }
  ]
}
```

### Angular + ApexCharts
```typescript
// In component:
this.http.get(`${AI_BASE}/ai/analytics/revenue-trend/${boId}?period=monthly`)
  .subscribe((res: any) => {
    this.revenueChart = {
      series: [
        { name: 'Revenue (EGP)', data: res.data.map((d: any) => d.revenue) },
        { name: 'Orders', data: res.data.map((d: any) => d.order_count) }
      ],
      xaxis: { categories: res.data.map((d: any) => d.period) },
      chart: { type: 'line', height: 350 },
      stroke: { curve: 'smooth' },
      colors: ['#2ECC71', '#3498DB'],
      title: { text: `Revenue Trend — ${res.overall_trend}` }
    };
  });
```

```html
<apx-chart
  [series]="revenueChart.series"
  [xaxis]="revenueChart.xaxis"
  [chart]="{ type: 'line', height: 350 }"
  [title]="{ text: 'Revenue Trend' }">
</apx-chart>
```

> **Query params:** `period=weekly` or `period=monthly`

---

## 3. Review Sentiment Chart (Bar/Area Chart)

**Endpoint:** `GET /ai/reviews/trends/{bo_user_id}?period=monthly`

### Response
```json
{
  "user_id": "a091d9c9-...",
  "period": "monthly",
  "data": [
    { "period": "Period 1", "avg_sentiment": 0.6821, "review_count": 29, "negative_count": 4, "negative_pct": 13.8 },
    { "period": "Period 2", "avg_sentiment": 0.5134, "review_count": 29, "negative_count": 6, "negative_pct": 20.7 },
    { "period": "Period 3", "avg_sentiment": 0.7210, "review_count": 29, "negative_count": 2, "negative_pct": 6.9 }
  ]
}
```

### Angular + ApexCharts
```typescript
this.reviewChart = {
  series: [
    { name: 'Avg Sentiment', data: res.data.map((d: any) => d.avg_sentiment) },
    { name: 'Negative %', data: res.data.map((d: any) => d.negative_pct) }
  ],
  xaxis: { categories: res.data.map((d: any) => d.period) },
  chart: { type: 'bar', height: 300 },
  colors: ['#2ECC71', '#E74C3C'],
  yaxis: [
    { title: { text: 'Sentiment (0–1)' }, min: 0, max: 1 },
    { opposite: true, title: { text: 'Negative %' }, min: 0, max: 100 }
  ]
};
```

---

## 4. Benchmark Radar Chart

**Endpoint:** `GET /ai/benchmark/{bo_user_id}`

### Response
```json
{
  "user_id": "a091d9c9-...",
  "fulfillment_rank": "bottom 40%",
  "fulfillment_rank_pct": 34,
  "quality_rank": "average",
  "quality_rank_pct": 46,
  "rating_rank": "average",
  "rating_rank_pct": 50,
  "bo_fulfillment_hours": 864.0,
  "platform_avg_fulfillment_hours": 663.8,
  "bo_quality_score": 0.29,
  "platform_avg_quality": 0.31
}
```

### Angular + ApexCharts (Radar)
```typescript
this.benchmarkChart = {
  series: [
    {
      name: 'Your Rank',
      data: [
        res.fulfillment_rank_pct,
        res.quality_rank_pct,
        res.rating_rank_pct
      ]
    }
  ],
  xaxis: { categories: ['Fulfillment Speed', 'Product Quality', 'Review Rating'] },
  chart: { type: 'radar', height: 350 },
  fill: { opacity: 0.4 },
  colors: ['#3498DB']
};
```

### Comparison Cards
```
┌─────────────────────────────┐
│  Fulfillment Speed          │
│  You: 864 hrs               │
│  Platform avg: 664 hrs      │
│  Rank: Bottom 40%  🔴       │
└─────────────────────────────┘
┌─────────────────────────────┐
│  Product Quality Score      │
│  You: 0.29 / 1.0            │
│  Platform avg: 0.31         │
│  Rank: Average  🟡          │
└─────────────────────────────┘
```

---

## 5. Churn Risk Indicator

**Endpoint:** `POST /ai/predict/churn/{user_id}`

> Call this when BO logs in or on dashboard load.

### Request
```http
POST http://ai-service:8000/ai/predict/churn/a091d9c9-e581-4f6e-8cf6-d38fc68dffbf
Content-Length: 0
```

### Response
```json
{
  "user_id": "a091d9c9-e581-4f6e-8cf6-d38fc68dffbf",
  "churn_risk_score": 0.9997
}
```

### UI — Risk Meter
```typescript
getChurnLabel(score: number): { label: string; color: string } {
  if (score >= 0.7) return { label: 'High Risk 🔴', color: '#E74C3C' };
  if (score >= 0.4) return { label: 'Medium Risk 🟡', color: '#F39C12' };
  return { label: 'Low Risk 🟢', color: '#2ECC71' };
}
```

```html
<mat-progress-bar
  mode="determinate"
  [value]="churnScore * 100"
  [color]="churnScore > 0.7 ? 'warn' : 'primary'">
</mat-progress-bar>
<span>{{ (churnScore * 100).toFixed(1) }}% churn risk</span>
```

---

## 6. Financial Export Buttons

**Endpoints:**
```
GET /ai/export/financial/{bo_user_id}?format=csv&from=2026-01-01&to=2026-04-17
GET /ai/export/financial/{bo_user_id}?format=pdf&from=2026-01-01&to=2026-04-17
```

### Angular Download Button
```typescript
downloadReport(format: 'csv' | 'pdf') {
  const url = `${AI_BASE}/ai/export/financial/${this.boUserId}` +
              `?format=${format}&from=${this.fromDate}&to=${this.toDate}`;
  window.open(url, '_blank');   // browser triggers download automatically
}
```

```html
<button (click)="downloadReport('csv')">📥 Export CSV</button>
<button (click)="downloadReport('pdf')">📄 Export PDF</button>
```

> No authentication needed on AI service calls — auth is handled by .NET backend.

---

## 7. Notification Triggers (.NET Backend)

The .NET backend should call these AI endpoints when specific events happen:

| .NET Event | Call AI Endpoint | When |
|---|---|---|
| BO updates profile | `POST /ai/compute/profile/{bo_id}` | On save |
| Product created/updated | `POST /ai/compute/product/{product_id}` | On save |
| Production request → Completed | `POST /ai/compute/request/{request_id}` | On status change |
| New review submitted | `POST /ai/predict/sentiment/{review_id}` | On create |
| New support ticket | `POST /ai/predict/triage/{ticket_id}` | On create |
| New transaction recorded | `POST /ai/predict/anomaly/{tx_id}` | On create |

### .NET HTTP Client Example (C#)
```csharp
// In your .NET service layer
private readonly HttpClient _aiClient;

public async Task NotifyNewReview(int reviewId)
{
    var response = await _aiClient.PostAsync(
        $"http://ai-service:8000/ai/predict/sentiment/{reviewId}",
        null
    );
    // AI scores the review and writes back to DB automatically
}
```

---

## 8. Automatic Nightly Updates

The AI service runs scheduled jobs automatically — **no action needed:**

| Time | Job |
|---|---|
| Every night 02:00 Cairo | Recomputes all predictions for all BOs |
| Every Sunday 03:00 Cairo | Retrains ML models on accumulated real data |

So dashboard data is always fresh by morning without any frontend polling.

---

## 9. TypeScript Interface Definitions

```typescript
// ai.models.ts

export interface DashboardSummary {
  user_id: string;
  revenue_total: number;
  revenue_last_30d: number;
  revenue_trend: 'Rising' | 'Stable' | 'Falling';
  total_orders: number;
  avg_fulfillment_hours: number;
  fraud_alerts: number;
  low_stock_count: number;
  churn_risk_score: number;
  profile_completeness_pct: number;
  avg_product_quality_score: number;
  avg_review_sentiment: number;
  negative_reviews_count: number;
  open_support_tickets: number;
}

export interface RevenueTrend {
  user_id: string;
  period: string;
  overall_trend: 'Rising' | 'Stable' | 'Falling';
  data: { period: string; revenue: number; order_count: number; avg_order_value: number }[];
}

export interface ReviewTrend {
  user_id: string;
  period: string;
  data: { period: string; avg_sentiment: number; review_count: number; negative_count: number; negative_pct: number }[];
}

export interface BenchmarkResult {
  user_id: string;
  fulfillment_rank: string;
  fulfillment_rank_pct: number;
  quality_rank: string;
  quality_rank_pct: number;
  rating_rank: string;
  rating_rank_pct: number;
  bo_fulfillment_hours: number;
  platform_avg_fulfillment_hours: number;
  bo_quality_score: number;
  platform_avg_quality: number;
}
```

---

## 10. Environment Config

```typescript
// environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000',         // .NET backend
  aiUrl: 'http://localhost:8000',          // AI microservice
};
```

```typescript
// ai.service.ts
import { environment } from '../environments/environment';

const AI_BASE = environment.aiUrl;
```

---

## Quick Reference — All Endpoints

| Method | Endpoint | Called By | Purpose |
|---|---|---|---|
| GET | `/ai/status` | Frontend | Health check |
| GET | `/ai/dashboard/{bo_id}` | Frontend | All KPI cards |
| GET | `/ai/analytics/revenue-trend/{bo_id}` | Frontend | Line chart |
| GET | `/ai/reviews/trends/{bo_id}` | Frontend | Sentiment chart |
| GET | `/ai/benchmark/{bo_id}` | Frontend | Radar/comparison |
| GET | `/ai/models/status` | Admin panel | Model accuracy |
| GET | `/ai/export/financial/{bo_id}?format=csv` | Frontend | Download CSV |
| GET | `/ai/export/financial/{bo_id}?format=pdf` | Frontend | Download PDF |
| POST | `/ai/predict/churn/{user_id}` | .NET backend | On BO login |
| POST | `/ai/predict/sentiment/{review_id}` | .NET backend | On new review |
| POST | `/ai/predict/triage/{ticket_id}` | .NET backend | On new ticket |
| POST | `/ai/predict/fraud/{request_id}` | .NET backend | On new request |
| POST | `/ai/predict/anomaly/{tx_id}` | .NET backend | On new transaction |
| POST | `/ai/predict/demand/{product_id}` | .NET backend | On product update |
| POST | `/ai/compute/all` | Admin/manual | Full recompute |
| POST | `/ai/notify/check/{bo_id}` | .NET backend | Check thresholds |
| POST | `/ai/train/all` | Scheduler/manual | Retrain models |

---

## Recommended Angular Libraries

```bash
npm install ng-apexcharts apexcharts         # Charts
npm install @angular/material                 # KPI cards, progress bars
npm install @angular/cdk                      # Overlays, tooltips
```

**Interactive Swagger docs:** `http://ai-service:8000/docs`  
All endpoints can be tested there with real data.
