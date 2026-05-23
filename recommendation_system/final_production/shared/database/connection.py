from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from shared.config.settings import settings
from shared.utils.logger import db_logger

# Create engine with custom pool configurations
# Using pymssql as driver
try:
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    db_logger.error(f"Error creating SQLAlchemy engine: {e}")
    # Fallback/Mock placeholder for local setups without active db connection on boot
    engine = None
    SessionLocal = None

Base = declarative_base()

def get_db():
    """FastAPI DB dependency injector."""
    if SessionLocal is None:
        db_logger.warning("Database SessionLocal is not initialized. Database endpoints will fail.")
        raise ConnectionError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> bool:
    """Verifies connection status for API health check endpoint."""
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        db_logger.error(f"Database health check failed: {e}")
        return False
