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
from shared.data_sources import DataSourceFactory
from shared.feature_engineering.customer.customer_feature_builder import CustomerFeatureBuilder
from shared.feature_validation import FeatureValidator
from shared.feature_store import ParquetFeatureStore

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
    
    # 1. LOAD DATA VIA DATA SOURCE ABSTRACTION LAYER (SQL + Fallback to JSON)
    data_source = DataSourceFactory.get_data_source()
    products_df = data_source.load_products()
    interactions_df = data_source.load_customer_interactions()
    
    customer_logger.info(f"Loaded {len(products_df)} products and {len(interactions_df)} customer interactions.")
    
    # Sort interactions temporally to ensure safe temporal validation split
    interactions_df["interaction_timestamp"] = pd.to_datetime(interactions_df["interaction_timestamp"])
    interactions_df = interactions_df.sort_values(by="interaction_timestamp")
    
    # Split: Train (85%) and Test (15%) based on time
    split_idx = int(len(interactions_df) * 0.85)
    train_raw = interactions_df.iloc[:split_idx].copy()
    test_df = interactions_df.iloc[split_idx:].copy()
    
    customer_logger.info(f"Train split size: {len(train_raw)} raw rows, Test split size: {len(test_df)}")
    
    # 2. FEATURE ENGINEERING PIPELINE
    feature_builder = CustomerFeatureBuilder()
    train_features = feature_builder.build_features(train_raw, products_df)
    
    # 3. FEATURE VALIDATION LAYER
    FeatureValidator.validate_customer_features(train_features)
    
    # 4. Parquet VERSIONED FEATURE STORE PERSISTENCE
    feature_store = ParquetFeatureStore()
    feature_version = feature_store.save_features(train_features, "customer_features")
    customer_logger.info(f"Persisted training features to Parquet Feature Store (version {feature_version})")
    
    # 5. FIT MODEL STRICTLY FROM ENGINEERED FEATURES
    recommender = CustomerHybridRecommender(alpha=alpha)
    recommender.fit(train_features, products_df)
    customer_logger.info("Hybrid recommender training complete.")
    
    # 6. EVALUATE MODEL
    # Build actual set of user purchases/clicks in test set to measure metrics
    # Only consider users who have positive purchase or click behavior in test set
    test_interactions = (
        test_df[test_df["interaction_type"].isin(["purchase", "click"])]
        .groupby("user_id")["item_id"]
        .apply(set)
        .to_dict()
    )
    
    # Filter test users to those who were present in training set (to avoid pure cold-start bias on metrics)
    train_users = set(train_features["user_id"].unique())
    test_interactions_filtered = {
        uid: items for uid, items in test_interactions.items()
        if uid in train_users
    }
    
    customer_logger.info(f"Evaluating model on {len(test_interactions_filtered)} active test users...")
    metrics_k5 = evaluate_recommender(recommender, test_interactions_filtered, k=5)
    metrics_k10 = evaluate_recommender(recommender, test_interactions_filtered, k=10)
    
    all_metrics = {**metrics_k5, **metrics_k10}
    customer_logger.info(f"Evaluation Metrics: {all_metrics}")
    
    # 7. MLFLOW LOGGING
    try:
        with mlflow.start_run():
            mlflow.log_param("alpha", alpha)
            mlflow.log_param("train_raw_size", len(train_raw))
            mlflow.log_param("train_feature_size", len(train_features))
            mlflow.log_param("test_size", len(test_df))
            mlflow.log_param("feature_version", feature_version)
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
