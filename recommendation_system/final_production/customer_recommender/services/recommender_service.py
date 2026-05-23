import os
from typing import List, Dict, Any, Optional
from shared.config.settings import settings
from shared.utils.logger import customer_logger
from customer_recommender.model.recommender import CustomerHybridRecommender

class CustomerRecommenderService:
    """Service layer exposing customer product recommendations, model info, and reload functionality."""
    def __init__(self):
        self.model_path = os.path.join(settings.MODEL_DIR, "customer", "latest", "customer_model.joblib")
        self.model: Optional[CustomerHybridRecommender] = None
        self.load_model()
        
    def load_model(self) -> bool:
        """Loads or reloads the Customer Hybrid Recommender model from disk."""
        if not os.path.exists(self.model_path):
            customer_logger.warning(
                f"Customer model file not found at {self.model_path}. "
                "Service will run in fallback popularity-only mode until trained."
            )
            self.model = None
            return False
            
        try:
            self.model = CustomerHybridRecommender.load(self.model_path)
            customer_logger.info(f"Customer recommendation model loaded successfully from {self.model_path}.")
            return True
        except Exception as e:
            customer_logger.error(f"Error loading Customer recommendation model: {e}")
            self.model = None
            return False
            
    def get_recommendations(self, customer_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """Fetches product recommendations for a customer, falling back to popularity if model is not loaded."""
        if self.model is None:
            customer_logger.warning("Recommendation model is not loaded. Yielding popularity fallback.")
            return self._get_fallback_popular_recommendations(top_k)
            
        try:
            return self.model.recommend(user_id=customer_id, top_k=top_k)
        except Exception as e:
            customer_logger.error(f"Error generating recommendations for customer {customer_id}: {e}")
            return self._get_fallback_popular_recommendations(top_k)
            
    def get_model_info(self) -> Dict[str, Any]:
        """Exposes metadata and parameter states of the currently loaded model."""
        if self.model is None:
            return {"status": "uninitialized", "message": "No model loaded on server"}
            
        return {
            "status": "active",
            "alpha": self.model.alpha,
            "trained_users_count": len(self.model.user_mapper),
            "trained_items_count": len(self.model.item_mapper),
            "popular_items_count": len(self.model.global_popular_items),
            "model_class": self.model.__class__.__name__,
            "last_modified": self._get_model_timestamp()
        }
        
    def _get_model_timestamp(self) -> str:
        """Fetches file modification timestamp of the active model."""
        if not os.path.exists(self.model_path):
            return "N/A"
        try:
            mtime = os.path.getmtime(self.model_path)
            from datetime import datetime
            return datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            return "Unknown"

    def _get_fallback_popular_recommendations(self, top_k: int) -> List[Dict[str, Any]]:
        """Mock fallback catalog recommendation helper when models are not yet compiled."""
        # Simple fallback product list
        fallback_products = [
            {"product_id": 1, "product_name": "Premium Wireless Earbuds Model A1", "category": "electronics", "price": 89.99, "description": "Popular choice", "score": 0.5},
            {"product_id": 2, "product_name": "Comfort Fit Denim Jeans Model C2", "category": "clothing", "price": 49.99, "description": "Highly demanded", "score": 0.5},
            {"product_id": 3, "product_name": "Minimalist Desk Lamp Model L3", "category": "home_decor", "price": 29.99, "description": "Sleek look", "score": 0.5},
            {"product_id": 4, "product_name": "Organic Coffee Grade-A", "category": "grocery", "price": 12.50, "description": "Fresh roast", "score": 0.5},
            {"product_id": 5, "product_name": "Hydrating Facial Moisturizer", "category": "beauty", "price": 24.00, "description": "Skin care favorite", "score": 0.5}
        ]
        return fallback_products[:top_k]

# Global service instance
customer_service = CustomerRecommenderService()
