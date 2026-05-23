import os
os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "0"
os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "2"
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import mlflow
import joblib

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config.settings import settings
from shared.utils.logger import customer_logger
from customer_recommender.model.recommender import CustomerHybridRecommender
from customer_recommender.evaluation.metrics import evaluate_recommender

def run_training(alpha: float = 0.4, data_dir: str = "data"):
    customer_logger.info("Starting Customer Product Recommender Offline Training...")
    
    # Configure MLflow with safe local fallback to prevent network timeouts
    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("customer_recommender_experiment")
    except Exception as ex:
        customer_logger.warning(f"Could not connect to MLflow server at {settings.MLFLOW_TRACKING_URI}. Falling back to local file logging. Error: {ex}")
        mlflow.set_tracking_uri("./mlruns")
        mlflow.set_experiment("customer_recommender_experiment")
    
    # 1. LOAD DATA
    prod_path = os.path.join(data_dir, "products.json")
    inter_path = os.path.join(data_dir, "customer_interactions.json")
    
    if not os.path.exists(prod_path) or not os.path.exists(inter_path):
        customer_logger.error("Training files not found. Ensure generate_data.py has been run.")
        raise FileNotFoundError("Products or customer interactions files not found.")
        
    products_df = pd.read_json(prod_path)
    interactions_df = pd.read_json(inter_path)
    
    customer_logger.info(f"Loaded {len(products_df)} products and {len(interactions_df)} customer interactions.")
    
    # Sort interactions temporally to ensure safe temporal validation split
    interactions_df["interaction_timestamp"] = pd.to_datetime(interactions_df["interaction_timestamp"])
    interactions_df = interactions_df.sort_values(by="interaction_timestamp")
    
    # Split: Train (85%) and Test (15%) based on time
    split_idx = int(len(interactions_df) * 0.85)
    train_df = interactions_df.iloc[:split_idx].copy()
    test_df = interactions_df.iloc[split_idx:].copy()
    
    customer_logger.info(f"Train split size: {len(train_df)}, Test split size: {len(test_df)}")
    
    # 2. FIT MODEL
    recommender = CustomerHybridRecommender(alpha=alpha)
    recommender.fit(train_df, products_df)
    customer_logger.info("Hybrid recommender training complete.")
    
    # 3. EVALUATE MODEL
    # Build actual set of user purchases/clicks in test set to measure metrics
    # Only consider users who have positive purchase or click behavior in test set
    test_interactions = (
        test_df[test_df["interaction_type"].isin(["purchase", "click"])]
        .groupby("user_id")["item_id"]
        .apply(set)
        .to_dict()
    )
    
    # Filter test users to those who were present in training set (to avoid pure cold-start bias on metrics)
    train_users = set(train_df["user_id"].unique())
    test_interactions_filtered = {
        uid: items for uid, items in test_interactions.items()
        if uid in train_users
    }
    
    customer_logger.info(f"Evaluating model on {len(test_interactions_filtered)} active test users...")
    metrics_k5 = evaluate_recommender(recommender, test_interactions_filtered, k=5)
    metrics_k10 = evaluate_recommender(recommender, test_interactions_filtered, k=10)
    
    all_metrics = {**metrics_k5, **metrics_k10}
    customer_logger.info(f"Evaluation Metrics: {all_metrics}")
    
    # 4. MLFLOW LOGGING
    try:
        with mlflow.start_run():
            mlflow.log_param("alpha", alpha)
            mlflow.log_param("train_size", len(train_df))
            mlflow.log_param("test_size", len(test_df))
            mlflow.log_param("model_type", "Hybrid_Content_Collaborative_Filtering")
            
            # Log Metrics
            for m_name, m_val in all_metrics.items():
                mlflow.log_metric(m_name, m_val)
                
            # Log local artifacts
            mlflow.log_text(str(all_metrics), "evaluation_metrics.json")
            
            customer_logger.info("Logged parameters and metrics to MLflow tracking server.")
    except Exception as ex:
        customer_logger.warning(f"Failed to connect to MLflow tracking server: {ex}. Storing model locally anyway.")
        
    # 5. PERSIST MODELS
    # We save to two folders: a version-specific folder (v1, v2) and the 'latest' folder for active FastAPI serving
    version_dir = os.path.join(settings.MODEL_DIR, "customer", "v1")
    latest_dir = os.path.join(settings.MODEL_DIR, "customer", "latest")
    
    os.makedirs(version_dir, exist_ok=True)
    os.makedirs(latest_dir, exist_ok=True)
    
    version_path = os.path.join(version_dir, "customer_model.joblib")
    latest_path = os.path.join(latest_dir, "customer_model.joblib")
    
    recommender.save(version_path)
    recommender.save(latest_path)
    
    customer_logger.info(f"Saved versioned model to {version_path}")
    customer_logger.info(f"Saved latest production model to {latest_path}")
    
    return all_metrics

if __name__ == "__main__":
    run_training()
