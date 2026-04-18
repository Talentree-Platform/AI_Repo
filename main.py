"""
Talentree AI — FastAPI Microservice
====================================
All AI endpoints for the Business Owner Dashboard.
Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
import io

from db.connection import get_conn
from services import (
    churn_service, fraud_service, anomaly_service,
    product_service, profile_service, order_service,
    material_service, sentiment_service, triage_service,
    notification_service, benchmark_service,
    dashboard_service, analytics_service,
    export_service, retrain_service,
)

app = FastAPI(
    title="Talentree AI Service",
    description="AI computation microservice for the Business Owner Dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start nightly/weekly scheduler on app startup
@app.on_event("startup")
async def startup_scheduler():
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

