"""
Admin Forecast Service — Model 8 (NEW)
========================================
Revenue Forecasting using Linear Regression on monthly transaction data.
Predicts next 3 months of platform-wide gross sales.

Algorithm: sklearn LinearRegression
  Input : monthly revenue for last 12 months
  Output: 3 forward-looking monthly revenue predictions
"""
import pickle
import os
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
FORECAST_MODEL_PATH = os.path.join(MODELS_DIR, "admin_forecast_model.pkl")


# ── Training ───────────────────────────────────────────────────────────────────

def train_forecast_model(cursor) -> dict:
    """
    Train a LinearRegression model on the last 12 months of monthly revenue.
    Saves model to admin_forecast_model.pkl.
    Returns training summary.
    """
    from sklearn.linear_model import LinearRegression

    cursor.execute("""
        SELECT
            FORMAT(CreatedAt, 'yyyy-MM') AS month,
            SUM(Amount)                  AS revenue
        FROM Transactions
        WHERE Type = 'Sale'
          AND CreatedAt >= DATEADD(month, -12, GETDATE())
        GROUP BY FORMAT(CreatedAt, 'yyyy-MM')
        ORDER BY month ASC
    """)
    rows = cursor.fetchall()

    if len(rows) < 2:
        return {"status": "skipped", "reason": "Not enough data (need >= 2 months)", "rows": len(rows)}

    months   = [r[0] for r in rows]        # e.g. ['2025-06', '2025-07', ...]
    revenues = [float(r[1] or 0) for r in rows]

    X = np.array(range(len(revenues))).reshape(-1, 1)
    y = np.array(revenues)

    model = LinearRegression()
    model.fit(X, y)

    bundle = {
        "model":       model,
        "months":      months,
        "revenues":    revenues,
        "trained_at":  datetime.utcnow().isoformat(),
        "n_samples":   len(revenues),
        "r2_score":    round(float(model.score(X, y)), 4),
        "coef":        round(float(model.coef_[0]), 2),
        "intercept":   round(float(model.intercept_), 2),
    }

    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(FORECAST_MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)

    return {
        "status":    "trained",
        "n_samples": bundle["n_samples"],
        "r2_score":  bundle["r2_score"],
        "trained_at":bundle["trained_at"],
    }


# ── Inference ──────────────────────────────────────────────────────────────────

def get_revenue_forecast(cursor) -> dict:
    """
    Return:
      - actuals  : last 6 months of real revenue
      - forecast : next 3 months predicted revenue
    Falls back to linear fallback if model not trained yet.
    """
    # Actuals — always fresh from DB
    cursor.execute("""
        SELECT
            FORMAT(CreatedAt, 'yyyy-MM') AS month,
            SUM(Amount)                  AS revenue
        FROM Transactions
        WHERE Type = 'Sale'
          AND CreatedAt >= DATEADD(month, -6, GETDATE())
        GROUP BY FORMAT(CreatedAt, 'yyyy-MM')
        ORDER BY month ASC
    """)
    actuals_rows = cursor.fetchall()
    actuals = [
        {"month": r[0], "revenue": round(float(r[1] or 0.0), 2)}
        for r in actuals_rows
    ]

    # Try loading trained model
    if os.path.exists(FORECAST_MODEL_PATH):
        try:
            with open(FORECAST_MODEL_PATH, "rb") as f:
                bundle = pickle.load(f)

            model   = bundle["model"]
            n_known = bundle["n_samples"]
            trained_at = bundle.get("trained_at", "unknown")

            # Predict next 3 months
            future_indices = np.array([n_known, n_known + 1, n_known + 2]).reshape(-1, 1)
            predictions    = model.predict(future_indices)

            # Build month labels from today
            base = date.today().replace(day=1)
            forecast = []
            for i, pred in enumerate(predictions):
                future_month = base + relativedelta(months=i + 1)
                forecast.append({
                    "month":            future_month.strftime("%Y-%m"),
                    "forecasted_revenue": round(max(0.0, float(pred)), 2),
                })

            return {
                "actuals":    actuals,
                "forecast":   forecast,
                "model_meta": {
                    "trained_at": trained_at,
                    "r2_score":   bundle.get("r2_score", None),
                    "method":     "LinearRegression",
                },
            }
        except Exception:
            pass  # Fall through to simple fallback

    # Simple fallback (no model trained yet)
    forecast = _simple_fallback_forecast(actuals)
    return {
        "actuals":  actuals,
        "forecast": forecast,
        "model_meta": {"method": "simple_average_fallback", "trained_at": None},
    }


def _simple_fallback_forecast(actuals: list) -> list:
    """Use average of last 3 months as flat forecast when no model exists."""
    last_3 = [a["revenue"] for a in actuals[-3:]] if actuals else [0]
    avg    = sum(last_3) / len(last_3)
    base   = date.today().replace(day=1)
    return [
        {
            "month": (base + relativedelta(months=i + 1)).strftime("%Y-%m"),
            "forecasted_revenue": round(avg, 2),
        }
        for i in range(3)
    ]
