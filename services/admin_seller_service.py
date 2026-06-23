"""
Admin Seller Service — FR-AD-19
=================================
Ranked seller performance table with AI-enhanced risk flags.
Reads ChurnRiskScore (Model 1) and FraudScore (Model 2) from DB.
"""


def _risk_level(churn_score: float, avg_fraud_score: float) -> str:
    """Classify seller using churn + fraud scores."""
    if churn_score > 0.7 or avg_fraud_score > 0.6:
        return "High Risk"
    elif churn_score > 0.4 or avg_fraud_score > 0.3:
        return "Medium Risk"
    return "Healthy"


def get_sellers_report(cursor, sort_by: str = "revenue") -> list:
    """
    Return all sellers with performance and AI risk metrics.

    sort_by options: 'revenue' | 'rating' | 'risk' | 'orders'
    """
    cursor.execute("""
        SELECT
            u.Id                                                        AS seller_id,
            u.Email,
            u.IsActive,
            ISNULL(u.ChurnRiskScore, 0.0)                               AS churn_risk_score,
            bop.BusinessName,
            bop.BusinessCategory,
            bop.Status                                                  AS approval_status,
            ISNULL(bop.ProfileCompletenessPct, 0)                       AS profile_completeness,
            bop.CreatedAt                                               AS joined_date,

            -- Products
            (SELECT COUNT(*) FROM Products p
             WHERE p.BusinessOwnerProfileId = bop.Id
               AND p.IsDeleted = 0)                                     AS products_count,

            (SELECT COUNT(*) FROM Products p
             WHERE p.BusinessOwnerProfileId = bop.Id
               AND p.IsDeleted = 0 AND p.Status = 3)                    AS approved_products,

            -- Revenue
            ISNULL((SELECT SUM(t.Amount) FROM Transactions t
                    WHERE t.BusinessOwnerId = u.Id
                      AND t.Type = 'Sale'), 0.0)                        AS total_revenue,

            -- B2B Orders
            (SELECT COUNT(*) FROM BoProductionRequests bpr
             WHERE bpr.BusinessOwnerId = u.Id)                          AS b2b_orders_total,

            (SELECT COUNT(*) FROM BoProductionRequests bpr
             WHERE bpr.BusinessOwnerId = u.Id
               AND bpr.Status = 'Completed')                            AS b2b_orders_completed,

            -- Avg fulfillment hours
            ISNULL((SELECT AVG(CAST(bpr.FulfillmentTimeHours AS FLOAT))
                    FROM BoProductionRequests bpr
                    WHERE bpr.BusinessOwnerId = u.Id
                      AND bpr.Status = 'Completed'
                      AND bpr.FulfillmentTimeHours > 0), 0.0)           AS avg_fulfillment_hours,

            -- Customer Rating
            ISNULL((SELECT AVG(CAST(pr.Rating AS FLOAT))
                    FROM ProductReviews pr
                    JOIN Products p ON p.Id = pr.ProductId
                    WHERE p.BusinessOwnerProfileId = bop.Id), 0.0)      AS avg_customer_rating,

            -- Avg Fraud Score (Model 2)
            ISNULL((SELECT AVG(CAST(bpr.FraudScore AS FLOAT))
                    FROM BoProductionRequests bpr
                    WHERE bpr.BusinessOwnerId = u.Id
                      AND bpr.FraudScore IS NOT NULL), 0.0)             AS avg_fraud_score,

            -- Avg Description Quality (Model 6)
            ISNULL((SELECT AVG(CAST(p.DescriptionQualityScore AS FLOAT))
                    FROM Products p
                    WHERE p.BusinessOwnerProfileId = bop.Id
                      AND p.IsDeleted = 0), 0.0)                        AS avg_quality_score

        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        JOIN BusinessOwnerProfile bop ON bop.UserId = u.Id AND bop.IsDeleted = 0
        WHERE r.Name = 'BusinessOwner'
    """)
    rows = cursor.fetchall()

    sellers = []
    for r in rows:
        churn  = float(r[3] or 0.0)
        fraud  = float(r[16] or 0.0)
        revenue = float(r[11] or 0.0)
        rating  = float(r[15] or 0.0)
        orders  = r[12] or 0

        sellers.append({
            "seller_id":            r[0],
            "email":                r[1],
            "is_active":            bool(r[2]),
            "churn_risk_score":     round(churn, 4),
            "risk_level":           _risk_level(churn, fraud),
            "business_name":        r[4],
            "category":             r[5],
            "approval_status":      r[6],
            "profile_completeness": float(r[7] or 0),
            "joined_date":          r[8].isoformat() if r[8] else None,
            "products_count":       r[9] or 0,
            "approved_products":    r[10] or 0,
            "total_revenue":        round(revenue, 2),
            "b2b_orders_total":     orders,
            "b2b_orders_completed": r[13] or 0,
            "avg_fulfillment_hours":round(float(r[14] or 0.0), 1),
            "avg_customer_rating":  round(rating, 2),
            "avg_fraud_score":      round(fraud, 4),
            "avg_quality_score":    round(float(r[17] or 0.0), 2),
        })

    # Sort
    sort_key = {
        "revenue": lambda x: x["total_revenue"],
        "rating":  lambda x: x["avg_customer_rating"],
        "risk":    lambda x: x["churn_risk_score"],
        "orders":  lambda x: x["b2b_orders_total"],
    }.get(sort_by, lambda x: x["total_revenue"])

    sellers.sort(key=sort_key, reverse=True)
    return sellers


def get_seller_detail(cursor, seller_id: str) -> dict:
    """Return a single seller's full performance profile."""
    all_sellers = get_sellers_report(cursor)
    match = next((s for s in all_sellers if s["seller_id"] == seller_id), None)
    if not match:
        return {"error": f"Seller {seller_id} not found"}

    # Extra: monthly revenue trend for this seller (last 6 months)
    cursor.execute("""
        SELECT FORMAT(CreatedAt, 'yyyy-MM') AS month, SUM(Amount) AS revenue
        FROM Transactions
        WHERE BusinessOwnerId = ? AND Type = 'Sale'
          AND CreatedAt >= DATEADD(month, -6, GETDATE())
        GROUP BY FORMAT(CreatedAt, 'yyyy-MM')
        ORDER BY month ASC
    """, (seller_id,))
    match["revenue_trend"] = [
        {"month": r[0], "revenue": float(r[1] or 0.0)} for r in cursor.fetchall()
    ]

    return match
