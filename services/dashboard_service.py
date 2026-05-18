"""Dashboard summary service — single endpoint for all AI metrics."""


def get_dashboard_summary(cursor, bo_user_id: str) -> dict:
    """Return all AI-computed metrics for a BO in one call."""

    # Revenue total + trend
    cursor.execute("""
        SELECT
            ISNULL(SUM(CASE WHEN Amount > 0 THEN Amount ELSE 0 END), 0) AS revenue_total,
            ISNULL(SUM(CASE WHEN Amount > 0 AND CreatedAt >= DATEADD(day,-30,GETDATE()) THEN Amount ELSE 0 END), 0) AS revenue_30d,
            ISNULL(SUM(CASE WHEN Amount > 0 AND CreatedAt >= DATEADD(day,-60,GETDATE())
                            AND CreatedAt < DATEADD(day,-30,GETDATE()) THEN Amount ELSE 0 END), 0) AS revenue_prev_30d
        FROM Transactions WHERE BusinessOwnerId = ? AND Type = 'Sale'
    """, (bo_user_id,))
    rev_row = cursor.fetchone()
    revenue_total = float(rev_row[0] or 0)
    revenue_30d = float(rev_row[1] or 0)
    revenue_prev_30d = float(rev_row[2] or 0)
    if revenue_prev_30d == 0:
        revenue_trend = "Stable"
    elif revenue_30d > revenue_prev_30d * 1.05:
        revenue_trend = "Rising"
    elif revenue_30d < revenue_prev_30d * 0.95:
        revenue_trend = "Falling"
    else:
        revenue_trend = "Stable"

    # Total orders
    cursor.execute("SELECT COUNT(*) FROM BoProductionRequests WHERE BusinessOwnerId=?", (bo_user_id,))
    total_orders = (cursor.fetchone() or [0])[0]

    # Avg fulfillment
    cursor.execute("""
        SELECT ISNULL(AVG(CAST(FulfillmentTimeHours AS FLOAT)), 0)
        FROM BoProductionRequests WHERE BusinessOwnerId=? AND Status='Completed'
    """, (bo_user_id,))
    avg_fulfillment = round(float((cursor.fetchone() or [0])[0] or 0), 1)

    # Fraud alerts
    cursor.execute("""
        SELECT COUNT(*) FROM BoProductionRequests WHERE BusinessOwnerId=? AND IsFraudFlag=1
    """, (bo_user_id,))
    fraud_alerts = (cursor.fetchone() or [0])[0]

    # Low stock count
    cursor.execute("""
        SELECT COUNT(*) FROM Products p
        JOIN BusinessOwnerProfile bop ON bop.Id = p.BusinessOwnerProfileId
        WHERE bop.UserId=? AND p.LowStockFlag=1 AND p.IsDeleted=0
    """, (bo_user_id,))
    low_stock_count = (cursor.fetchone() or [0])[0]

    # Churn risk
    cursor.execute("SELECT ISNULL(ChurnRiskScore, 0) FROM AspNetUsers WHERE Id=?", (bo_user_id,))
    churn_risk = round(float((cursor.fetchone() or [0])[0] or 0), 4)

    # Profile completeness
    cursor.execute("SELECT ISNULL(ProfileCompletenessPct, 0) FROM BusinessOwnerProfile WHERE UserId=?", (bo_user_id,))
    profile_pct = (cursor.fetchone() or [0])[0] or 0

    # Avg product quality
    cursor.execute("""
        SELECT ISNULL(AVG(CAST(p.DescriptionQualityScore AS FLOAT)), 0)
        FROM Products p
        JOIN BusinessOwnerProfile bop ON bop.Id = p.BusinessOwnerProfileId
        WHERE bop.UserId=? AND p.IsDeleted=0
    """, (bo_user_id,))
    avg_quality = round(float((cursor.fetchone() or [0])[0] or 0), 2)

    # Avg review sentiment
    cursor.execute("""
        SELECT
            ISNULL(AVG(CAST(pr.SentimentScore AS FLOAT)), 0),
            COUNT(CASE WHEN pr.SentimentLabel = 'Negative' THEN 1 END)
        FROM ProductReviews pr
        JOIN Products p ON p.Id = pr.ProductId
        JOIN BusinessOwnerProfile bop ON bop.Id = p.BusinessOwnerProfileId
        WHERE bop.UserId=?
    """, (bo_user_id,))
    sent_row = cursor.fetchone()
    avg_sentiment = round(float(sent_row[0] or 0), 4) if sent_row else 0.0
    negative_reviews = int(sent_row[1] or 0) if sent_row else 0

    # Open tickets  (Status: 0=Open, 1=InProgress in new schema)
    cursor.execute("""
        SELECT COUNT(*) FROM SupportTickets WHERE BusinessOwnerUserId=? AND Status IN (0, 1)
    """, (bo_user_id,))
    open_tickets = (cursor.fetchone() or [0])[0]

    return {
        "user_id": bo_user_id,
        "revenue_total": round(revenue_total, 2),
        "revenue_last_30d": round(revenue_30d, 2),
        "revenue_trend": revenue_trend,
        "total_orders": total_orders,
        "avg_fulfillment_hours": avg_fulfillment,
        "fraud_alerts": fraud_alerts,
        "low_stock_count": low_stock_count,
        "churn_risk_score": churn_risk,
        "profile_completeness_pct": profile_pct,
        "avg_product_quality_score": avg_quality,
        "avg_review_sentiment": avg_sentiment,
        "negative_reviews_count": negative_reviews,
        "open_support_tickets": open_tickets,
    }
