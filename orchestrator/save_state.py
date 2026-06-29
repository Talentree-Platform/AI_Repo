import re
import time
import logging
from orchestrator.state import AgentState
from repositories.message_repository import save_chat_message, save_image_metadata
from repositories.session_repository import update_session_activity
from services.cache_service import redis_mgr

logger = logging.getLogger("talentree.orchestrator.save_state")

def save_state_node(state: AgentState) -> dict:
    """Saves user query and assistant output in permanent and transient memory, caching answers."""
    session_id = state.get("session_id", "guest")
    query = state.get("current_query", "")
    output = state.get("agent_output", "")
    routed_agent = state.get("routed_agent", "GENERAL")
    logo_base64 = state.get("logo_base64", "")
    logo_prompt = state.get("logo_prompt", "")
    
    if routed_agent == "CACHED":
        return {}
        
    # Clean output from giant base64 HTML image tags for chat history memory to prevent context length overflow
    clean_output = re.sub(r"<img[^>]+src=['\"]data:image/[^'\"]+['\"][^>]*>", "[Generated Logo Image]", output)
    
    # Check if a logo was generated and we need to save the image metadata
    db_output = output
    storage_url = None
    r2_object_key = None
    
    if logo_base64:
        timestamp = int(time.time())
        # Formulate object key and mock public R2 serving URL
        r2_object_key = f"logos/{session_id}_{timestamp}.png"
        storage_url = f"https://pub-mock-r2.dev/{r2_object_key}"
        
        # Replace the raw base64 image tag in the database message content with the public URL
        img_html = f"<img src='{storage_url}' style='width:250px; border-radius:8px; border:1px solid #ddd; margin:10px 0;' />"
        db_output = re.sub(r"<img[^>]+src=['\"]data:image/[^'\"]+['\"][^>]*>", img_html, output)
        logger.info(f"save_state_node: Generated image public URL: {storage_url}")
        
    # Save user message to database and Redis
    save_chat_message(session_id, "user", query)
    
    # Save assistant message: pass db_output for DB storage and clean_output for Redis
    assistant_msg_id = save_chat_message(session_id, "assistant", db_output, redis_content=clean_output)
    
    # If we generated a logo and successfully saved the message, save the image details
    if logo_base64 and assistant_msg_id:
        logger.info(f"save_state_node: Saving image metadata referencing MessageId {assistant_msg_id}")
        save_image_metadata(
            message_id=assistant_msg_id,
            storage_url=storage_url,
            r2_object_key=r2_object_key,
            enhanced_prompt=logo_prompt if logo_prompt else "Brand Logo Design"
        )
        
    # Update active session activity
    update_session_activity(session_id)
    
    # Write to semantic/exact cache
    redis_mgr.set_cache(query, clean_output)
    redis_mgr.add_semantic_cache(query, clean_output)
    
    return {}
