"""Database connection module — powered by SQLAlchemy (mssql+pyodbc)."""
import sys
import os
import pyodbc

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION, SQLALCHEMY_URL

# Module-level singleton engine — connection pool is managed automatically.
_engine: Engine = None


def get_engine() -> Engine:
    """Return the shared SQLAlchemy Engine (creates it once, reuses afterwards)."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            "mssql+pyodbc://",
            creator=lambda: pyodbc.connect(DB_CONNECTION),
            # Keep a small connection pool; adjust pool_size for production load.
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,   # Detect stale connections before use.
            pool_recycle=1800,    # Recycle connections every 30 minutes.
        )
    return _engine


def get_conn():
    """Return a raw DBAPI connection from the SQLAlchemy pool.

    The returned object behaves exactly like a pyodbc connection:
      - conn.cursor()   → DBAPI cursor (supports '?' placeholders)
      - conn.commit()   / conn.rollback()
      - conn.close()    → returns the connection to the pool

    All existing callers (main.py, scheduler.py, services) work without changes.
    """
    return get_engine().raw_connection()

