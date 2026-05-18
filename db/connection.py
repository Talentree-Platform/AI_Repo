"""Database connection module."""
import pyodbc
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONNECTION

def get_conn():
    """Return a new pyodbc connection."""
    return pyodbc.connect(DB_CONNECTION)
