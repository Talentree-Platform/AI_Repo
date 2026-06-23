"""
Talentree AI — Nightly + Weekly Scheduler
==========================================
Nightly (02:00 Cairo): Recompute all predictions
Weekly (Sunday 03:00): Retrain models on real DB data

Run standalone: python scheduler.py
Or imported by main.py startup.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db.connection import get_conn
from services import (
    profile_service, product_service, order_service,
    material_service, churn_service, fraud_service,
    anomaly_service, sentiment_service, triage_service,
    notification_service, retrain_service,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scheduler")


# ── Nightly Jobs ────────────────────────────────────────────────────────────

def job_compute_profiles():
    log.info("NIGHTLY: Computing profile completeness...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = profile_service.compute_all_profiles(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} profiles updated")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_compute_products():
    log.info("NIGHTLY: Computing product metrics...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = product_service.compute_all_products(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} products updated")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_compute_materials():
    log.info("NIGHTLY: Computing material stats...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = material_service.compute_material_stats(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} materials updated")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_predict_fulfillment():
    log.info("NIGHTLY: Computing fulfillment times...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = order_service.compute_all_fulfillment(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} requests updated")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_predict_churn():
    log.info("NIGHTLY: Predicting churn for all BOs...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = churn_service.predict_churn_all(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} users scored")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_predict_fraud():
    log.info("NIGHTLY: Predicting fraud for new requests...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = fraud_service.predict_fraud_all(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} requests scored")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_predict_anomalies():
    log.info("NIGHTLY: Predicting transaction anomalies...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = anomaly_service.predict_anomaly_all(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} transactions scored")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_predict_sentiment():
    log.info("NIGHTLY: Analyzing review sentiment...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = sentiment_service.predict_sentiment_all(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} reviews scored")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_predict_triage():
    log.info("NIGHTLY: Triaging support tickets...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = triage_service.triage_all_tickets(cur)
        conn.commit()
        log.info(f"  Done: {len(results)} tickets triaged")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


def job_notify_all():
    log.info("NIGHTLY: Checking notification thresholds...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = notification_service.check_and_notify_all(cur)
        conn.commit()
        total = sum(r.get("notifications_fired", 0) for r in results if isinstance(r, dict))
        log.info(f"  Done: {total} notifications fired for {len(results)} BOs")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


# ── Weekly Retrain Job ───────────────────────────────────────────────────────

def job_retrain_all():
    log.info("WEEKLY: Retraining models on real DB data...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        results = retrain_service.retrain_all(cur)
        conn.commit()
        for model, result in results.items():
            log.info(f"  {model}: {result}")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR: {e}")
    finally:
        cur.close(); conn.close()


# ── Admin Weekly Jobs ─────────────────────────────────────────────────────────

def job_admin_forecast():
    """WEEKLY: Retrain revenue forecast model (Model 8) on latest Transactions."""
    log.info("WEEKLY (ADMIN): Retraining revenue forecast model...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        from services import admin_forecast_service
        result = admin_forecast_service.train_forecast_model(cur)
        conn.commit()
        log.info(f"  Forecast model: {result}")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR (forecast): {e}")
    finally:
        cur.close(); conn.close()


def job_admin_rfm_segment():
    """WEEKLY: Re-cluster B2C customers with RFM K-Means (Model 9) and write segments to DB."""
    log.info("WEEKLY (ADMIN): Running RFM customer segmentation...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        from services import admin_rfm_service
        # 1. Retrain clusters on latest order data
        train_result = admin_rfm_service.train_rfm_model(cur)
        log.info(f"  RFM train: {train_result}")
        # 2. Score all customers and write RfmSegment back to DB
        seg_result = admin_rfm_service.segment_all_customers(cur)
        conn.commit()
        log.info(f"  RFM segments: {seg_result}")
    except Exception as e:
        conn.rollback(); log.error(f"  ERROR (rfm): {e}")
    finally:
        cur.close(); conn.close()


# ── Scheduler Setup ──────────────────────────────────────────────────────────

def create_scheduler() -> BackgroundScheduler:
    """Create and configure the scheduler. Call .start() to activate."""
    scheduler = BackgroundScheduler(timezone="Africa/Cairo")

    # NIGHTLY JOBS — 02:00 Cairo time, staggered by 5 min each
    scheduler.add_job(job_compute_profiles,   CronTrigger(hour=2, minute=0))
    scheduler.add_job(job_compute_products,   CronTrigger(hour=2, minute=5))
    scheduler.add_job(job_compute_materials,  CronTrigger(hour=2, minute=10))
    scheduler.add_job(job_predict_fulfillment, CronTrigger(hour=2, minute=15))
    scheduler.add_job(job_predict_churn,      CronTrigger(hour=2, minute=20))
    scheduler.add_job(job_predict_fraud,      CronTrigger(hour=2, minute=25))
    scheduler.add_job(job_predict_anomalies,  CronTrigger(hour=2, minute=30))
    scheduler.add_job(job_predict_sentiment,  CronTrigger(hour=2, minute=35))
    scheduler.add_job(job_predict_triage,     CronTrigger(hour=2, minute=40))
    scheduler.add_job(job_notify_all,         CronTrigger(hour=2, minute=45))

    # WEEKLY RETRAIN — Sunday 03:00 Cairo
    scheduler.add_job(job_retrain_all,        CronTrigger(day_of_week="sun", hour=3, minute=0))

    # ADMIN WEEKLY JOBS — Sunday 03:30 & 03:45 Cairo (after BO retrain)
    scheduler.add_job(job_admin_forecast,     CronTrigger(day_of_week="sun", hour=3, minute=30),
                      id="admin_forecast",     replace_existing=True)
    scheduler.add_job(job_admin_rfm_segment,  CronTrigger(day_of_week="sun", hour=3, minute=45),
                      id="admin_rfm_segment",  replace_existing=True)

    log.info("Scheduler configured: 10 nightly jobs + 1 weekly retrain + 2 admin weekly jobs")
    return scheduler


if __name__ == "__main__":
    # Run standalone (without FastAPI)
    scheduler = create_scheduler()
    scheduler.start()
    log.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        log.info("Scheduler stopped.")
