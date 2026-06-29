import logging
from langchain_core.prompts import PromptTemplate
from orchestrator.state import AgentState
from services.llm_service import chat_fast
from prompts.router_prompt import router_prompt_template

logger = logging.getLogger("talentree.orchestrator.router")

def orchestrator_router_node(state: AgentState) -> dict:
    """Classifies user queries to route them to specific sub-agents."""
    if state.get("routed_agent") == "CACHED":
        return {"routed_agent": "END"}
        
    query = state.get("current_query", "").lower()
    
    # Fast intercept for logo rendering triggers
    LOGO_TRIGGERS = {"generate", "create logo", "make logo", "logo now", "render logo", "draw logo"}
    if any(word in query for word in LOGO_TRIGGERS):
        if "logo" in query or "image" in query or "design" in query:
            return {"routed_agent": "LOGO_GEN"}
            
    # Fast intercept for explicit pricing verbs/terms
    PRICING_TRIGGERS = {"اسعر", "تسعير", "اسعره", "اسعرها", "تسعيره", "تسعيرها", "هامش ربح", "pricing", "profit margin"}
    if any(word in query for word in PRICING_TRIGGERS):
        return {"routed_agent": "PRICING"}
            
    # LLM Router classification
    try:
        prompt = PromptTemplate.from_template(router_prompt_template)
        chain = prompt | chat_fast
        resp = chain.invoke({"user_input": query})
        routed = resp.content.strip().upper()
    except Exception as e:
        logger.error(f"Router LLM classification failed: {e}")
        routed = "GENERAL"
        
    valid_agents = {"BRANDING", "LOGO_PROMPT", "LOGO_GEN", "MARKETING", "COPYWRITING", "PRICING", "GENERAL"}
    found_agent = "GENERAL"
    for ag in valid_agents:
        if ag in routed:
            found_agent = ag
            break
            
    return {"routed_agent": found_agent}
