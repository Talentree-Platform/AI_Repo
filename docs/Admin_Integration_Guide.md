# Admin Dashboard — Integration Guide
> **For:** Angular Frontend Team & .NET Backend Team
> **AI Service Base URL (Production):** `http://20.244.32.232:8000`
> **AI Service Base URL (Local):** `http://localhost:8000`
> **Swagger Docs:** `http://20.244.32.232:8000/docs` → scroll to **Admin** section
> **Last Updated:** June 2026

---

## Overview

The Admin Dashboard calls the **same AI microservice** as the BO Dashboard — just different endpoints.

```
┌────────────────────┐     JSON/REST      ┌────────────────────────────────┐
│  Angular Admin     │ ─────────────────► │  Talentree AI Service          │
│  Frontend          │                    │  /admin/* endpoints            │
└────────────────────┘                    └────────────────────────────────┘
                                                         │
                                                    SQL Server DB
                                                  (reads AI columns
                                                   written by BO jobs)
```

> **No new .NET backend triggers needed for admin.** All admin endpoints are called directly by the Angular admin frontend. The .NET backend only needs to add one DB column (`AspNetUsers.RfmSegment`).

---

## Environment Setup

```typescript
// environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000',       // .NET backend
  aiUrl:  'http://localhost:8000',       // AI microservice
};

// environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://api.talentree.com',
  aiUrl:  'http://20.244.32.232:8000',
};
```

```typescript
// admin-ai.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

const AI = environment.aiUrl;

@Injectable({ providedIn: 'root' })
export class AdminAiService {
  constructor(private http: HttpClient) {}
  // ... methods below
}
```

---

## 1. Admin Dashboard Overview — `GET /admin/dashboard`

Call on page load to populate all metric cards, pending action badges, alert feeds, and recent activity.

### Request
```http
GET /admin/dashboard
Accept: application/json
```

### Response Shape
```typescript
// admin-ai.models.ts
export interface AdminDashboard {
  sellers: {
    total: number; active: number; pending: number; suspended: number;
  };
  customers_total: number;
  products: { total: number; approved: number; pending: number };
  b2c_orders: {
    pending: number; processing: number; shipped: number;
    delivered: number; cancelled: number; total: number;
  };
  b2b_orders: {
    submitted: number; under_review: number; quoted: number;
    confirmed: number; in_production: number; completed: number;
    rejected: number; cancelled: number; total: number;
  };
  current_month_revenue: number;
  pending_actions: {
    sellers_pending_approval: number;
    products_pending_approval: number;
    overdue_complaints: number;
    overdue_tickets: number;
    total: number;
  };
  alerts: {
    low_stock_products:        LowStockProduct[];
    sellers_awaiting_approval: SellerAwaiting[];
    overdue_complaints:        OverdueComplaint[];
    anomaly_transactions:      AnomalyTransaction[];
  };
  recent_activity: {
    new_sellers:    NewSeller[];
    new_products:   NewProduct[];
    recent_tickets: RecentTicket[];
  };
}

export interface LowStockProduct {
  product_id: number; name: string; stock_qty: number;
  demand_forecast_qty: number; seller: string; category: string;
}
export interface SellerAwaiting {
  user_id: string; business_name: string; category: string;
  submitted_at: string; deadline: string | null; waiting_days: number;
}
export interface AnomalyTransaction {
  tx_id: number; seller_id: string; amount: number;
  anomaly_score: number; type: string; created_at: string;
}
```

### Angular Service Method
```typescript
getDashboard(): Observable<AdminDashboard> {
  return this.http.get<AdminDashboard>(`${AI}/admin/dashboard`);
}
```

### UI Mapping — Metric Cards
| JSON Field | Card Label | Format | Color Rule |
|---|---|---|---|
| `sellers.active` | Active Sellers | `5` | Neutral |
| `sellers.pending` | Pending Approval | `1` | 🟠 Orange badge if > 0 |
| `customers_total` | Total Customers | `13` | Neutral |
| `products.pending` | Products Pending | `2` | 🟠 Orange if > 0 |
| `current_month_revenue` | This Month Revenue | `EGP 17,350` | Green |
| `b2c_orders.total` | B2C Orders | `3` | Neutral |
| `pending_actions.total` | Action Required | `4` | 🔴 Red badge if > 0 |

