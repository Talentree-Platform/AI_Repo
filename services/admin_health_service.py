"""
Admin Health Service (Model 11)
Calculates the live Platform Health Score (0-100).
"""

def get_platform_health_score(cursor) -> dict:
    # 1. Avg Customer Rating
    cursor.execute("SELECT ISNULL(AVG(CAST(Rating AS FLOAT)), 0) FROM ProductReviews")
    avg_rating = cursor.fetchone()[0] or 0.0

    # 2. Conversion Rate (Customers with orders / Total Customers)
    cursor.execute("""
        SELECT COUNT(DISTINCT c.CustomerId) 
        FROM CustomerOrders c
    """)
    buying_customers = cursor.fetchone()[0] or 0
    
    cursor.execute("""
        SELECT COUNT(u.Id) FROM AspNetUsers u
        JOIN AspNetUserRoles ur ON ur.UserId = u.Id
        JOIN AspNetRoles r ON r.Id = ur.RoleId
        WHERE r.Name = 'Customer'
    """)
    total_customers = cursor.fetchone()[0] or 1
    
    conversion_rate = (buying_customers / total_customers) * 100

    # 3. Churn Rate (Sellers with ChurnRiskScore > 0.6)
    cursor.execute("SELECT COUNT(*) FROM AspNetUsers WHERE ChurnRiskScore IS NOT NULL")
    total_scored_sellers = cursor.fetchone()[0] or 1
    
    cursor.execute("SELECT COUNT(*) FROM AspNetUsers WHERE ChurnRiskScore > 0.6")
    churning_sellers = cursor.fetchone()[0] or 0
    
    churn_rate = (churning_sellers / total_scored_sellers) * 100

    # 4. Fraud Rate (Production Requests)
    cursor.execute("SELECT COUNT(*) FROM BoProductionRequests WHERE IsFraudFlag = 1")
    fraud_requests = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM BoProductionRequests")
    total_requests = cursor.fetchone()[0] or 1
    
    fraud_rate = (fraud_requests / total_requests) * 100

    # 5. Anomaly Rate (Transactions)
    cursor.execute("SELECT COUNT(*) FROM Transactions WHERE AnomalyFlag = 1")
    anomaly_tx = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM Transactions")
    total_tx = cursor.fetchone()[0] or 1
    
    anomaly_rate = (anomaly_tx / total_tx) * 100

    # Health Score Formula
    score = (
        (avg_rating / 5.0) * 40
        + (min(conversion_rate, 50) / 50) * 20
        + ((100 - churn_rate) / 100) * 20
        + ((100 - fraud_rate) / 100) * 10
        + ((100 - anomaly_rate) / 100) * 10
    )

    score = round(max(0, min(100, score)), 1)
    
    if score >= 80:
        label = "Excellent"
    elif score >= 60:
        label = "Good"
    elif score >= 40:
        label = "Fair"
    else:
        label = "Needs Attention"

    return {
        "health_score": score,
        "label": label,
        "components": {
            "avg_rating": round(avg_rating, 2),
            "conversion_rate_pct": round(conversion_rate, 2),
            "churn_rate_pct": round(churn_rate, 2),
            "fraud_rate_pct": round(fraud_rate, 2),
            "anomaly_rate_pct": round(anomaly_rate, 2)
        }
    }
