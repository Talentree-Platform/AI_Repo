from orchestrator.state import AgentState

def cache_checker_node(state: AgentState) -> dict:
    """Checks cache. Currently configured to bypass global chat caching to ensure stateful context works."""
    return {"routed_agent": "CONTINUE"}
