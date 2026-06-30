import logging
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.llms import chat_fast, chat_creative
from config import fetch_profile_and_catalog
from cache import redis_mgr
from tools.geolocation import get_ip_location

# Import sub-agent nodes
from agents.branding import branding_node
from agents.logo import prompt_enhancement_node, logo_generation_node
from agents.marketing import marketing_node
from agents.copywriting import copywriting_node
from agents.pricing import pricing_node
from agents.general import general_node

logger = logging.getLogger("talentree.agents.orchestrator")

# Router Orchestrator prompt mapping
router_prompt_template = """You are the Router Orchestrator for an AI Multi-Agent Brand Platform.
Read the user request and classify it into EXACTLY ONE of the following agent targets:
- BRANDING (Queries about brand tone, positioning, colors, visual identity ideas)
- LOGO_PROMPT (Instructions or descriptions to enhance, build, or write a logo design prompt)
- LOGO_GEN (Explicit commands to generate, draw, render, or create a logo image)
- MARKETING (Requests for marketing ideas, holiday roadmaps, launch checklists, 30-day plans)
- COPYWRITING (Requests for social media captions, product descriptions, ad copies, CTAs)
- PRICING (Questions about pricing strategies, competitor prices, profit margins, cost calculations, or how to sell and price a product in a market)
- GENERAL (Greetings, basic questions, general advice)

Output ONLY the category word. No other text.

User Request: {user_input}"""

def load_context_node(state: AgentState) -> dict:
    profile_id = state.get("profile_id", 1)
    session_id = state.get("session_id", "guest")
    user_ip = state.get("user_ip", "127.0.0.1")
    
    # Dynamic Geolocation Lookup
    location_ctx = get_ip_location(user_ip)
    
    # Fetch mock data
    db_ctx = fetch_profile_and_catalog(profile_id)
    brand_profile = db_ctx.get("profile", {})
    products = db_ctx.get("products", [])
    
    # Load past active history from Redis
    redis_history = redis_mgr.get_messages(session_id, max_count=10)
    messages = []
    for m in redis_history:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))
    
    current_query = state.get("current_query", "")
    messages.append(HumanMessage(content=current_query))
    
    return {
        "brand_profile": brand_profile,
        "products": products,
        "messages": messages,
        "location_context": location_ctx
    }

def cache_checker_node(state: AgentState) -> dict:
    # Bypass global chat caching to ensure live, stateful context works
    return {"routed_agent": "CONTINUE"}

def orchestrator_router_node(state: AgentState) -> dict:
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
            
    # LLM Router
    prompt = PromptTemplate.from_template(router_prompt_template)
    chain = prompt | chat_fast
    resp = chain.invoke({"user_input": query})
    routed = resp.content.strip().upper()
    
    valid_agents = {"BRANDING", "LOGO_PROMPT", "LOGO_GEN", "MARKETING", "COPYWRITING", "PRICING", "GENERAL"}
    found_agent = "GENERAL"
    for ag in valid_agents:
        if ag in routed:
            found_agent = ag
            break
            
    return {"routed_agent": found_agent}

def save_state_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "guest")
    query = state.get("current_query", "")
    output = state.get("agent_output", "")
    routed_agent = state.get("routed_agent", "GENERAL")
    
    if routed_agent == "CACHED":
        return {}
        
    import re
    # Clean output from giant base64 image tags for chat history memory to prevent context length overflow
    clean_output = re.sub(r"<img[^>]+src=['\"]data:image/[^'\"]+['\"][^>]*>", "[Generated Logo Image]", output)
        
    # Save memory only in Redis/memory cache. Database saves removed.
    redis_mgr.add_message(session_id, "user", query)
    redis_mgr.add_message(session_id, "assistant", clean_output)
    
    # Cache result
    redis_mgr.set_cache(query, clean_output)
    redis_mgr.add_semantic_cache(query, clean_output)
    
    return {}

# 5. Build StateGraph Flow
def create_workflow():
    builder = StateGraph(AgentState)
    
    builder.add_node("load_context", load_context_node)
    builder.add_node("cache_checker", cache_checker_node)
    builder.add_node("orchestrator", orchestrator_router_node)
    builder.add_node("branding", branding_node)
    builder.add_node("prompt_enhancement", prompt_enhancement_node)
    builder.add_node("logo_generation", logo_generation_node)
    builder.add_node("marketing", marketing_node)
    builder.add_node("copywriting", copywriting_node)
    builder.add_node("pricing", pricing_node)
    builder.add_node("general", general_node)
    builder.add_node("save_state", save_state_node)
    
    builder.set_entry_point("load_context")
    builder.add_edge("load_context", "cache_checker")
    
    builder.add_conditional_edges(
        "cache_checker",
        lambda state: state.get("routed_agent", "CONTINUE"),
        {
            "CACHED": "save_state",
            "CONTINUE": "orchestrator"
        }
    )
    
    builder.add_conditional_edges(
        "orchestrator",
        lambda state: state.get("routed_agent", "GENERAL"),
        {
            "BRANDING": "branding",
            "LOGO_PROMPT": "prompt_enhancement",
            "LOGO_GEN": "logo_generation",
            "MARKETING": "marketing",
            "COPYWRITING": "copywriting",
            "PRICING": "pricing",
            "GENERAL": "general",
            "END": "save_state"
        }
    )
    
    builder.add_edge("branding", "save_state")
    builder.add_edge("prompt_enhancement", "save_state")
    builder.add_edge("logo_generation", "save_state")
    builder.add_edge("marketing", "save_state")
    builder.add_edge("copywriting", "save_state")
    builder.add_edge("pricing", "save_state")
    builder.add_edge("general", "save_state")
    builder.add_edge("save_state", END)
    
    return builder.compile()

# Compile the graph
agent_run_graph = create_workflow()