### Alert Feed UI
```typescript
// In component
ngOnInit() {
  this.adminAiService.getDashboard().subscribe(data => {
    this.metrics    = data;
    this.alerts     = data.alerts;
    this.badgeCount = data.pending_actions.total;
  });
}
```

```html
<!-- Alert badge on sidebar icon -->
<mat-icon matBadge="{{ badgeCount }}" matBadgeColor="warn">notifications</mat-icon>

<!-- Low stock alert list -->
<div *ngFor="let item of alerts.low_stock_products" class="alert-item warning">
  <span>⚠️ {{ item.name }}</span>
  <span>Stock: {{ item.stock_qty }} | Forecast: {{ item.demand_forecast_qty }}</span>
</div>

<!-- Anomaly transaction alert -->
<div *ngFor="let tx of alerts.anomaly_transactions" class="alert-item danger">
  <span>🚨 Tx #{{ tx.tx_id }} — EGP {{ tx.amount | number:'1.2-2' }}</span>
  <span>Score: {{ tx.anomaly_score | number:'1.4-4' }} | {{ tx.type }}</span>
</div>
```

---

## 2. Platform KPIs & Health Score — `GET /admin/kpis`

### Response Shape
```typescript
export interface AdminKpis {
  health_score: number;    // 0–100
  health_label: 'Excellent' | 'Good' | 'Fair' | 'Needs Attention';
  kpis: {
    customer_conversion_rate:       number;  // %
    average_order_value:            number;  // EGP
    seller_churn_rate:              number;  // %
    product_approval_rate:          number;  // %
    customer_satisfaction_rating:   number;  // 0–5
    fraud_rate:                     number;  // %
    transaction_anomaly_rate:       number;  // %
    avg_fulfillment_hours:          number;  // hours
    avg_seller_profile_completeness:number;  // %
  };
}
```

### Angular Service Method
```typescript
getKpis(): Observable<AdminKpis> {
  return this.http.get<AdminKpis>(`${AI}/admin/kpis`);
}
```

### Health Score UI — Gauge Chart (ApexCharts)
```typescript
this.gaugeChart = {
  series: [data.health_score],
  chart: { type: 'radialBar', height: 280 },
  plotOptions: {
    radialBar: {
      startAngle: -135, endAngle: 135,
      dataLabels: {
        name:  { fontSize: '14px', offsetY: -10 },
        value: { fontSize: '32px', formatter: (val: number) => val.toFixed(0) }
      }
    }
  },
  colors: [data.health_score >= 80 ? '#2ECC71' :
           data.health_score >= 60 ? '#F39C12' : '#E74C3C'],
  labels: [data.health_label],
};
```

### KPI Cards Color Logic
```typescript
getKpiColor(key: string, value: number): string {
  const rules: Record<string, (v: number) => string> = {
    seller_churn_rate:         v => v > 30 ? 'danger' : v > 15 ? 'warning' : 'success',
    fraud_rate:                v => v > 5  ? 'danger' : v > 2  ? 'warning' : 'success',
    transaction_anomaly_rate:  v => v > 10 ? 'danger' : v > 5  ? 'warning' : 'success',
    customer_satisfaction_rating: v => v >= 4 ? 'success' : v >= 3 ? 'warning' : 'danger',
    product_approval_rate:     v => v >= 80 ? 'success' : 'warning',
  };
  return rules[key]?.(value) ?? 'neutral';
}
```

---

## 3. Platform Analytics Charts — `GET /admin/analytics?period=monthly`

### Request
```http
GET /admin/analytics?period=monthly   # or period=weekly
```

