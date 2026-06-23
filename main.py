"""
Talentree AI — FastAPI Microservice
====================================
AI endpoints for:
  - Business Owner (BO) Dashboard  →  /ai/*
  - Admin Dashboard                →  /admin/*
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
import io

from db.connection import get_conn

# ── BO Services ───────────────────────────────────────────────────────────────
from services import (
    churn_service, fraud_service, anomaly_service,
    product_service, profile_service, order_service,
    material_service, sentiment_service, triage_service,
    notification_service, benchmark_service,
    dashboard_service, analytics_service,
    export_service, retrain_service,
)

# ── Admin Services ────────────────────────────────────────────────────────────
from services import (
    admin_dashboard_service,
    admin_kpi_service,
    admin_analytics_service,
    admin_seller_service,
    admin_customer_service,
    admin_category_service,
    admin_export_service,
    admin_forecast_service,
    admin_rfm_service,
)

app = FastAPI(
    title="Talentree AI Service",
    description=(
        "AI computation microservice powering the Talentree platform.\n\n"
        "**BO Dashboard** (`/ai/*`) — Per-seller predictions: churn, fraud, anomaly, sentiment, demand, quality, triage.\n\n"
        "**Admin Dashboard** (`/admin/*`) — Platform-wide analytics: KPIs, health score, seller ranking, "
        "customer RFM segmentation, revenue forecasting, and data export."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-train models if pkl files are missing (e.g. first boot / HF Space restart)
def _ensure_models():
    """Train any missing models synchronously using the retrain service.
    HF Spaces uses ephemeral storage — models must be re-trained on every restart.
    """
    import os
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    required = ["churn_model.pkl", "fraud_model.pkl", "anomaly_model.pkl", "demand_model.pkl"]
    missing  = [m for m in required if not os.path.exists(os.path.join(models_dir, m))]
    if not missing:
        print("[STARTUP] All model files present.")
        return

    print(f"[STARTUP] Missing models: {missing} — retraining from DB ...")
    try:
        from db.connection import get_conn
        from services import retrain_service
        conn = get_conn()
        cur  = conn.cursor()
        result = retrain_service.retrain_all(cur)
        conn.commit()
        cur.close()
        conn.close()
        print(f"[STARTUP] Retrain result: {result}")
        # demand model: reuse train_models.py only for demand (XGBoost regressor)
        demand_path = os.path.join(models_dir, "demand_model.pkl")
        if not os.path.exists(demand_path):
            import subprocess, sys
            train_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train", "train_models.py")
            subprocess.run([sys.executable, train_script], capture_output=True)
            print("[STARTUP] Demand model trained via train_models.py")
    except Exception as e:
        print(f"[STARTUP] Auto-train failed: {e}")

# Start nightly/weekly scheduler on app startup
@app.on_event("startup")
async def startup_scheduler():
    import asyncio
    # Run model training SYNCHRONOUSLY first — HF Spaces ephemeral FS wipes pkl on restart
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _ensure_models)
    try:
        from scheduler import create_scheduler
        _scheduler = create_scheduler()
        _scheduler.start()
        app.state.scheduler = _scheduler
        print("[OK] Scheduler started (nightly 02:00 + weekly Sunday 03:00)")
    except Exception as e:
        print(f"[WARN] Scheduler failed to start: {e}")

@app.on_event("shutdown")
async def shutdown_scheduler():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        print("[OK] Scheduler stopped")

# ── Root ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    """Redirect root URL to Swagger docs."""
    return RedirectResponse(url="/docs")

# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/ai/status")
def status():
    return {"status": "ok", "service": "Talentree AI", "version": "1.0.0"}


# ── Dashboard Summary (FR-BO-05) ────────────────────────────────────────────

@app.get("/ai/dashboard/{bo_user_id}")
def get_dashboard(bo_user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        return dashboard_service.get_dashboard_summary(cur, bo_user_id)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Analytics & Trends ──────────────────────────────────────────────────────

@app.get("/ai/analytics/revenue-trend/{bo_user_id}")
def revenue_trend(bo_user_id: str, period: str = Query("weekly", enum=["weekly", "monthly"])):
    conn = get_conn()
    cur = conn.cursor()
    try:
        return analytics_service.get_revenue_trend(cur, bo_user_id, period)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.get("/ai/reviews/trends/{bo_user_id}")
def review_trends(bo_user_id: str, period: str = Query("monthly", enum=["weekly", "monthly"])):
    conn = get_conn()
    cur = conn.cursor()
    try:
        return analytics_service.get_review_trends(cur, bo_user_id, period)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Predict Endpoints ───────────────────────────────────────────────────────

@app.post("/ai/predict/churn/{user_id}")
def predict_churn(user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        score = churn_service.predict_churn_for_user(cur, user_id)
        conn.commit()
        return {"user_id": user_id, "churn_risk_score": score}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/predict/fraud/{request_id}")
def predict_fraud(request_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = fraud_service.predict_fraud_for_request(cur, request_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/predict/anomaly/{tx_id}")
def predict_anomaly(tx_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = anomaly_service.predict_anomaly_for_tx(cur, tx_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/predict/sentiment/{review_id}")
def predict_sentiment(review_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = sentiment_service.predict_sentiment_for_review(cur, review_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/predict/triage/{ticket_id}")
def predict_triage(ticket_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = triage_service.triage_ticket(cur, ticket_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Compute Endpoints ───────────────────────────────────────────────────────

@app.post("/ai/compute/product/{product_id}")
def compute_product(product_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = product_service.compute_product_metrics(cur, product_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/compute/profile/{bo_user_id}")
def compute_profile(bo_user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = profile_service.compute_profile_completeness(cur, bo_user_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/compute/request/{request_id}")
def compute_request(request_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        r1 = order_service.compute_fulfillment_time(cur, request_id)
        r2 = fraud_service.predict_fraud_for_request(cur, request_id)
        conn.commit()
        return {"fulfillment": r1, "fraud": r2}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/compute/materials/all")
def compute_materials():
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = material_service.compute_material_stats(cur)
        conn.commit()
        return {"count": len(results), "results": results}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/compute/all")
def compute_all():
    """Run ALL AI computations across the entire DB. Takes a few minutes."""
    conn = get_conn()
    cur = conn.cursor()
    summary = {}
    try:
        summary["profiles"] = profile_service.compute_all_profiles(cur); conn.commit()
        summary["products"] = product_service.compute_all_products(cur); conn.commit()
        summary["fulfillment"] = order_service.compute_all_fulfillment(cur); conn.commit()
        summary["materials"] = material_service.compute_material_stats(cur); conn.commit()
        summary["churn"] = churn_service.predict_churn_all(cur); conn.commit()
        summary["fraud"] = fraud_service.predict_fraud_all(cur); conn.commit()
        summary["anomaly"] = anomaly_service.predict_anomaly_all(cur); conn.commit()
        summary["sentiment"] = sentiment_service.predict_sentiment_all(cur); conn.commit()
        summary["triage"] = triage_service.triage_all_tickets(cur); conn.commit()
        summary["notifications"] = notification_service.check_and_notify_all(cur); conn.commit()
        return {"status": "complete", "summary": {k: len(v) if isinstance(v, list) else v for k, v in summary.items()}}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Notification & Benchmark ────────────────────────────────────────────────

@app.post("/ai/notify/check/{bo_user_id}")
def notify_check(bo_user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = notification_service.check_and_notify_bo(cur, bo_user_id)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/notify/check/all")
def notify_check_all():
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = notification_service.check_and_notify_all(cur)
        conn.commit()
        return {"count": len(results), "results": results}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.get("/ai/benchmark/{bo_user_id}")
def get_benchmark(bo_user_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        return benchmark_service.get_benchmark(cur, bo_user_id)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.get("/ai/benchmark/all")
def get_all_benchmarks():
    conn = get_conn()
    cur = conn.cursor()
    try:
        return benchmark_service.get_all_benchmarks(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Models Status ───────────────────────────────────────────────────────────

@app.get("/ai/models/status")
def models_status():
    import os, json
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    result = {}
    for f in os.listdir(models_dir):
        if f.endswith("_meta.json"):
            with open(os.path.join(models_dir, f)) as fp:
                result[f.replace("_meta.json", "")] = json.load(fp)
    return result


# ── Demand Forecast ──────────────────────────────────────────────────────────

@app.post("/ai/predict/demand/{product_id}")
def predict_demand(product_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = product_service.compute_product_metrics(cur, product_id)
        conn.commit()
        return {
            "product_id": product_id,
            "demand_forecast_qty": result.get("demand_forecast_qty", 0),
            "low_stock_flag": result.get("low_stock_flag", False),
        }
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Retrain Endpoints ────────────────────────────────────────────────────────

@app.post("/ai/train/churn")
def train_churn():
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = retrain_service.retrain_churn(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/train/fraud")
def train_fraud():
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = retrain_service.retrain_fraud(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/train/anomaly")
def train_anomaly():
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = retrain_service.retrain_anomaly(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/ai/train/all")
def train_all():
    """Retrain all models on real DB data (skips if not enough rows)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = retrain_service.retrain_all(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Financial Export (FR-BO-23) ──────────────────────────────────────────────

@app.get("/ai/export/financial/{bo_user_id}")
def export_financial(
    bo_user_id: str,
    format: str = Query("csv", enum=["csv", "pdf"]),
    from_date: str = Query(None, description="YYYY-MM-DD"),
    to_date: str = Query(None, description="YYYY-MM-DD"),
    tx_type: str = Query(None, enum=["Sale", "MaterialPurchase", "Refund", "Fee", "Payout"]),
):
    conn = get_conn()
    cur = conn.cursor()
    try:
        transactions = export_service.get_transactions(cur, bo_user_id, from_date, to_date, tx_type)
        summary = export_service.compute_summary(transactions)

        if format == "pdf":
            content = export_service.export_pdf(transactions, summary, bo_user_id)
            media_type = "application/pdf"
            filename = f"talentree_financial_{bo_user_id[:8]}.pdf"
        else:
            content = export_service.export_csv(transactions, summary)
            media_type = "text/csv"
            filename = f"talentree_financial_{bo_user_id[:8]}.csv"

        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# ADMIN MODULE — /admin/* routes
# (Services imported at top of file)
# ════════════════════════════════════════════════════════════════════════════════


# ── 0. Admin Status (deployment health check) ─────────────────────────────────

@app.get("/admin/status", tags=["Admin"])
def get_admin_status():
    """
    Confirm the admin module is loaded and running.
    Returns version, available endpoints count, and scheduler job count.
    Use this to verify a fresh Azure deployment has the admin routes active.
    """
    return {
        "status": "ok",
        "module": "admin",
        "service_version": "2.0.0",
        "admin_endpoints": 13,
        "new_models": ["revenue_forecast (Model 8)", "rfm_segmentation (Model 9)"],
        "docs": "https://talentree-ai-service.azurewebsites.net/docs#/Admin",
    }


# ── 1. Admin Dashboard (FR-AD-01) ─────────────────────────────────────────────

@app.get("/admin/dashboard", tags=["Admin"])
def get_admin_dashboard():
    """
    Platform-wide overview: metric cards, pending actions,
    4 alert feeds (low-stock, awaiting approval, overdue complaints, anomalies),
    and recent activity feed.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_dashboard_service.get_admin_dashboard(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 2. Platform KPIs & Health Score (FR-AD-02) ────────────────────────────────

@app.get("/admin/kpis", tags=["Admin"])
def get_admin_kpis():
    """
    9 platform KPIs + composite Platform Health Score (0–100).
    Reads pre-computed ML columns — no live inference.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_kpi_service.get_platform_kpis(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 3. Platform Analytics & Trends (FR-AD-18) ─────────────────────────────────

@app.get("/admin/analytics", tags=["Admin"])
def get_admin_analytics(period: str = Query("monthly", enum=["weekly", "monthly"])):
    """
    Chart-ready trend data: revenue, user growth, order volume,
    category distribution, B2B status split, sentiment breakdown.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_analytics_service.get_platform_analytics(cur, period)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 4. Revenue Forecast (Model 8 — NEW) ──────────────────────────────────────

@app.get("/admin/analytics/forecast", tags=["Admin"])
def get_admin_revenue_forecast():
    """
    3-month forward revenue forecast using LinearRegression (Model 8).
    Returns actuals (last 6 months) + predicted (next 3 months).
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_forecast_service.get_revenue_forecast(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 5. Seller Performance Report (FR-AD-19) ───────────────────────────────────

@app.get("/admin/sellers", tags=["Admin"])
def get_admin_sellers(sort_by: str = Query("revenue", enum=["revenue", "rating", "risk", "orders"])):
    """
    All sellers ranked with AI risk flags (churn score, fraud score).
    sort_by: revenue | rating | risk | orders
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_seller_service.get_sellers_report(cur, sort_by)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.get("/admin/sellers/{seller_id}", tags=["Admin"])
def get_admin_seller_detail(seller_id: str):
    """Full performance profile for a single seller including 6-month revenue trend."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = admin_seller_service.get_seller_detail(cur, seller_id)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 6. Customer Insights (FR-AD-20) ───────────────────────────────────────────

@app.get("/admin/customers", tags=["Admin"])
def get_admin_customers():
    """
    B2C customer cohort analysis: CLV segments, inactive customers,
    peak shopping hours, top wishlisted products, category preferences.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_customer_service.get_customer_insights(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 7. RFM Segments (Model 9 — NEW) ──────────────────────────────────────────

@app.get("/admin/customers/segments", tags=["Admin"])
def get_admin_rfm_segments():
    """
    Customer RFM segment distribution (Champion / Loyal / At Risk / Lost).
    Reads from AspNetUsers.RfmSegment if column exists, else computes live.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_rfm_service.get_rfm_segments(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 8. Category Performance (FR-AD-21) ────────────────────────────────────────

@app.get("/admin/categories", tags=["Admin"])
def get_admin_categories():
    """
    All product categories with: counts, pricing, purchases, revenue,
    average rating, quality score, low-stock alerts, and seller count.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_category_service.get_category_analytics(cur)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.get("/admin/categories/{category_id}/trend", tags=["Admin"])
def get_admin_category_trend(
    category_id: int,
    period: str = Query("monthly", enum=["weekly", "monthly"]),
):
    """Revenue trend for a single category (last 6 months monthly / 3 months weekly)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        return admin_category_service.get_category_trend(cur, category_id, period)
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── 9. Data Export (FR-AD-02 export) ─────────────────────────────────────────

@app.get("/admin/export/kpis", tags=["Admin"])
def export_admin_kpis(format: str = Query("csv", enum=["csv", "xlsx"])):
    """
    Download platform KPI report.
    format=csv  → flat CSV file
    format=xlsx → styled 3-sheet Excel workbook (KPIs, Sellers, Categories)
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        if format == "xlsx":
            data      = admin_export_service.export_kpis_xlsx(cur)
            media     = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename  = "talentree_admin_report.xlsx"
        else:
            data      = admin_export_service.export_kpis_csv(cur)
            media     = "text/csv"
            filename  = "talentree_admin_report.csv"

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ── Admin: Trigger RFM retrain manually ───────────────────────────────────────

@app.post("/admin/train/rfm", tags=["Admin"])
def train_admin_rfm():
    """Manually trigger RFM K-Means retrain + write segments to DB."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        train = admin_rfm_service.train_rfm_model(cur)
        seg   = admin_rfm_service.segment_all_customers(cur)
        conn.commit()
        return {"train": train, "segmentation": seg}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@app.post("/admin/train/forecast", tags=["Admin"])
def train_admin_forecast():
    """Manually trigger revenue forecast model retrain."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        result = admin_forecast_service.train_forecast_model(cur)
        conn.commit()
        return result
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()
