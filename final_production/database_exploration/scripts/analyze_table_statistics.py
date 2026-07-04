import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback, check_exploration_connection
from database_exploration.core.exploration_logger import exp_logger

def analyze_dataframe(df: pd.DataFrame, table_name: str, source: str) -> dict:
    """Computes descriptive EDA statistics on a pandas DataFrame."""
    total_rows = len(df)
    
    stats = {
        "table_name": table_name,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "total_rows": total_rows,
        "duplicate_rows_count": int(df.duplicated().sum()),
        "duplicate_rows_percentage": float((df.duplicated().sum() / total_rows * 100)) if total_rows > 0 else 0.0,
        "columns_statistics": {}
    }
    
    if total_rows == 0:
        exp_logger.warning(f"Table '{table_name}' is empty. No column statistics computed.")
        return stats

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = float((null_count / total_rows) * 100)
        unique_count = int(df[col].nunique())
        
        col_stats = {
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_values_count": unique_count
        }
        
        # Check numeric statistics
        if pd.api.types.is_numeric_dtype(df[col]):
            col_stats.update({
                "data_type": "numeric",
                "min": float(df[col].min()) if not np.isnan(df[col].min()) else None,
                "max": float(df[col].max()) if not np.isnan(df[col].max()) else None,
                "mean": float(df[col].mean()) if not np.isnan(df[col].mean()) else None,
                "std": float(df[col].std()) if not np.isnan(df[col].std()) else None
            })
        # Check datetime statistics
        elif pd.api.types.is_datetime64_any_dtype(df[col]) or "timestamp" in col.lower() or "date" in col.lower():
            try:
                dt_series = pd.to_datetime(df[col], errors='coerce')
                valid_dt = dt_series.dropna()
                if len(valid_dt) > 0:
                    col_stats.update({
                        "data_type": "datetime",
                        "min_timestamp": valid_dt.min().isoformat(),
                        "max_timestamp": valid_dt.max().isoformat(),
                        "range_days": float((valid_dt.max() - valid_dt.min()).days)
                    })
                else:
                    col_stats["data_type"] = "datetime_invalid"
            except Exception:
                col_stats["data_type"] = "text_or_other"
        else:
            col_stats["data_type"] = "text_or_other"
            # Get a sample of unique values
            sample_vals = df[col].dropna().unique()[:10]
            col_stats["unique_samples"] = [str(x) for x in sample_vals]
            
        stats["columns_statistics"][col] = col_stats
        
    return stats

def run_stats():
    parser = argparse.ArgumentParser(description="Analyze table quality and dataset statistics")
    parser.add_argument("--table", type=str, help="Table to analyze: 'interactions', 'products', 'raw_materials'. Defaults to all.")
    args = parser.parse_args()
    
    db_connected, _ = check_exploration_connection()
    engine = get_exploration_engine()
    
    # We inspect standard target tables
    target_tables = ["interactions", "products", "raw_materials"]
    if args.table:
        target_tables = [args.table]
        
    report_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports"
    )
    os.makedirs(report_dir, exist_ok=True)
    
    for table in target_tables:
        df = None
        source_label = ""
        
        if db_connected and engine is not None:
            try:
                # Query table directly from DB using read_sql
                query = f"SELECT * FROM {table}"
                df = pd.read_sql(query, engine)
                source_label = "SQL Database Server"
                exp_logger.info(f"Loaded '{table}' from SQL Server ({len(df)} rows)")
            except Exception as e:
                exp_logger.warning(f"Failed to query '{table}' from database: {e}. Falling back to JSON.")
                df = None
                
        if df is None:
            # Fallback to local files
            fallback_mapping = {
                "interactions": "customer_interactions", # customer interactions mapping
                "products": "products",
                "raw_materials": "raw_materials"
            }
            fallback_key = fallback_mapping.get(table.lower().strip())
            
            # If requesting generic table, check if owner interactions might be it
            if table.lower().strip() == "owner_interactions":
                fallback_key = "owner_interactions"
                
            if fallback_key:
                df = load_data_fallback(fallback_key)
                source_label = "JSON File Fallback"
            else:
                exp_logger.error(f"No fallback JSON available for non-standard table name '{table}' when DB is offline.")
                continue
                
        if df is not None:
            stats = analyze_dataframe(df, table, source_label)
            report_path = os.path.join(report_dir, f"statistics_{table}.json")
            
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=4)
                
            exp_logger.info(f"Generated table statistics for '{table}' at {report_path}")
            
            # Print output snippet
            print(f"\n================ TABLE STATISTICS: {table} ================")
            print(f"Source: {source_label}")
            print(f"Total Rows: {stats['total_rows']}")
            print(f"Duplicates: {stats['duplicate_rows_count']} rows ({stats['duplicate_rows_percentage']:.2f}%)")
            print("Data Quality:")
            for col, col_info in stats["columns_statistics"].items():
                print(f"  - {col} [{col_info['data_type']}]:")
                print(f"      Nulls: {col_info['null_count']} ({col_info['null_percentage']:.2f}%)")
                print(f"      Unique Values: {col_info['unique_values_count']}")
                if "min_timestamp" in col_info:
                    print(f"      Range: {col_info['min_timestamp']} to {col_info['max_timestamp']} ({col_info['range_days']} days)")
                if "mean" in col_info:
                    print(f"      Mean: {col_info['mean']:.2f} (std={col_info['std']:.2f})")
            print("============================================================\n")

if __name__ == "__main__":
    run_stats()
