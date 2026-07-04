import os
from typing import List, Dict, Any, Optional
from shared.config.settings import settings
from shared.utils.logger import owner_logger
from owner_recommender.model.recommender import OwnerRawMaterialRecommender

class OwnerRecommenderService:
    """Service layer exposing owner raw material recommendations, demand forecasting metrics, and reload functionality."""
    def __init__(self):
        self.model_path = os.path.join(settings.MODEL_DIR, "owner", "latest", "owner_model.joblib")
        self.model: Optional[OwnerRawMaterialRecommender] = None
        self.load_model()
        
    def load_model(self) -> bool:
        """Loads or reloads the Owner Raw Material Recommender model from disk."""
        if not os.path.exists(self.model_path):
            owner_logger.warning(
                f"Owner model file not found at {self.model_path}. "
                "Service will run in fallback popularity-only mode until trained."
            )
            self.model = None
            return False
            
        try:
            self.model = OwnerRawMaterialRecommender.load(self.model_path)
            owner_logger.info(f"Owner recommendation model loaded successfully from {self.model_path}.")
            return True
        except Exception as e:
            owner_logger.error(f"Error loading Owner recommendation model: {e}")
            self.model = None
            return False
            
    def get_recommendations(self, owner_id: Any, top_k: int = 6) -> List[Dict[str, Any]]:
        """Fetches raw material recommendations for an owner, falling back to popularity if model is not loaded."""
        # Cleanly try to cast numeric strings to int so pre-trained forecasting features match
        try:
            owner_id = int(owner_id)
        except (ValueError, TypeError):
            pass

        if self.model is None:
            owner_logger.warning("Recommendation model is not loaded. Yielding popularity fallback.")
            return self._get_fallback_popular_materials(top_k)
            
        try:
            return self.model.recommend(owner_id=owner_id, top_k=top_k)
        except Exception as e:
            owner_logger.error(f"Error generating recommendations for owner {owner_id}: {e}")
            return self._get_fallback_popular_materials(top_k)
            
    def get_model_info(self) -> Dict[str, Any]:
        """Exposes metadata and parameter states of the currently loaded model."""
        if self.model is None:
            return {"status": "uninitialized", "message": "No model loaded on server"}
            
        return {
            "status": "active",
            "forecaster_class": self.model.forecaster.__class__.__name__,
            "trained_materials_count": len(self.model.material_mapper),
            "reorder_cycles_tracked": len(self.model.reorder_cycles),
            "popular_materials_count": len(self.model.global_popular_materials),
            "model_class": self.model.__class__.__name__,
            "last_modified": self._get_model_timestamp()
        }
        
    def _get_model_timestamp(self) -> str:
        """Fetches file modification timestamp of the active model as ISO 8601 string."""
        if not os.path.exists(self.model_path):
            return "N/A"
        try:
            mtime = os.path.getmtime(self.model_path)
            from datetime import datetime
            return datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            return "Unknown"
 
    def _get_fallback_popular_materials(self, top_k: int = 6) -> List[Dict[str, Any]]:
        """Mock fallback catalog recommendation helper when models are not yet compiled."""
        fallback_materials = [
            {"material_id": 1, "material_name": "Premium Cotton Yarn Grade-A", "category": "Fashion & Accessories", "price": 15.99, "description": "Highly demanded weaving thread", "predicted_demand_qty": 120.0, "urgency_days_elapsed": 5, "urgency_cycle_days": 14, "score": 0.5},
            {"material_id": 2, "material_name": "Refined Pottery Clay Sheet", "category": "Handmade & Crafts", "price": 8.50, "description": "High purity structural clay block", "predicted_demand_qty": 45.0, "urgency_days_elapsed": 8, "urgency_cycle_days": 21, "score": 0.5},
            {"material_id": 3, "material_name": "Organic Shea Butter Bulk Base", "category": "Natural & Beauty Products", "price": 48.00, "description": "Raw unrefined coconut oil base", "predicted_demand_qty": 95.0, "urgency_days_elapsed": 3, "urgency_cycle_days": 7, "score": 0.5},
            {"material_id": 4, "material_name": "Linen Fabric Roll Premium", "category": "Fashion & Accessories", "price": 32.50, "description": "Woven linen direct roll", "predicted_demand_qty": 350.0, "urgency_days_elapsed": 12, "urgency_cycle_days": 30, "score": 0.5},
            {"material_id": 5, "material_name": "Natural Soy Wax Flakes Base", "category": "Handmade & Crafts", "price": 14.20, "description": "Artisan candle soy wax package", "predicted_demand_qty": 800.0, "urgency_days_elapsed": 6, "urgency_cycle_days": 14, "score": 0.5},
            {"material_id": 6, "material_name": "Sandalwood Essential Oil Extract", "category": "Natural & Beauty Products", "price": 75.50, "description": "Highly pure aromatic sandlewood essence", "predicted_demand_qty": 150.0, "urgency_days_elapsed": 4, "urgency_cycle_days": 10, "score": 0.5}
        ]
        return fallback_materials[:top_k]

# Global service instance
owner_service = OwnerRecommenderService()
