import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
from typing import List, Dict, Any, Tuple
import joblib

class CustomerHybridRecommender:
    """
    Hybrid Product Recommender System combining Item-Item Collaborative Filtering 
    and Content-Based Filtering (TF-IDF on Product Category and Description).
    """
    def __init__(self, alpha: float = 0.4):
        """
        Args:
            alpha (float): Content-based weight. Collaborative filtering weight will be (1 - alpha).
        """
        self.alpha = alpha
        self.products_df: pd.DataFrame = None
        self.user_item_matrix: csr_matrix = None
        self.user_mapper: Dict[int, int] = {}       # Maps external user_id -> internal matrix row index
        self.item_mapper: Dict[int, int] = {}       # Maps external product_id -> internal matrix col index
        self.reverse_user_mapper: Dict[int, int] = {}
        self.reverse_item_mapper: Dict[int, int] = {}
        
        self.item_similarity_cf: np.ndarray = None  # Item-Item collaborative similarity matrix
        self.item_similarity_cb: np.ndarray = None  # Item-Item content-based similarity matrix
        
        self.user_interactions: pd.DataFrame = None
        self.global_popular_items: List[int] = []    # Fallback for cold-start users
        self.tfidf_vectorizer: TfidfVectorizer = None

    def fit(self, interactions_df: pd.DataFrame, products_df: pd.DataFrame):
        """Trains both Collaborative and Content-based similarity components."""
        self.products_df = products_df.copy()
        self.user_interactions = interactions_df.copy()
        
        # 1. COMPUTE GLOBAL POPULARITY (Cold Start Fallback)
        if "weighted_score" in interactions_df.columns:
            # Feature Store dataset path
            popular_items = (
                interactions_df.groupby("item_id")["item_interaction_count"]
                .max()
                .reset_index()
                .sort_values(by="item_interaction_count", ascending=False)
            )
            self.global_popular_items = popular_items["item_id"].head(50).tolist()
        else:
            # Traditional raw interactions path
            purchase_counts = (
                interactions_df[interactions_df["interaction_type"] == "purchase"]
                .groupby("item_id")
                .size()
                .reset_index(name="purchase_count")
            )
            popular_items = (
                interactions_df.groupby("item_id")
                .size()
                .reset_index(name="total_interactions")
                .merge(purchase_counts, on="item_id", how="left")
                .fillna(0)
                .sort_values(by=["purchase_count", "total_interactions"], ascending=False)
            )
            self.global_popular_items = popular_items["item_id"].head(50).tolist()

        # 2. CONTENT-BASED FILTERING: TF-IDF on product metadata
        # Combine Category and Description for rich content profiling
        self.products_df["metadata"] = (
            self.products_df["category"] + " " + self.products_df["description"]
        )
        self.tfidf_vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.products_df["metadata"])
        self.item_similarity_cb = cosine_similarity(tfidf_matrix)

        # 3. COLLABORATIVE FILTERING: Item-Item Cosine Similarity
        if "weighted_score" in interactions_df.columns:
            # We are using the engineered Feature Store DataFrame!
            user_item_scores = interactions_df.copy()
            user_item_scores.rename(columns={"weighted_score": "score"}, inplace=True)
        else:
            # Weight interactions: view=1, click=2, purchase=5
            weight_map = {"view": 1.0, "click": 2.0, "purchase": 5.0}
            interactions_df["score"] = interactions_df["interaction_type"].map(weight_map)
            
            # Group by user-item and aggregate interaction score
            user_item_scores = (
                interactions_df.groupby(["user_id", "item_id"])["score"]
                .sum()
                .reset_index()
            )
        
        # Build index mappers to support sparse matrices
        unique_users = sorted(user_item_scores["user_id"].unique())
        unique_items = sorted(self.products_df["product_id"].unique())
        
        self.user_mapper = {uid: idx for idx, uid in enumerate(unique_users)}
        self.item_mapper = {iid: idx for idx, iid in enumerate(unique_items)}
        self.reverse_user_mapper = {idx: uid for uid, idx in self.user_mapper.items()}
        self.reverse_item_mapper = {idx: iid for iid, idx in self.item_mapper.items()}
        
        # Map user/item columns
        user_item_scores["u_idx"] = user_item_scores["user_id"].map(self.user_mapper)
        user_item_scores["i_idx"] = user_item_scores["item_id"].map(self.item_mapper)
        
        # Drop interactions with items not present in catalog
        user_item_scores = user_item_scores.dropna()
        
        # Create Sparse User-Item Matrix
        num_users = len(self.user_mapper)
        num_items = len(self.item_mapper)
        
        self.user_item_matrix = csr_matrix(
            (user_item_scores["score"], (user_item_scores["u_idx"].astype(int), user_item_scores["i_idx"].astype(int))),
            shape=(num_users, num_items)
        )
        
        # Item-Item Collaborative Similarity (using cosine similarity of columns)
        # Add a tiny epsilon to handle items with zero interactions
        item_cols = self.user_item_matrix.T
        self.item_similarity_cf = cosine_similarity(item_cols)
        
    def recommend(self, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Generates hybrid recommendations for a given user."""
        # COLD START: User not in training history
        if user_id not in self.user_mapper:
            return self._get_popular_recommendations(top_k)
            
        u_idx = self.user_mapper[user_id]
        user_vector = self.user_item_matrix[u_idx].toarray().flatten()
        
        # 1. COLLABORATIVE FILTERING SCORE
        # Predict interest = user_vector * item_similarity_cf
        # We normalize columns to prevent popularity bias
        denom = np.array([np.abs(self.item_similarity_cf).sum(axis=1)])
        denom = np.where(denom == 0, 1.0, denom)
        cf_preds = user_vector.dot(self.item_similarity_cf) / denom
        cf_preds = cf_preds.flatten()
        
        # Min-max normalize CF scores to [0, 1] range for combination consistency
        if cf_preds.max() > cf_preds.min():
            cf_scores = (cf_preds - cf_preds.min()) / (cf_preds.max() - cf_preds.min())
        else:
            cf_scores = cf_preds
            
        # 2. CONTENT-BASED FILTERING SCORE
        # Get products the user has interacted with, weighted by user score
        user_scores = user_vector.copy()
        # Find item similarity with these preferred items
        cb_preds = user_scores.dot(self.item_similarity_cb)
        
        # Min-max normalize CB scores to [0, 1]
        if cb_preds.max() > cb_preds.min():
            cb_scores = (cb_preds - cb_preds.min()) / (cb_preds.max() - cb_preds.min())
        else:
            cb_scores = cb_preds
            
        # 3. HYBRID WEIGHTED SCORE
        hybrid_scores = (1.0 - self.alpha) * cf_scores + self.alpha * cb_scores
        
        # 4. FILTER ITEMS ALREADY PURCHASED OR HIGHLY INTERACTED WITH
        # We want to recommend new products
        already_interacted = np.where(user_vector > 0)[0]
        hybrid_scores[already_interacted] = -1.0 # Suppress purchased/viewed items
        
        # Get Top K products
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]
        
        recommendations = []
        for idx in top_indices:
            score = float(hybrid_scores[idx])
            if score <= 0:
                continue
            item_id = self.reverse_item_mapper[idx]
            prod_info = self.products_df[self.products_df["product_id"] == item_id].iloc[0]
            
            recommendations.append({
                "product_id": int(item_id),
                "product_name": prod_info["product_name"],
                "category": prod_info["category"],
                "price": float(prod_info["price"]),
                "description": prod_info["description"],
                "score": round(score, 4)
            })
            
        # Fill with popular recommendations if we couldn't get enough
        if len(recommendations) < top_k:
            filled_rec = self._get_popular_recommendations(top_k * 2)
            existing_ids = {r["product_id"] for r in recommendations}
            for fr in filled_rec:
                if fr["product_id"] not in existing_ids:
                    recommendations.append(fr)
                    existing_ids.add(fr["product_id"])
                if len(recommendations) >= top_k:
                    break
                    
        return recommendations[:top_k]
        
    def _get_popular_recommendations(self, top_k: int) -> List[Dict[str, Any]]:
        """Returns globally popular products for cold-start users."""
        recommendations = []
        for item_id in self.global_popular_items[:top_k]:
            prod_info = self.products_df[self.products_df["product_id"] == item_id].iloc[0]
            recommendations.append({
                "product_id": int(item_id),
                "product_name": prod_info["product_name"],
                "category": prod_info["category"],
                "price": float(prod_info["price"]),
                "description": prod_info["description"],
                "score": 0.5 # Default medium confidence score
            })
        return recommendations

    def save(self, filepath: str):
        """Persists model state to disk."""
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "CustomerHybridRecommender":
        """Loads model state from disk."""
        return joblib.load(filepath)
