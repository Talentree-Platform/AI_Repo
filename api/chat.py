import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from repositories.user_repository import get_all_business_profiles
from orchestrator.graph import agent_run_graph

logger = logging.getLogger("talentree.api.chat")

router = APIRouter(prefix="/api", tags=["chat"])

class ChatRequest(BaseModel):
    seller_id: str = Field(..., description="Unique session ID")
    brand_name: str = Field(..., description="Seller brand name")
    category: str = Field(..., description="Business category")
    target_audience: str = Field(..., description="Target audience description")
    tone: str = Field(default="Professional", description="Tone specification")
    message: str = Field(..., description="The user query")

class ChatResponse(BaseModel):
    response: str

@router.post("/chat", response_model=ChatResponse)
def chat_route(request: ChatRequest, fastapi_req: Request):
    """API endpoint for invoking the stateful Multi-Agent brand platform."""
    # Resolve business profile ID by brand name using the User Repository
    profiles = get_all_business_profiles()
    profile_id = 1  # Default fallback
    for p in profiles:
        if p["name"].lower() == request.brand_name.lower():
            profile_id = p["id"]
            break

    # Resolve IP location
    client_ip = fastapi_req.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = fastapi_req.client.host if fastapi_req.client else "127.0.0.1"

    state_input = {
        "profile_id": profile_id,
        "current_query": request.message,
        "session_id": request.seller_id,
        "routed_agent": "CONTINUE",
        "logo_prompt": "",
        "logo_base64": "",
        "agent_output": "",
        "user_ip": client_ip
    }
    
    try:
        output_state = agent_run_graph.invoke(state_input)
        return ChatResponse(response=output_state.get("agent_output", "Processed successfully."))
    except Exception as e:
        logger.exception("API Chat route error")
        raise HTTPException(status_code=500, detail=str(e))
