import os
os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "0"
os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "2"
import sys
import pandas as pd
import numpy as np
import mlflow
import joblib

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config.settings import settings
from shared.utils.logger import owner_logger
from owner_recommender.model.recommender import OwnerRawMaterialRecommender
from owner_recommender.evaluation.metrics import evaluate_owner_forecast, evaluate_owner_recommender
from shared.data_sources import DataSourceFactory
from shared.feature_engineering.owner.owner_feature_builder import OwnerFeatureBuilder
from shared.feature_validation import FeatureValidator
from shared.feature_store import ParquetFeatureStore

def run_owner_training(data_dir: str = "data"):
    owner_logger.info("Starting Business Owner Raw Material Recommender Offline Training...")
    
    # Configure MLflow with safe local fallback to prevent network timeouts
    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("owner_recommender_experiment")
    except Exception as ex:
        owner_logger.warning(f"Could not connect to MLflow server at {settings.MLFLOW_TRACKING_URI}. Falling back to local file logging. Error: {ex}")
        mlflow.set_tracking_uri("./mlruns")
        mlflow.set_experiment("owner_recommender_experiment")
    
    # 1. LOAD DATA VIA DATA SOURCE ABSTRACTION LAYER (SQL + Fallback to JSON)
    data_source = DataSourceFactory.get_data_source()
    materials_df = data_source.load_raw_materials()
    interactions_df = data_source.load_owner_interactions()
    
    owner_logger.info(f"Loaded {len(materials_df)} raw materials and {len(interactions_df)} owner procurement records.")
    
    # Sort interactions temporally
    interactions_df["interaction_timestamp"] = pd.to_datetime(interactions_df["interaction_timestamp"])
    interactions_df = interactions_df.sort_values(by="interaction_timestamp")
    
    # Temporal Split: 85% Train, 15% Test
    split_idx = int(len(interactions_df) * 0.85)
    train_raw = interactions_df.iloc[:split_idx].copy()
    test_df = interactions_df.iloc[split_idx:].copy()
    
    owner_logger.info(f"Train split size: {len(train_raw)} raw rows, Test split size: {len(test_df)}")
    
    # 2. FEATURE ENGINEERING PIPELINE
    feature_builder = OwnerFeatureBuilder()
    train_features = feature_builder.build_features(train_raw, materials_df)
    
    # 3. FEATURE VALIDATION LAYER
    FeatureValidator.validate_owner_features(train_features)
    
    # 4. Parquet VERSIONED FEATURE STORE PERSISTENCE
    feature_store = ParquetFeatureStore()
    feature_version = feature_store.save_features(train_features, "owner_features")
    owner_logger.info(f"Persisted training features to Parquet Feature Store (version {feature_version})")
    
    # 5. FIT MODEL STRICTLY FROM ENGINEERED FEATURES
    recommender = OwnerRawMaterialRecommender()
    recommender.fit(train_features, materials_df)
    owner_logger.info("Raw material recommender and forecaster training complete.")
    
    # 6. EVALUATE FORECASTING ACCURACY
    # Build actual test weekly demand targets for forecasting validation
    test_df["week"] = test_df["interaction_timestamp"].dt.to_period("W").dt.start_time
    test_weekly = (
        test_df[test_df["interaction_type"].isin(["purchase", "reorder"])]
        .groupby(["user_id", "item_id", "week"])["quantity"]
        .sum()
        .reset_index()
    )
    
    actual_quantities = []
    predicted_quantities = []
    
    # Evaluate a sample of owner-item records present in training histories
    train_owner_items = set(zip(train_features["user_id"], train_features["item_id"]))
    
    sample_size = min(300, len(test_weekly))
    if sample_size > 0:
        sampled_test = test_weekly.sample(n=sample_size, random_state=42)
        for _, row in sampled_test.iterrows():
            oid = int(row["user_id"])
            iid = int(row["item_id"])
            if (oid, iid) in train_owner_items:
                # Forecasting uses raw temporal train_raw for historical time-series lags
                pred = recommender.forecaster.predict_next_week_demand(oid, iid, train_raw)
                actual_quantities.append(float(row["quantity"]))
                predicted_quantities.append(pred)
                
    forecasting_metrics = evaluate_owner_forecast(actual_quantities, predicted_quantities)
    owner_logger.info(f"Forecasting metrics: {forecasting_metrics}")
    
    # 7. EVALUATE RECOMMENDATION RELEVANCE
    test_owner_procurements = (
        test_df[test_df["interaction_type"].isin(["purchase", "reorder"])]
        .groupby("user_id")["item_id"]
        .apply(set)
        .to_dict()
    )
    
    train_owners = set(train_features["user_id"].unique())
    test_proc_filtered = {
        oid: items for oid, items in test_owner_procurements.items()
        if oid in train_owners
    }
    
    rec_metrics = evaluate_owner_recommender(recommender, test_proc_filtered, k=5)
    owner_logger.info(f"Procurement recommendation metrics: {rec_metrics}")
    
    all_metrics = {**forecasting_metrics, **rec_metrics}
    
    # 8. LOG TO MLFLOW
    try:
        with mlflow.start_run():
            mlflow.log_param("train_raw_size", len(train_raw))
            mlflow.log_param("train_feature_size", len(train_features))
            mlflow.log_param("test_size", len(test_df))
            mlflow.log_param("feature_version", feature_version)
            mlflow.log_param("model_type", "Owner_Raw_Material_Cyclic_Procurement_Forecaster")
            
            # Log Metrics
            for m_name, m_val in all_metrics.items():
                mlflow.log_metric(m_name, m_val)
                
            mlflow.log_text(str(all_metrics), "owner_evaluation_metrics.json")
            owner_logger.info("Logged parameters and metrics to MLflow tracking server.")
    except Exception as ex:
        owner_logger.warning(f"Failed to connect to MLflow tracking server: {ex}. Storing model locally anyway.")
        
    # 6. PERSIST MODELS
    version_dir = os.path.join(settings.MODEL_DIR, "owner", "v1")
    latest_dir = os.path.join(settings.MODEL_DIR, "owner", "latest")
    
    os.makedirs(version_dir, exist_ok=True)
    os.makedirs(latest_dir, exist_ok=True)
    
    version_path = os.path.join(version_dir, "owner_model.joblib")
    latest_path = os.path.join(latest_dir, "owner_model.joblib")
    
    recommender.save(version_path)
    recommender.save(latest_path)
    
    owner_logger.info(f"Saved versioned owner model to {version_path}")
    owner_logger.info(f"Saved latest production owner model to {latest_path}")
    
    return all_metrics

if __name__ == "__main__":
    run_owner_training()