### Response Shape
```typescript
export interface AdminAnalytics {
  period: 'monthly' | 'weekly';
  revenue_trend: {
    period: string; gross_sales: number; refunds: number;
    fees: number; net_revenue: number;
  }[];
  user_growth: {
    period: string; new_sellers: number; new_customers: number;
  }[];
  order_volume: {
    period: string; total_orders: number; delivered: number;
    cancelled: number; total_value: number;
  }[];
  category_distribution: {
    category: string; product_count: number; total_purchases: number;
    avg_rating: number; avg_price: number;
  }[];
  b2b_distribution: { status: string; count: number }[];
  sentiment_breakdown: { label: string; count: number; avg_score: number }[];
}
```

### Revenue Line Chart (ApexCharts)
```typescript
getAnalytics(period = 'monthly'): Observable<AdminAnalytics> {
  return this.http.get<AdminAnalytics>(`${AI}/admin/analytics?period=${period}`);
}

// In component:
this.adminAiService.getAnalytics('monthly').subscribe(data => {
  this.revenueChart = {
    series: [
      { name: 'Gross Sales',  data: data.revenue_trend.map(d => d.gross_sales)  },
      { name: 'Net Revenue',  data: data.revenue_trend.map(d => d.net_revenue)  },
      { name: 'Refunds',      data: data.revenue_trend.map(d => d.refunds)      },
    ],
    xaxis: { categories: data.revenue_trend.map(d => d.period) },
    chart:  { type: 'area', height: 350, stacked: false },
    stroke: { curve: 'smooth', width: 2 },
    colors: ['#2ECC71', '#3498DB', '#E74C3C'],
    fill:   { type: 'gradient' },
    dataLabels: { enabled: false },
  };

  this.userGrowthChart = {
    series: [
      { name: 'New Sellers',   data: data.user_growth.map(d => d.new_sellers)   },
      { name: 'New Customers', data: data.user_growth.map(d => d.new_customers) },
    ],
    xaxis:  { categories: data.user_growth.map(d => d.period) },
    chart:  { type: 'bar', height: 300 },
    colors: ['#9B59B6', '#1ABC9C'],
    plotOptions: { bar: { columnWidth: '60%', borderRadius: 4 } },
  };

  // Category donut chart
  this.categoryChart = {
    series: data.category_distribution.map(c => c.total_purchases),
    labels: data.category_distribution.map(c => c.category),
    chart:  { type: 'donut', height: 300 },
    colors: ['#3498DB', '#9B59B6', '#1ABC9C'],
    legend: { position: 'bottom' },
  };
});
```

---

## 4. Revenue Forecast — `GET /admin/analytics/forecast`

3-month forward prediction + last 6 months actuals.

### Response Shape
```typescript
export interface RevenueForecast {
  actuals:  { month: string; revenue: number }[];
  forecast: { month: string; forecasted_revenue: number }[];
  model_meta: {
    method: string;
    r2_score: number | null;
    trained_at: string | null;
  };
}
```

### Service Method
```typescript
getForecast(): Observable<RevenueForecast> {
  return this.http.get<RevenueForecast>(`${AI}/admin/analytics/forecast`);
}
```

### Mixed Line Chart (Actuals + Dashed Forecast)
```typescript
this.adminAiService.getForecast().subscribe(data => {
  const actualMonths   = data.actuals.map(d => d.month);
  const forecastMonths = data.forecast.map(d => d.month);

  this.forecastChart = {
    series: [
      {
        name: 'Actual Revenue',
        data: data.actuals.map(d => ({ x: d.month, y: d.revenue })),
      },
      {
        name: 'Forecast',
        data: data.forecast.map(d => ({ x: d.month, y: d.forecasted_revenue })),
      },
    ],
    chart:  { type: 'line', height: 350 },
    stroke: { width: [3, 2], dashArray: [0, 6] },  // solid actuals, dashed forecast
    colors: ['#2ECC71', '#E67E22'],
    markers: { size: [4, 6] },
    xaxis:  { type: 'category' },
    annotations: {
      xaxis: [{
        x: actualMonths[actualMonths.length - 1],
        borderColor: '#999',
        label: { text: 'Forecast starts →', style: { color: '#fff', background: '#999' } }
      }]
    },
    subtitle: { text: `R² = ${data.model_meta.r2_score?.toFixed(3) ?? 'N/A'}`, align: 'right' },
  };
});
```

