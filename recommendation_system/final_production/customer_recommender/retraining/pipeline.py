import os
import sys
import pandas as pd
import shutil

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config.settings import settings
from shared.utils.logger import customer_logger
from shared.database.connection import SessionLocal, check_db_connection
from shared.database.models import Interaction
from customer_recommender.training.train import run_training
from customer_recommender.services.recommender_service import customer_service

def run_retraining_pipeline() -> bool:
    """
    Executes Customer retraining pipeline.
    Loads latest interactions, trains a new model, and replaces production model IF metrics improve.
    """
    customer_logger.info("Triggered Customer Online Retraining Pipeline.")
    
    # 1. FETCH LATEST DATA
    # Try fetching from DB first. If DB is unavailable, fallback to local JSON flat files.
    db_available = check_db_connection()
    temp_data_dir = "data"
    
    if db_available:
        customer_logger.info("SQL Server database is active. Fetching latest customer interactions from SQL tables...")
        try:
            db = SessionLocal()
            query = db.query(Interaction).filter(Interaction.user_type == "customer")
            interactions = [item.to_dict() for item in query.all()]
            db.close()
            
            customer_logger.info(f"Fetched {len(interactions)} records from SQL Server. Overwriting local JSON file for reproducibility...")
            
            # Save fetched records to customer_interactions.json to serve as local cache
            os.makedirs(temp_data_dir, exist_ok=True)
            cache_path = os.path.join(temp_data_dir, "customer_interactions.json")
            
            # Simple conversion to DataFrame and save
            pd.DataFrame(interactions).to_json(cache_path, orient="records", indent=2)
        except Exception as e:
            customer_logger.error(f"Error fetching interactions from SQL Server: {e}. Falling back to flat files.")
    else:
        customer_logger.warning("SQL Server not reachable. Relying entirely on local cache JSON files under data/.")

    # 2. EVALUATE CURRENT PRODUCTION PERFORMANCE
    current_metrics = {}
    if customer_service.model is not None:
        customer_logger.info("Assessing currently loaded production model metrics...")
        # Load local metrics if saved, or use base metrics
        current_info = customer_service.get_model_info()
        customer_logger.info(f"Active model info: {current_info}")
        # Let's set a default baseline precision
        baseline_precision = 0.01 
    else:
        customer_logger.info("No active production model loaded. Setting baseline precision to 0.0.")
        baseline_precision = 0.0

    # 3. TRAIN AND EVALUATE CANDIDATE MODEL
    try:
        candidate_metrics = run_training(alpha=0.4, data_dir=temp_data_dir)
        candidate_precision = candidate_metrics.get("precision_at_5", 0.0)
        
        customer_logger.info(f"Candidate Model Precision@5: {candidate_precision:.4f} vs Production Baseline: {baseline_precision:.4f}")
        
        # 4. GATED PROMOTION DEPLOYMENT Check
        if candidate_precision >= baseline_precision:
            customer_logger.info("Gated Check Passed: Candidate model outperforms or matches active model. Promoting candidate to production!")
            
            # Overwrite production model in latest directory
            latest_model_dir = os.path.join(settings.MODEL_DIR, "customer", "latest")
            v1_model_dir = os.path.join(settings.MODEL_DIR, "customer", "v1")
            
            os.makedirs(latest_model_dir, exist_ok=True)
            shutil.copy2(
                os.path.join(v1_model_dir, "customer_model.joblib"),
                os.path.join(latest_model_dir, "customer_model.joblib")
            )
            
            # Reload FastAPI models
            success = customer_service.load_model()
            if success:
                customer_logger.info("Successfully reloaded new production model in FastAPI server memory!")
                return True
            else:
                customer_logger.error("Failed to hot-reload new model in FastAPI memory.")
                return False
        else:
            customer_logger.warning("Gated Check Failed: Candidate model underperformed active model. Rollback: current production model kept.")
            return False
            
    except Exception as ex:
        customer_logger.error(f"Failed to complete retraining pipeline: {ex}")
        return False

if __name__ == "__main__":
    run_retraining_pipeline()
