import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database_exploration.core.schema_inspector import SchemaInspector
from database_exploration.core.db_connector import get_fallback_json_paths
from database_exploration.core.exploration_logger import exp_logger

def run_list_tables():
    exp_logger.info("Executing list_all_tables.py...")
    inspector = SchemaInspector()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "database_connected": inspector.is_connected(),
        "connection_message": inspector.status_message,
        "tables": []
    }
    
    if inspector.is_connected():
        tables = inspector.get_all_tables()
        report["tables"] = tables
        report["tables_source"] = "SQL Server (MonsterASP/Azure/Local)"
    else:
        exp_logger.warning("Database offline. Listing local JSON fallback tables.")
        json_paths = get_fallback_json_paths()
        mock_tables = []
        for key, path in json_paths.items():
            if os.path.exists(path):
                mock_tables.append(f"fallback_json:{key} (File: {os.path.basename(path)})")
        report["tables"] = mock_tables
        report["tables_source"] = "JSON Fallback Filesystem"
        
    # Write report
    report_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports"
    )
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "all_tables_report.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    exp_logger.info(f"Successfully generated tables report at: {report_path}")
    print("\n--- DATABASE TABLES REPORT ---")
    print(f"Status: {'ONLINE' if report['database_connected'] else 'OFFLINE (Fallback)'}")
    print(f"Source: {report['tables_source']}")
    print(f"Tables Found: {len(report['tables'])}")
    for tbl in report["tables"]:
        print(f" - {tbl}")
    print("------------------------------\n")

if __name__ == "__main__":
    run_list_tables()
