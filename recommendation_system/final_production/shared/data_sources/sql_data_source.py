import pandas as pd
from shared.data_sources.base_data_source import BaseDataSource
from shared.database.connection import engine
from shared.utils.logger import db_logger

class SQLDataSource(BaseDataSource):
    """SQL Server data loader that queries tables directly using SQLAlchemy."""
    
    def __init__(self):
        self.engine = engine
        if self.engine is None:
            db_logger.error("SQLDataSource initialized but SQLAlchemy engine is None!")
            raise ConnectionError("SQL engine not initialized")
            
    def _read_query(self, query: str) -> pd.DataFrame:
        """Helper to run query and return pandas DataFrame."""
        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            db_logger.error(f"SQL database query failed: {e}")
            raise e

    def load_customer_interactions(self) -> pd.DataFrame:
        db_logger.info("Loading B2C customer interactions from SQL database...")
        df = self._read_query("SELECT * FROM interactions WHERE user_type = 'customer'")
        db_logger.info(f"Successfully loaded {len(df)} customer interactions.")
        return df

    def load_owner_interactions(self) -> pd.DataFrame:
        db_logger.info("Loading B2B owner interactions from SQL database...")
        df = self._read_query("SELECT * FROM interactions WHERE user_type = 'owner'")
        db_logger.info(f"Successfully loaded {len(df)} owner interactions.")
        return df

    def load_products(self) -> pd.DataFrame:
        db_logger.info("Loading product catalog from SQL database...")
        df = self._read_query("SELECT * FROM products")
        db_logger.info(f"Successfully loaded {len(df)} products from database.")
        return df

    def load_raw_materials(self) -> pd.DataFrame:
        db_logger.info("Loading raw materials catalog from SQL database...")
        df = self._read_query("SELECT * FROM raw_materials")
        db_logger.info(f"Successfully loaded {len(df)} raw materials from database.")
        return df
