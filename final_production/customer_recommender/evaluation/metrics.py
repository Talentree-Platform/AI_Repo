import numpy as np
from typing import List, Set, Dict, Any

def precision_at_k(recommended_ids: List[int], actual_ids: Set[int], k: int) -> float:
    """Computes Precision@K: Fraction of top K recommended items that are relevant."""
    if not recommended_ids or not actual_ids or k <= 0:
        return 0.0
    
    top_rec = recommended_ids[:k]
    hits = sum(1 for item in top_rec if item in actual_ids)
    return hits / k

def recall_at_k(recommended_ids: List[int], actual_ids: Set[int], k: int) -> float:
    """Computes Recall@K: Fraction of relevant items that are captured in top K recommendations."""
    if not recommended_ids or not actual_ids or k <= 0:
        return 0.0
    
    top_rec = recommended_ids[:k]
    hits = sum(1 for item in top_rec if item in actual_ids)
    return hits / len(actual_ids)

def ndcg_at_k(recommended_ids: List[int], actual_ids: Set[int], k: int) -> float:
    """
    Computes NDCG@K (Normalized Discounted Cumulative Gain).
    Assumes binary relevance (1 if in actual_ids, 0 otherwise).
    """
    if not recommended_ids or not actual_ids or k <= 0:
        return 0.0
    
    top_rec = recommended_ids[:k]
    dcg = 0.0
    for idx, item in enumerate(top_rec):
        if item in actual_ids:
            dcg += 1.0 / np.log2(idx + 2) # idx is 0-based, so rank is idx + 1, formula denominator log2(rank + 1)
            
    # Calculate IDCG (Ideal DCG)
    idcg = 0.0
    num_hits = min(len(actual_ids), k)
    for idx in range(num_hits):
        idcg += 1.0 / np.log2(idx + 2)
        
    if idcg == 0.0:
        return 0.0
        
    return dcg / idcg

def evaluate_recommender(recommender: Any, test_user_interactions: Dict[int, Set[int]], k: int = 5) -> Dict[str, float]:
    """
    Evaluates recommender across multiple users in the test set.
    
    Args:
        recommender: Fitted recommender object that has a `.recommend(user_id, top_k)` method.
        test_user_interactions: Dict mapping user_id to set of actual interacted item_ids in test set.
        k: top K to evaluate on.
    """
    precisions = []
    recalls = []
    ndcgs = []
    
    for uid, actuals in test_user_interactions.items():
        if not actuals:
            continue
            
        recs = recommender.recommend(user_id=uid, top_k=k)
        rec_ids = [r["product_id"] for r in recs]
        
        precisions.append(precision_at_k(rec_ids, actuals, k))
        recalls.append(recall_at_k(rec_ids, actuals, k))
        ndcgs.append(ndcg_at_k(rec_ids, actuals, k))
        
    return {
        f"precision_at_{k}": float(np.mean(precisions)) if precisions else 0.0,
        f"recall_at_{k}": float(np.mean(recalls)) if recalls else 0.0,
        f"ndcg_at_{k}": float(np.mean(ndcgs)) if ndcgs else 0.0
    }
