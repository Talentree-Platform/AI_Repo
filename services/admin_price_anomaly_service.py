"""
Admin Price Anomaly Service (Model 12)
Detects products with anomalous pricing compared to their category using Isolation Forest.
"""
from sklearn.ensemble import IsolationForest
import numpy as np

def get_price_anomalies(cursor) -> dict:
    # 1. Fetch all active products
    cursor.execute("""
        SELECT p.Id, p.Name, CAST(p.Price AS FLOAT), p.CategoryId, c.Name, b.BusinessName
        FROM Products p
        JOIN Categories c ON c.Id = p.CategoryId
        JOIN BusinessOwnerProfile b ON b.Id = p.BusinessOwnerProfileId
        WHERE p.IsDeleted = 0 AND c.IsDeleted = 0
    """)
    rows = cursor.fetchall()
    
    if len(rows) < 10:
        return {"status": "skipped", "reason": "Not enough products to detect price anomalies"}

    # Group by category to standardize prices within categories
    category_prices = {}
    for r in rows:
        cid = r[3]
        if cid not in category_prices:
            category_prices[cid] = []
        category_prices[cid].append(r[2])

    category_stats = {}
    for cid, prices in category_prices.items():
        category_stats[cid] = {
            "mean": np.mean(prices),
            "std": np.std(prices) if np.std(prices) > 0 else 1.0
        }

    # Prepare features: we use the normalized price (Z-score within category)
    # This allows IsolationForest to find extreme outliers regardless of absolute price.
    X = []
    product_data = []
    
    for r in rows:
        pid, pname, price, cid, cname, seller = r
        stats = category_stats[cid]
        z_score = (price - stats["mean"]) / stats["std"]
        X.append([z_score])
        product_data.append({
            "product_id": pid,
            "name": pname,
            "price": price,
            "category": cname,
            "seller": seller,
            "category_avg": round(stats["mean"], 2),
            "z_score": z_score
        })

    # Train Isolation Forest on the fly
    # Contamination = 0.05 implies we expect ~5% of prices to be anomalous
    clf = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    clf.fit(X)
    
    preds = clf.predict(X)
    scores = clf.decision_function(X) # lower score = more anomalous

    anomalies = []
    for i, p in enumerate(product_data):
        if preds[i] == -1: # Outlier
            # Calculate anomaly severity (0 to 1) based on score
            severity = round(abs(float(scores[i])), 3)
            anomalies.append({
                "product_id": p["product_id"],
                "name": p["name"],
                "seller": p["seller"],
                "category": p["category"],
                "price": p["price"],
                "category_avg_price": p["category_avg"],
                "anomaly_severity": severity,
                "reason": "Price is significantly higher than category average" if p["z_score"] > 0 else "Price is significantly lower than category average"
            })
            
    # Sort by severity descending
    anomalies.sort(key=lambda x: x["anomaly_severity"], reverse=True)

    return {
        "status": "success",
        "total_products_scanned": len(rows),
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies
    }
