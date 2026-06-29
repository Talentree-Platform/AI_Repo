from langchain_core.messages import SystemMessage
from orchestrator.state import AgentState
from services.llm_service import chat_fast
from prompts.general_prompt import get_general_prompt

def general_node(state: AgentState) -> dict:
    brand = state.get("brand_profile", {})
    messages = state.get("messages", [])
    query = state.get("current_query", "")
    location_ctx = state.get("location_context", {"country": "Egypt", "currency": "EGP"})
    country = location_ctx.get("country", "Egypt")
    
    is_ar = any(u'\u0600' <= char <= u'\u06FF' for char in query) if query else False
    if is_ar:
        lang_rule = "You MUST respond entirely in clear, natural Arabic. Do NOT reply in English."
    else:
        lang_rule = "You MUST respond entirely in English. Do NOT reply in Arabic."
        
    system_prompt = get_general_prompt(
        brand_name=brand.get("name", "Unknown"),
        brand_category=brand.get("category", "Unknown"),
        brand_desc=brand.get("description", "Unknown"),
        brand_tone=brand.get("tone", "Professional"),
        target_audience=brand.get("target_audience", "General public"),
        country=country,
        lang_rule=lang_rule
    )
    
    full_messages = [SystemMessage(content=system_prompt)] + messages
    resp = chat_fast.invoke(full_messages)
    return {"agent_output": resp.content.strip()}
