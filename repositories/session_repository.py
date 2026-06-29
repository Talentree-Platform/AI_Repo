import uuid
import logging
from repositories.db_connection import get_db_connection

logger = logging.getLogger("talentree.repositories.session")

def ensure_uuid(session_id: str) -> str:
    """Ensures the session_id is a valid UUID string. Converts non-UUIDs deterministically."""
    try:
        val = uuid.UUID(session_id)
        return str(val)
    except ValueError:
        # Generate a deterministic UUID based on the input string
        deterministic_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, session_id)
        return str(deterministic_uuid)

def get_or_create_session(session_id: str, business_profile_id: int, title: str = "New AI Chat") -> dict:
    """
    Retrieves or inserts an active session record in the AiSessions database table.
    Ensures session_id is formatted as a valid SQL Server uniqueidentifier UUID.
    """
    db_session_id = ensure_uuid(session_id)
    logger.info(f"SessionRepository: Fetching/creating session '{db_session_id}' (original: '{session_id}') for profile {business_profile_id}")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if session exists
                cursor.execute("SELECT Id, BusinessOwnerProfileId, Title FROM AiSessions WHERE Id = ?", (db_session_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": str(row[0]),
                        "business_profile_id": row[1],
                        "title": row[2]
                    }
                
                # Create session if not exists
                cursor.execute("""
                    INSERT INTO AiSessions (Id, BusinessOwnerProfileId, Title, CreatedAt, CreatedBy)
                    VALUES (?, ?, ?, GETDATE(), 'AI System')
                """, (db_session_id, business_profile_id, title))
                conn.commit()
    except Exception as e:
        logger.error(f"SessionRepository: Error in get_or_create_session: {e}")
        
    return {
        "id": db_session_id,
        "business_profile_id": business_profile_id,
        "title": title
    }

def update_session_activity(session_id: str):
    """Updates the last activity timestamp (UpdatedAt) in the AiSessions table."""
    db_session_id = ensure_uuid(session_id)
    logger.info(f"SessionRepository: Updating last activity for session '{db_session_id}'")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE AiSessions 
                    SET UpdatedAt = GETDATE(), UpdatedBy = 'AI System' 
                    WHERE Id = ?
                """, (db_session_id,))
                conn.commit()
    except Exception as e:
        logger.error(f"SessionRepository: Failed to update session activity: {e}")
