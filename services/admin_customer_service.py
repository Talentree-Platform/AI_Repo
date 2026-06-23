"""
Admin Customer Service — FR-AD-20
===================================
B2C customer cohort analysis: CLV segments, inactive customers,
peak shopping hours, and wishlist insights.
"""


def get_customer_insights(cursor) -> dict:
    """Return B2C customer cohorts and behavioral insights."""

    # ── 1. Top 10 customers by Customer Lifetime Value (CLV) ──────────────────
    cursor.execute("""
        SELECT TOP 10
            u.Id,
            u.DisplayName,
            u.Email,
            COUNT(co.Id)              AS orders_count,
            ISNULL(SUM(co.TotalAmount), 0)  AS lifetime_value,
            ISNULL(AVG(co.TotalAmount), 0)  AS avg_order_value,
            MIN(co.CreatedAt)         AS first_order_date,
            MAX(co.CreatedAt)         AS last_order_date,
            DATEDIFF(day, MAX(co.CreatedAt), GETDATE()) AS days_since_last_order
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        LEFT JOIN CustomerOrders co
            ON co.CustomerId = u.Id AND co.Status != 5
        WHERE r.Name = 'Customer'
        GROUP BY u.Id, u.DisplayName, u.Email
        ORDER BY lifetime_value DESC
    """)
    high_value = [
        {
            "customer_id":       r[0],
            "name":              r[1],
            "email":             r[2],
            "orders_count":      r[3] or 0,
            "lifetime_value":    round(float(r[4] or 0.0), 2),
            "avg_order_value":   round(float(r[5] or 0.0), 2),
            "first_order_date":  r[6].isoformat() if r[6] else None,
            "last_order_date":   r[7].isoformat() if r[7] else None,
            "days_since_last":   r[8] or 0,
        }
        for r in cursor.fetchall()
    ]

    # ── 2. Inactive Customers (no order in last 90 days) ──────────────────────
    cursor.execute("""
        SELECT
            u.Id, u.DisplayName, u.Email,
            MAX(co.CreatedAt) AS last_order,
            COUNT(co.Id)      AS total_orders
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        JOIN CustomerOrders co ON co.CustomerId = u.Id
        WHERE r.Name = 'Customer'
        GROUP BY u.Id, u.DisplayName, u.Email
        HAVING MAX(co.CreatedAt) <= DATEADD(day, -90, GETDATE())
        ORDER BY last_order ASC
    """)
    inactive = [
        {
            "customer_id":   r[0],
            "name":          r[1],
            "email":         r[2],
            "last_order_date": r[3].isoformat() if r[3] else None,
            "total_orders":  r[4] or 0,
        }
        for r in cursor.fetchall()
    ]

    # ── 3. Peak Shopping Hours ────────────────────────────────────────────────
    cursor.execute("""
        SELECT
            DATEPART(HOUR, CreatedAt) AS hour_of_day,
            COUNT(*)                  AS orders_count
        FROM CustomerOrders
        GROUP BY DATEPART(HOUR, CreatedAt)
        ORDER BY hour_of_day ASC
    """)
    peak_hours = [
        {"hour": r[0], "orders": r[1]} for r in cursor.fetchall()
    ]

    # ── 4. Most Wishlisted Products ───────────────────────────────────────────
    cursor.execute("""
        SELECT TOP 10
            p.Id, p.Name, COUNT(*) AS wishlist_count,
            c.Name AS category, p.Price, p.AvgRating
        FROM CustomerWishlistItems cwi
        JOIN Products p ON p.Id = cwi.ProductId
        LEFT JOIN Categories c ON c.Id = p.CategoryId
        WHERE p.IsDeleted = 0
        GROUP BY p.Id, p.Name, c.Name, p.Price, p.AvgRating
        ORDER BY wishlist_count DESC
    """)
    top_wishlisted = [
        {
            "product_id":     r[0],
            "name":           r[1],
            "wishlist_count": r[2],
            "category":       r[3],
            "price":          float(r[4] or 0.0),
            "avg_rating":     round(float(r[5] or 0.0), 2),
        }
        for r in cursor.fetchall()
    ]

    # ── 5. Category Preferences (from B2C order items) ────────────────────────
    cursor.execute("""
        SELECT c.Name AS category, COUNT(*) AS items_ordered
        FROM CustomerOrderItems coi
        JOIN Products p ON p.Id = coi.ProductId
        JOIN Categories c ON c.Id = p.CategoryId
        GROUP BY c.Name
        ORDER BY items_ordered DESC
    """)
    category_prefs = [
        {"category": r[0], "items_ordered": r[1]} for r in cursor.fetchall()
    ]

    # ── 6. New vs Returning Customers (last 30 days) ───────────────────────────
    cursor.execute("""
        SELECT
            COUNT(DISTINCT CASE
                WHEN first_order.min_date >= DATEADD(day, -30, GETDATE())
                THEN co.CustomerId END) AS new_customers,
            COUNT(DISTINCT CASE
                WHEN first_order.min_date < DATEADD(day, -30, GETDATE())
                THEN co.CustomerId END) AS returning_customers
        FROM CustomerOrders co
        JOIN (
            SELECT CustomerId, MIN(CreatedAt) AS min_date
            FROM CustomerOrders GROUP BY CustomerId
        ) first_order ON first_order.CustomerId = co.CustomerId
        WHERE co.CreatedAt >= DATEADD(day, -30, GETDATE())
    """)
    nr = cursor.fetchone() or (0, 0)
    new_vs_returning = {
        "new_customers":       nr[0] or 0,
        "returning_customers": nr[1] or 0,
    }

    return {
        "high_value_segments":  high_value,
        "inactive_90d_segments":inactive,
        "peak_shopping_hours":  peak_hours,
        "top_wishlisted_products": top_wishlisted,
        "category_preferences": category_prefs,
        "new_vs_returning_30d": new_vs_returning,
    }
