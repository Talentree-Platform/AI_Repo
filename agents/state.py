from typing import Dict, Any, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]
    profile_id: int
    brand_profile: Dict[str, Any]
    products: List[Dict[str, Any]]
    current_query: str
    routed_agent: str
    logo_prompt: str
    logo_base64: str
    agent_output: str
    session_id: str
    user_ip: str
    location_context: Dict[str, str]
