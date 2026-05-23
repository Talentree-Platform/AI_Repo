import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
from typing import List, Dict, Any, Set

def evaluate_owner_forecast(actuals: List[float], predictions: List[float]) -> Dict[str, float]:
    """Computes forecasting accuracy metrics between actual demand and predictions."""
    if not actuals or not predictions or len(actuals) != len(predictions):
        return {"rmse": 0.0, "mae": 0.0}
        
    rmse = np.sqrt(mean_squared_error(actuals, predictions))
    mae = mean_absolute_error(actuals, predictions)
    return {
        "demand_forecast_rmse": float(rmse),
        "demand_forecast_mae": float(mae)
    }

def evaluate_owner_recommender(recommender: Any, test_owner_procurements: Dict[int, Set[int]], k: int = 5) -> Dict[str, float]:
    """Computes Precision@K and Recall@K for the recommendation lists of business owners in the test set."""
    precisions = []
    recalls = []
    
    for oid, actuals in test_owner_procurements.items():
        if not actuals:
            continue
            
        recs = recommender.recommend(owner_id=oid, top_k=k)
        rec_ids = [r["material_id"] for r in recs]
        
        # Calculate Precision@K
        top_rec = rec_ids[:k]
        hits = sum(1 for item in top_rec if item in actuals)
        
        precisions.append(hits / k)
        recalls.append(hits / len(actuals) if len(actuals) > 0 else 0.0)
        
    return {
        f"owner_precision_at_{k}": float(np.mean(precisions)) if precisions else 0.0,
        f"owner_recall_at_{k}": float(np.mean(recalls)) if recalls else 0.0
    }
