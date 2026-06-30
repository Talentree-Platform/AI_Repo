import logging
from repositories.db_connection import get_db_connection

logger = logging.getLogger("talentree.repositories.user")

def get_all_business_profiles() -> list[dict]:
    """Retrieves all business owner profiles from the SQL Server database."""
    logger.info("UserRepository: Loading profiles from database.")
    profiles = []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT Id, BusinessName, BusinessCategory, BusinessDescription, WebsiteLink, InstagramLink, BrandTone, TargetAudience 
                    FROM BusinessOwnerProfile 
                    WHERE IsDeleted = 0
                """)
                rows = cursor.fetchall()
                for row in rows:
                    profiles.append({
                        "id": row[0],
                        "name": row[1] if row[1] else "Unknown",
                        "category": row[2] if row[2] else "Unknown",
                        "description": row[3] if row[3] else "",
                        "website": row[4] if row[4] else "",
                        "instagram": row[5] if row[5] else "",
                        "tone": row[6] if row[6] else "Professional",
                        "target_audience": row[7] if row[7] else "General public"
                    })
    except Exception as e:
        logger.error(f"UserRepository: Failed to fetch profiles from database: {e}")
        
    return profiles

def get_profile_and_catalog(profile_id: int) -> dict:
    """Retrieves business profile and catalog products from the database for a specific profile ID."""
    logger.info(f"UserRepository: Loading profile context for ID: {profile_id} from database.")
    profile = {}
    products = []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Fetch profile
                cursor.execute("""
                    SELECT Id, BusinessName, BusinessCategory, BusinessDescription, WebsiteLink, InstagramLink, BrandTone, TargetAudience 
                    FROM BusinessOwnerProfile 
                    WHERE Id = ? AND IsDeleted = 0
                """, (profile_id,))
                row = cursor.fetchone()
                if row:
                    profile = {
                        "id": row[0],
                        "name": row[1] if row[1] else "Unknown",
                        "category": row[2] if row[2] else "Unknown",
                        "description": row[3] if row[3] else "",
                        "website": row[4] if row[4] else "",
                        "instagram": row[5] if row[5] else "",
                        "tone": row[6] if row[6] else "Professional",
                        "target_audience": row[7] if row[7] else "General public"
                    }
                
                # 2. Fetch products
                cursor.execute("""
                    SELECT Id, Name, Price, Description, Tags 
                    FROM Products 
                    WHERE BusinessOwnerProfileId = ? AND IsDeleted = 0
                """, (profile_id,))
                rows = cursor.fetchall()
                for p_row in rows:
                    products.append({
                        "id": p_row[0],
                        "name": p_row[1],
                        "price": float(p_row[2]) if p_row[2] is not None else 0.0,
                        "description": p_row[3] if p_row[3] else "",
                        "tags": p_row[4] if p_row[4] else ""
                    })
    except Exception as e:
        logger.error(f"UserRepository: Failed to load profile & catalog for ID {profile_id}: {e}")
        
    return {"profile": profile, "products": products}
