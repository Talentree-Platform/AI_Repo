import pandas as pd
from shared.data_sources.base_data_source import BaseDataSource
from shared.data_sources.sql_data_source import SQLDataSource
from shared.data_sources.json_data_source import JSONDataSource
from shared.database.connection import check_db_connection
from shared.utils.logger import db_logger

class FallbackDataSource(BaseDataSource):
    """Smart composite data source that attempts SQL loads and falls back to JSON flat files if offline or empty."""
    
    def __init__(self):
        self.json_src = JSONDataSource()
        self.sql_src = None
        
        try:
            if check_db_connection():
                self.sql_src = SQLDataSource()
                db_logger.info("SQL database connected successfully. Initialized SQL Data Source.")
            else:
                db_logger.warning("Database offline. Falling back to JSON data source.")
        except Exception as e:
            db_logger.warning(f"Error starting SQL Data Source: {e}. Falling back to JSON data source.")

    def load_customer_interactions(self) -> pd.DataFrame:
        if self.sql_src is not None:
            try:
                df = self.sql_src.load_customer_interactions()
                if len(df) > 0:
                    return df
                db_logger.warning("Customer interactions table empty. Falling back to data/customer_interactions.json")
            except Exception as e:
                db_logger.warning(f"Error loading customer interactions from SQL: {e}. Falling back to data/customer_interactions.json")
        return self.json_src.load_customer_interactions()

    def load_owner_interactions(self) -> pd.DataFrame:
        if self.sql_src is not None:
            try:
                df = self.sql_src.load_owner_interactions()
                if len(df) > 0:
                    return df
                db_logger.warning("Owner interactions table empty. Falling back to data/owner_interactions.json")
            except Exception as e:
                db_logger.warning(f"Error loading owner interactions from SQL: {e}. Falling back to data/owner_interactions.json")
        return self.json_src.load_owner_interactions()

    def load_products(self) -> pd.DataFrame:
        if self.sql_src is not None:
            try:
                df = self.sql_src.load_products()
                if len(df) > 0:
                    return df
                db_logger.warning("Products table empty. Falling back to data/products.json")
            except Exception as e:
                db_logger.warning(f"Error loading products from SQL: {e}. Falling back to data/products.json")
        return self.json_src.load_products()

    def load_raw_materials(self) -> pd.DataFrame:
        if self.sql_src is not None:
            try:
                df = self.sql_src.load_raw_materials()
                if len(df) > 0:
                    return df
                db_logger.warning("Raw materials table empty. Falling back to data/raw_materials.json")
            except Exception as e:
                db_logger.warning(f"Error loading raw materials from SQL: {e}. Falling back to data/raw_materials.json")
        return self.json_src.load_raw_materials()

class DataSourceFactory:
    """Factory to get the system default DataSource."""
    
    @staticmethod
    def get_data_source() -> BaseDataSource:
        """Returns the robust fallback data source wrapper."""
        return FallbackDataSource()
