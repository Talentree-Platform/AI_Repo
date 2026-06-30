import io
import os
import logging
import base64
import gradio as gr
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import repositories and services
from repositories.user_repository import get_all_business_profiles, get_profile_and_catalog
from services.geo_service import get_ip_location, detect_location_from_text
from services.image_service import generate_logo_image
from services.cache_service import redis_mgr

# Import orchestrator and agent nodes
from orchestrator.graph import agent_run_graph
from agents.logo import prompt_enhancement_node, logo_generation_node
from agents.pricing import pricing_node

# Import API routes
from api.chat import router as chat_router

logger = logging.getLogger("talentree.main")

# ==========================================
# FASTAPI APP & MIDDLEWARE CONFIG
# ==========================================
fastapi_app = FastAPI(
    title="TalentTree AI Orchestrated API",
    description="Stateful Multi-Agent AI system using LangGraph + Redis",
    version="2.0.0",
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(chat_router)

@fastapi_app.get("/api")
def root():
    return {"status": "ok", "system": "TalentTree Multi-Agent Platform Running"}


# ==========================================
# GRADIO CALLBACK HANDLERS
# ==========================================

# Load business choices
profiles_list = get_all_business_profiles()
profile_choices = [f"{p['id']}: {p['name']} ({p['category']})" for p in profiles_list] or ["1: Tech Galaxy (Electronics)"]

def handle_profile_select(selected_profile_str):
    if not selected_profile_str:
        return 1, "", "", "", "", ""
    try:
        profile_id = int(selected_profile_str.split(":")[0])
        ctx = get_profile_and_catalog(profile_id)
        profile = ctx.get("profile", {})
        
        products = ctx.get("products", [])
        prod_str = "\n".join([f"- {p['name']} ({p['price']} LE) - {p.get('tags', '')}" for p in products])
        
        return (
            profile_id,
            profile.get("name", ""),
            profile.get("category", ""),
            profile.get("description", ""),
            profile.get("website", ""),
            prod_str
        )
    except Exception as e:
        logger.error(f"Error resolving profile selection: {e}")
        return 1, "Error", "", "", "", ""

def run_chat_interface(message, history, profile_id, session_id, request: gr.Request = None):
    if not message:
        return "", history
        
    client_ip = "127.0.0.1"
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

    # Get location context for the session
    location_ctx = get_ip_location(client_ip)

    state_input = {
        "profile_id": int(profile_id),
        "current_query": message,
        "session_id": session_id.strip() or "guest",
        "routed_agent": "CONTINUE",
        "logo_prompt": "",
        "logo_base64": "",
        "agent_output": "",
        "user_ip": client_ip,
        "location_context": location_ctx
    }
    try:
        res = agent_run_graph.invoke(state_input)
        response = res.get("agent_output", "No response generated.")
    except Exception as e:
        response = f"Error executing Multi-Agent: {str(e)}"
        
    new_history = list(history or []) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response}
    ]
    return "", new_history

def run_logo_enhance(logo_idea, profile_id):
    state_input = {
        "profile_id": int(profile_id),
        "current_query": logo_idea,
        "session_id": "logo_temp",
        "routed_agent": "LOGO_PROMPT",
        "logo_prompt": "",
        "logo_base64": "",
        "agent_output": ""
    }
    try:
        res = prompt_enhancement_node(state_input)
        return res.get("logo_prompt", ""), res.get("agent_output", "")
    except Exception as e:
        return "", f"Error: {e}"

def run_logo_generate(enhanced_prompt, profile_id):
    state_input = {
        "profile_id": int(profile_id),
        "current_query": "generate logo",
        "session_id": "logo_temp",
        "routed_agent": "LOGO_GEN",
        "logo_prompt": enhanced_prompt,
        "logo_base64": "",
        "agent_output": ""
    }
    try:
        res = logo_generation_node(state_input)
        base64_data = res.get("logo_base64", "")
        img_path = None
        if base64_data:
            img_bytes = base64.b64decode(base64_data)
            img_path = "temp_generated_logo.png"
            with open(img_path, "wb") as f:
                f.write(img_bytes)
        return img_path, res.get("agent_output", "Failed to render logo.")
    except Exception as e:
        return None, f"Error generating image: {e}"

