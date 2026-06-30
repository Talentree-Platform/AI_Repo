import os
import logging
import pyodbc
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("talentree.repositories.db_connection")

CONN_STR = os.getenv(
    "SQL_SERVER_CONN_STR",
    "Server=db52715.public.databaseasp.net; Database=db52715; User Id=db52715; Password=Kg4+5#hGcH=8; Encrypt=True; TrustServerCertificate=True; MultipleActiveResultSets=True;"
)

def get_db_connection():
    """
    Creates and returns a connection to the MS SQL Server database.
    Appends the ODBC driver for SQL Server automatically depending on availability.
    """
    conn_str = CONN_STR
    # Collapse all whitespace and newlines to a single space
    conn_str = " ".join(conn_str.split())
    
    # Normalize boolean values to yes/no for ODBC driver compatibility
    conn_str = conn_str.replace("Encrypt=True", "Encrypt=yes").replace("Encrypt=true", "Encrypt=yes")
    conn_str = conn_str.replace("TrustServerCertificate=True", "TrustServerCertificate=yes").replace("TrustServerCertificate=true", "TrustServerCertificate=yes")
    
    # Normalize attribute names to UID and PWD for ODBC driver compatibility
    import re
    conn_str = re.sub(r'(?i)\buser\s+id\b', 'UID', conn_str)
    conn_str = re.sub(r'(?i)\bpassword\b', 'PWD', conn_str)
    
    if "Driver=" not in conn_str:
        # Resolve which driver is installed
        available_drivers = pyodbc.drivers()
        driver = "ODBC Driver 17 for SQL Server"
        
        # Prefer ODBC Driver 17 or 18 if available
        if "ODBC Driver 18 for SQL Server" in available_drivers:
            driver = "ODBC Driver 18 for SQL Server"
        elif "ODBC Driver 17 for SQL Server" in available_drivers:
            driver = "ODBC Driver 17 for SQL Server"
        elif "SQL Server" in available_drivers:
            driver = "SQL Server"
            
        conn_str = f"Driver={{{driver}}};{conn_str}"
        
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        logger.error(f"Failed to connect to database using connection string: {conn_str}. Error: {e}")
        raise e
