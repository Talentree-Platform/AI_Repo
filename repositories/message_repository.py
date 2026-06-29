import logging
from services.cache_service import redis_mgr
from repositories.db_connection import get_db_connection
from repositories.session_repository import ensure_uuid

logger = logging.getLogger("talentree.repositories.message")

def save_chat_message(session_id: str, role: str, content: str, redis_content: str = None) -> int:
    """
    Saves a message to both Redis cache (for active context) and SQL Server (for permanent storage).
    Returns the newly inserted message Id (integer) from the database.
    """
    db_session_id = ensure_uuid(session_id)
    logger.info(f"MessageRepository: Saving message for session '{db_session_id}' (Role: {role})")
    
    # 1. Save to Redis (for active LLM sliding-window memory)
    try:
        redis_mgr.add_message(session_id, role, redis_content if redis_content else content)
    except Exception as re:
        logger.warning(f"MessageRepository: Failed to save to Redis: {re}")
    
    # 2. Save to SQL Server Database
    message_id = None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SET NOCOUNT ON;
                    INSERT INTO AiMessages (SessionId, Role, Content, CreatedAt)
                    VALUES (?, ?, ?, GETDATE());
                    SELECT SCOPE_IDENTITY();
                """, (db_session_id, role, content))
                row = cursor.fetchone()
                if row and row[0] is not None:
                    message_id = int(row[0])
                conn.commit()
    except Exception as e:
        logger.error(f"MessageRepository: Failed to save message to SQL Server: {e}")
        
    return message_id

def load_chat_history(session_id: str, max_count: int = 10) -> list:
    """
    Loads chat messages from Redis cache (for speed). Fallback to database if Redis misses.
    """
    logger.info(f"MessageRepository: Loading last {max_count} messages for session '{session_id}'")
    
    # Try fetching from Redis first
    try:
        history = redis_mgr.get_messages(session_id, max_count=max_count)
        if history:
             return history
    except Exception as re:
        logger.warning(f"MessageRepository: Redis fetch failed: {re}")
         
    # Fallback to database
    db_session_id = ensure_uuid(session_id)
    history_db = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Select the latest messages, then order them chronologically (ASC)
                cursor.execute("""
                    SELECT Role, Content FROM (
                        SELECT TOP (?) Role, Content, CreatedAt
                        FROM AiMessages
                        WHERE SessionId = ?
                        ORDER BY CreatedAt DESC
                    ) AS Sub
                    ORDER BY CreatedAt ASC
                """, (max_count, db_session_id))
                rows = cursor.fetchall()
                for row in rows:
                    history_db.append({
                        "role": row[0],
                        "content": row[1]
                    })
    except Exception as e:
        logger.error(f"MessageRepository: Database chat history load failed: {e}")
        
    return history_db

def save_image_metadata(message_id: int, storage_url: str, r2_object_key: str, enhanced_prompt: str):
    """Saves generated logo metadata to the AiImages table, linking it to the assistant's Message ID."""
    logger.info(f"MessageRepository: Saving image metadata for MessageId: {message_id}")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO AiImages (MessageId, StorageUrl, R2ObjectKey, EnhancedPrompt, CreatedAt)
                    VALUES (?, ?, ?, ?, GETDATE())
                """, (message_id, storage_url, r2_object_key, enhanced_prompt))
                conn.commit()
    except Exception as e:
        logger.error(f"MessageRepository: Failed to save image metadata: {e}")
