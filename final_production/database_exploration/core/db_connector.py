import os
import sys
import pandas as pd
from typing import Optional, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database.connection import engine
from shared.config.settings import settings
from database_exploration.core.exploration_logger import exp_logger

def get_exploration_engine():
    """Returns the SQLAlchemy engine for exploration. Reuses the main connection engine."""
    if engine is None:
        exp_logger.warning("Main SQLAlchemy database engine is not initialized.")
    return engine

def check_exploration_connection() -> Tuple[bool, str]:
    """Checks the database connection and returns connection state."""
    db_engine = get_exploration_engine()
    if db_engine is None:
        return False, "SQLAlchemy engine is None (possibly settings database_url issue)"
    try:
        from sqlalchemy import text
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Successfully connected to SQL Server"
    except Exception as e:
        err_msg = str(e)
        exp_logger.error(f"SQL Server connection failed: {err_msg}")
        return False, err_msg

def get_fallback_json_paths() -> dict:
    """Returns absolute paths to fallback JSON datasets."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
    return {
        "interactions": os.path.join(data_dir, "customer_interactions.json"),
        "owner_interactions": os.path.join(data_dir, "owner_interactions.json"),
        "products": os.path.join(data_dir, "products.json"),
        "raw_materials": os.path.join(data_dir, "raw_materials.json")
    }

def load_data_fallback(key: str) -> Optional[pd.DataFrame]:
    """Loads a fallback JSON dataset as a pandas DataFrame."""
    paths = get_fallback_json_paths()
    if key not in paths:
        exp_logger.error(f"Invalid fallback key '{key}' requested.")
        return None
    path = paths[key]
    if not os.path.exists(path):
        exp_logger.error(f"Fallback JSON file not found at: {path}")
        return None
    try:
        df = pd.read_json(path)
        exp_logger.info(f"Loaded fallback data for '{key}' from JSON ({len(df)} rows)")
        return df
    except Exception as e:
        exp_logger.error(f"Error reading JSON fallback for '{key}': {e}")
        return None
