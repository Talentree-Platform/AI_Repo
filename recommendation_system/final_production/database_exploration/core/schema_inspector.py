import os
import sys
from typing import List, Dict, Any, Optional
from sqlalchemy import inspect

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.db_connector import get_exploration_engine, check_exploration_connection
from database_exploration.core.exploration_logger import exp_logger

class SchemaInspector:
    """Wrapper around SQLAlchemy Inspector for dynamic database schema discovery."""
    
    def __init__(self):
        self.engine = get_exploration_engine()
        self.connected, self.status_message = check_exploration_connection()
        self._inspector = None
        
        if self.connected and self.engine is not None:
            try:
                self._inspector = inspect(self.engine)
            except Exception as e:
                exp_logger.error(f"Failed to initialize SQLAlchemy Inspector: {e}")
                self.connected = False
                self.status_message = f"Inspector initialization error: {e}"
        else:
            exp_logger.warning("SchemaInspector initialized in OFFLINE mode.")

    def is_connected(self) -> bool:
        """Returns True if connected to database, False otherwise."""
        return self.connected

    def get_all_tables(self) -> List[str]:
        """Dynamically retrieves names of all tables in the database."""
        if not self.connected or self._inspector is None:
            exp_logger.warning("Offline: Cannot retrieve tables from SQL database. Suggesting local files.")
            return []
        try:
            tables = self._inspector.get_table_names()
            exp_logger.info(f"Retrieved {len(tables)} tables from database: {tables}")
            return tables
        except Exception as e:
            exp_logger.error(f"Error listing tables: {e}")
            return []

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Retrieves columns, types, nullability, and defaults for a specific table."""
        if not self.connected or self._inspector is None:
            exp_logger.warning(f"Offline: Cannot inspect columns for table '{table_name}'.")
            return []
        try:
            columns = self._inspector.get_columns(table_name)
            parsed_columns = []
            for col in columns:
                parsed_columns.append({
                    "name": col.get("name"),
                    "type": str(col.get("type")),
                    "nullable": col.get("nullable"),
                    "default": str(col.get("default")) if col.get("default") is not None else None
                })
            return parsed_columns
        except Exception as e:
            exp_logger.error(f"Error inspecting columns for '{table_name}': {e}")
            return []

    def get_primary_keys(self, table_name: str) -> List[str]:
        """Retrieves primary key column names for a specific table."""
        if not self.connected or self._inspector is None:
            return []
        try:
            return self._inspector.get_pk_constraint(table_name).get("constrained_columns", [])
        except Exception as e:
            exp_logger.error(f"Error getting primary keys for '{table_name}': {e}")
            return []

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Retrieves foreign key relationships for a specific table."""
        if not self.connected or self._inspector is None:
            return []
        try:
            fkeys = self._inspector.get_foreign_keys(table_name)
            parsed_fkeys = []
            for fk in fkeys:
                parsed_fkeys.append({
                    "constrained_columns": fk.get("constrained_columns"),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": fk.get("referred_columns")
                })
            return parsed_fkeys
        except Exception as e:
            exp_logger.error(f"Error getting foreign keys for '{table_name}': {e}")
            return []

    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Retrieves index structures for a specific table."""
        if not self.connected or self._inspector is None:
            return []
        try:
            indexes = self._inspector.get_indexes(table_name)
            return [
                {
                    "name": idx.get("name"),
                    "column_names": idx.get("column_names"),
                    "unique": idx.get("unique", False)
                } for idx in indexes
            ]
        except Exception as e:
            exp_logger.error(f"Error getting indexes for '{table_name}': {e}")
            return []
            
    def reflect_entire_schema(self) -> Dict[str, Any]:
        """Performs full schema discovery and returns a structured report dict."""
        if not self.connected:
            return {"status": "offline", "connection_error": self.status_message}
            
        tables = self.get_all_tables()
        schema_data = {
            "status": "online",
            "connection_message": self.status_message,
            "tables_count": len(tables),
            "schema": {}
        }
        
        for table in tables:
            schema_data["schema"][table] = {
                "columns": self.get_table_columns(table),
                "primary_keys": self.get_primary_keys(table),
                "foreign_keys": self.get_foreign_keys(table),
                "indexes": self.get_indexes(table)
            }
            
        return schema_data