def run_pricing_intelligence(product_name, raw_cost, mfg_cost, is_luxury, profile_id, request: gr.Request = None):
    client_ip = "127.0.0.1"
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

    location_ctx = get_ip_location(client_ip)
    detected_ctx = detect_location_from_text(product_name)
    if detected_ctx:
        location_ctx = detected_ctx

    currency = location_ctx.get("currency", "EGP")
    total_cost = float(raw_cost or 0) + float(mfg_cost or 0)
    audience = "Luxury / Premium" if is_luxury else "Mass market"
    query = f"Product name: {product_name}. Raw material cost: {raw_cost} {currency}. Manufacturing: {mfg_cost} {currency}. Target audience: {audience}. Total Cost: {total_cost} {currency}."
    
    state_input = {
        "profile_id": int(profile_id),
        "current_query": query,
        "session_id": "pricing_temp",
        "routed_agent": "PRICING",
        "logo_prompt": "",
        "logo_base64": "",
        "agent_output": "",
        "user_ip": client_ip,
        "location_context": location_ctx
    }
    try:
        res = pricing_node(state_input)
        return res.get("agent_output", "No recommendation generated.")
    except Exception as e:
        return f"Error analyzing pricing: {e}"


# ==========================================
# GRADIO BLOCKS LAYOUT & LIFECYCLE
# ==========================================

def load_initial_params(request: gr.Request):
    """
    Parses optional query parameters from the URL (profile_id and session_id).
    Loads last 10 chat history messages from SQL Server database to resume chat.
    """
    profile_id = 1
    session_id = "guest"
    history = []
    
    if request:
        params = request.query_params
        try:
            profile_id = int(params.get("profile_id", 1))
        except (ValueError, TypeError):
            profile_id = 1
        session_id = params.get("session_id", "guest")
        
    # Query database message history
    from repositories.message_repository import load_chat_history
    try:
        db_history = load_chat_history(session_id, max_count=10)
        for m in db_history:
            history.append({
                "role": m["role"],
                "content": m["content"]
            })
    except Exception as e:
        logger.error(f"Error loading chat history on startup: {e}")
        
    logger.info(f"Loaded session '{session_id}' for Profile ID {profile_id} with {len(history)} past messages.")
    return profile_id, session_id, history

with gr.Blocks(title="TalentTree AI Assistant", theme=gr.themes.Soft()) as gradio_ui:
    # Hidden states to hold the profile ID and session ID from URL query parameters
    profile_id_state = gr.State(value=1)
    session_id_state = gr.State(value="guest")
    
    gr.HTML("<div style='text-align: center; margin: 10px 0;'><h2 style='color:#1E3A8A; font-family: Outfit, sans-serif;'>🌳 TalentTree AI Assistant</h2></div>")
    
    chatbot_display = gr.Chatbot(label="Chatbot History", height=500)
    with gr.Row():
        chat_input = gr.Textbox(
            label=None,
            placeholder="Type your message here...",
            show_label=False,
            scale=4
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)
        
    # Setup handlers
    chat_input.submit(
        fn=run_chat_interface,
        inputs=[chat_input, chatbot_display, profile_id_state, session_id_state],
        outputs=[chat_input, chatbot_display]
    )
    submit_btn.click(
        fn=run_chat_interface,
        inputs=[chat_input, chatbot_display, profile_id_state, session_id_state],
        outputs=[chat_input, chatbot_display]
    )
    
    # Load session and parameters on page load
    gradio_ui.load(
        fn=load_initial_params,
        inputs=None,
        outputs=[profile_id_state, session_id_state, chatbot_display]
    )

# Mount Gradio into FastAPI
app = gr.mount_gradio_app(fastapi_app, gradio_ui, path="/")

if __name__ == "__main__":
    import uvicorn
    # Start web server
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
