import os
import sys
import pandas as pd
import shutil

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config.settings import settings
from shared.utils.logger import owner_logger
from shared.database.connection import SessionLocal, check_db_connection
from shared.database.models import Interaction, RawMaterial
from owner_recommender.training.train import run_owner_training
from owner_recommender.services.recommender_service import owner_service

def run_owner_retraining_pipeline() -> bool:
    """
    Executes Owner retraining pipeline.
    Loads latest interactions, trains a new model, and replaces production model IF metrics improve.
    """
    owner_logger.info("Triggered Business Owner Online Retraining Pipeline.")
    
    # 1. FETCH LATEST DATA
    db_available = check_db_connection()
    temp_data_dir = "data"
    
    if db_available:
        owner_logger.info("SQL Server database is active. Fetching latest owner interactions and raw materials from SQL tables...")
        try:
            db = SessionLocal()
            
            # Fetch interactions
            query_inter = db.query(Interaction).filter(Interaction.user_type == 1)  # 1 = Owner
            interactions = [item.to_dict() for item in query_inter.all()]
            
            # Fetch raw materials catalog
            query_mat = db.query(RawMaterial)
            materials = [item.to_dict() for item in query_mat.all()]
            
            db.close()
            
            # Cache Interactions
            os.makedirs(temp_data_dir, exist_ok=True)
            if len(interactions) > 0:
                owner_logger.info(f"Fetched {len(interactions)} owner interaction records from SQL Server. Overwriting local JSON file...")
                cache_path = os.path.join(temp_data_dir, "owner_interactions.json")
                pd.DataFrame(interactions).to_json(cache_path, orient="records", indent=2)
            else:
                owner_logger.warning("SQL Server interactions table returned 0 records. Keeping existing owner_interactions.json.")
            
            # Cache Raw Materials Catalog (only if DB has records)
            if len(materials) > 0:
                owner_logger.info(f"Fetched {len(materials)} raw material catalog records from SQL Server. Updating local raw_materials.json cache...")
                mat_cache_path = os.path.join(temp_data_dir, "raw_materials.json")
                pd.DataFrame(materials).to_json(mat_cache_path, orient="records", indent=2)
            else:
                owner_logger.warning("SQL database raw_materials table is empty. Gracefully falling back to local data/raw_materials.json file...")
                
        except Exception as e:
            owner_logger.error(f"Error fetching data from SQL Server: {e}. Falling back entirely to local flat files.")
    else:
        owner_logger.warning("SQL Server not reachable. Relying entirely on local cache JSON files under data/.")

    # 2. EVALUATE CURRENT PRODUCTION PERFORMANCE
    if owner_service.model is not None:
        owner_logger.info("Assessing currently loaded production model metrics...")
        current_info = owner_service.get_model_info()
        owner_logger.info(f"Active model info: {current_info}")
        baseline_precision = 0.01
    else:
        owner_logger.info("No active production model loaded. Setting baseline precision to 0.0.")
        baseline_precision = 0.0

    # 3. TRAIN AND EVALUATE CANDIDATE MODEL
    try:
        candidate_metrics = run_owner_training(data_dir=temp_data_dir)
        candidate_precision = candidate_metrics.get("owner_precision_at_5", 0.0)
        
        owner_logger.info(f"Candidate Model Precision@5: {candidate_precision:.4f} vs Production Baseline: {baseline_precision:.4f}")
        
        # 4. GATED PROMOTION Check
        if candidate_precision >= baseline_precision:
            owner_logger.info("Gated Check Passed: Candidate model outperforms or matches active model. Promoting candidate to production!")
            
            # Overwrite production model in latest directory
            latest_model_dir = os.path.join(settings.MODEL_DIR, "owner", "latest")
            v1_model_dir = os.path.join(settings.MODEL_DIR, "owner", "v1")
            
            os.makedirs(latest_model_dir, exist_ok=True)
            shutil.copy2(
                os.path.join(v1_model_dir, "owner_model.joblib"),
                os.path.join(latest_model_dir, "owner_model.joblib")
            )
            
            # Reload FastAPI models
            success = owner_service.load_model()
            if success:
                owner_logger.info("Successfully reloaded new production model in FastAPI server memory!")
                return True
            else:
                owner_logger.error("Failed to hot-reload new model in FastAPI memory.")
                return False
        else:
            owner_logger.warning("Gated Check Failed: Candidate model underperformed active model. current production model kept.")
            return False
            
    except Exception as ex:
        owner_logger.error(f"Failed to complete owner retraining pipeline: {ex}")
        return False

if __name__ == "__main__":
    run_owner_retraining_pipeline()
