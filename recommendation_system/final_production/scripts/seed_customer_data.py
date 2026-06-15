import os
import json
import sys
from datetime import datetime, timezone

# Add root folder to sys.path so we can import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.connection import engine, SessionLocal, Base
from shared.database.models import Interaction
from shared.utils.logger import db_logger

def seed_customer_data(file_path="data/customer_interactions.json", batch_size=2000):
    db_logger.info("Initializing database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        db_logger.info("Database schema initialized successfully.")
    except Exception as e:
        db_logger.error(f"Error creating database tables: {e}")
        db_logger.warning("Please ensure SQL Server is running and connection credentials in settings are correct.")
        sys.exit(1)

    if not os.path.exists(file_path):
        db_logger.error(f"Seeding file not found: {file_path}. Please run generate_data.py first.")
        sys.exit(1)

    db_logger.info(f"Reading interactions from {file_path}...")
    with open(file_path, "r") as f:
        interactions_data = json.load(f)

    db_logger.info(f"Loaded {len(interactions_data)} customer interactions. Beginning seeding process in batches...")
    
    db = SessionLocal()
    try:
        count = 0
        batch = []
        for idx, item in enumerate(interactions_data):
            # Parse timestamp
            ts = datetime.strptime(item["interaction_timestamp"], "%Y-%m-%d %H:%M:%S")
            
            interaction = Interaction(
                user_type=item["user_type"],
                user_id=item["user_id"],
                item_id=item["item_id"],
                item_type=item["item_type"],
                interaction_type=item["interaction_type"],
                category=item["category"],
                quantity=item["quantity"],
                price=item["price"],
                interaction_timestamp=ts,
                created_at=datetime.now(timezone.utc)
            )
            batch.append(interaction)
            
            if len(batch) >= batch_size:
                db.bulk_save_objects(batch)
                db.commit()
                count += len(batch)
                db_logger.info(f"Seeded {count}/{len(interactions_data)} records...")
                batch = []
                
        # Seed remaining
        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            count += len(batch)
            db_logger.info(f"Seeded total {count}/{len(interactions_data)} customer records successfully.")
            
    except Exception as e:
        db.rollback()
        db_logger.error(f"Error seeding customer data: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_customer_data()
