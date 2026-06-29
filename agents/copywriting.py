from langchain_core.messages import SystemMessage
from orchestrator.state import AgentState
from services.llm_service import chat_creative
from prompts.copywriting_prompt import get_copywriting_prompt

def copywriting_node(state: AgentState) -> dict:
    brand = state.get("brand_profile", {})
    messages = state.get("messages", [])
    query = state.get("current_query", "")
    location_ctx = state.get("location_context", {"country": "Egypt", "currency": "EGP"})
    country = location_ctx.get("country", "Egypt")
    
    is_ar = any(u'\u0600' <= char <= u'\u06FF' for char in query) if query else False
    if is_ar:
        lang_rule = "You MUST write all captions in engaging, natural Arabic suitable for local social media users of the target country (بالعامية الفصيحة المبسطة الجذابة والمناسبة للبلد المستهدف). Do NOT reply in English."
    else:
        lang_rule = "You MUST write all captions in English. Do NOT reply in Arabic."

    system_prompt = get_copywriting_prompt(
        brand_name=brand.get("name", "Unknown"),
        brand_category=brand.get("category", "Unknown"),
        brand_desc=brand.get("description", "Unknown"),
        brand_tone=brand.get("tone", "Professional"),
        target_audience=brand.get("target_audience", "General public"),
        country=country,
        lang_rule=lang_rule
    )

    full_messages = [SystemMessage(content=system_prompt)] + messages
    resp = chat_creative.invoke(full_messages)
    return {"agent_output": resp.content.strip()}
