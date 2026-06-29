import logging
from langgraph.graph import StateGraph, END

from orchestrator.state import AgentState
from orchestrator.context_loader import load_context_node
from orchestrator.cache import cache_checker_node
from orchestrator.router import orchestrator_router_node
from orchestrator.save_state import save_state_node

# Import Worker Agent Nodes
from agents.branding import branding_node
from agents.logo import prompt_enhancement_node, logo_generation_node
from agents.marketing import marketing_node
from agents.copywriting import copywriting_node
from agents.pricing import pricing_node
from agents.general import general_node

logger = logging.getLogger("talentree.orchestrator.graph")

def create_workflow():
    builder = StateGraph(AgentState)
    
    # Register Nodes
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
    
    # Configure Entry and Edges
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

# Expose compiled LangGraph graph
agent_run_graph = create_workflow()
