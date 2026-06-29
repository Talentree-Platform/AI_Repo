from typing import TypedDict, List
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    profile_id: int
    session_id: str
    current_query: str
    messages: List[BaseMessage]
    location_context: dict
    brand_profile: dict
    products: List[dict]
    routed_agent: str
    logo_prompt: str
    logo_base64: str
    agent_output: str
    user_ip: str
