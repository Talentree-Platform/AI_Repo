import os
import pandas as pd
from shared.data_sources.base_data_source import BaseDataSource
from shared.utils.logger import db_logger

class JSONDataSource(BaseDataSource):
    """JSON flat-file data loader serving as the fallback source for offline local runs."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir

    def _load_json(self, filename: str) -> pd.DataFrame:
        """Loads a JSON dataset and returns as a pandas DataFrame."""
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            db_logger.error(f"Fallback JSON file not found at: {path}")
            raise FileNotFoundError(f"Fallback file {filename} not found.")
        try:
            df = pd.read_json(path)
            return df
        except Exception as e:
            db_logger.error(f"Error reading JSON fallback file {filename}: {e}")
            raise e

    def load_customer_interactions(self) -> pd.DataFrame:
        db_logger.info("Loading B2C customer interactions from JSON file fallback...")
        df = self._load_json("customer_interactions.json")
        db_logger.info(f"Successfully loaded {len(df)} customer interactions from JSON.")
        return df

    def load_owner_interactions(self) -> pd.DataFrame:
        db_logger.info("Loading B2B owner interactions from JSON file fallback...")
        # Check if the fallback file is named customer_interactions or owner_interactions
        # In our case we have both: customer_interactions.json and owner_interactions.json!
        df = self._load_json("owner_interactions.json")
        db_logger.info(f"Successfully loaded {len(df)} owner interactions from JSON.")
        return df

    def load_products(self) -> pd.DataFrame:
        db_logger.info("Loading product catalog from JSON file fallback...")
        df = self._load_json("products.json")
        db_logger.info(f"Successfully loaded {len(df)} products from JSON.")
        return df

    def load_raw_materials(self) -> pd.DataFrame:
        db_logger.info("Loading raw materials catalog from JSON file fallback...")
        df = self._load_json("raw_materials.json")
        db_logger.info(f"Successfully loaded {len(df)} raw materials from JSON.")
        return df
