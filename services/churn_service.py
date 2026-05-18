"""Churn prediction service — reads users from DB, writes ChurnRiskScore."""
import pickle
import os
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

def _load_model():
    with open(os.path.join(MODELS_DIR, "churn_model.pkl"), "rb") as f:
        return pickle.load(f)

def predict_churn_for_user(cursor, user_id: str) -> float:
    """Compute churn risk score for a single user and write to DB."""
    # Gather features from DB
    cursor.execute("""
        SELECT
            DATEDIFF(day, MAX(lh.LoginAt), GETDATE())        AS days_since_last_login,
            COUNT(CASE WHEN lh.LoginAt >= DATEADD(day,-30,GETDATE()) THEN 1 END) AS login_count_30d,
            u.LoginCount
        FROM AspNetUsers u
        LEFT JOIN LoginHistories lh ON lh.UserId = u.Id
        WHERE u.Id = ?
        GROUP BY u.Id, u.LoginCount
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return 0.0

    days_since_last_login = row[0] or 90
    login_count_30d       = row[1] or 0
    login_count_total     = row[2] or 0

    # Get BO-level stats
    cursor.execute("""
        SELECT
            COUNT(*)                              AS total_orders,
            ISNULL(AVG(CAST(QuotedPrice AS FLOAT)), 0) AS avg_order_value,
            ISNULL(SUM(CASE WHEN Status='Completed' AND
                CreatedAt >= DATEADD(day,-30,GETDATE()) THEN QuotedPrice ELSE 0 END), 0) AS revenue_30d
        FROM BoProductionRequests
        WHERE BusinessOwnerId = ?
    """, (user_id,))
    order_row = cursor.fetchone()
    total_orders   = order_row[0] if order_row else 0
    avg_order_val  = order_row[1] if order_row else 0
    revenue_30d    = order_row[2] if order_row else 0

    cursor.execute("""
        SELECT COUNT(*) FROM SupportTickets
        WHERE BusinessOwnerUserId = ? AND Status IN (0, 1)
    """, (user_id,))
    open_tickets = (cursor.fetchone() or [0])[0]

    cursor.execute("""
        SELECT ISNULL(ProfileCompletenessPct, 30)
        FROM BusinessOwnerProfile WHERE UserId = ?
    """, (user_id,))
    pct_row = cursor.fetchone()
    profile_pct = pct_row[0] if pct_row else 30

    cursor.execute("SELECT COUNT(*) FROM Products WHERE BusinessOwnerProfileId IN (SELECT Id FROM BusinessOwnerProfile WHERE UserId = ?) AND IsDeleted=0", (user_id,))
    product_count = (cursor.fetchone() or [0])[0]

    account_age = max(login_count_total // 2, 30)  # Estimate

    features = [[
        days_since_last_login,
        login_count_30d,
        total_orders,
        avg_order_val,
        open_tickets,
        profile_pct,
        account_age,
        product_count,
        revenue_30d,
        0.05,   # negative_review_pct placeholder
        login_count_30d / 4.0,   # login_frequency_weekly
        10.0    # avg_session_minutes placeholder
    ]]

    bundle = _load_model()
    X_scaled = bundle["scaler"].transform(features)
    score = float(bundle["model"].predict_proba(X_scaled)[0][1])
    score = round(score, 4)

    cursor.execute("""
        UPDATE AspNetUsers
        SET ChurnRiskScore = ?, ChurnRiskUpdatedAt = GETDATE()
        WHERE Id = ?
    """, (score, user_id))
    return score


def predict_churn_all(cursor) -> dict:
    """Run churn prediction for all business owners."""
    cursor.execute("SELECT UserId FROM BusinessOwnerProfile WHERE IsDeleted=0")
    bo_ids = [r[0] for r in cursor.fetchall()]
    results = {}
    for uid in bo_ids:
        try:
            score = predict_churn_for_user(cursor, uid)
            results[uid] = score
        except Exception as e:
            results[uid] = f"ERROR: {e}"
    return results