---

## 5. Seller Performance Table — `GET /admin/sellers?sort_by=revenue`

### Request
```http
GET /admin/sellers?sort_by=revenue   # revenue | rating | risk | orders
```

### Response Shape
```typescript
export interface AdminSeller {
  seller_id: string;
  email: string;
  is_active: boolean;
  churn_risk_score: number;     // 0–1
  risk_level: 'Healthy' | 'Medium Risk' | 'High Risk';
  business_name: string;
  category: string;
  approval_status: 1 | 2 | 3;  // 1=Pending 2=Approved 3=Suspended
  profile_completeness: number;
  joined_date: string;
  products_count: number;
  approved_products: number;
  total_revenue: number;
  b2b_orders_total: number;
  b2b_orders_completed: number;
  avg_fulfillment_hours: number;
  avg_customer_rating: number;
  avg_fraud_score: number;
  avg_quality_score: number;
}
```

### Service Methods
```typescript
getSellers(sortBy = 'revenue'): Observable<AdminSeller[]> {
  return this.http.get<AdminSeller[]>(`${AI}/admin/sellers?sort_by=${sortBy}`);
}

getSellerDetail(sellerId: string): Observable<AdminSeller & { revenue_trend: any[] }> {
  return this.http.get<any>(`${AI}/admin/sellers/${sellerId}`);
}
```

### Risk Badge Color
```typescript
getRiskColor(level: string): string {
  return { 'High Risk': '#E74C3C', 'Medium Risk': '#F39C12', 'Healthy': '#2ECC71' }[level] ?? '#999';
}
```

### Approval Status Label
```typescript
getApprovalLabel(status: number): string {
  return { 1: 'Pending', 2: 'Approved', 3: 'Suspended' }[status] ?? 'Unknown';
}
```

---

## 6. Customer Insights — `GET /admin/customers`

### Response Shape
```typescript
export interface AdminCustomers {
  high_value_segments: {
    customer_id: string; name: string; email: string;
    orders_count: number; lifetime_value: number;
    avg_order_value: number; days_since_last: number;
  }[];
  inactive_90d_segments: {
    customer_id: string; name: string; email: string;
    last_order_date: string; total_orders: number;
  }[];
  peak_shopping_hours: { hour: number; orders: number }[];
  top_wishlisted_products: {
    product_id: number; name: string; wishlist_count: number;
    category: string; price: number; avg_rating: number;
  }[];
  category_preferences: { category: string; items_ordered: number }[];
  new_vs_returning_30d: { new_customers: number; returning_customers: number };
}
```

### Peak Hours Heatmap
```typescript
this.adminAiService.getCustomers().subscribe(data => {
  this.peakHoursChart = {
    series: [{ name: 'Orders', data: data.peak_shopping_hours.map(h => h.orders) }],
    xaxis:  { categories: data.peak_shopping_hours.map(h => `${h.hour}:00`) },
    chart:  { type: 'bar', height: 200 },
    colors: ['#3498DB'],
    plotOptions: { bar: { borderRadius: 3 } },
    dataLabels: { enabled: false },
  };

  this.newVsReturningChart = {
    series: [data.new_vs_returning_30d.new_customers, data.new_vs_returning_30d.returning_customers],
    labels: ['New Customers', 'Returning'],
    chart:  { type: 'pie', height: 250 },
    colors: ['#9B59B6', '#1ABC9C'],
  };
});
```

---

## 7. RFM Customer Segments — `GET /admin/customers/segments`

### Response Shape
```typescript
export interface RfmSegments {
  source: 'database' | 'computed';
  distribution: {
    Champion?: number; Loyal?: number;
    'At Risk'?: number; Lost?: number;
  };
  total: number;
}
```

