"""
Admin Category Forecast Service (Model 13)
Predicts the 3-month forward demand (order quantity) per category using Linear Regression.
"""
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime, timedelta

def get_category_demand_forecast(cursor) -> dict:
    # 1. Fetch monthly quantity sold per category
    # We look at the last 12 months
    cursor.execute("""
        SELECT 
            c.Id AS CategoryId,
            c.Name AS CategoryName,
            FORMAT(o.CreatedAt, 'yyyy-MM') AS MonthKey,
            SUM(oi.Quantity) AS TotalQty
        FROM Categories c
        JOIN Products p ON p.CategoryId = c.Id
        JOIN CustomerOrderItems oi ON oi.ProductId = p.Id
        JOIN CustomerOrders o ON o.Id = oi.OrderId
        WHERE o.Status IN (1, 2, 3, 4) -- exclude cancelled
          AND o.CreatedAt >= DATEADD(month, -12, GETDATE())
        GROUP BY c.Id, c.Name, FORMAT(o.CreatedAt, 'yyyy-MM')
        ORDER BY c.Id, MonthKey
    """)
    rows = cursor.fetchall()
    
    if not rows:
        return {"status": "skipped", "reason": "No order data found to forecast demand."}

    # Structure data: { category_id: { month_key: qty } }
    cat_data = {}
    cat_names = {}
    all_months = set()
    
    for r in rows:
        cid, cname, mkey, qty = r
        if cid not in cat_data:
            cat_data[cid] = {}
            cat_names[cid] = cname
        cat_data[cid][mkey] = qty
        all_months.add(mkey)
        
    sorted_months = sorted(list(all_months))
    if len(sorted_months) < 2:
        return {"status": "skipped", "reason": "Not enough historical months (need >= 2) to compute a trend."}

    # Map months to indices (1, 2, 3...)
    month_to_idx = {m: i+1 for i, m in enumerate(sorted_months)}
    
    results = []
    
    for cid, data in cat_data.items():
        X = []
        y = []
        for m in sorted_months:
            if m in data:
                X.append([month_to_idx[m]])
                y.append(data[m])
                
        if len(X) < 2:
            continue
            
        # Train Linear Regression for this category
        model = LinearRegression()
        model.fit(X, y)
        r2 = model.score(X, y) if len(X) > 2 else 0.0
        
        # Predict next 3 months
        last_idx = month_to_idx[sorted_months[-1]]
        future_X = [[last_idx + 1], [last_idx + 2], [last_idx + 3]]
        preds = model.predict(future_X)
        
        # Calculate growth rate
        current_avg = np.mean(y[-3:]) if len(y) >= 3 else np.mean(y)
        future_avg = np.mean(preds)
        growth_pct = ((future_avg - current_avg) / current_avg * 100) if current_avg > 0 else 0
        
        # Parse future month labels
        # A simple way is just +1, +2, +3 months from now
        now = datetime.now()
        future_months = []
        for i in range(1, 4):
            nxt = now.replace(day=1) + timedelta(days=32*i)
            future_months.append(nxt.strftime('%Y-%m'))
            
        forecast_pts = []
        for i, p in enumerate(preds):
            forecast_pts.append({
                "month": future_months[i],
                "forecasted_qty": int(max(0, round(p)))
            })
            
        results.append({
            "category_id": cid,
            "category_name": cat_names[cid],
            "historical_months_used": len(X),
            "trend_r2_score": round(r2, 4),
            "projected_growth_pct": round(growth_pct, 1),
            "forecast": forecast_pts
        })
        
    # Sort by highest projected growth
    results.sort(key=lambda x: x["projected_growth_pct"], reverse=True)

    return {
        "status": "success",
        "categories_forecasted": len(results),
        "forecasts": results
    }
