"""
Admin KPI Service — FR-AD-02
==============================
9 platform-wide KPIs + composite Platform Health Score (0–100).
All metrics read from pre-computed ML columns — no retraining here.
"""


def get_platform_kpis(cursor) -> dict:
    """
    Return 9 platform KPIs and a composite health score.

    Health Score formula (0–100):
        40% — Customer Satisfaction  (avg review rating / 5)
        20% — B2C Conversion Rate    (customers who ordered / total customers)
        20% — Seller Retention       (% sellers NOT at high churn risk)
        10% — Fraud Safety           (% B2B requests not flagged as fraud)
        10% — Financial Integrity    (% transactions not anomalous)
    """

    # ── 1. Customer Conversion Rate ───────────────────────────────────────────
    cursor.execute("""
        SELECT
            COUNT(DISTINCT co.CustomerId) * 100.0 /
            NULLIF(
                (SELECT COUNT(u.Id)
                 FROM AspNetUsers u
                 JOIN AspNetUserRoles ur ON ur.UserId = u.Id
                 JOIN AspNetRoles r ON r.Id = ur.RoleId
                 WHERE r.Name = 'Customer'), 0
            )
        FROM CustomerOrders co
    """)
    conversion_rate = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 2. Average Order Value (B2C, excluding cancelled) ─────────────────────
    cursor.execute("""
        SELECT AVG(CAST(TotalAmount AS FLOAT))
        FROM CustomerOrders
        WHERE Status != 5
    """)
    avg_order_value = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 3. Seller Churn Rate (Model 1 — ChurnRiskScore > 0.7) ────────────────
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN u.ChurnRiskScore > 0.7 THEN 1 END) * 100.0 /
            NULLIF(COUNT(*), 0)
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        WHERE r.Name = 'BusinessOwner'
    """)
    seller_churn_rate = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 4. Product Approval Rate ──────────────────────────────────────────────
    # Status: 3 = Approved
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN Status = 3 THEN 1 END) * 100.0 /
            NULLIF(COUNT(*), 0)
        FROM Products WHERE IsDeleted = 0
    """)
    product_approval_rate = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 5. Customer Satisfaction Rating (Model 4 — avg review rating) ─────────
    cursor.execute("SELECT AVG(CAST(Rating AS FLOAT)) FROM ProductReviews")
    avg_satisfaction = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 6. Platform Fraud Rate (Model 2 — IsFraudFlag) ───────────────────────
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN IsFraudFlag = 1 THEN 1 END) * 100.0 /
            NULLIF(COUNT(*), 0)
        FROM BoProductionRequests
    """)
    fraud_rate = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 7. Transaction Anomaly Rate (Model 3 — AnomalyFlag) ──────────────────
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN AnomalyFlag = 1 THEN 1 END) * 100.0 /
            NULLIF(COUNT(*), 0)
        FROM Transactions
    """)
    anomaly_rate = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 8. Avg Time to Fulfil B2B Order (hours) ───────────────────────────────
    cursor.execute("""
        SELECT AVG(CAST(FulfillmentTimeHours AS FLOAT))
        FROM BoProductionRequests
        WHERE Status = 'Completed'
          AND FulfillmentTimeHours IS NOT NULL
          AND FulfillmentTimeHours > 0
    """)
    avg_fulfillment_hours = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 9. Avg Seller Profile Completeness ───────────────────────────────────
    cursor.execute("""
        SELECT AVG(CAST(ProfileCompletenessPct AS FLOAT))
        FROM BusinessOwnerProfile
        WHERE IsDeleted = 0
    """)
    avg_profile_completeness = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── Composite Platform Health Score ───────────────────────────────────────
    health_score = (
        (avg_satisfaction / 5.0 * 40.0) +
        (min(conversion_rate, 50.0) / 50.0 * 20.0) +
        ((100.0 - seller_churn_rate) / 100.0 * 20.0) +
        ((100.0 - fraud_rate) / 100.0 * 10.0) +
        ((100.0 - anomaly_rate) / 100.0 * 10.0)
    )
    health_score = round(max(0.0, min(100.0, health_score)), 1)

    # Health label
    if health_score >= 80:
        health_label = "Excellent"
    elif health_score >= 60:
        health_label = "Good"
    elif health_score >= 40:
        health_label = "Fair"
    else:
        health_label = "Needs Attention"

    return {
        "health_score": health_score,
        "health_label": health_label,
        "kpis": {
            "customer_conversion_rate":    round(conversion_rate, 2),
            "average_order_value":         round(avg_order_value, 2),
            "seller_churn_rate":           round(seller_churn_rate, 2),
            "product_approval_rate":       round(product_approval_rate, 2),
            "customer_satisfaction_rating":round(avg_satisfaction, 2),
            "fraud_rate":                  round(fraud_rate, 2),
            "transaction_anomaly_rate":    round(anomaly_rate, 2),
            "avg_fulfillment_hours":       round(avg_fulfillment_hours, 1),
            "avg_seller_profile_completeness": round(avg_profile_completeness, 1),
        },
    }
