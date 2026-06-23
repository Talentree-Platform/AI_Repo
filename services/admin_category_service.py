"""
Admin Category Service — FR-AD-21
====================================
Category-level analytics using the real Categories table
(Products.CategoryId → Categories.Id).
"""


def get_category_analytics(cursor) -> list:
    """
    Return performance metrics for each product category.
    Uses the real Categories table with 3 confirmed categories:
      - Fashion & Accessories
      - Handmade & Crafts
      - Natural & Beauty Products
    """
    cursor.execute("""
        SELECT
            c.Id                                AS category_id,
            c.Name                              AS category_name,
            c.BusinessType,

            -- Product counts
            COUNT(DISTINCT p.Id)                AS total_products,
            COUNT(DISTINCT CASE WHEN p.Status = 3 THEN p.Id END) AS approved_products,
            COUNT(DISTINCT CASE WHEN p.Status = 2 THEN p.Id END) AS pending_products,

            -- Pricing
            ISNULL(AVG(p.Price), 0)             AS avg_price,
            ISNULL(MIN(p.Price), 0)             AS min_price,
            ISNULL(MAX(p.Price), 0)             AS max_price,

            -- Demand & sales
            ISNULL(SUM(p.PurchaseCount),  0)    AS total_purchases,
            ISNULL(SUM(p.RevenueTotal),   0)    AS total_revenue,
            ISNULL(SUM(p.ViewCount),      0)    AS total_views,

            -- Quality signals
            ISNULL(AVG(p.AvgRating),             0) AS avg_rating,
            ISNULL(AVG(p.DescriptionQualityScore),0) AS avg_quality_score,

            -- Stock health
            COUNT(DISTINCT CASE WHEN p.LowStockFlag = 1 THEN p.Id END) AS low_stock_count,

            -- Sellers active in this category
            COUNT(DISTINCT bop.Id)              AS seller_count

        FROM Categories c
        LEFT JOIN Products p
            ON p.CategoryId = c.Id AND p.IsDeleted = 0
        LEFT JOIN BusinessOwnerProfile bop
            ON bop.BusinessCategory = c.Name AND bop.IsDeleted = 0
        WHERE c.IsDeleted = 0
        GROUP BY c.Id, c.Name, c.BusinessType
        ORDER BY total_purchases DESC
    """)

    results = []
    for r in cursor.fetchall():
        total_products = r[3] or 0
        approved       = r[4] or 0
        approval_rate  = round(approved / total_products * 100, 1) if total_products > 0 else 0.0

        results.append({
            "category_id":       r[0],
            "category_name":     r[1],
            "business_type":     r[2],
            "total_products":    total_products,
            "approved_products": approved,
            "pending_products":  r[5] or 0,
            "approval_rate_pct": approval_rate,
            "avg_price":         round(float(r[6] or 0.0), 2),
            "min_price":         round(float(r[7] or 0.0), 2),
            "max_price":         round(float(r[8] or 0.0), 2),
            "total_purchases":   r[9] or 0,
            "total_revenue":     round(float(r[10] or 0.0), 2),
            "total_views":       r[11] or 0,
            "avg_rating":        round(float(r[12] or 0.0), 2),
            "avg_quality_score": round(float(r[13] or 0.0), 2),
            "low_stock_count":   r[14] or 0,
            "seller_count":      r[15] or 0,
        })
    return results


def get_category_trend(cursor, category_id: int, period: str = "monthly") -> list:
    """Return monthly revenue + purchase trend for a single category."""
    fmt = "yyyy-MM-dd" if period == "weekly" else "yyyy-MM"
    lookback = 3 if period == "weekly" else 6

    cursor.execute(f"""
        SELECT
            FORMAT(t.CreatedAt, '{fmt}') AS period_key,
            SUM(t.Amount)               AS revenue
        FROM Transactions t
        JOIN BusinessOwnerProfile bop ON bop.UserId = t.BusinessOwnerId
        JOIN Products p ON p.BusinessOwnerProfileId = bop.Id
        WHERE p.CategoryId = ?
          AND t.Type = 'Sale'
          AND t.CreatedAt >= DATEADD(month, -{lookback}, GETDATE())
        GROUP BY FORMAT(t.CreatedAt, '{fmt}')
        ORDER BY period_key ASC
    """, (category_id,))
    return [
        {"period": r[0], "revenue": round(float(r[1] or 0.0), 2)}
        for r in cursor.fetchall()
    ]
