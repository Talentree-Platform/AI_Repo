import os
import sys
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.schema_inspector import SchemaInspector
from database_exploration.core.exploration_logger import exp_logger

# Fallback schema descriptions when DB is offline
JSON_FALLBACK_SCHEMAS = {
    "interactions": {
        "columns": [
            {"name": "interaction_id", "type": "INTEGER", "nullable": False, "default": "Identity"},
            {"name": "user_type", "type": "VARCHAR(20)", "nullable": False, "default": None},
            {"name": "user_id", "type": "INTEGER", "nullable": False, "default": None},
            {"name": "item_id", "type": "INTEGER", "nullable": False, "default": None},
            {"name": "item_type", "type": "VARCHAR(20)", "nullable": False, "default": None},
            {"name": "interaction_type", "type": "VARCHAR(50)", "nullable": False, "default": None},
            {"name": "category", "type": "VARCHAR(100)", "nullable": False, "default": None},
            {"name": "quantity", "type": "INTEGER", "nullable": False, "default": "1"},
            {"name": "price", "type": "FLOAT", "nullable": False, "default": None},
            {"name": "interaction_timestamp", "type": "DATETIME", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        ],
        "primary_keys": ["interaction_id"],
        "foreign_keys": [],
        "indexes": [
            {"name": "ix_interactions_user_id", "column_names": ["user_id"], "unique": False},
            {"name": "ix_interactions_item_id", "column_names": ["item_id"], "unique": False},
            {"name": "ix_interactions_interaction_timestamp", "column_names": ["interaction_timestamp"], "unique": False}
        ]
    },
    "products": {
        "columns": [
            {"name": "product_id", "type": "INTEGER", "nullable": False, "default": None},
            {"name": "product_name", "type": "VARCHAR(150)", "nullable": False, "default": None},
            {"name": "category", "type": "VARCHAR(100)", "nullable": False, "default": None},
            {"name": "price", "type": "FLOAT", "nullable": False, "default": None},
            {"name": "description", "type": "VARCHAR(500)", "nullable": True, "default": None}
        ],
        "primary_keys": ["product_id"],
        "foreign_keys": [],
        "indexes": [
            {"name": "ix_products_product_id", "column_names": ["product_id"], "unique": True}
        ]
    },
    "raw_materials": {
        "columns": [
            {"name": "material_id", "type": "INTEGER", "nullable": False, "default": None},
            {"name": "material_name", "type": "VARCHAR(150)", "nullable": False, "default": None},
            {"name": "category", "type": "VARCHAR(100)", "nullable": False, "default": None},
            {"name": "price", "type": "FLOAT", "nullable": False, "default": None},
            {"name": "description", "type": "VARCHAR(500)", "nullable": True, "default": None}
        ],
        "primary_keys": ["material_id"],
        "foreign_keys": [],
        "indexes": [
            {"name": "ix_raw_materials_material_id", "column_names": ["material_id"], "unique": True}
        ]
    }
}

def inspect_table(table_name: str, inspector: SchemaInspector) -> dict:
    """Collects metadata schemas for a single table."""
    report = {
        "table_name": table_name,
        "timestamp": datetime.now().isoformat(),
        "database_connected": inspector.is_connected()
    }
    
    if inspector.is_connected():
        exp_logger.info(f"Reflecting table '{table_name}' from SQL database...")
        report["columns"] = inspector.get_table_columns(table_name)
        report["primary_keys"] = inspector.get_primary_keys(table_name)
        report["foreign_keys"] = inspector.get_foreign_keys(table_name)
        report["indexes"] = inspector.get_indexes(table_name)
        report["source"] = "SQL Database Server"
    else:
        # Fallback description
        tbl_stripped = table_name.lower().strip()
        if tbl_stripped in JSON_FALLBACK_SCHEMAS:
            exp_logger.info(f"Using standard JSON schema model fallback for '{table_name}'...")
            report.update(JSON_FALLBACK_SCHEMAS[tbl_stripped])
            report["source"] = "JSON Static Schema Fallback"
        else:
            exp_logger.warning(f"Table '{table_name}' not defined in fallback schemas and DB is offline.")
            report.update({
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "indexes": [],
                "source": "Offline (Not Found in Schema Registry)"
            })
            
    return report

def run_inspect():
    parser = argparse.ArgumentParser(description="Inspect table schemas inside SQL Server or Fallbacks")
    parser.add_argument("--table", type=str, help="Table name to inspect. If omitted, all tables are inspected.")
    args = parser.parse_args()
    
    inspector = SchemaInspector()
    
    tables_to_inspect = []
    if args.table:
        tables_to_inspect = [args.table]
    else:
        # Default tables
        if inspector.is_connected():
            tables_to_inspect = inspector.get_all_tables()
            if not tables_to_inspect:
                tables_to_inspect = ["interactions", "products", "raw_materials"]
        else:
            tables_to_inspect = ["interactions", "products", "raw_materials"]
            
    report_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports"
    )
    os.makedirs(report_dir, exist_ok=True)
    
    for table in tables_to_inspect:
        report = inspect_table(table, inspector)
        report_path = os.path.join(report_dir, f"schema_{table}.json")
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
            
        exp_logger.info(f"Wrote schema report for '{table}' to {report_path}")
        
        # Pretty print schema description
        print(f"\n================ TABLE SCHEMA: {table} ================")
        print(f"Source: {report['source']}")
        print(f"Primary Keys: {', '.join(report['primary_keys']) if report['primary_keys'] else 'None'}")
        print("Columns:")
        for col in report["columns"]:
            null_str = "NULL" if col["nullable"] else "NOT NULL"
            def_str = f" DEFAULT {col['default']}" if col['default'] else ""
            print(f"  - {col['name']}: {col['type']} {null_str}{def_str}")
        if report["foreign_keys"]:
            print("Foreign Keys:")
            for fk in report["foreign_keys"]:
                print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        if report["indexes"]:
            print("Indexes:")
            for idx in report["indexes"]:
                uniq_str = "UNIQUE " if idx["unique"] else ""
                print(f"  - {idx['name']} ({uniq_str}{', '.join(idx['column_names'])})")
        print("========================================================\n")

if __name__ == "__main__":
    run_inspect()
