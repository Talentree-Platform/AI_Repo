import logging
from langchain_core.messages import HumanMessage, AIMessage
from orchestrator.state import AgentState
from services.geo_service import get_ip_location
from repositories.user_repository import get_profile_and_catalog
from repositories.message_repository import load_chat_history

logger = logging.getLogger("talentree.orchestrator.context_loader")

def load_context_node(state: AgentState) -> dict:
    """Loads geolocation, business profiles, and past message history context."""
    profile_id = state.get("profile_id", 1)
    session_id = state.get("session_id", "guest")
    user_ip = state.get("user_ip", "127.0.0.1")
    
    # 1. Geolocation lookup
    location_ctx = get_ip_location(user_ip)
    
    # 2. Database loading using User Repository
    db_ctx = get_profile_and_catalog(profile_id)
    brand_profile = db_ctx.get("profile", {})
    products = db_ctx.get("products", [])
    
    # 3. Ensure the session exists in the SQL Server database
    from repositories.session_repository import get_or_create_session
    brand_name = brand_profile.get("name", "Brand")
    get_or_create_session(session_id, profile_id, title=f"Chat for {brand_name}")
    
    # 3. Chat history loading using Message Repository
    history = load_chat_history(session_id, max_count=10)
    messages = []
    for m in history:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))
            
    # Append the current user query to the active message context
    current_query = state.get("current_query", "")
    messages.append(HumanMessage(content=current_query))
    
    return {
        "brand_profile": brand_profile,
        "products": products,
        "messages": messages,
        "location_context": location_ctx
    }
