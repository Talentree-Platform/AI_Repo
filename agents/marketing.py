from langchain_core.messages import SystemMessage
from orchestrator.state import AgentState
from services.llm_service import chat_creative
from prompts.marketing_prompt import get_marketing_prompt

def marketing_node(state: AgentState) -> dict:
    brand = state.get("brand_profile", {})
    products = state.get("products", [])
    messages = state.get("messages", [])
    query = state.get("current_query", "")
    location_ctx = state.get("location_context", {"country": "Egypt", "currency": "EGP"})
    country = location_ctx.get("country", "Egypt")
    
    prod_lines = []
    for p in products[:5]:
        prod_lines.append(f"- {p['name']} ({p['price']} LE) - {p.get('description', '')}")
    catalog_list = "\n".join(prod_lines) if prod_lines else "No registered products yet."
    
    is_ar = any(u'\u0600' <= char <= u'\u06FF' for char in query) if query else False
    if is_ar:
        lang_rule = "You MUST write the entire 30-day marketing plan in clear, professional Arabic. Do NOT reply in English."
    else:
        lang_rule = "You MUST write the entire marketing plan in English. Do NOT reply in Arabic."

    system_prompt = get_marketing_prompt(
        brand_name=brand.get("name", "Unknown"),
        brand_category=brand.get("category", "Unknown"),
        brand_desc=brand.get("description", "Unknown"),
        brand_tone=brand.get("tone", "Professional"),
        target_audience=brand.get("target_audience", "General public"),
        catalog_list=catalog_list,
        country=country,
        lang_rule=lang_rule
    )

    full_messages = [SystemMessage(content=system_prompt)] + messages
    resp = chat_creative.invoke(full_messages)
    return {"agent_output": resp.content.strip()}
