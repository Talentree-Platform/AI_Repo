import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple
import joblib
from datetime import datetime

from owner_recommender.model.forecaster import OwnerDemandForecaster

class OwnerRawMaterialRecommender:
    """
    Business Owner Recommendation System that scores and ranks raw materials based on:
    1. Historical procurement volume (popular demands)
    2. Cyclic reorder frequency and calendar schedules (urgency calculation)
    3. Multi-period demand forecasting (future quantity requirement)
    4. Category TF-IDF similarities
    """
    def __init__(self):
        self.materials_df: pd.DataFrame = None
        self.interactions_df: pd.DataFrame = None
        self.forecaster = OwnerDemandForecaster()
        
        # Urgency baselines
        self.reorder_cycles: Dict[str, float] = {}   # Key: "owner_id_item_id" -> mean days between purchases
        self.last_purchase_dates: Dict[str, datetime] = {} # Key: "owner_id_item_id" -> datetime
        
        # Category Similarity (TF-IDF)
        self.tfidf_vectorizer = TfidfVectorizer(stop_words="english")
        self.material_similarity_cb: np.ndarray = None
        self.material_mapper: Dict[int, int] = {}
        self.reverse_material_mapper: Dict[int, int] = {}
        
        self.global_popular_materials: List[int] = [] # Fallback

    def fit(self, interactions_df: pd.DataFrame, materials_df: pd.DataFrame):
        """Fits demand forecaster, calculates cycles, and builds TF-IDF profiles."""
        self.materials_df = materials_df.copy()
        self.interactions_df = interactions_df.copy()
        self.interactions_df["interaction_timestamp"] = pd.to_datetime(self.interactions_df["interaction_timestamp"])
        
        # 1. FIT DEMAND FORECASTER
        self.forecaster.fit(self.interactions_df)
        
        # 2. CALCULATE GLOBAL POPULARITY (Fallback)
        popular = (
            self.interactions_df.groupby("item_id")
            .size()
            .reset_index(name="count")
            .sort_values(by="count", ascending=False)
        )
        self.global_popular_materials = popular["item_id"].head(20).tolist()
        
        # 3. CONTENT-BASED SIMILARITY (TF-IDF on raw materials metadata)
        self.materials_df["metadata"] = (
            self.materials_df["category"] + " " + self.materials_df["description"]
        )
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.materials_df["metadata"])
        self.material_similarity_cb = cosine_similarity(tfidf_matrix)
        
        for idx, row in self.materials_df.iterrows():
            self.material_mapper[int(row["material_id"])] = idx
            self.reverse_material_mapper[idx] = int(row["material_id"])
            
        # 4. COMPUTE CYCLIC REORDER INTERVALS PER OWNER-ITEM
        # Focus on purchase/reorder types
        procurements = self.interactions_df[
            self.interactions_df["interaction_type"].isin(["purchase", "reorder"])
        ].sort_values(by=["user_id", "item_id", "interaction_timestamp"])
        
        grouped = procurements.groupby(["user_id", "item_id"])
        
        for (owner_id, item_id), group in grouped:
            key = f"{owner_id}_{item_id}"
            
            # Store last purchase date
            last_date = group["interaction_timestamp"].iloc[-1]
            self.last_purchase_dates[key] = last_date
            
            if len(group) >= 2:
                # Compute average difference in days between consecutive purchases
                diffs = group["interaction_timestamp"].diff().dropna()
                mean_days = float(diffs.dt.total_seconds().mean() / (24 * 3600))
                # Set a boundary, e.g. minimum 3 days and maximum 90 days
                self.reorder_cycles[key] = max(3.0, min(90.0, mean_days))
            else:
                # Default cycle when only single interaction exists
                self.reorder_cycles[key] = 21.0 # 3 weeks default

    def recommend(self, owner_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Generates raw material procurement recommendations for a business owner."""
        # Check if owner is in training log
        owner_interactions = self.interactions_df[self.interactions_df["user_id"] == owner_id]
        
        if len(owner_interactions) == 0:
            # Cold start fallback
            return self._get_fallback_popular_materials(top_k)
            
        recommendations = []
        
        # Score ALL raw materials in catalog
        all_material_ids = self.materials_df["material_id"].unique()
        
        # Max values for normalization of scores
        max_total_interactions = len(owner_interactions)
        
        for mat_id in all_material_ids:
            key = f"{owner_id}_{mat_id}"
            mat_info = self.materials_df[self.materials_df["material_id"] == mat_id].iloc[0]
            
            # A. HISTORICAL PROCURED VOLUME SCORE (0 to 1)
            procured_count = len(
                owner_interactions[
                    (owner_interactions["item_id"] == mat_id) & 
                    (owner_interactions["interaction_type"].isin(["purchase", "reorder"]))
                ]
            )
            volume_score = min(1.0, procured_count / 15.0) if procured_count > 0 else 0.0
            
            # B. CYCLIC REORDER URGENCY SCORE (0 to 1)
            urgency_score = 0.0
            if key in self.last_purchase_dates:
                last_purchase = self.last_purchase_dates[key]
                # Calculate days since last purchase (simulate based on dataset's absolute max date to prevent stale live datetime drift!)
                max_dataset_date = self.interactions_df["interaction_timestamp"].max()
                days_elapsed = (max_dataset_date - last_purchase).days
                cycle_days = self.reorder_cycles.get(key, 21.0)
                
                # Ratio: days_elapsed / cycle_days. If elapsed exceeds cycle, urgency is capped at 1.0
                urgency_ratio = days_elapsed / cycle_days
                urgency_score = min(1.0, max(0.0, urgency_ratio))
                
            # C. DEMAND FORECAST SCORE (0 to 1)
            forecast_qty = self.forecaster.predict_next_week_demand(owner_id, int(mat_id), self.interactions_df)
            # Normalize forecasting: assume anything above 200 units is a high-volume forecast (scale 0-1)
            forecast_score = min(1.0, forecast_qty / 200.0) if forecast_qty > 0 else 0.0
            
            # D. CATEGORY SIMILARITY SCORE (0 to 1)
            # Compute similarity with owner's most active raw materials
            sim_score = 0.0
            idx = self.material_mapper.get(int(mat_id))
            if idx is not None:
                # Find all items this owner purchased
                purchased_mat_ids = owner_interactions["item_id"].unique()
                purchased_indices = [self.material_mapper[int(mid)] for mid in purchased_mat_ids if int(mid) in self.material_mapper]
                
                if purchased_indices:
                    # Average cosine similarity
                    similarities = self.material_similarity_cb[idx, purchased_indices]
                    sim_score = float(np.mean(similarities))
                    
            # COMBINED SCORE EQUATION
            # weights: Volume=0.3, Urgency=0.3, Forecast=0.2, Similarity=0.2
            combined_score = (
                0.3 * volume_score + 
                0.3 * urgency_score + 
                0.2 * forecast_score + 
                0.2 * sim_score
            )
            
            # Store predicted values
            recommendations.append({
                "material_id": int(mat_id),
                "material_name": mat_info["material_name"],
                "category": mat_info["category"],
                "price": float(mat_info["price"]),
                "description": mat_info["description"],
                "predicted_demand_qty": round(forecast_qty, 1),
                "urgency_days_elapsed": int((self.interactions_df["interaction_timestamp"].max() - self.last_purchase_dates[key]).days) if key in self.last_purchase_dates else 0,
                "urgency_cycle_days": int(self.reorder_cycles.get(key, 0.0)) if key in self.reorder_cycles else 0,
                "score": round(combined_score, 4)
            })
            
        # Sort by final score in descending order
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:top_k]

    def _get_fallback_popular_materials(self, top_k: int) -> List[Dict[str, Any]]:
        """Returns popular raw materials for cold-start owners."""
        recommendations = []
        for mat_id in self.global_popular_materials[:top_k]:
            mat_info = self.materials_df[self.materials_df["material_id"] == mat_id].iloc[0]
            recommendations.append({
                "material_id": int(mat_id),
                "material_name": mat_info["material_name"],
                "category": mat_info["category"],
                "price": float(mat_info["price"]),
                "description": mat_info["description"],
                "predicted_demand_qty": 50.0,
                "urgency_days_elapsed": 7,
                "urgency_cycle_days": 14,
                "score": 0.5
            })
        return recommendations

    def save(self, filepath: str):
        """Persists model state to disk."""
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "OwnerRawMaterialRecommender":
        """Loads model state from disk."""
        return joblib.load(filepath)