### Service Method
```typescript
getRfmSegments(): Observable<RfmSegments> {
  return this.http.get<RfmSegments>(`${AI}/admin/customers/segments`);
}
```

### RFM Donut Chart
```typescript
this.adminAiService.getRfmSegments().subscribe(data => {
  const dist = data.distribution;
  this.rfmChart = {
    series: [
      dist['Champion'] ?? 0,
      dist['Loyal']    ?? 0,
      dist['At Risk']  ?? 0,
      dist['Lost']     ?? 0,
    ],
    labels: ['🏆 Champion', '💛 Loyal', '⚠️ At Risk', '❌ Lost'],
    chart:  { type: 'donut', height: 320 },
    colors: ['#2ECC71', '#3498DB', '#F39C12', '#E74C3C'],
    legend: { position: 'bottom' },
    plotOptions: { pie: { donut: { size: '70%' } } },
  };
});
```

### Manual Retrain Trigger (Admin Button)
```typescript
trainRfm(): Observable<any> {
  return this.http.post(`${AI}/admin/train/rfm`, {});
}

// In component:
this.adminAiService.trainRfm().subscribe(result => {
  console.log('RFM retrain done:', result);
  this.loadSegments();  // refresh chart
});
```

---

## 8. Category Analytics — `GET /admin/categories`

### Response Shape
```typescript
export interface AdminCategory {
  category_id: number; category_name: string; business_type: string;
  total_products: number; approved_products: number; pending_products: number;
  approval_rate_pct: number;
  avg_price: number; min_price: number; max_price: number;
  total_purchases: number; total_revenue: number; total_views: number;
  avg_rating: number; avg_quality_score: number;
  low_stock_count: number; seller_count: number;
}
```

### Service Methods
```typescript
getCategories(): Observable<AdminCategory[]> {
  return this.http.get<AdminCategory[]>(`${AI}/admin/categories`);
}

getCategoryTrend(categoryId: number, period = 'monthly'): Observable<{ period: string; revenue: number }[]> {
  return this.http.get<any[]>(`${AI}/admin/categories/${categoryId}/trend?period=${period}`);
}
```

### Category Revenue Bar Chart
```typescript
this.adminAiService.getCategories().subscribe(cats => {
  this.categoryRevenueChart = {
    series: [
      { name: 'Revenue (EGP)',    data: cats.map(c => c.total_revenue)   },
      { name: 'Total Purchases',  data: cats.map(c => c.total_purchases) },
    ],
    xaxis:  { categories: cats.map(c => c.category_name) },
    chart:  { type: 'bar', height: 300 },
    colors: ['#3498DB', '#2ECC71'],
    plotOptions: { bar: { columnWidth: '55%', borderRadius: 4 } },
  };
});
```

---

## 9. Export Report — `GET /admin/export/kpis?format=csv|xlsx`

### Service Method
```typescript
exportReport(format: 'csv' | 'xlsx'): void {
  const url = `${AI}/admin/export/kpis?format=${format}`;
  window.open(url, '_blank');  // browser triggers download automatically
}
```

### Angular Buttons
```html
<button mat-raised-button color="primary" (click)="exportReport('csv')">
  📥 Export CSV
</button>
<button mat-raised-button color="accent" (click)="exportReport('xlsx')">
  📊 Export Excel (3 sheets)
</button>
```

The XLSX download contains:
- **Sheet 1:** Platform KPIs + Health Score
- **Sheet 2:** All sellers ranked by revenue
- **Sheet 3:** All categories with metrics

---

## 10. .NET Backend — What You Need To Do

### Required DB Migration (One-Time)
```sql
ALTER TABLE AspNetUsers
ADD RfmSegment NVARCHAR(20) NULL;
```

### No New Event Triggers Required
Unlike the BO dashboard (which needs .NET to trigger AI on events like new review, new ticket), the **admin dashboard is entirely read-driven** — Angular calls the admin endpoints directly.

The admin reads data already scored by the existing BO nightly jobs.

