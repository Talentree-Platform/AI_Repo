"""
Talentree AI - Database Backup Exporter
Exports all AI-seeded tables to JSON files for backup/restore.
"""
import json
import os
import sys
from datetime import datetime, date
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION
import pyodbc

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def serialize(val):
    """Convert DB types to JSON-serializable."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.hex()
    return val


def export_table_safe(cursor, table_name, where_clause=""):
    """Export table, skipping any columns with unsupported ODBC types."""
    cursor.execute(f"SELECT TOP 0 * FROM {table_name}")
    all_columns = [desc[0] for desc in cursor.description]

    safe_columns = []
    for col in all_columns:
        try:
            cursor.execute(f"SELECT TOP 1 [{col}] FROM {table_name}")
            cursor.fetchone()
            safe_columns.append(col)
        except Exception:
            pass  # skip unsupported type

    col_list = ", ".join(f"[{c}]" for c in safe_columns)
    sql = f"SELECT {col_list} FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += " ORDER BY Id"

    cursor.execute(sql)
    rows = cursor.fetchall()
    return [
        {col: serialize(val) for col, val in zip(safe_columns, row)}
        for row in rows
    ]


def main():
    print("=" * 60)
    print("  Talentree AI - Database Backup Exporter")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn = pyodbc.connect(DB_CONNECTION)
    cursor = conn.cursor()

    tables = [
        ("Transactions",           ""),
        ("LoginHistories",         ""),
        ("ProductReviews",         ""),
        ("SupportTickets",         ""),
        ("TicketMessages",         ""),
        ("OnboardingProgress",     ""),
        ("PayoutRequests",         ""),
        ("BoProductionRequests",   ""),
        ("Products",               "IsDeleted = 0"),
        ("BusinessOwnerProfile",   "IsDeleted = 0"),
        ("AspNetUsers",            ""),
    ]

    backup = {
        "_meta": {
            "exported_at": datetime.now().isoformat(),
            "database": "db52715",
            "server": "db52715.public.databaseasp.net",
            "purpose": "Talentree AI seeded data backup for restore"
        }
    }

    total_rows = 0
    for table, where in tables:
        try:
            data = export_table_safe(cursor, table, where)
            backup[table] = data
            total_rows += len(data)
            print(f"  [OK] {table:<30} {len(data):>6} rows")
        except Exception as e:
            print(f"  [SKIP] {table}: {e}")
            backup[table] = []

    cursor.close()
    conn.close()

    # Save one combined JSON
    combined_path = os.path.join(OUTPUT_DIR, "db_backup_full.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(combined_path) / 1024
    print(f"\n  [OK] Full backup: db_backup_full.json ({size_kb:.1f} KB)")

    # Also save individual table JSON files
    for table_name, _ in tables:
        if table_name not in backup:
            continue
        path = os.path.join(OUTPUT_DIR, f"{table_name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(backup[table_name], f, ensure_ascii=False, indent=2)

    print(f"  Total rows exported: {total_rows}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    print("  [OK] BACKUP COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
