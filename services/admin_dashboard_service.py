"""
Admin Dashboard Service — FR-AD-01
====================================
Platform-wide overview: metric cards, monthly revenue,
and 4 active alert feeds powered by existing ML model outputs.
"""


def get_admin_dashboard(cursor) -> dict:
    """Return all platform metric cards and active alerts in one call."""

    # ── 1. Sellers by status ─────────────────────────────────────────────────
    # Status: 1=Pending, 2=Approved, 3=Suspended
    cursor.execute("""
        SELECT
            COUNT(u.Id)                                                          AS total,
            SUM(CASE WHEN bop.Status = 2 AND u.IsActive = 1 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN bop.Status = 1                    THEN 1 ELSE 0 END)  AS pending,
            SUM(CASE WHEN bop.Status = 3 OR u.IsActive = 0  THEN 1 ELSE 0 END)  AS suspended
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles      r  ON r.Id     = ur.RoleId
        LEFT JOIN BusinessOwnerProfile bop ON bop.UserId = u.Id AND bop.IsDeleted = 0
        WHERE r.Name = 'BusinessOwner'
    """)
    s = cursor.fetchone() or (0, 0, 0, 0)

    # ── 2. Total Customers ────────────────────────────────────────────────────
    cursor.execute("""
        SELECT COUNT(u.Id)
        FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles      r  ON r.Id     = ur.RoleId
        WHERE r.Name = 'Customer'
    """)
    customers_total = (cursor.fetchone() or (0,))[0]

    # ── 3. Products by status ─────────────────────────────────────────────────
    # Status: 2=Pending, 3=Approved
    cursor.execute("""
        SELECT
            COUNT(*),
            SUM(CASE WHEN Status = 3 THEN 1 ELSE 0 END),
            SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END)
        FROM Products WHERE IsDeleted = 0
    """)
    p = cursor.fetchone() or (0, 0, 0)

    # ── 4. B2C Orders by status ───────────────────────────────────────────────
    # Status: 1=Pending 2=Processing 3=Shipped 4=Delivered 5=Cancelled
    cursor.execute("SELECT Status, COUNT(*) FROM CustomerOrders GROUP BY Status")
    orders_map = {r[0]: r[1] for r in cursor.fetchall()}

    # ── 5. B2B Production Requests by status (string values) ─────────────────
    cursor.execute("SELECT Status, COUNT(*) FROM BoProductionRequests GROUP BY Status")
    b2b_map = {r[0]: r[1] for r in cursor.fetchall()}

    # ── 6. Current month net revenue ──────────────────────────────────────────
    cursor.execute("""
        SELECT
            ISNULL(SUM(CASE WHEN Type = 'Sale'   THEN Amount ELSE 0 END), 0)
          - ISNULL(SUM(CASE WHEN Type = 'Refund' THEN Amount ELSE 0 END), 0)
        FROM Transactions
        WHERE CreatedAt >= DATEADD(month, DATEDIFF(month, 0, GETDATE()), 0)
    """)
    current_month_revenue = float((cursor.fetchone() or (0.0,))[0] or 0.0)

    # ── 7. Pending actions count ──────────────────────────────────────────────
    pending_sellers   = s[2] or 0
    pending_products  = p[2] or 0
    cursor.execute("""
        SELECT COUNT(*) FROM Complaints
        WHERE Status = 1 AND CreatedAt <= DATEADD(hour, -48, GETDATE())
    """)
    overdue_complaints_count = (cursor.fetchone() or (0,))[0]
    cursor.execute("""
        SELECT COUNT(*) FROM SupportTickets
        WHERE Status IN (1, 2) AND CreatedAt <= DATEADD(hour, -48, GETDATE())
          AND IsDeleted = 0
    """)
    overdue_tickets_count = (cursor.fetchone() or (0,))[0]

    # ── 8. ALERT: Low stock products (Model 5 — LowStockFlag) ────────────────
    cursor.execute("""
        SELECT TOP 10
            p.Id, p.Name, p.StockQuantity, p.DemandForecastQty,
            bop.BusinessName, c.Name AS category
        FROM Products p
        JOIN BusinessOwnerProfile bop ON bop.Id = p.BusinessOwnerProfileId
        LEFT JOIN Categories c ON c.Id = p.CategoryId
        WHERE p.LowStockFlag = 1 AND p.IsDeleted = 0
        ORDER BY p.StockQuantity ASC
    """)
    low_stock = [
        {
            "product_id": r[0], "name": r[1], "stock_qty": r[2],
            "demand_forecast_qty": r[3], "seller": r[4], "category": r[5]
        } for r in cursor.fetchall()
    ]

    # ── 9. ALERT: Sellers awaiting approval ───────────────────────────────────
    cursor.execute("""
        SELECT TOP 10
            bop.UserId, bop.BusinessName, bop.BusinessCategory,
            bop.CreatedAt, bop.AutoApprovalDeadline,
            DATEDIFF(day, bop.CreatedAt, GETDATE()) AS waiting_days
        FROM BusinessOwnerProfile bop
        WHERE bop.Status = 1 AND bop.IsDeleted = 0
        ORDER BY bop.CreatedAt ASC
    """)
    awaiting_approval = [
        {
            "user_id": r[0], "business_name": r[1], "category": r[2],
            "submitted_at": r[3].isoformat() if r[3] else None,
            "deadline": r[4].isoformat() if r[4] else None,
            "waiting_days": r[5]
        } for r in cursor.fetchall()
    ]

    # ── 10. ALERT: Overdue complaints > 48h (Status=1 Open) ──────────────────
    cursor.execute("""
        SELECT TOP 10
            Id, Description, CreatedAt,
            DATEDIFF(hour, CreatedAt, GETDATE()) AS hours_open
        FROM Complaints
        WHERE Status = 1 AND CreatedAt <= DATEADD(hour, -48, GETDATE())
        ORDER BY CreatedAt ASC
    """)
    overdue_complaints = [
        {
            "complaint_id": r[0], "description": (r[1] or "")[:120],
            "created_at": r[2].isoformat() if r[2] else None,
            "hours_open": r[3]
        } for r in cursor.fetchall()
    ]

    # ── 11. ALERT: Anomaly transactions (Model 3 — AnomalyFlag) ──────────────
    cursor.execute("""
        SELECT TOP 10
            Id, BusinessOwnerId, Amount, AnomalyScore, Type, CreatedAt
        FROM Transactions
        WHERE AnomalyFlag = 1
        ORDER BY AnomalyScore DESC
    """)
    anomaly_transactions = [
        {
            "tx_id": r[0], "seller_id": r[1], "amount": float(r[2]),
            "anomaly_score": round(float(r[3]), 4), "type": r[4],
            "created_at": r[5].isoformat() if r[5] else None
        } for r in cursor.fetchall()
    ]

    # ── 12. Recent activity feed ──────────────────────────────────────────────
    # New seller registrations (last 7 days)
    cursor.execute("""
        SELECT TOP 5
            u.Id, u.Email, bop.BusinessName, bop.BusinessCategory, u.CreatedAt
        FROM BusinessOwnerProfile bop
        JOIN AspNetUsers u ON u.Id = bop.UserId
        WHERE bop.IsDeleted = 0
        ORDER BY u.CreatedAt DESC
    """)
    new_sellers = [
        {
            "user_id": r[0], "email": r[1], "business_name": r[2],
            "category": r[3], "registered_at": r[4].isoformat() if r[4] else None
        } for r in cursor.fetchall()
    ]

    # Recent products submitted
    cursor.execute("""
        SELECT TOP 5
            p.Id, p.Name, p.Status, p.CreatedAt, c.Name AS category
        FROM Products p
        LEFT JOIN Categories c ON c.Id = p.CategoryId
        WHERE p.IsDeleted = 0
        ORDER BY p.CreatedAt DESC
    """)
    new_products = [
        {
            "product_id": r[0], "name": r[1], "status": r[2],
            "submitted_at": r[3].isoformat() if r[3] else None, "category": r[4]
        } for r in cursor.fetchall()
    ]

    # Recent support tickets
    cursor.execute("""
        SELECT TOP 5
            Id, TicketNumber, Subject, AutoCategory, PriorityScore, Status, CreatedAt
        FROM SupportTickets
        WHERE IsDeleted = 0
        ORDER BY CreatedAt DESC
    """)
    recent_tickets = [
        {
            "ticket_id": r[0], "ticket_number": r[1], "subject": r[2],
            "auto_category": r[3], "priority_score": round(float(r[4] or 0), 2),
            "status": r[5], "created_at": r[6].isoformat() if r[6] else None
        } for r in cursor.fetchall()
    ]

    return {
        # ── Metric Cards ──────────────────────────────────────────────────────
        "sellers": {
            "total": s[0] or 0,
            "active": s[1] or 0,
            "pending": s[2] or 0,
            "suspended": s[3] or 0,
        },
        "customers_total": customers_total,
        "products": {
            "total": p[0] or 0,
            "approved": p[1] or 0,
            "pending": p[2] or 0,
        },
        "b2c_orders": {
            "pending":    orders_map.get(1, 0),
            "processing": orders_map.get(2, 0),
            "shipped":    orders_map.get(3, 0),
            "delivered":  orders_map.get(4, 0),
            "cancelled":  orders_map.get(5, 0),
            "total":      sum(orders_map.values()),
        },
        "b2b_orders": {
            "submitted":    b2b_map.get("Submitted", 0),
            "under_review": b2b_map.get("UnderReview", 0),
            "quoted":       b2b_map.get("Quoted", 0),
            "confirmed":    b2b_map.get("Confirmed", 0),
            "in_production":b2b_map.get("InProduction", 0),
            "completed":    b2b_map.get("Completed", 0),
            "rejected":     b2b_map.get("Rejected", 0),
            "cancelled":    b2b_map.get("Cancelled", 0),
            "total":        sum(b2b_map.values()),
        },
        "current_month_revenue": round(current_month_revenue, 2),
        # ── Pending Actions ───────────────────────────────────────────────────
        "pending_actions": {
            "sellers_pending_approval": pending_sellers,
            "products_pending_approval": pending_products,
            "overdue_complaints": overdue_complaints_count,
            "overdue_tickets": overdue_tickets_count,
            "total": pending_sellers + pending_products + overdue_complaints_count + overdue_tickets_count,
        },
        # ── Alert Feeds ───────────────────────────────────────────────────────
        "alerts": {
            "low_stock_products":      low_stock,
            "sellers_awaiting_approval": awaiting_approval,
            "overdue_complaints":       overdue_complaints,
            "anomaly_transactions":     anomaly_transactions,
        },
        # ── Recent Activity ───────────────────────────────────────────────────
        "recent_activity": {
            "new_sellers":   new_sellers,
            "new_products":  new_products,
            "recent_tickets": recent_tickets,
        },
    }