### Summary of .NET Work for Admin
| Task | Effort |
|---|---|
| Add `RfmSegment` column to `AspNetUsers` | ✅ 5 minutes (one SQL command) |
| Add new API controllers | ❌ Not needed |
| New event triggers | ❌ Not needed |
| New authentication policies for admin role | ⚠️ Recommended (guard admin routes by `Role = Admin`) |

---

## 11. Quick Reference — All Admin Endpoints

| Method | Endpoint | Called By | Purpose |
|---|---|---|---|
| GET | `/admin/dashboard` | Angular Admin | All metrics + 4 alert feeds |
| GET | `/admin/kpis` | Angular Admin | 9 KPIs + health score |
| GET | `/admin/analytics?period=monthly\|weekly` | Angular Admin | Revenue/user/order/category charts |
| GET | `/admin/analytics/forecast` | Angular Admin | 3-month revenue forecast |
| GET | `/admin/sellers?sort_by=revenue\|rating\|risk\|orders` | Angular Admin | Seller performance table |
| GET | `/admin/sellers/{seller_id}` | Angular Admin | Single seller profile |
| GET | `/admin/customers` | Angular Admin | Customer CLV cohorts |
| GET | `/admin/customers/segments` | Angular Admin | RFM segment distribution |
| GET | `/admin/categories` | Angular Admin | Category performance |
| GET | `/admin/categories/{id}/trend` | Angular Admin | Category revenue trend |
| GET | `/admin/export/kpis?format=csv\|xlsx` | Angular Admin | Download report |
| POST | `/admin/train/rfm` | Admin button | Trigger RFM retrain manually |
| POST | `/admin/train/forecast` | Admin button | Trigger forecast retrain manually |

---

## 13. Platform Health Score — `GET /admin/platform/health`

### Request
```http
GET /admin/platform/health
Accept: application/json
```

### Response Shape
```typescript
export interface PlatformHealth {
  health_score: number;
  label: string;
  components: {
    avg_rating: number;
    conversion_rate_pct: number;
    churn_rate_pct: number;
    fraud_rate_pct: number;
    anomaly_rate_pct: number;
  };
}
```

---

## 14. Price Anomaly Detection — `GET /admin/products/price-anomalies`

### Request
```http
GET /admin/products/price-anomalies
Accept: application/json
```

### Response Shape
```typescript
export interface PriceAnomaliesResponse {
  status: string;
  total_products_scanned: number;
  anomalies_detected: number;
  anomalies: PriceAnomaly[];
}

export interface PriceAnomaly {
  product_id: number;
  name: string;
  seller: string;
  category: string;
  price: number;
  category_avg_price: number;
  anomaly_severity: number;
  reason: string;
}
```

---

## 15. Category Demand Forecast — `GET /admin/categories/forecast`

### Request
```http
GET /admin/categories/forecast
Accept: application/json
```

### Response Shape
```typescript
export interface CategoryForecastResponse {
  status: string;
  categories_forecasted: number;
  forecasts: CategoryForecast[];
}

export interface CategoryForecast {
  category_id: number;
  category_name: string;
  historical_months_used: number;
  trend_r2_score: number;
  projected_growth_pct: number;
  forecast: {
    month: string;
    forecasted_qty: number;
  }[];
}
```

---

## 16. Swagger Testing

All admin endpoints are testable directly in Swagger UI:

```
http://20.244.32.232:8000/docs
```

Scroll to the **Admin** section (after the Business Owner section). Click any endpoint → **Try it out** → **Execute**.

```bash
# Health check
curl http://20.244.32.232:8000/ai/status

# Admin dashboard
curl http://20.244.32.232:8000/admin/dashboard

# KPIs
curl http://20.244.32.232:8000/admin/kpis

# 3-month forecast
curl http://20.244.32.232:8000/admin/analytics/forecast

# Sellers ranked by risk
curl "http://20.244.32.232:8000/admin/sellers?sort_by=risk"

# Download Excel report
curl -OJ "http://20.244.32.232:8000/admin/export/kpis?format=xlsx"
```
