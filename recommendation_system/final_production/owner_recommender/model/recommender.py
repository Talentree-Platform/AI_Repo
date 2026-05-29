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
        
        # 1. Check if we are fitting from engineered features
        if "weighted_score" in self.interactions_df.columns:
            # Fit demand forecaster using engineered Feature Store columns
            self.forecaster.fit(self.interactions_df)
            
            # Map global popularity
            popular = (
                self.interactions_df.groupby("item_id")["material_interaction_count"]
                .max()
                .reset_index()
                .sort_values(by="material_interaction_count", ascending=False)
            )
            self.global_popular_materials = popular["item_id"].head(20).tolist()
            
            # Map reorder cycles and last purchase dates
            for _, row in self.interactions_df.iterrows():
                key = f"{int(row['user_id'])}_{int(row['item_id'])}"
                self.reorder_cycles[key] = float(row["avg_procurement_interval_days"])
                # Simulation default last date
                self.last_purchase_dates[key] = datetime.now()
        else:
            # Traditional raw interactions path
            self.interactions_df["interaction_timestamp"] = pd.to_datetime(self.interactions_df["interaction_timestamp"])
            self.forecaster.fit(self.interactions_df)
            
            popular = (
                self.interactions_df.groupby("item_id")
                .size()
                .reset_index(name="count")
                .sort_values(by="count", ascending=False)
            )
            self.global_popular_materials = popular["item_id"].head(20).tolist()
            
            # Focus on purchase/reorder types
            procurements = self.interactions_df[
                self.interactions_df["interaction_type"].isin(["purchase", "reorder"])
            ].sort_values(by=["user_id", "item_id", "interaction_timestamp"])
            
            grouped = procurements.groupby(["user_id", "item_id"])
            for (owner_id, item_id), group in grouped:
                key = f"{owner_id}_{item_id}"
                last_date = group["interaction_timestamp"].iloc[-1]
                self.last_purchase_dates[key] = last_date
                
                if len(group) >= 2:
                    diffs = group["interaction_timestamp"].diff().dropna()
                    mean_days = float(diffs.dt.total_seconds().mean() / (24 * 3600))
                    self.reorder_cycles[key] = max(3.0, min(90.0, mean_days))
                else:
                    self.reorder_cycles[key] = 21.0
                    
        # 3. CONTENT-BASED SIMILARITY (TF-IDF on raw materials metadata)
        self.materials_df["metadata"] = (
            self.materials_df["category"] + " " + self.materials_df["description"]
        )
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.materials_df["metadata"])
        self.material_similarity_cb = cosine_similarity(tfidf_matrix)
        
        for idx, row in self.materials_df.iterrows():
            self.material_mapper[int(row["material_id"])] = idx
            self.reverse_material_mapper[idx] = int(row["material_id"])

    def recommend(self, owner_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Generates raw material procurement recommendations for a business owner."""
        # Check if owner is in training log
        owner_interactions = self.interactions_df[self.interactions_df["user_id"] == owner_id]
        
        if len(owner_interactions) == 0:
            # Cold start fallback
            return self._get_fallback_popular_materials(top_k)
            
        recommendations = []
        all_material_ids = self.materials_df["material_id"].unique()
        
        is_preprocessed = "weighted_score" in self.interactions_df.columns
        
        for mat_id in all_material_ids:
            key = f"{owner_id}_{mat_id}"
            mat_info = self.materials_df[self.materials_df["material_id"] == mat_id].iloc[0]
            
            row_slice = owner_interactions[owner_interactions["item_id"] == mat_id]
            has_record = len(row_slice) > 0
            
            if is_preprocessed:
                # --- PREPROCESSED PATH (Feature Store) ---
                if has_record:
                    # Look up precomputed metrics
                    proc_count = float(row_slice["procurement_count"].iloc[0])
                    volume_score = min(1.0, proc_count / 15.0)
                    
                    cycle_days = float(row_slice["avg_procurement_interval_days"].iloc[0])
                    # Simulating urgency based on precomputed cycle (ratio of expected interval)
                    urgency_score = min(1.0, 7.0 / cycle_days) if cycle_days > 0 else 0.5
                    
                    forecast_qty = float(row_slice["avg_procurement_quantity"].iloc[0])
                    forecast_score = min(1.0, forecast_qty / 200.0) if forecast_qty > 0 else 0.0
                else:
                    volume_score = 0.0
                    urgency_score = 0.0
                    forecast_qty = 0.0
                    forecast_score = 0.0
            else:
                # --- TRADITIONAL RAW INTERACTIONS PATH ---
                procured_count = len(
                    owner_interactions[
                        (owner_interactions["item_id"] == mat_id) & 
                        (owner_interactions["interaction_type"].isin(["purchase", "reorder"]))
                    ]
                )
                volume_score = min(1.0, procured_count / 15.0) if procured_count > 0 else 0.0
                
                urgency_score = 0.0
                if key in self.last_purchase_dates:
                    last_purchase = self.last_purchase_dates[key]
                    max_dataset_date = self.interactions_df["interaction_timestamp"].max()
                    days_elapsed = (max_dataset_date - last_purchase).days
                    cycle_days = self.reorder_cycles.get(key, 21.0)
                    
                    # Ratio: days_elapsed / cycle_days
                    urgency_ratio = days_elapsed / cycle_days
                    urgency_score = min(1.0, max(0.0, urgency_ratio))
                    
                forecast_qty = self.forecaster.predict_next_week_demand(owner_id, int(mat_id), self.interactions_df)
                forecast_score = min(1.0, forecast_qty / 200.0) if forecast_qty > 0 else 0.0
            
            # D. CATEGORY SIMILARITY SCORE (0 to 1)
            sim_score = 0.0
            idx = self.material_mapper.get(int(mat_id))
            if idx is not None:
                purchased_mat_ids = owner_interactions["item_id"].unique()
                purchased_indices = [self.material_mapper[int(mid)] for mid in purchased_mat_ids if int(mid) in self.material_mapper]
                
                if purchased_indices:
                    similarities = self.material_similarity_cb[idx, purchased_indices]
                    sim_score = float(np.mean(similarities))
                    
            # COMBINED SCORE EQUATION
            combined_score = (
                0.3 * volume_score + 
                0.3 * urgency_score + 
                0.2 * forecast_score + 
                0.2 * sim_score
            )
            
            # Days elapsed / cycle extraction for metadata
            if is_preprocessed and has_record:
                cycle_val = int(row_slice["avg_procurement_interval_days"].iloc[0])
                elapsed_val = 7 # default simulated
            else:
                cycle_val = int(self.reorder_cycles.get(key, 0.0)) if key in self.reorder_cycles else 0
                elapsed_val = int((self.interactions_df["interaction_timestamp"].max() - self.last_purchase_dates[key]).days) if key in self.last_purchase_dates else 0
                
            recommendations.append({
                "material_id": int(mat_id),
                "material_name": mat_info["material_name"],
                "category": mat_info["category"],
                "price": float(mat_info["price"]),
                "description": mat_info["description"],
                "predicted_demand_qty": round(forecast_qty, 1),
                "urgency_days_elapsed": elapsed_val,
                "urgency_cycle_days": cycle_val,
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
