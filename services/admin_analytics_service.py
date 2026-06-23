"""
Admin Analytics Service — FR-AD-18
=====================================
Trend data for charts: revenue, user growth, order volume,
category distribution. Supports ?period=weekly|monthly.
"""
from datetime import datetime, timedelta


# ── Helpers ───────────────────────────────────────────────────────────────────

def _period_format(period: str) -> str:
    return "yyyy-MM-dd" if period == "weekly" else "yyyy-MM"


def _lookback_months(period: str) -> int:
    return 3 if period == "weekly" else 6


# ── Main function ─────────────────────────────────────────────────────────────

def get_platform_analytics(cursor, period: str = "monthly") -> dict:
    """
    Return chart-ready trend data for the admin analytics page.

    period = 'monthly' → last 6 months, grouped by yyyy-MM
    period = 'weekly'  → last 3 months, grouped by yyyy-MM-dd (week start Mon)
    """
    fmt      = _period_format(period)
    lookback = _lookback_months(period)

    # ── 1. Revenue Trend (gross sales) ────────────────────────────────────────
    cursor.execute(f"""
        SELECT
            FORMAT(CreatedAt, '{fmt}') AS period_key,
            SUM(CASE WHEN Type = 'Sale'   THEN Amount ELSE 0 END) AS gross_sales,
            SUM(CASE WHEN Type = 'Refund' THEN Amount ELSE 0 END) AS refunds,
            SUM(CASE WHEN Type = 'Fee'    THEN Amount ELSE 0 END) AS fees
        FROM Transactions
        WHERE CreatedAt >= DATEADD(month, -{lookback}, GETDATE())
        GROUP BY FORMAT(CreatedAt, '{fmt}')
        ORDER BY period_key ASC
    """)
    revenue_trend = [
        {
            "period": r[0],
            "gross_sales": float(r[1] or 0.0),
            "refunds":     float(r[2] or 0.0),
            "fees":        float(r[3] or 0.0),
            "net_revenue": round(float(r[1] or 0.0) - float(r[2] or 0.0), 2),
        }
        for r in cursor.fetchall()
    ]

    # ── 2. User Growth (new sellers vs new customers) ─────────────────────────
    cursor.execute(f"""
        SELECT
            FORMAT(u.CreatedAt, '{fmt}') AS period_key,
            SUM(CASE WHEN r.Name = 'BusinessOwner' THEN 1 ELSE 0 END) AS new_sellers,
            SUM(CASE WHEN r.Name = 'Customer'      THEN 1 ELSE 0 END) AS new_customers
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        WHERE u.CreatedAt >= DATEADD(month, -{lookback}, GETDATE())
        GROUP BY FORMAT(u.CreatedAt, '{fmt}')
        ORDER BY period_key ASC
    """)
    user_growth = [
        {"period": r[0], "new_sellers": r[1] or 0, "new_customers": r[2] or 0}
        for r in cursor.fetchall()
    ]

    # ── 3. Order Volume Trend (B2C) ───────────────────────────────────────────
    # Status: 4=Delivered (completed), 5=Cancelled
    cursor.execute(f"""
        SELECT
            FORMAT(CreatedAt, '{fmt}') AS period_key,
            COUNT(*)                                                   AS total_orders,
            SUM(CASE WHEN Status = 4 THEN 1 ELSE 0 END)               AS delivered,
            SUM(CASE WHEN Status = 5 THEN 1 ELSE 0 END)               AS cancelled,
            SUM(CAST(TotalAmount AS FLOAT))                            AS total_value
        FROM CustomerOrders
        WHERE CreatedAt >= DATEADD(month, -{lookback}, GETDATE())
        GROUP BY FORMAT(CreatedAt, '{fmt}')
        ORDER BY period_key ASC
    """)
    order_volume = [
        {
            "period":       r[0],
            "total_orders": r[1] or 0,
            "delivered":    r[2] or 0,
            "cancelled":    r[3] or 0,
            "total_value":  round(float(r[4] or 0.0), 2),
        }
        for r in cursor.fetchall()
    ]

    # ── 4. Category Distribution (products & purchases) ───────────────────────
    cursor.execute("""
        SELECT
            c.Name                         AS category,
            COUNT(DISTINCT p.Id)           AS product_count,
            ISNULL(SUM(p.PurchaseCount), 0) AS total_purchases,
            ISNULL(AVG(p.AvgRating),     0) AS avg_rating,
            ISNULL(AVG(p.Price),         0) AS avg_price
        FROM Categories c
        LEFT JOIN Products p ON p.CategoryId = c.Id AND p.IsDeleted = 0
        WHERE c.IsDeleted = 0
        GROUP BY c.Id, c.Name
        ORDER BY total_purchases DESC
    """)
    category_distribution = [
        {
            "category":       r[0],
            "product_count":  r[1] or 0,
            "total_purchases":r[2] or 0,
            "avg_rating":     round(float(r[3] or 0.0), 2),
            "avg_price":      round(float(r[4] or 0.0), 2),
        }
        for r in cursor.fetchall()
    ]

    # ── 5. B2B Order Status Distribution ─────────────────────────────────────
    cursor.execute("""
        SELECT Status, COUNT(*) AS cnt
        FROM BoProductionRequests
        GROUP BY Status
        ORDER BY cnt DESC
    """)
    b2b_distribution = [
        {"status": r[0], "count": r[1]} for r in cursor.fetchall()
    ]

    # ── 6. Platform-wide sentiment breakdown (Model 4) ────────────────────────
    cursor.execute("""
        SELECT
            SentimentLabel,
            COUNT(*) AS cnt,
            AVG(CAST(SentimentScore AS FLOAT)) AS avg_score
        FROM ProductReviews
        WHERE SentimentLabel IS NOT NULL
        GROUP BY SentimentLabel
    """)
    sentiment_breakdown = [
        {"label": r[0], "count": r[1], "avg_score": round(float(r[2] or 0.0), 4)}
        for r in cursor.fetchall()
    ]

    return {
        "period":                period,
        "revenue_trend":         revenue_trend,
        "user_growth":           user_growth,
        "order_volume":          order_volume,
        "category_distribution": category_distribution,
        "b2b_distribution":      b2b_distribution,
        "sentiment_breakdown":   sentiment_breakdown,
    }
