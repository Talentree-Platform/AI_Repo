import pandas as pd
from shared.data_sources.base_data_source import BaseDataSource
from shared.database.connection import engine
from shared.utils.logger import db_logger

class SQLDataSource(BaseDataSource):
    """SQL Server data loader that queries the real backend tables directly using SQLAlchemy."""
    
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
        db_logger.info("Loading B2C customer interactions from SQL database (UserInteractions)...")
        # UserType=0 → 'customer', ItemType=0 → 'product', ActionType ints → string names
        # CASE statements convert stored integer enums back to the string values
        # the ML pipeline uses (e.g. 'purchase', 'view', 'customer', 'product')
        df = self._read_query("""
            SELECT
                Id                   AS interaction_id,
                UserId               AS user_id,
                CASE UserType
                    WHEN 0 THEN 'customer'
                    WHEN 1 THEN 'owner'
                    ELSE        'unknown'
                END                  AS user_type,
                ItemId               AS item_id,
                CASE ItemType
                    WHEN 0 THEN 'product'
                    WHEN 1 THEN 'raw_material'
                    ELSE        'unknown'
                END                  AS item_type,
                CASE ActionType
                    WHEN 0 THEN 'view'
                    WHEN 1 THEN 'click'
                    WHEN 2 THEN 'purchase'
                    WHEN 3 THEN 'reorder'
                    ELSE        'unknown'
                END                  AS interaction_type,
                Category             AS category,
                Quantity             AS quantity,
                Price                AS price,
                InteractionTimestamp AS interaction_timestamp,
                CreatedAt            AS created_at
            FROM UserInteractions
            WHERE UserType = 0
        """)
        db_logger.info(f"Successfully loaded {len(df)} customer interactions from UserInteractions.")
        return df

    def load_owner_interactions(self) -> pd.DataFrame:
        db_logger.info("Loading B2B owner interactions from SQL database (UserInteractions)...")
        df = self._read_query("""
            SELECT
                Id                   AS interaction_id,
                UserId               AS user_id,
                CASE UserType
                    WHEN 0 THEN 'customer'
                    WHEN 1 THEN 'owner'
                    ELSE        'unknown'
                END                  AS user_type,
                ItemId               AS item_id,
                CASE ItemType
                    WHEN 0 THEN 'product'
                    WHEN 1 THEN 'raw_material'
                    ELSE        'unknown'
                END                  AS item_type,
                CASE ActionType
                    WHEN 0 THEN 'view'
                    WHEN 1 THEN 'click'
                    WHEN 2 THEN 'purchase'
                    WHEN 3 THEN 'reorder'
                    ELSE        'unknown'
                END                  AS interaction_type,
                Category             AS category,
                Quantity             AS quantity,
                Price                AS price,
                InteractionTimestamp AS interaction_timestamp,
                CreatedAt            AS created_at
            FROM UserInteractions
            WHERE UserType = 1
        """)
        db_logger.info(f"Successfully loaded {len(df)} owner interactions from UserInteractions.")
        return df

    def load_products(self) -> pd.DataFrame:
        db_logger.info("Loading product catalog from SQL database (Products)...")
        # CategoryId is resolved to the category string using the same
        # mapping as the backend seeding script (1=Fashion, 2=Handmade, 3=Natural)
        df = self._read_query("""
            SELECT
                Id          AS product_id,
                Name        AS product_name,
                Price       AS price,
                Description AS description,
                CASE CategoryId
                    WHEN 1 THEN 'Fashion & Accessories'
                    WHEN 2 THEN 'Handmade & Crafts'
                    WHEN 3 THEN 'Natural & Beauty Products'
                    ELSE        'Unknown'
                END         AS category
            FROM Products
            WHERE IsDeleted = 0
        """)
        db_logger.info(f"Successfully loaded {len(df)} products from Products table.")
        return df

    def load_raw_materials(self) -> pd.DataFrame:
        db_logger.info("Loading raw materials catalog from SQL database (RawMaterials)...")
        df = self._read_query("""
            SELECT
                Id          AS material_id,
                Name        AS material_name,
                Category    AS category,
                Price       AS price,
                Description AS description
            FROM RawMaterials
            WHERE IsDeleted = 0
        """)
        db_logger.info(f"Successfully loaded {len(df)} raw materials from RawMaterials table.")
        return df
