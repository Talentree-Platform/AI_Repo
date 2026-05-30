# ============================================================
# Talentree AI Service — Configuration
# Reads from environment variables (Docker) or falls back to defaults (local dev)
# ============================================================
import os
from urllib.parse import quote_plus

_server   = os.getenv("DB_SERVER",     "db52715.public.databaseasp.net")
_name     = os.getenv("DB_NAME",       "db52715")
_user     = os.getenv("DB_USER",       "db52715")
_password = os.getenv("DB_PASSWORD",   "Kg4+5#hGcH=8")

# ── Legacy pyodbc connection string (kept for reference / fallback) ────────────
DB_CONNECTION = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"Server={_server};"
    f"Database={_name};"
    f"UID={_user};"
    f"PWD={_password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
    f"MultipleActiveResultSets=True;"
)

# ── SQLAlchemy connection URL (mssql + pyodbc driver) ─────────────────────────
# The pyodbc connection string is percent-encoded and passed as the `odbc_connect` query param.
_odbc_str = quote_plus(DB_CONNECTION)
SQLALCHEMY_URL = f"mssql+pyodbc:///?odbc_connect={_odbc_str}"

