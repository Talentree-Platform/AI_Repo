import os
import sys
import json
import argparse
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback, check_exploration_connection
from database_exploration.core.exploration_logger import exp_logger

def run_export_samples():
    parser = argparse.ArgumentParser(description="Export sample rows from tables for inspection")
    parser.add_argument("--table", type=str, required=True, help="Table to sample e.g. interactions, products, raw_materials")
    parser.add_argument("--rows", type=int, default=100, help="Number of rows to sample (default 100)")
    args = parser.parse_args()
    
    db_connected, _ = check_exploration_connection()
    engine = get_exploration_engine()
    
    table_name = args.table.lower().strip()
    df = None
    source_label = ""
    
    if db_connected and engine is not None:
        try:
            # Query top N rows using SQL Server syntax (SELECT TOP N ...)
            query = f"SELECT TOP {args.rows} * FROM {args.table}"
            df = pd.read_sql(query, engine)
            source_label = f"SQL Server Database (TOP {args.rows})"
            exp_logger.info(f"Loaded {len(df)} sample rows from SQL database table '{args.table}'")
        except Exception as e:
            exp_logger.warning(f"Failed to query '{args.table}' sample: {e}. Trying fallback to JSON.")
            df = None
            
    if df is None:
        # Fallback to local files
        fallback_mapping = {
            "interactions": "customer_interactions",
            "owner_interactions": "owner_interactions",
            "products": "products",
            "raw_materials": "raw_materials"
        }
        
        fallback_key = fallback_mapping.get(table_name)
        if fallback_key:
            full_df = load_data_fallback(fallback_key)
            if full_df is not None:
                df = full_df.head(args.rows)
                source_label = f"JSON Fallback File (First {args.rows} rows)"
        else:
            exp_logger.error(f"No fallback JSON available for table '{args.table}' when database is offline.")
            
    if df is not None:
        export_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "exports"
        )
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, f"{table_name}_sample.json")
        
        # Save sample data
        records = df.to_dict(orient="records")
        # Format timestamps if any datetime columns exist
        for row in records:
            for k, v in row.items():
                if isinstance(v, pd.Timestamp):
                    row[k] = v.isoformat()
                elif hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                    
        export_payload = {
            "table_name": table_name,
            "export_timestamp": datetime.now().isoformat(),
            "source": source_label,
            "rows_requested": args.rows,
            "rows_exported": len(records),
            "data": records
        }
        
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, indent=4)
            
        exp_logger.info(f"Successfully exported {len(records)} sample rows to: {export_path}")
        print(f"\nSuccessfully exported {len(records)} sample rows from table '{table_name}'")
        print(f"Source: {source_label}")
        print(f"Export Saved to: {export_path}\n")
    else:
        print(f"\nError: Could not export sample for table '{args.table}'")

if __name__ == "__main__":
    run_export_samples()
